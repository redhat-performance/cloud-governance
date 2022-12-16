from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.subscription import SubscriptionClient

from cloud_governance.main.environment_variables import environment_variables


class AzureOperations:
    """
    This class represents the Azure account operations
    """

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__tenant_id = self.__environment_variables_dict.get('AZURE_TENANT_ID')
        self.__client_id = self.__environment_variables_dict.get('AZURE_CLIENT_ID')
        self.__client_secret = self.__environment_variables_dict.get('AZURE_CLIENT_SECRET')
        self.__default_creds = DefaultAzureCredential()
        self.__subscription_client = SubscriptionClient(credential=self.__default_creds)
        self.cost_mgmt_client = CostManagementClient(credential=self.__default_creds)
        self.subscription_id, self.account_name = self.__get_subscription_id()
        self.cloud_name = 'AZURE'
        self.scope = f'subscriptions/{self.subscription_id}'

    def __get_subscription_id(self):
        """
        This methods return the subscription ID
        @return:
        """
        subscription_list = self.__subscription_client.subscriptions.list()
        for subscription in subscription_list:
            data_dict = subscription.as_dict()
            subscription_id = data_dict.get('subscription_id')
            account_name = data_dict.get('display_name').split()[0]
            return subscription_id, account_name
        return '', ''



