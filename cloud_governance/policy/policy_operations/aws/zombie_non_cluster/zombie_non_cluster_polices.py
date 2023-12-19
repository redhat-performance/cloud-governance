import importlib
import inspect
from datetime import datetime

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_operations.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class ZombieNonClusterPolicies(NonClusterZombiePolicy):

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method run the zombie non-cluster policies class
        @return:
        """
        logger.info(f'account={self._account}, region={self._region}, policy={self._policy}, dry_run={self._dry_run}')
        zombie_non_cluster_policy_module = importlib.import_module(f'cloud_governance.policy.aws.{self._policy}')

        for cls in inspect.getmembers(zombie_non_cluster_policy_module, inspect.isclass):
            if self._policy.replace('_', '') == cls[0].lower():
                response = cls[1]().run()
                if isinstance(response, str):
                    logger.info(f'key: {cls[0]}, Response: {response}')
                else:
                    logger.info(f'key: {cls[0]}, count: {len(response)}, {response}')
                    policy_result = response

                    if self._es_operations.check_elastic_search_connection():
                        if policy_result:
                            if len(policy_result) > 500:
                                self._es_operations.upload_data_in_bulk(data_items=policy_result.copy(),
                                                                        index=self._es_index)
                            else:
                                for policy_dict in policy_result:
                                    policy_dict['region_name'] = self._region
                                    policy_dict['account'] = self._account
                                    self._es_operations.upload_to_elasticsearch(data=policy_dict.copy(), index=self._es_index)
                            logger.info(f'Uploaded the policy results to elasticsearch index: {self._es_index}')
                        else:
                            logger.error(f'No data to upload on @{self._account}  at {datetime.utcnow()}')
                    else:
                        logger.error('ElasticSearch host is not pingable, Please check ')

                    if self._policy_output:
                        # if self._policy not in ('ec2_idle', 'ebs_in_use', 'ec2_run', 's3_inactive', 'zombie_snapshots', 'nat_gateway_unused'):
                        #     beautify_data = self._beautify_upload_data(upload_resource_data=response)
                        #     policy_result = {'count': len(beautify_data), self._policy: beautify_data}
                        logger.info(policy_result)
                        self._s3operations.save_results_to_s3(policy=self._policy.replace('_', '-'), policy_output=self._policy_output, policy_result=policy_result)
