
import json
import os
import tempfile
from datetime import datetime
from time import strftime
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

    def __get_resource_cost(self, resource: str, item_data: dict):
        """
        This method calculate ec2 cost from launch time or ebs per month in $
        @return:
        """
        if resource == 'ec2' and item_data['State']['Name'] == 'running':
            # Get current price for a given 'running' instance, region and os
            ec2_type_cost = '0'
            try:
                # walk around for NA values in eu-central-1
                # if self.__region == 'eu-central-1':
                #     curr_region = 'us-east-1'
                # else:
                #     curr_region = self.__region
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
            return ec2_cost
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
            return ebs_monthly_cost

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
        # fetch data from s3 per region/policy
        data = self.__get_last_s3_policy_content(policy=policy, file_name=s3_json_file)
        if data:
            data_list = json.loads(data)
            # if json folding in list need to extract it
            if type(data_list) == list:
                # resources_list\resources_name_list is a list of ids\names that was triggered by policy
                data_dict = {'resources_list': [], 'resources_name_list': []}
                # resources_name_list is a list of resources name
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
                                data_dict['resources_name_list'].append(val['Value'])
                                ec2_ebs_name = val['Value']
                            if val['Value'] == 'owned':
                                cluster_owned = val['Key']
                    # ec2
                    # instance id | name | state | instance type | cost($) | cluster id
                    if item.get('InstanceId'):
                        ec2_cost = self.__get_resource_cost(resource='ec2', item_data=item)
                        data_dict['resources_list'].append(f"{item['InstanceId']} | {ec2_ebs_name} | {item['State']['Name']} | {item['InstanceType']} | {ec2_cost} | {cluster_owned} ")
                    # ebs
                    # volume id | name | volume type | size(gb) | cost($/month)
                    if item.get('VolumeId'):
                        ebs_monthly_cost = self.__get_resource_cost(resource='ebs', item_data=item)
                        data_dict['resources_list'].append(f"{item['VolumeId']} | {ec2_ebs_name} | {item['VolumeType']} | {item['Size']} | {ebs_monthly_cost}")
                    # gitleaks
                    if item.get('leakURL'):
                        gitleaks_leakurl = item.get('leakURL')
                    if item.get('email'):
                        data_dict['resources_list'].append(f"{item.get('email')} | {gitleaks_leakurl}")
                data = data_dict
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

