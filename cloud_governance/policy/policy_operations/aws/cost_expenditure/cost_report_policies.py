import importlib
import inspect

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.main.environment_variables import environment_variables


class CostReportPolicies:

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self._account = self.__environment_variables_dict.get('account', '')
        self._policy = self.__environment_variables_dict.get('policy', '')

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
