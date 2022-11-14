import json
from datetime import datetime
import pandas as pd

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.clouds.aws.price.price import AWSPrice


class ESUploader:
    """
    This class upload data to elastic search from s3 bucket
    """

    def __init__(self, **kwargs):
        self.__es_host = kwargs.get('es_host')
        self.__es_port = kwargs.get('es_port')
        self.__es_index = kwargs.get('es_index')
        self.__es_doc_type = kwargs.get('es_doc_type')
        self.__es_add_items = kwargs.get('es_add_items')
        self.__bucket_name = kwargs.get('bucket')
        self.__s3_file_name = kwargs.get('s3_file_name')
        self.__logs_bucket_key = kwargs.get('logs_bucket_key')
        self.__region_name = kwargs.get('region')
        self.__policy_name = kwargs.get('policy')
        self.es_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port,
                                                     region=self.__region_name, bucket=self.__bucket_name,
                                                     logs_bucket_key=self.__logs_bucket_key)
        if self.__region_name:
            self.__s3_operation = S3Operations(region_name=self.__region_name, bucket=self.__bucket_name,
                                               logs_bucket_key=self.__logs_bucket_key)
            self.__aws_price = AWSPrice()

    def __get_cluster_cost(self, data, resource, clusters_launch_time, clusters_user):
        """
        This method aggregate cluster cost data
        @param data:
        @param resource:
        @param clusters_user:
        @return:
        """
        # aggregate ec2/ebs cluster cost data
        resource_data = [item.split('|') for item in data['resources_list']]
        df = pd.DataFrame(resource_data)
        # MUST : every fix, change ec2/ebs title
        # cost column: remove space
        df[df.columns[2]] = df[df.columns[2]].str.strip()
        # cost column: change to float
        df[df.columns[2]] = df[df.columns[2]].astype(float).round(3)
        # group by cluster owned column
        cluster_cost = df.groupby(df.columns[-1])[df.columns[2]].sum()
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
                    cluster_cost_results.append(
                        f" cluster_{num} | {round(cost, 3)} | {clusters_user.get(name.strip())} | {clusters_launch_time.get(name.strip())} | {name.strip()} ")
                    data[f'cluster_{num}'] = {'name': name.strip(), 'cost': round(cost, 3),
                                              'user': clusters_user.get(name.strip()),
                                              'launch_time': clusters_launch_time.get(name.strip())}
                    num += 1
        return cluster_cost_results

    def __get_user_cost(self, data):
        """
        This method aggregate user cost data
        @param data:
        @return:
        """
        # aggregate ec2/ebs cluster cost data
        resource_data = [item.split('|') for item in data['resources_list']]
        df = pd.DataFrame(resource_data)
        # MUST : every fix, change ec2/ebs title
        # cost column: remove space
        df[df.columns[2]] = df[df.columns[2]].str.strip()
        # cost column: change to float
        df[df.columns[2]] = df[df.columns[2]].astype(float).round(3)
        # group by user
        user_cost = df.groupby(df.columns[1])[df.columns[2]].sum()
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

    def upload_last_policy_to_elasticsearch(self, policy: str, index: str, doc_type: str, s3_json_file: str,
                                            es_add_items: dict = None):
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
        data = self.__s3_operation.get_last_s3_policy_content(policy=policy, file_name=s3_json_file)
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
                    user = ''
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
                            if val['Key'].lower() == 'user':
                                user = val['Value'].lower()
                    if cluster_owned:
                        cluster_user[cluster_owned] = user
                    # ec2 - MUST: every fix, change also cluster title
                    # title:  instance id | user | cost($) | state | instance type | launch time | name | cluster owned
                    if item.get('InstanceId'):
                        resource = 'ec2'
                        # lt_datetime = datetime.strptime(item['LaunchTime'], '%Y-%m-%dT%H:%M:%S+00:00')
                        ec2_cost = self.__aws_price.get_ec2_price(resource=resource, item_data=item)
                        launch_time_format = item['LaunchTime'][:-15].replace('T', ' ')
                        if cluster_owned:
                            clusters_launch_time_dict[cluster_owned] = launch_time_format
                        data_dict['resources_list'].append(
                            f"{item['InstanceId']} | {user} | {ec2_cost} | {item['State']['Name']} | {item['InstanceType']}  | {launch_time_format} | {ec2_ebs_name} | {cluster_owned} ")

                    # ebs - MUST: every fix, change also cluster title
                    # title: volume id | user | cost($/month) | state | volume type | create time | size(gb) | name |  cluster owned
                    if item.get('VolumeId'):
                        resource = 'ebs'
                        ebs_monthly_cost = self.__aws_price.get_ec2_price(resource=resource, item_data=item)
                        create_time_format = item['CreateTime'][:-22].replace('T', ' ')
                        if cluster_owned:
                            clusters_launch_time_dict[cluster_owned] = create_time_format
                        data_dict['resources_list'].append(
                            f"{item['VolumeId']} | {user} | {ebs_monthly_cost} | {item['State']} | {item['VolumeType']} | {create_time_format} | {item['Size']} | {ec2_ebs_name} |  {cluster_owned} ")
                    # gitleaks
                    if item.get('leakURL'):
                        gitleaks_leakurl = item.get('leakURL')
                    if item.get('email'):
                        data_dict['resources_list'].append(f"{item.get('email')} | {gitleaks_leakurl}")

                # get cluster cost data only for ec2 and ebs
                if resource:
                    cluster_cost_results = self.__get_cluster_cost(data=data_dict, resource=resource,
                                                                   clusters_launch_time=clusters_launch_time_dict,
                                                                   clusters_user=cluster_user)
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
                self.es_operations.upload_to_elasticsearch(index=index, data=data)
            else:  # JSON Array
                for record in data:
                    self.es_operations.upload_to_elasticsearch(index=index, data=record)
            return True
        except Exception:
            raise

    @logger_time_stamp
    def upload_to_es(self, account):
        """
        This method upload data to input ELK
        """
        self.__es_add_items.update({'policy': self.__policy_name, 'region': self.__region_name})
        self.upload_last_policy_to_elasticsearch(policy=self.__policy_name, index=self.__es_index,
                                                 doc_type=self.__es_doc_type, s3_json_file=self.__s3_file_name,
                                                 es_add_items=self.__es_add_items)
