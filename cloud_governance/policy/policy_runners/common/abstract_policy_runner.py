from abc import abstractmethod, ABC

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_runners.aws.upload_s3 import UploadS3
from cloud_governance.policy.policy_runners.elasticsearch.upload_elastic_search import UploadElasticSearch


class AbstractPolicyRunner(ABC):

    def __init__(self):
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._policy = self._environment_variables_dict.get('policy', '')
        self._account = self._environment_variables_dict.get('account', '')
        self._dry_run = self._environment_variables_dict.get('dry_run', 'yes')
        self._region = self._environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-2')
        self._run_active_regions = self._environment_variables_dict.get('RUN_ACTIVE_REGIONS')
        self._upload_to_s3 = UploadS3()
        self._upload_elastic_search = UploadElasticSearch()

    @abstractmethod
    def run(self):
        raise NotImplementedError("This method is not yet implemented")
