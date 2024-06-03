
import importlib
import inspect

from typing import Callable

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_runners.aws.upload_s3 import UploadS3
from cloud_governance.policy.policy_runners.common.abstract_policy_runner import AbstractPolicyRunner


class PolicyRunner(AbstractPolicyRunner):

    def __init__(self):
        super().__init__()

    def execute_policy(self, policy_class_name: str, run_policy: Callable, upload: bool):
        """
        This method executes the policy
        :param policy_class_name:
        :type policy_class_name:
        :param run_policy:
        :type run_policy:
        :param upload:
        :type upload:
        :return:
        :rtype:
        """
        policy_result = []
        ec2_operations = EC2Operations()
        upload_to_s3 = UploadS3()
        active_regions = [self._region]
        if self._run_active_regions:
            active_regions = ec2_operations.get_active_regions()
            logger.info("Running the policy in All AWS active regions")
        for active_region in active_regions:
            logger.info(f"Running the {self._policy} in Region: {active_region}")
            self._environment_variables_dict['AWS_DEFAULT_REGION'] = active_region
            response = run_policy().run()
            if isinstance(response, str):
                logger.info(f'key: {policy_class_name}, Response: {response}')
            else:
                policy_result.extend(response)
                logger.info(f'key: {policy_class_name}, count: {len(response)}, {response}')
                if upload:
                    self._upload_elastic_search.upload(data=response)
                    upload_to_s3.upload(data=response)
        return policy_result
