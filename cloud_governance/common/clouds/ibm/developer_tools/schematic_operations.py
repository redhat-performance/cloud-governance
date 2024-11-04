from ibm_schematics.schematics_v1 import SchematicsV1

from cloud_governance.common.clouds.ibm.account.ibm_authenticator import IBMAuthenticator


class SchematicOperations(IBMAuthenticator):
    """
    This class performs schematic operations.
    """
    REGION_SCHEMATICS_URL = "https://%s.schematics.cloud.ibm.com/"

    def __init__(self):
        super().__init__()
        self.__client = SchematicsV1(self.iam_authenticator)
        self.__client.set_service_url('https://us.schematics.cloud.ibm.com')

    def set_service_url(self, region: str):
        """
        This method sets the service URL.
        :param region:
        :return:
        """
        service_url = self.REGION_SCHEMATICS_URL % region
        self.__client.set_service_url(service_url)

    def get_workspaces(self):
        """
        This method lists all available schematics workspaces
        :return:
        """
        response = self.__client.list_workspaces().get_result()
        return response['workspaces']

    def get_supported_locations(self):
        """
        This method lists supported locations
        :return:
        """
        response = self.__client.list_locations().get_result()
        return response['locations']

    def get_all_workspaces(self):
        """
        This method lists all available schematics workspaces
        :return:
        """
        locations = self.get_supported_locations()
        resources_list = {}
        for location in locations:
            region = location['region']
            geography_code = location['geography_code']
            self.set_service_url(region)
            if geography_code not in resources_list:
                resources_list[geography_code] = self.get_workspaces()
        return resources_list
