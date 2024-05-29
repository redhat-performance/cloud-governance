from cloud_governance.common.utils.utils import Utils
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_runners.azure.policy_runner import PolicyRunner as AzurePolicyRunner
from cloud_governance.policy.policy_runners.aws.policy_runner import PolicyRunner as AWSPolicyRunner


class MainOperations:

    def __init__(self):
        self.utils = Utils()
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._policy = self._environment_variables_dict.get('policy', '')
        self._public_cloud_name = self._environment_variables_dict.get('PUBLIC_CLOUD_NAME', '')

    def get_policy_runner(self):
        """
        This method returns the cloud policy runner object
        :return:
        :rtype:
        """
        policy_runner = None
        if Utils.equal_ignore_case(self._public_cloud_name, 'AWS'):
            policy_runner = AWSPolicyRunner()
        else:
            if Utils.equal_ignore_case(self._public_cloud_name, 'AZURE'):
                policy_runner = AzurePolicyRunner()

        return policy_runner

    def run(self):
        """
        This method run the AWS Policy operations
        :return:
        :rtype:
        """
        policies_list = Utils.get_cloud_policies(cloud_name=self._public_cloud_name, dir_dict=True)
        policy_runner = self.get_policy_runner()
        for policy_type, policies in policies_list.items():
            # @Todo support for all the aws policies, currently supports ec2_run as urgent requirement
            if self._policy in policies and self._policy in ["instance_run", "unattached_volume", "cluster_run",
                                                             "ip_unattached", "unused_nat_gateway", "instance_idle",
                                                             "zombie_snapshots", "database_idle", "s3_inactive",
                                                             "empty_roles"]:
                source = policy_type
                if Utils.equal_ignore_case(policy_type, self._public_cloud_name):
                    source = ''
                policy_runner.run(source=source)
                return True
        return False
