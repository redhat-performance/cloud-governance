import importlib
import inspect

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieNonClusterPolicies(NonClusterZombiePolicy):

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method run the zombie non-cluster policies class
        @return:
        """
        logger.info(f'account={self._account}, region={self._region}, policy={self._policy}, dry_run={self._dry_run}')
        zombie_non_cluster_policy_module = importlib.import_module(f'cloud_governance.policy.{self._policy}')

        for cls in inspect.getmembers(zombie_non_cluster_policy_module, inspect.isclass):
            if self._policy.replace('_', '') == cls[0].lower():
                response = cls[1]().run()
                logger.info(f'key: {cls[0]}, count: {len(response)}, {response}')
                if self._policy_output:
                    beautify_data = self._beautify_upload_data(upload_resource_data=response)
                    policy_result = {'count': len(beautify_data), self._policy: beautify_data }
                    logger.info(policy_result)
                    self._s3operations.save_results_to_s3(policy=self._policy.replace('_', '-'), policy_output=self._policy_output, policy_result=policy_result)
