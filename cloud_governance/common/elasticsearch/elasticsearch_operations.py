import json
import os
import boto3
import tempfile
from datetime import datetime, timedelta
from time import strftime
import time
import pandas as pd

from elasticsearch_dsl import Search
from elasticsearch import Elasticsearch
from typeguard import typechecked

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.clouds.aws.price.price import AWSPrice
from cloud_governance.common.elasticsearch.elasticsearch_exceptions import ElasticSearchDataNotUploaded
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp, logger


class ElasticSearchOperations:
    """
    This class related to ElasticSearch operations
    """

    # sleep time between checks is 10 sec
    SLEEP_TIME = 10
    # ElasticSearch fetch data of last 15 minutes
    ES_FETCH_MIN_TIME = 15
    # max search results
    MAX_SEARCH_RESULTS = 1000
    MIN_SEARCH_RESULTS = 100

    def __init__(self, es_host: str, es_port: str, region: str = '', bucket: str = '', logs_bucket_key: str = '',
                 timeout: int = 2000):
        self.__es_host = es_host
        self.__es_port = es_port
        self.__region = region
        self.__timeout = timeout
        self.__es = Elasticsearch([{'host': self.__es_host, 'port': self.__es_port}])
        if region:
            self.__s3_operation = S3Operations(region_name=self.__region)
            self.__bucket = bucket
            self.__logs_bucket_key = logs_bucket_key
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
        @param resource:
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
                    # title:  instance id | user | cost($) | state | instance type | launch time | name | cluster owned
                    if item.get('InstanceId'):
                        resource = 'ec2'
                        lt_datetime = datetime.strptime(item['LaunchTime'], '%Y-%m-%dT%H:%M:%S+00:00')
                        user = self.__get_user_from_trail_events(lt_datetime)
                        ec2_cost = self.__aws_price.get_ec2_price(resource=resource, item_data=item)
                        launch_time_format = item['LaunchTime'][:-15].replace('T', ' ')
                        if cluster_owned:
                            clusters_launch_time_dict[cluster_owned] = launch_time_format
                            if not cluster_user.get(cluster_owned):
                                cluster_user = self.__get_cluster_user(clusters=clusters_launch_time_dict)
                            user = cluster_user.get(cluster_owned)
                        data_dict['resources_list'].append(
                            f"{item['InstanceId']} | {user} | {ec2_cost} | {item['State']['Name']} | {item['InstanceType']}  | {launch_time_format} | {ec2_ebs_name} | {cluster_owned} ")

                    # ebs - MUST: every fix, change also cluster title
                    # title: volume id | user | cost($/month) | state | volume type | create time | size(gb) | name |  cluster owned
                    if item.get('VolumeId'):
                        resource = 'ebs'
                        lt_datetime = datetime.strptime(item['CreateTime'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
                        user = self.__get_user_from_trail_events(lt_datetime)
                        ebs_monthly_cost = self.__aws_price.get_ec2_price(resource=resource, item_data=item)
                        create_time_format = item['CreateTime'][:-22].replace('T', ' ')
                        if cluster_owned:
                            clusters_launch_time_dict[cluster_owned] = launch_time_format
                            if not cluster_user.get(cluster_owned):
                                cluster_user = self.__get_cluster_user(clusters=clusters_launch_time_dict)
                            user = cluster_user.get(cluster_owned)
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
                                                                   clusters_launch_time=clusters_launch_time_dict)
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

    def __elasticsearch_get_index_hits(self, index: str, uuid: str = '', workload: str = '', fast_check: bool = False,
                                       id: bool = False):
        """
        This method search for data per index in last 2 minutes and return the number of docs or zero
        :param index:
        :param workload: need only if there is different timestamp parameter in Elasticsearch
        :param id: True to return the doc ids
        :param fast_check: return fast response
        :return:
        """
        """
        :return:
        """
        ids = []
        # https://github.com/elastic/elasticsearch-dsl-py/issues/49
        self.__es.indices.refresh(index=index)
        # timestamp name in Elasticsearch is different
        search = Search(using=self.__es, index=index).filter('range', timestamp={
            'gte': f'now-{self.ES_FETCH_MIN_TIME}m', 'lt': 'now'})
        # reduce the search result
        if fast_check:
            search = search[0:self.MIN_SEARCH_RESULTS]
        else:
            search = search[0:self.MAX_SEARCH_RESULTS]
        search_response = search.execute()
        if search_response.hits:
            if uuid:
                count_hits = 0
                for row in search_response:
                    if type(row['uuid']) == str:
                        # uperf return str
                        current_uuid = row['uuid']
                    else:
                        current_uuid = row['uuid'][0]
                    if current_uuid == uuid:
                        if fast_check:
                            return 1
                        ids.append(row.meta.id)
                        count_hits += 1
                if id:
                    return ids
                else:
                    return count_hits
            else:
                return len(search_response.hits)
        else:
            return 0

    @typechecked()
    @logger_time_stamp
    def verify_elasticsearch_data_uploaded(self, index: str, uuid: str = '', workload: str = '',
                                           fast_check: bool = False):
        """
        The method wait till data upload to elastic search and wait if there is new data, search in last 15 minutes
        :param index:
        :param uuid: the current workload uuid
        :param workload: workload name only if there is a different timestamp parameter name in elasticsearch
        :param fast_check: return response on first doc
        :return:
        """
        current_wait_time = 0
        current_hits = 0
        # waiting for any hits
        while current_wait_time <= self.__timeout:
            # waiting for new hits
            new_hits = self.__elasticsearch_get_index_hits(index=index, uuid=uuid, workload=workload,
                                                           fast_check=fast_check)
            if current_hits < new_hits:
                logger.info(f'Data with index: {index} and uuid={uuid} was uploaded to ElasticSearch successfully')
                return self.__elasticsearch_get_index_hits(index=index, uuid=uuid, workload=workload, id=True,
                                                           fast_check=fast_check)
            # sleep for x seconds
            time.sleep(self.SLEEP_TIME)
            current_wait_time += self.SLEEP_TIME
        raise ElasticSearchDataNotUploaded

    @typechecked()
    def upload_to_elasticsearch(self, index: str, data: dict, doc_type: str = '_doc', es_add_items: dict = None):
        """
        This method is upload json data into elasticsearch
        :param index: index name to be stored in elasticsearch
        :param data: data must me in dictionary i.e. {'key': 'value'}
        :param doc_type:
        :param es_add_items:
        :return:
        """
        # read json to dict
        json_path = ""

        # Add items
        if es_add_items:
            for key, value in es_add_items.items():
                data[key] = value

        # utcnow - solve timestamp issue
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow()  # datetime.now()

        # Upload data to elastic search server
        try:
            if isinstance(data, dict):  # JSON Object
                self.__es.index(index=index, doc_type=doc_type, body=data)
            else:  # JSON Array
                for record in data:
                    self.__es.index(index=index, doc_type=doc_type, body=record)
            return True
        except Exception as err:
            raise err

    @typechecked()
    def update_elasticsearch_index(self, index: str, id: str, metadata: dict = ''):
        """
        This method update existing index
        :param index: index name
        :param id: The specific index id
        :param metadata: The metadata for enrich that existing index according to id
        :return:
        """
        self.__es.update(index=index, id=id, body={"doc": metadata})

    @typechecked()
    @logger_time_stamp
    def get_elasticsearch_index_by_id(self, index: str, id: str):
        """
        This method return elastic search index data by id
        :param index: index name
        :param id: The specific index id
        :return:
        """
        return self.__es.get(index=index, id=id)

    @typechecked()
    @logger_time_stamp
    def get_index_hits(self, days: int, index: str):
        """
        This method return the last days data from elastic search
        @param days:
        @param index:
        @return:
        """
        search = Search(using=self.__es, index=index).filter('range', timestamp={'gte': f'now-{days}d', 'lt': 'now'})
        search = search[0:self.MAX_SEARCH_RESULTS]
        search_response = search.execute()
        df = pd.DataFrame()
        for row in search_response:
            df = pd.concat([df, pd.DataFrame([row.to_dict()])], ignore_index=True).fillna({})
        return df.to_dict('records')

    @typechecked()
    @logger_time_stamp
    def clear_data_in_es(self, es_index: str):
        """
        This method clears index data in elastic search
        @param es_index: index_name
        @return:
        """
        if self.__es.indices.exists(index=es_index):
            return self.__es.indices.delete(index=es_index)
