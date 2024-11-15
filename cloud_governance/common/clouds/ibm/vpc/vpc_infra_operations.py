import time
from functools import wraps
from urllib.parse import urlparse, parse_qs

import ibm_vpc
from typing import Callable

from cloud_governance.common.clouds.ibm.account.ibm_authenticator import IBMAuthenticator


def region_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        vpc_obj = VpcInfraOperations()
        regions = vpc_obj.get_regions()
        resources_list = {}
        exec_func = getattr(vpc_obj, func(*args, **kwargs), None)
        for region in regions:
            region_name = region.get('name')
            if region['status'] == 'available':
                vpc_obj.set_service_url(region_name)
                result = exec_func() if exec_func else []
                if result:
                    owned_resources = []
                    for resource in result:
                        if 'crn' in resource:
                            if vpc_obj.account_id in resource['crn']:
                                owned_resources.append(resource)
                        else:
                            owned_resources.append(resource)
                    if owned_resources:
                        resources_list[region_name] = owned_resources
        return resources_list

    return wrapper


class VpcInfraOperations(IBMAuthenticator):
    """
    This class contains methods to perform operations on VPC Infra Operations.
    """

    REGION_SERVICE_URL = "https://%s.iaas.cloud.ibm.com/v1"

    def __init__(self):
        super().__init__()
        self.__client = ibm_vpc.vpc_v1.VpcV1(authenticator=self.iam_authenticator)

    def get_regions(self):
        """
        This method lists all available regions.
        :return:
        """
        regions = self.__client.list_regions().get_result()['regions']
        return regions

    def set_service_url(self, region_name: str):
        """
        This method sets the service URL.
        :param region_name:
        :return:
        """
        service_url = self.REGION_SERVICE_URL % region_name
        self.__client.set_service_url(service_url)

    def iter_next_resources(self, exec_func: Callable, resource_name: str, region_name: str = None, **kwargs):
        """
        This method .
        :param region_name:
        :param exec_func:
        :param resource_name:
        :return:
        """
        if region_name:
            self.set_service_url(region_name)
        response = exec_func(**kwargs).get_result()
        resources = response[resource_name]
        count = 1
        while response.get('next'):
            parsed_url = urlparse(response['next']['href'])
            params = parse_qs(parsed_url.query)
            if params and 'start' in params:
                start = params['start'][0]
                response = exec_func(start=start, **kwargs).get_result()
                resources.extend(response[resource_name])
            count += 1
            if count == 5:
                time.sleep(30)
                count = 0
        return resources

    def get_instances(self, region_name: str = None):
        """
        This method lists available instances in one region, default 'us-south'
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_instances,
                                        resource_name='instances', region_name=region_name)

    def get_images(self, region_name: str = None):
        """
        This method lists available images in one region, default 'us-south'
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_images, resource_name='images',
                                        region_name=region_name, status='available')

    def get_placement_groups(self, region_name: str = None):
        """
        This method returns available placement groups in one region, default 'us-south'
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_placement_groups,
                                        resource_name='placement_groups', region_name=region_name)

    def get_volumes(self, region_name: str = None):
        """
        This method lists available volumes.
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_volumes,
                                        resource_name='volumes', region_name=region_name)

    def get_floating_ips(self, region_name: str = None):
        """
        This method lists available floating ips.
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_floating_ips,
                                        resource_name='floating_ips', region_name=region_name)

    def get_vpcs(self, region_name: str = None):
        """
        This method lists available vpcs.
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_vpcs,
                                        resource_name='vpcs', region_name=region_name)

    def get_virtual_network_interfaces(self, region_name: str = None):
        """
        This method lists available virtual network interfaces.
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_virtual_network_interfaces,
                                        resource_name='virtual_network_interfaces', region_name=region_name)

    def get_security_groups(self, region_name: str = None):
        """
        This method lists available security_groups
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_security_groups,
                                        resource_name='security_groups', region_name=region_name)

    def get_public_gateways(self, region_name: str = None):
        """
        This method lists available public_gateways
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_public_gateways,
                                        resource_name='public_gateways', region_name=region_name)

    def get_vpc_endpoint_gateways(self, region_name: str = None):
        """
        This method lists available vpc endpoint gateways
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_endpoint_gateways,
                                        resource_name='endpoint_gateways', region_name=region_name)

    def get_load_balancers(self, region_name: str = None):
        """
        This method lists available load balancers
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_load_balancers,
                                        resource_name='load_balancers', region_name=region_name)

    def get_baremetal_servers(self, region_name: str = None):
        """
        This method lists available baremetals
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_bare_metal_servers,
                                        resource_name='bare_metal_servers', region_name=region_name)

    @region_wrapper
    def get_all_instances(self):
        """
        This method lists all available instances.
        :return:
        """
        return "get_instances"

    @region_wrapper
    def get_all_volumes(self):
        """
        This method lists all available volumes.
        :return:
        """
        return "get_volumes"

    @region_wrapper
    def get_all_vpcs(self):
        """
        This method lists all available vpc's.
        :return:
        """
        return "get_vpcs"

    @region_wrapper
    def get_all_floating_ips(self):
        """
        This method lists all floating ips.
        :return:
        """
        return "get_floating_ips"

    @region_wrapper
    def get_all_virtual_network_interfaces(self):
        """
        This method lists all available virtual network interfaces.
        :return:
        """
        return "get_virtual_network_interfaces"

    @region_wrapper
    def get_all_security_groups(self):
        """
        This method lists all available security_groups
        :return:
        """
        return "get_security_groups"

    @region_wrapper
    def get_all_public_gateways(self):
        """
        This method lists all available public_gateways
        :return:
        """
        return "get_public_gateways"

    @region_wrapper
    def get_all_vpc_endpoint_gateways(self):
        """
        This method lists all available vpc endpoint gateways
        :return:
        """
        return "get_vpc_endpoint_gateways"

    @region_wrapper
    def get_all_load_balancers(self):
        """
        This method lists all available load balancers.
        :return:
        """
        return "get_load_balancers"

    @region_wrapper
    def get_all_baremetal_servers(self):
        """
        This method lists all available baremetals.
        :return:
        """
        return "get_baremetal_servers"

    @region_wrapper
    def get_all_placement_groups(self):
        """
        This method lists all available placement groups.
        :return:
        """
        return "get_placement_groups"

    @region_wrapper
    def get_all_images(self):
        """
        This method lists all available images.
        :return:
        """
        return "get_images"
