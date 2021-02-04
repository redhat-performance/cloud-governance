import json
import os
import tempfile
from datetime import datetime
from cloud_governance.common.aws.s3.s3_operations import S3Operations
from elasticsearch import Elasticsearch

es_host = 'localhost'
es_port = 9200


class ElkOperations:
    """
    This class related to elk operations
    """

    def __init__(self, region='us-east-2', policy_bucket='redhat-cloud-governance', logs_dir='logs'):
        self.__s3_operation = S3Operations(region_name=region)
        self.__policy_bucket = policy_bucket
        self.__logs_dir = logs_dir
        self.es = Elasticsearch([{'host': es_host, 'port': es_port}])

    def __get_s3_latest_policy_file(self, policy: str, region: str):
        """
        This method return latest policy logs
        @param policy:
        @return:
        """
        return self.__s3_operation.get_last_objects(bucket=self.__policy_bucket,
                                                    logs_dir=f'{self.__logs_dir}/{region}',
                                                    policy=policy)

    def __get_last_s3_policy_content(self, policy: str, region: str, file_name: str = 'resources.json'):
        """
        This method return last policy content
        @return:
        """
        with tempfile.TemporaryDirectory() as temp_local_directory:
            local_file = temp_local_directory + '/' + file_name + '.gz'
            if self.__get_s3_latest_policy_file(policy=policy, region=region):
                latest_policy_path = self.__get_s3_latest_policy_file(policy=policy, region=region)
                self.__s3_operation.download_file(bucket=self.__policy_bucket,
                                           key=str(latest_policy_path),
                                           download_file=file_name + '.gz',
                                           file_name_path=local_file)
                # gzip
                os.system(f"gzip -d {local_file}")
                with open(os.path.join(temp_local_directory, file_name)) as f:
                    return f.read()

    def upload_last_policy_to_es(self, policy: str, region: str, index: str, doc_type: str, json_file: str = 'resources.json', add_items: dict = None):
        """
        This method is upload json kubernetes cluster data into elasticsearch
        :param policy:
        :param region:
        :param json_file:
        :param index:
        :param doc_type:
        :param add_items:
        :return:
        """

        # fetch data from s3 per region/policy
        data = self.__get_last_s3_policy_content(policy=policy, region=region, file_name=json_file)
        if data:
            data_list = json.loads(data)
            # if json folding in list need to extract it
            if type(data_list) == list:
                data_dict = {}
                for i, item in enumerate(data_list):
                    data_dict[f'resource{i + 1}'] = item
                    data_dict[f'resource_{i + 1}'] = 1
                    data_dict['resources'] = i + 1
                data = data_dict
        # no data for policy
        else:
            data = {'resources': 0}

        # Add items
        for key, value in add_items.items():
            data[key] = value

        # utcnow - solve timestamp issue
        data['timestamp'] = datetime.utcnow()  # datetime.now()

        # Upload data to elastic search server
        try:
            if isinstance(data, dict):  # JSON Object
                self.es.index(index=index, doc_type=doc_type, body=data)
            else:  # JSON Array
                for record in data:
                    self.es.index(index=index, doc_type=doc_type, body=record)
            return True
        except Exception:
            raise

