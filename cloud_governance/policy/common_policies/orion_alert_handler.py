from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.common.orion.slack_notifier import OrionSlackNotifier
from cloud_governance.main.environment_variables import environment_variables


class OrionAlertHandler:
    """
    Policy wrapper that reads Orion's JSON output file and posts any
    detected regressions to Slack. Intended to run after the Orion
    container has written its analysis results to a shared path.
    """

    def __init__(self):
        self.__env = environment_variables.environment_variables_dict
        self.__account = self.__env.get('account', '')
        self.__slack_token = self.__env.get('SLACK_API_TOKEN', '')
        self.__slack_channel = self.__env.get('SLACK_CHANNEL_NAME', '')
        self.__orion_output_file = self.__env.get('ORION_OUTPUT_FILE', '')

    @logger_time_stamp
    def run(self):
        if not self.__orion_output_file:
            logger.warning('ORION_OUTPUT_FILE not set, skipping alert handler')
            return {'status': 'skipped', 'message': 'ORION_OUTPUT_FILE not set'}

        if not self.__slack_token or not self.__slack_channel:
            logger.warning('Slack credentials not configured, skipping alert handler')
            return {'status': 'skipped', 'message': 'Slack credentials not configured'}

        notifier = OrionSlackNotifier(
            slack_token=self.__slack_token,
            slack_channel=self.__slack_channel,
        )
        result = notifier.notify(
            file_path=self.__orion_output_file,
            account=self.__account,
        )
        logger.info('Orion alert handler result: %s', result)
        return result
