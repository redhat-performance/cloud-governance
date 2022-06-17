import json
from multiprocessing import Process

from cloud_governance.common.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations


class GenerateCostExplorerReport:

    def __init__(self, cost_tags: list, es_host: str = '', es_port: str = '', es_index: str = '', metric_type: str = 'BlendedCost', file_name: str = ''):
        self.cost_tags = cost_tags
        self.__cost_explorer = CostExplorerOperations()
        self.file_name = file_name
        self.__es_host = es_host
        self.__es_port = es_port
        self.__es_index = es_index
        self.__elastic_search_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)
        self.metric_type = metric_type

    def filter_data_by_tag(self, groups: list, tag: str):
        """
        This method extract data by tag
        @param tag:
        @param groups: Data from the cloud explorer
        @return: converted into dict format
        """
        data = []
        for group in groups:
            name = ''
            amount = ''
            if group.get('Keys'):
                name = group.get('Keys')[0].split('$')[-1]
                name = name if name else 'NoTagKey'
            if group.get('Metrics'):
                amount = group.get('Metrics').get(self.metric_type).get('Amount')
            if name and amount:
                data.append({tag: name, 'Cost': round(float(amount), 3)})
        return data

    def __get_daily_cost_by_tags(self):
        """
        This method extracts the costs by tags and upload to elastic search
        @return:
        """
        if not self.metric_type:
            self.metric_type = 'BlendedCost'
        data_house = {}
        for tag in self.cost_tags:
            response = self.__cost_explorer.get_daily_cost_usage(tag=tag, metrics_type=self.metric_type)
            results_by_time = response.get('ResultsByTime')
            if results_by_time:
                data_house[tag] = self.filter_data_by_tag(results_by_time[0].get('Groups'), tag)
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
                    file.write(f'{value}\n')
        else:
            for value in data:
                self.__elastic_search_operations.upload_to_elasticsearch(index=index, data=value)
        logger.info(f'Data uploaded to {index}')

    def upload_tags_cost_to_elastic_search(self):
        """
        This method upload daily tag cost into ElasticSearch
        @return:
        """
        cost_data = self.__get_daily_cost_by_tags()
        jobs = []
        for key, values in cost_data.items():
            index = f'{self.__es_index}-{key.lower()}'
            p = Process(target=self.__upload_data, args=(values, index, ))
            p.start()
            jobs.append(p)
        for job in jobs:
            job.join()
