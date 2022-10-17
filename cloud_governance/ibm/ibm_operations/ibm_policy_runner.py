import importlib
import inspect

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.ibm.ibm_operations.ibm_operations import IBMOperations


class IBMPolicyRunner(IBMOperations):
    """
    This class run the IBM Policies from policy/ibm
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method run the ibm policies
        @return:
        """
        logger.info(f'account={self._account}, policy={self._policy}, dry_run={self._dry_run}, tag_operation={self._tag_operation}')
        ibm_policy_run = importlib.import_module(f'cloud_governance.policy.ibm.{self._policy}')
        for cls in inspect.getmembers(ibm_policy_run, inspect.isclass):
            if self._policy.replace('_', '') == cls[0].lower():
                response = cls[1]().run()
                if isinstance(response, list) and len(response) > 0:
                    logger.info(f'key: {cls[0]}, count: {len(response)}, {response}')
