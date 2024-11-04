from functools import wraps

import ibm_vpc
from typing import Callable

from cloud_governance.common.clouds.ibm.account.ibm_authenticator import IBMAuthenticator


def region_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        vpc_obj = VpcInfraOperations()
        regions = vpc_obj.get_regions()
        resources_list = {}
        for region in regions:
            region_name = region.get('name')
            if region['status'] == 'available':
                vpc_obj.set_service_url(region_name)
                resources_list[region_name] = func(*args, **kwargs)
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

    def iter_next_resources(self, exec_func: Callable, resource_name: str, region_name: str = None):
        """
        This method .
        :param region_name:
        :param exec_func:
        :param resource_name:
        :return:
        """
        if region_name:
            self.set_service_url(region_name)
        response = exec_func().get_result()
        resources = response[resource_name]
        while response.get('next'):
            href = response['next']['href']
            start = href.split('&')[-1].split('=')[-1]
            response = exec_func(start=start).get_result()
            resources.extend(response[resource_name])
        return resources

    def get_instances(self, region_name: str = None):
        """
        This method lists available instances in one region, default 'us-south'
        :param region_name:
        :return:
        """
        return self.iter_next_resources(exec_func=self.__client.list_instances,
                                        resource_name='instances', region_name=region_name)

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

    @region_wrapper
    def get_all_instances(self):
        """
        This method lists all available instances.
        :return:
        """
        return self.get_instances()

    @region_wrapper
    def get_all_volumes(self):
        """
        This method lists all available volumes.
        :return:
        """
        return self.get_volumes()

    @region_wrapper
    def get_all_vpcs(self):
        """
        This method lists all available vpc's.
        :return:
        """
        return self.get_vpcs()

    @region_wrapper
    def get_all_floating_ips(self):
        """
        This method lists all floating ips.
        :return:
        """
        return self.get_floating_ips()

    @region_wrapper
    def get_all_virtual_network_interfaces(self):
        """
        This method lists all available virtual network interfaces.
        :return:
        """
        return self.get_virtual_network_interfaces()

    @region_wrapper
    def get_all_security_groups(self):
        """
        This method lists all available security_groups
        :return:
        """
        return self.get_security_groups()

    @region_wrapper
    def get_all_public_gateways(self):
        """
        This method lists all available public_gateways
        :return:
        """
        return self.get_public_gateways()

    @region_wrapper
    def get_all_vpc_endpoint_gateways(self):
        """
        This method lists all available vpc endpoint gateways
        :return:
        """
        return self.get_vpc_endpoint_gateways()

    @region_wrapper
    def get_all_load_balancers(self):
        """
        This method lists all available load balancers.
        :return:
        """
        return self.get_load_balancers()
