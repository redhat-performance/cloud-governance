import json
from multiprocessing import Process

from cloud_governance.common.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations


class GenerateCostExplorerReport:

    def __init__(self, cost_tags: list, account: str, granularity: str = 'DAILY', es_host: str = '', es_port: str = '', es_index: str = '', cost_metric: str = 'UnblendedCost', file_name: str = '', start_date: str = '', end_date: str = ''):
        self.start_date = start_date
        self.end_date = end_date
        self.granularity = granularity
        self.cost_metric = cost_metric
        self.cost_tags = cost_tags
        self.__cost_explorer = CostExplorerOperations()
        self.file_name = file_name
        self.__es_host = es_host
        self.__es_port = es_port
        self.__es_index = es_index
        self.acconut = account
        self.__elastic_search_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port)

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
                name = name if name else f'{self.acconut}-REFUND'
            if group.get('Metrics'):
                amount = group.get('Metrics').get(self.cost_metric).get('Amount')
            if name and amount:
                data.append({tag: name, 'Cost': round(float(amount), 3)})
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
                    if self.__es_index == 'cloud-governance-cost-explorer-global':
                        if 'Budget' not in value:
                            value['Budget'] = self.acconut
                    file.write(f'{value}\n')
        else:
            for value in data:
                if self.__es_index == 'cloud-governance-cost-explorer-global':
                    if 'Budget' not in value:
                        value['Budget'] = self.acconut
                self.__elastic_search_operations.upload_to_elasticsearch(index=index, data=value)
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
            index = f'{self.__es_index}-{key.lower()}'
            p = Process(target=self.__upload_data, args=(values, index, ))
            p.start()
            jobs.append(p)
        for job in jobs:
            job.join()
