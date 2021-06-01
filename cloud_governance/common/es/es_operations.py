
import json
import os
import boto3
import tempfile
from datetime import datetime, timedelta
from time import strftime
import pandas as pd

from elasticsearch import Elasticsearch
from cloud_governance.common.aws.s3.s3_operations import S3Operations
from cloud_governance.common.aws.price.price import AWSPrice


class ESOperations:
    """
    This class related to ElasticSearch operations
    """

    def __init__(self, es_host: str, es_port: str,  region: str, bucket: str, logs_bucket_key: str):
        self.__es_host = es_host
        self.__es_port = es_port
        self.__region = region
        self.__s3_operation = S3Operations(region_name=self.__region)
        self.__bucket = bucket
        self.__logs_bucket_key = logs_bucket_key
        self.__es = Elasticsearch([{'host': self.__es_host, 'port': self.__es_port}])
        self.__aws_price = AWSPrice()
        self.__iam_client = boto3.client('iam', region_name=region)
        self.__trail_client = boto3.client('cloudtrail', region_name=region)

    def __get_s3_latest_policy_file(self, policy: str):
        """
        This method return latest policy logs
        @param policy:
        @return:
        """
        return self.__s3_operation.get_last_objects(bucket=self.__bucket,
                                                    logs_bucket_key=f'{self.__logs_bucket_key}/{self.__region}',
                                                    policy=policy)

    def __get_last_s3_policy_content(self, policy: str, file_name: str):
        """
        This method return last policy content
        @return:
        """
        with tempfile.TemporaryDirectory() as temp_local_directory:
            local_file = temp_local_directory + '/' + file_name + '.gz'
            if self.__get_s3_latest_policy_file(policy=policy):
                latest_policy_path = self.__get_s3_latest_policy_file(policy=policy)
                self.__s3_operation.download_file(bucket=self.__bucket,
                                           key=str(latest_policy_path),
                                           download_file=file_name + '.gz',
                                           file_name_path=local_file)
                # gzip
                os.system(f"gzip -d {local_file}")
                with open(os.path.join(temp_local_directory, file_name)) as f:
                    return f.read()

    def __get_user_from_trail_events(self, date_time):
        """
        This method find user name in cloud trail events according to date time
        @param date_time:
        @return:
        """
        diff = timedelta(seconds=1)
        end_date_time = date_time + diff
        try:
            response = self.__trail_client.lookup_events(
                StartTime=date_time,
                EndTime=end_date_time,
                MaxResults=123
            )
        except:
            return ''
        if response:
            for event in response['Events']:
                if event.get('Username'):
                    return event['Username']
        return ''

    def __get_cluster_user(self, clusters):
        """
        This method find cluster user according to cluster owned tag
        1. Scan each user and verify if it is a cluster, if yes return Creation time
        2. Scan in CloudTrail the Creation time and return the user
        """
        cluster_user = {}
        for cluster in cluster_user:
            cluster_user[cluster] = ''
        clusters_key = clusters.keys()
        cluster_create_date_dict = {}
        users = self.__iam_client.list_users()
        users_data = users['Users']
        for user in users_data:
            user_name = user['UserName']
            user_data = self.__iam_client.get_user(UserName=user_name)
            data = user_data['User']
            user_id = data['UserId']
            create_date = data['CreateDate']
            if data.get('Tags'):
                for tag in data['Tags']:
                    for cluster in clusters_key:
                        if tag['Key'].split() == cluster.split():
                            cluster_create_date_dict[cluster] = create_date
        for cluster, date_time in cluster_create_date_dict.items():
            user_name = self.__get_user_from_trail_events(date_time)
            cluster_user[cluster] = user_name
        return cluster_user

    def __get_cluster_cost(self, data, resource, clusters_launch_time):
        """
        This method aggregate cluster cost data
        @param data:
        @param resource:
        @param clusters_launch_time:
        @return:
        """
        clusters_user = self.__get_cluster_user(clusters=clusters_launch_time)
        # aggregate ec2/ebs cluster cost data
        resource_data = [item.split('|') for item in data['resources_list']]
        df = pd.DataFrame(resource_data)
        # MUST : every fix, change ec2/ebs title
        # cost column: remove space
        df[df.columns[1]] = df[df.columns[1]].str.strip()
        # cost column: change to float
        df[df.columns[1]] = df[df.columns[1]].astype(float).round(3)
        # group by cluster owned column
        cluster_cost = df.groupby(df.columns[-1])[df.columns[1]].sum()
        cluster_cost_results = []
        # cluster
        # title: cluster# | cost($) | user | launch time | cluster owned
        num = 1
        for name, cost in cluster_cost.items():
            if cost > 0:
                if name == '  ':
                    cluster_cost_results.append(f'non cluster | {round(cost, 3)} ')
                    data['non cluster'] = {'name': f'{resource} (non cluster)', 'cost': round(cost, 3)}
                else:
                    cluster_cost_results.append(f" cluster_{num} | {round(cost, 3)} | {clusters_user.get(name.strip())} | {clusters_launch_time.get(name.strip())} | {name.strip()} ")
                    data[f'cluster_{num}'] = {'name': name.strip(), 'cost': round(cost, 3), 'user': clusters_user.get(name.strip()), 'launch_time': clusters_launch_time.get(name.strip())}
                    num += 1
        return cluster_cost_results

    def __get_user_cost(self, data):
        """
        This method aggregate user cost data
        @param data:
        @param resource:
        @return:
        """
        # aggregate ec2/ebs cluster cost data
        resource_data = [item.split('|') for item in data['resources_list']]
        df = pd.DataFrame(resource_data)
        # MUST : every fix, change ec2/ebs title
        # cost column: remove space
        df[df.columns[1]] = df[df.columns[1]].str.strip()
        # cost column: change to float
        df[df.columns[1]] = df[df.columns[1]].astype(float).round(3)
        # group by user
        user_cost = df.groupby(df.columns[0])[df.columns[1]].sum()
        user_cost_results = []
        # user
        # title: user# | cost($) | user
        num = 1
        for user, cost in user_cost.items():
            if cost > 0 and user != '  ' and user:
                user_cost_results.append(f"user_{num} | {round(cost, 3)}  | {user.strip()} ")
                data[f'user_{num}'] = {'name': user.strip(), 'cost': round(cost, 3)}
                num += 1
        return user_cost_results

    def __get_resource_cost(self, resource: str, item_data: dict):
        """
        This method calculate ec2 cost from launch time or ebs per month in $
        @return:cluster_cost_results
        """
        if resource == 'ec2' and item_data['State']['Name'] == 'running':
            # Get current price for a given 'running' instance, region and os
            ec2_type_cost = '0'
            try:
                ec2_type_cost = self.__aws_price.get_price(self.__aws_price.get_region_name('us-east-1'),
                                                            item_data['InstanceType'], 'Linux')
            except:
                return 'NA'
            ec2_lanuch_time = item_data['LaunchTime']
            d1 = datetime.strptime(ec2_lanuch_time, "%Y-%m-%dT%H:%M:%S+00:00")
            d2 = datetime.strptime(strftime("%Y-%m-%dT%H:%M:%S+00:00"), "%Y-%m-%dT%H:%M:%S+00:00")
            diff = d2 - d1
            diff_in_hours = diff.total_seconds() / 3600
            ec2_cost = round(float(ec2_type_cost) * diff_in_hours, 3)
            return round(ec2_cost, 3)
        elif resource == 'ec2' and item_data['State']['Name'] != 'running':
            return '0'
        elif resource == 'ebs':
            ebs_monthly_cost = '0'
            if item_data['VolumeType'] == 'gp2':
                ebs_monthly_cost = 0.1 * item_data['Size']
            elif item_data['VolumeType'] == 'io1':
                ebs_monthly_cost = 0.125 * item_data['Size']
            else:
                ebs_monthly_cost = 0.1 * item_data['Size']
            return round(ebs_monthly_cost, 3)

    def upload_last_policy_to_es(self, policy: str, index: str, doc_type: str, s3_json_file: str, es_add_items: dict = None):
        """
        This method is upload json kubernetes cluster data into elasticsearch
        :param policy:
        :param s3_json_file:
        :param index:
        :param doc_type:
        :param es_add_items:
        :return:
        """
        resource = ''
        launch_time_format = ''
        # fetch data from s3 per region/policy
        data = self.__get_last_s3_policy_content(policy=policy, file_name=s3_json_file)
        if data:
            # cluster owned launch time
            clusters_launch_time_dict = {}
            # cluster owned user name
            cluster_user = {}
            data_list = json.loads(data)
            # if json folding in list need to extract it
            if type(data_list) == list:
                # resources_list is a list of items that was triggered by policy
                data_dict = {'resources_list': []}
                for i, item in enumerate(data_list):
                    ec2_ebs_name = ''
                    gitleaks_leakurl = ''
                    # cluster resource tag
                    cluster_owned = ''
                    # filter all data to save place
                    # data_dict[f'resource{i + 1}'] = item
                    # data_dict[f'resource_{i + 1}'] = 1
                    data_dict['resources'] = i + 1
                    # ec2/ebs
                    if item.get('Tags'):
                        for val in item['Tags']:
                            if val['Key'] == 'Name':
                                ec2_ebs_name = val['Value']
                            if val['Value'] == 'owned':
                                cluster_owned = val['Key']
                    # ec2 - MUST: every fix, change also cluster title
                    # title:  user | cost($) | state | instance type | launch time | name | instance id | cluster owned
                    if item.get('InstanceId'):
                        resource = 'ec2'
                        lt_datetime = datetime.strptime(item['LaunchTime'], '%Y-%m-%dT%H:%M:%S+00:00')
                        user = self.__get_user_from_trail_events(lt_datetime)
                        ec2_cost = self.__get_resource_cost(resource=resource, item_data=item)
                        launch_time_format = item['LaunchTime'][:-15].replace('T', ' ')
                        if cluster_owned:
                            clusters_launch_time_dict[cluster_owned] = launch_time_format
                            if not cluster_user.get(cluster_owned):
                                cluster_user = self.__get_cluster_user(clusters=clusters_launch_time_dict)
                            user = cluster_user.get(cluster_owned)
                        data_dict['resources_list'].append(f"{user} | {ec2_cost} | {item['State']['Name']} | {item['InstanceType']}  | {launch_time_format} | {ec2_ebs_name} | {item['InstanceId']} | {cluster_owned} ")

                    # ebs - MUST: every fix, change also cluster title
                    # title: user | cost($/month) | state | volume type | create time | size(gb) | name | volume id | cluster owned
                    if item.get('VolumeId'):
                        resource = 'ebs'
                        lt_datetime = datetime.strptime(item['CreateTime'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
                        user = self.__get_user_from_trail_events(lt_datetime)
                        ebs_monthly_cost = self.__get_resource_cost(resource=resource, item_data=item)
                        create_time_format = item['CreateTime'][:-22].replace('T', ' ')
                        if cluster_owned:
                            clusters_launch_time_dict[cluster_owned] = launch_time_format
                            if not cluster_user.get(cluster_owned):
                                cluster_user = self.__get_cluster_user(clusters=clusters_launch_time_dict)
                            user = cluster_user.get(cluster_owned)
                        data_dict['resources_list'].append(f"{user} | {ebs_monthly_cost} | {item['State']} | {item['VolumeType']} | {create_time_format} | {item['Size']} | {ec2_ebs_name} |  {item['VolumeId']} | {cluster_owned} ")
                    # gitleaks
                    if item.get('leakURL'):
                        gitleaks_leakurl = item.get('leakURL')
                    if item.get('email'):
                        data_dict['resources_list'].append(f"{item.get('email')} | {gitleaks_leakurl}")

                # get cluster cost data only for ec2 and ebs
                if resource:
                    cluster_cost_results = self.__get_cluster_cost(data=data_dict, resource=resource, clusters_launch_time=clusters_launch_time_dict)
                    data_dict['cluster_cost_data'] = cluster_cost_results
                    user_cost_results = self.__get_user_cost(data=data_dict)
                    data_dict['user_cost_data'] = user_cost_results
                data = data_dict
            elif type(data_list) == dict:
                data = data_list

        # no data for policy
        else:
            data = {'resources': 0}

        # Add items
        for key, value in es_add_items.items():
            data[key] = value

        # utcnow - solve timestamp issue
        data['timestamp'] = datetime.utcnow()  # datetime.now()

        # Upload data to elastic search server
        try:
            if isinstance(data, dict):  # JSON Object
                self.__es.index(index=index, doc_type=doc_type, body=data)
            else:  # JSON Array
                for record in data:
                    self.__es.index(index=index, doc_type=doc_type, body=record)
            return True
        except Exception:
            raise
