from typing import Callable

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_runners.common.abstract_policy_runner import AbstractPolicyRunner


class PolicyRunner(AbstractPolicyRunner):

    def execute_policy(self, policy_class_name: str, run_policy: Callable, upload: bool = False):
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
        response = run_policy().run()
        if isinstance(response, str):
            logger.info(response)
        else:
            logger.info(response)
            policy_result.extend(response)
            self._upload_elastic_search.upload(data=policy_result)
        return policy_result

    def __init__(self):
        super().__init__()
