import boto3

from cloud_governance.common.logger.init_logger import logger


class SupportOperations:
    """
    This class performs the support operations
    """

    def __init__(self):
        self.__client = boto3.client('support', region_name='us-east-1')

    def get_describe_trusted_advisor_checks(self):
        """
        This method returns the trusted advisor check results
        :return:
        :rtype:
        """
        try:
            response = self.__client.describe_trusted_advisor_checks(language='en')
            return response.get('checks', [])
        except Exception as err:
            logger.error(err)
        return []

    def get_trusted_advisor_reports(self):
        """
        This method returns the reports of the checks
        :return:
        :rtype:
        """
        result = {}
        try:
            advisor_checks_list = self.get_describe_trusted_advisor_checks()
            for check in advisor_checks_list:
                response = self.__client.describe_trusted_advisor_check_result(checkId=check.get('id'))
                result.setdefault(check.get('category'), {}).setdefault(check.get('id'), {
                    'metadata': check,
                    'reports': response.get('result', [])
                })
        except Exception as err:
            logger.err(err)
        return result
