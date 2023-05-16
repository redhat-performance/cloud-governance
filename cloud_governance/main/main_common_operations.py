from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.policy.policy_runners.common_policy_runner import CommonPolicyRunner


@logger_time_stamp
def run_common_policies():
    """
    This method run the common policies
    :return:
    """
    common_policy_runner = CommonPolicyRunner()
    common_policy_runner.run()
