import importlib
import inspect

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.non_cluster_zombie_policy import NonClusterZombiePolicy


class CustomPolicies(NonClusterZombiePolicy):

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method run the custom policy class
        @return:
        """
        logger.info(f'account={self._account}, region={self._region}, policy={self._custom_policy}, dry_run={self._dry_run}')
        custom_policy_module = importlib.import_module(f'cloud_governance.policy.{self._custom_policy}')

        for cls in inspect.getmembers(custom_policy_module, inspect.isclass):
            if self._custom_policy.replace('_', '') == cls[0].lower():
                response = cls[1]().run()
                logger.info(f'key: {cls[0]}, count: {len(response)}, {response}')
                if self._policy_output:
                    beautify_data = self._beautify_upload_data(upload_resource_data=response)
                    policy_result = {'count': len(beautify_data), self._custom_policy: beautify_data }
                    logger.info(policy_result)
                    self._s3operations.save_results_to_s3(policy=self._custom_policy.replace('_', '-'), policy_output=self._policy_output, policy_result=policy_result)
