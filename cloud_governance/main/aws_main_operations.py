import os

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_runners.aws.policy_runner import PolicyRunner


class AWSMainOperations:

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__policy = self.__environment_variables_dict.get('policy', '')
        self.__policy_runner = PolicyRunner()

    def __get_policies(self) -> dict:
        """
        This method gets the aws policies
        :return:
        :rtype:
        """
        policies = {}
        policies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'policy', 'aws')
        for (dirpath, dirnames, filenames) in os.walk(policies_path):
            immediate_parent = dirpath.split("/")[-1]
            for filename in filenames:
                if not filename.startswith('__') and (filename.endswith('.yml') or filename.endswith('.py')):
                    policies.setdefault(immediate_parent, []).append(os.path.splitext(filename)[0])
        return policies

    def run(self):
        """
        This method run the AWS Policy operations
        :return:
        :rtype:
        """
        policies_list = self.__get_policies()
        for policy_type, policies in policies_list.items():
            # @Todo support for all the aws policies, currently supports ec2_run as urgent requirement
            if self.__policy in policies and self.__policy == "ec2_run":
                self.__policy_runner.run(source=policy_type)
                return True
        return False
