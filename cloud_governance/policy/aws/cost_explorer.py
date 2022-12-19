import datetime
from ast import literal_eval
from multiprocessing import Process

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.main.environment_variables import environment_variables


class CostExplorer:
    """
    This class fetches the cost_explorer report from the AWS based on two days ago data and upload to ElasticSearch.
    fetching AWS cost explorer of two days ago because day ago cost calculation is not closed.
    """

    def __init__(self):
        super().__init__()
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.start_date = self.__environment_variables_dict.get('start_date', '')  # yyyy-mm-dd
        self.end_date = self.__environment_variables_dict.get('end_date', '')  # yyyy-mm-dd
        self.granularity = self.__environment_variables_dict.get('granularity', 'DAILY')
        self.cost_metric = self.__environment_variables_dict.get('cost_metric', 'UnblendedCost')
        self.cost_tags = literal_eval(self.__environment_variables_dict.get('cost_explorer_tags', '{}'))
        self.file_name = self.__environment_variables_dict.get('file_name', '')
        self.__cost_explorer = CostExplorerOperations()
        self.region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-1')
        self._ec2_operations = EC2Operations(region=self.region)
        self._elastic_upload = ElasticUpload()
        self.__account = self.__environment_variables_dict.get('account')

    def get_user_resources(self):
        """
        This method get User all region ec2 instances
        @return:
        """
        ec2_global_list_user_resources = self._ec2_operations.get_global_ec2_list_by_user()
        return ec2_global_list_user_resources

    def filter_data_by_tag(self, groups: dict, tag: str):
        """
        This method extract data by tag
        @param tag:
        @param groups: Data from the cloud explorer
        @return: converted into dict format
        """
        data = {}
        user_resources = []
        start_time = groups.get('TimePeriod').get('Start')
        account = self.__account
        if tag == 'User':
            user_resources = self.get_user_resources()
        for group in groups.get('Groups'):
            name = ''
            amount = ''
            if group.get('Keys'):
                name = group.get('Keys')[0].split('$')[-1]
                name = name if name else f'{self._elastic_upload.account}-REFUND'
            if group.get('Metrics'):
                amount = group.get('Metrics').get(self.cost_metric).get('Amount')
            if name and amount:
                if 'aws-go-sdk' in name:
                    name = 'aws-go-sdk'
                else:
                    if 'vm_import_image' in name:
                        name = 'vm_import_image'
                index_id = f'{start_time.lower()}-{account.lower()}-{tag.lower()}-{name.lower()}'
                if index_id not in data:
                    upload_data = {tag: name.upper(), 'Cost': round(float(amount), 3), 'index_id': index_id}
                    if user_resources and name in user_resources:
                        upload_data['Instances'] = user_resources[name]
                    upload_data['timestamp'] = start_time
                    data[index_id] = upload_data
                else:
                    data[index_id]['Cost'] += round(float(amount), 3)
        return list(data.values())

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
                    data_house[tag].extend(self.filter_data_by_tag(result, tag))
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
                    if self._elastic_upload.es_index == 'cloud-governance-cost-explorer-global':
                        if 'Budget' not in value:
                            value['Budget'] = self._elastic_upload.account
                    file.write(f'{value}\n')
        else:
            for value in data:
                if self._elastic_upload.es_index == 'cloud-governance-cost-explorer-global':
                    if 'Budget' not in value:
                        value['Budget'] = self._elastic_upload.account
                self._elastic_upload.elastic_search_operations.upload_to_elasticsearch(index=index, data=value, id=value['index_id'])
        logger.info(f'Data uploaded to {index}, Total Data: {len(data)}')

    def upload_tags_cost_to_elastic_search(self):
        """
        This method upload daily tag cost into ElasticSearch
        @return:
        """
        logger.info(f'Get {self.granularity} Cost usage by metric: {self.cost_metric}')
        cost_data = self.__get_daily_cost_by_tags()
        jobs = []
        for key, values in cost_data.items():
            index = f'{self._elastic_upload.es_index}-{key.lower()}'
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
