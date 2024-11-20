import logging

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from cloud_governance.main.environment_variables import environment_variables


class IBMAuthenticator:
    """
    Refer: https://cloud.ibm.com/apidocs/vpc/latest
    Refer: https://github.com/IBM/ibm-cloud-sdk-common?tab=readme-ov-file
    """

    def __init__(self):
        logging.disable(logging.DEBUG)
        self.env_config = environment_variables
        if hasattr(self.env_config, 'IBM_ACCOUNT_ID'):
            self.account_id = self.env_config.IBM_ACCOUNT_ID
        else:
            self.account_id = self.env_config.environment_variables_dict.get('IBM_ACCOUNT_ID')
        if hasattr(self.env_config, 'IBM_CLOUD_API_KEY'):
            self.__api_key = self.env_config.IBM_CLOUD_API_KEY
        else:
            self.__api_key = self.env_config.environment_variables_dict.get('IBM_CLOUD_API_KEY')
        self.iam_authenticator = IAMAuthenticator(self.__api_key)
