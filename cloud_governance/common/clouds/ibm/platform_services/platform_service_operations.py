import json
from urllib.parse import urlparse, parse_qs

from ibm_platform_services import ResourceControllerV2

from cloud_governance.common.clouds.ibm.account.ibm_authenticator import IBMAuthenticator


class PlatformServiceOperations(IBMAuthenticator):

    def __init__(self):
        super().__init__()
        self.__client = ResourceControllerV2(authenticator=self.iam_authenticator)

    def get_resource_instances(self):
        """
        This method returns all the service instances
        :return:
        """
        responses = self.__client.list_resource_instances().get_result()
        resources = responses['resources']
        while responses.get('next_url'):
            parsed_url = urlparse(responses['next_url'])
            params = parse_qs(parsed_url.query)
            if params and 'start' in params:
                start = params['start'][0]
                responses = self.__client.list_resource_instances(start=start).get_result()
                resources.extend(responses['resources'])
        resource_instances = []
        for resource in resources:
            if resource['type'] == 'resource_instance':
                resource_instances.append(resource)
        return {'global': resource_instances}
