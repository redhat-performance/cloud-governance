import importlib
import inspect
import os

from cloud_governance.common.logger.init_logger import logger


class CostReportPolicies:

    def __init__(self):
        self._account = os.environ.get('account', '')
        self._policy = os.environ.get('policy', '')

    def run(self):
        """
        This method run the AWS cost policies
        @return:
        """
        logger.info(f'account={self._account}, policy={self._policy}')
        cost_report_policy_module = importlib.import_module(f'cloud_governance.policy.aws.{self._policy}')
        for cls in inspect.getmembers(cost_report_policy_module, inspect.isclass):
            if self._policy.replace('_', '') == cls[0].lower():
                response = cls[1]().run()
                if response:
                    logger.info(f'key: {cls[0]}, count: {len(response)}, {response}')
