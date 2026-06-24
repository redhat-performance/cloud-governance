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
        :raises: RuntimeError if unable to query any region
        """
        # list_locations() was removed from IBM Schematics SDK
        # Use known IBM Cloud regions instead
        known_regions = ['us-south', 'us-east', 'eu-de', 'eu-gb']
        resources_list = {}
        failed_regions = []

        for region in known_regions:
            try:
                self.set_service_url(region)
                workspaces = self.get_workspaces()
                if workspaces:
                    resources_list[region] = workspaces
            except Exception as exc:
                # Track failed regions for debugging
                failed_regions.append((region, str(exc)))
                continue

        # If all regions failed, raise error instead of returning empty dict
        if not resources_list and len(failed_regions) == len(known_regions):
            failed_details = '; '.join(f"{region}: {error}" for region, error in failed_regions)
            raise RuntimeError(
                f"Unable to list Schematics workspaces in any region. "
                f"All {len(known_regions)} regions failed. "
                f"Check credentials and permissions. Details: {failed_details}"
            )

        return resources_list
