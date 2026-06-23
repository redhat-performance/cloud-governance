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
        DEPRECATED: list_locations() was removed from IBM Schematics SDK
        :return:
        """
        # Method no longer available in IBM Schematics SDK
        # Use known regions in get_all_workspaces() instead
        raise NotImplementedError("list_locations() is no longer available in IBM Schematics SDK")

    def get_all_workspaces(self):
        """
        This method lists all available schematics workspaces
        :return:
        """
        # list_locations() was removed from IBM Schematics SDK
        # Use known IBM Cloud regions instead
        known_regions = ['us-south', 'us-east', 'eu-de', 'eu-gb']
        resources_list = {}

        for region in known_regions:
            try:
                self.set_service_url(region)
                workspaces = self.get_workspaces()
                if workspaces:
                    resources_list[region] = workspaces
            except Exception:
                # Skip regions where schematics is not available or no access
                continue

        return resources_list
