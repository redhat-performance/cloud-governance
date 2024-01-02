from abc import ABC, abstractmethod
from datetime import datetime

from cloud_governance.common.elasticsearch.elastic_upload import ElasticUpload
from cloud_governance.main.environment_variables import environment_variables


class AbstractInstanceRun(ABC):

    INSTANCE_TYPES_ES_INDEX = 'cloud-governance-instance-types'
    RESOURCE_ACTION = "Stopped"

    def __init__(self):
        self.__es_upload = ElasticUpload()
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__account = self.__environment_variables_dict.get('account').upper().replace('OPENSHIFT-', '')
        self.__cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME')
        super().__init__()

    def _upload_instance_type_count_to_elastic_search(self):
        """
        This method uploads the data to elasticsearch
        :return:
        :rtype:
        """
        instance_types = self._update_instance_type_count()
        account = self.__account
        current_day = datetime.utcnow()
        es_instance_types_data = []
        for region, instance_types in instance_types.items():
            for instance_type, instance_type_count in instance_types.items():
                es_instance_types_data.append({
                    'instance_type': instance_type,
                    'instance_count': instance_type_count,
                    'timestamp': current_day,
                    'region': region,
                    'account': account,
                    'PublicCloud': self.__cloud_name,
                    'index_id': f'{instance_type}-{self.__cloud_name.lower()}-{account.lower()}-{region}-{str(current_day.date())}'
                })
        self.__es_upload.es_upload_data(items=es_instance_types_data, es_index=self.INSTANCE_TYPES_ES_INDEX,
                                        set_index='index_id')

    def _get_es_data_schema_format(self, resource_id: str, user: str, skip_policy: str, launch_time: datetime,
                                   instance_type: str, instance_state: str, running_days: int, cleanup_days: int,
                                   dry_run: str, name: str, region: str, cleanup_result: str, cloud_name: str):
        """
        This method returns the schema of the es
        :return:
        :rtype:
        """
        current_date = datetime.utcnow().date()
        return {
            'ResourceId': resource_id,
            'User': user,
            'SkipPolicy': skip_policy,
            'LaunchTime': launch_time,
            'InstanceType': instance_type,
            'InstanceState': instance_state,
            'RunningDays': running_days,
            'CleanUpDays': cleanup_days,
            'DryRun': dry_run,
            'Name': name,
            'RegionName': region,
            f'Resource{self.RESOURCE_ACTION}': cleanup_result,
            'PublicCloud': cloud_name,
            'index-id': f'{current_date}-{cloud_name.lower()}-{self.__account.lower()}-{region.lower()}-{resource_id}-{instance_state.lower()}'
        }

    @abstractmethod
    def _update_instance_type_count(self):
        """
        This method updates the instance type count to the elasticsearch
        :return: { region: { instance_type: count } }
        :rtype: dict
        """
        raise NotImplementedError("This method not yet implemented")

    @abstractmethod
    def _instance_run(self):
        """
        This method returns  the running instances and upload to elastic_search
        :return:
        :rtype:
        """
        raise NotImplementedError("This method not yet implemented")

    def run(self):
        """
        This method starts the instance run operations
        :return:
        :rtype:
        """
        self._upload_instance_type_count_to_elastic_search()
        return self._instance_run()
