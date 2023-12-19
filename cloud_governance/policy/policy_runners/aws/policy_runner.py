
import importlib
import inspect

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_runners.aws.upload_s3 import UploadS3
from cloud_governance.policy.policy_runners.common.abstract_policy_runner import AbstractPolicyRunner


class PolicyRunner(AbstractPolicyRunner):

    def __init__(self):
        super().__init__()

    def run(self, source: str = "", upload: bool = True):
        """
        This method run the AWS policies classes
        :param upload:
        :type upload:
        :param source:
        :type source:
        :return:
        :rtype:
        """
        source_policy = f"{source}.{self._policy}" if source else self._policy
        logger.info(f'account={self._account}, policy={self._policy}, dry_run={self._dry_run}')
        zombie_non_cluster_policy_module = importlib.import_module(f'cloud_governance.policy.aws.{source_policy}')

        policy_result = []
        ec2_operations = EC2Operations()
        upload_to_s3 = UploadS3()
        for cls in inspect.getmembers(zombie_non_cluster_policy_module, inspect.isclass):
            if self._policy.replace('_', '').replace('-', '') == cls[0].lower():
                active_regions = [self._region]
                if self._run_active_regions:
                    active_regions = ec2_operations.get_active_regions()
                    logger.info("Running the policy in All AWS active regions")
                for active_region in active_regions:
                    logger.info(f"Running the {self._policy} in Region: {active_region}")
                    self._environment_variables_dict['AWS_DEFAULT_REGION'] = active_region
                    response = cls[1]().run()
                    if isinstance(response, str):
                        logger.info(f'key: {cls[0]}, Response: {response}')
                    else:
                        policy_result.extend(response)
                        logger.info(f'key: {cls[0]}, count: {len(response)}, {response}')
                        if upload:
                            self._upload_elastic_search.upload(data=response)
                            upload_to_s3.upload(data=response)
        if self._save_to_file_path:
            self.write_to_file(data=policy_result)
