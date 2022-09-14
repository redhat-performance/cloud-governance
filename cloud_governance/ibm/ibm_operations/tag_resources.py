import importlib
import inspect

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.ibm.ibm_operations.ibm_operations import IBMOperations


class TagResources(IBMOperations):
    """
    This class run the IBM Policies from policy/ibm
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method run the ibm tag policies
        @return:
        """
        logger.info(f'account={self._account}, policy={self._policy}, dry_run={self._dry_run}, tag_operation={self._tag_operation}')
        if self._policy.startswith('tag') or self._policy.startswith('remove'):
            tag_ibm_policy_module = importlib.import_module(f'cloud_governance.policy.ibm.{self._policy}')
            for cls in inspect.getmembers(tag_ibm_policy_module, inspect.isclass):
                if self._policy.replace('_', '') == cls[0].lower():
                    response = cls[1]().run()
                    if len(response) > 0:
                        logger.info(f'key: {cls[0]}, count: {len(response)}, {response}')
