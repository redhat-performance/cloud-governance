import datetime
import os
from multiprocessing import Process

import numpy as np
import pandas as pd

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.common.logger.init_logger import logger


class CostExplorer(ElasticUpload):
    """
    This class fetches the cost_explorer report from the AWS based on two days ago data and upload to ElasticSearch.
    fetching AWS cost explorer of two days ago because day ago cost calculation is not closed.
    """

    def __init__(self):
        super().__init__()
        self.start_date = os.environ.get('start_date', '')  # yyyy-mm-dd
        self.end_date = os.environ.get('end_date', '')  # yyyy-mm-dd
        self.granularity = os.environ.get('granularity', 'DAILY')
        self.cost_metric = os.environ.get('cost_metric', 'UnblendedCost')
        self.cost_tags = self._literal_eval(os.environ.get('cost_explorer_tags', '{}'))
        self.file_name = os.environ.get('file_name', '')
        self.__cost_explorer = CostExplorerOperations()
        self._ec2_operations = EC2Operations()

    def get_user_resources(self):
        """
        This method get User all region ec2 instances
        @return:
        """
        ec2_global_list_user_resources = self._ec2_operations.get_global_ec2_list_by_user()
        return ec2_global_list_user_resources

    def filter_data_by_tag(self, groups: list, tag: str):
        """
        This method extract data by tag
        @param tag:
        @param groups: Data from the cloud explorer
        @return: converted into dict format
        """
        data = []
        user_resources = []
        if tag == 'User':
            user_resources = self.get_user_resources()
        for group in groups:
            name = ''
            amount = ''
            if group.get('Keys'):
                name = group.get('Keys')[0].split('$')[-1]
                name = name if name else f'{self.account}-REFUND'
            if group.get('Metrics'):
                amount = group.get('Metrics').get(self.cost_metric).get('Amount')
            if name and amount:
                upload_data = {tag: name, 'Cost': round(float(amount), 3)}
                if user_resources and name in user_resources:
                    upload_data['Instances'] = user_resources[name]
                upload_data['timestamp'] = datetime.datetime.utcnow() - datetime.timedelta(2)
                data.append(upload_data)
        return data

    def __get_daily_cost_by_tags(self):
        """
        This method extracts the costs by tags and upload to elastic search
        @return:
        """
        data_house = {}
        for tag in self.cost_tags:
            if self.start_date and self.end_date:
                response = self.__cost_explorer.get_cost_by_tags(tag=tag, start_date=self.start_date, end_date=self.end_date, granularity=self.granularity, cost_metric=self.cost_metric)
            else:
                response = self.__cost_explorer.get_cost_by_tags(tag=tag, granularity=self.granularity, cost_metric=self.cost_metric)
            results_by_time = response.get('ResultsByTime')
            if results_by_time:
                data_house[tag] = []
                for result in results_by_time:
                    data_house[tag].extend(self.filter_data_by_tag(result.get('Groups'), tag))
        return data_house

    def __upload_data(self, data: list, index: str):
        """
        This method upload to elastic search
        @param data:
        @param index:
        @return:
        """
        if self.file_name:
            with open(f'/tmp/{self.file_name}', 'a') as file:
                for value in data:
                    if self._es_index == 'cloud-governance-cost-explorer-global':
                        if 'Budget' not in value:
                            value['Budget'] = self.account
                    file.write(f'{value}\n')
        else:
            for value in data:
                if self._es_index == 'cloud-governance-cost-explorer-global':
                    if 'Budget' not in value:
                        value['Budget'] = self.account
                self._elastic_search_operations.upload_to_elasticsearch(index=index, data=value)
        logger.info(f'Data uploaded to {index}')

    def upload_tags_cost_to_elastic_search(self):
        """
        This method upload daily tag cost into ElasticSearch
        @return:
        """
        logger.info(f'Get {self.granularity} Cost usage by metric: {self.cost_metric}')
        cost_data = self.__get_daily_cost_by_tags()
        jobs = []
        for key, values in cost_data.items():
            index = f'{self._es_index}-{key.lower()}'
            p = Process(target=self.__upload_data, args=(values, index, ))
            p.start()
            jobs.append(p)
        for job in jobs:
            job.join()

    def run(self):
        """
        This method run the operations
        @return:
        """
        self.upload_tags_cost_to_elastic_search()
