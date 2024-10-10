from cloud_governance.common.clouds.aws.price.price import AWSPrice
from cloud_governance.common.utils.configs import DEFAULT_ROUND_DIGITS
from cloud_governance.main.environment_variables import environment_variables


class ResourcesPricing:
    """
    This class calculates the AWS resources pricing
    """

    MONTHLY_HOURS = 730
    IP_HOURLY_COST = 0.005

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self._aws_pricing = AWSPrice()
        self.region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-1')

    def ec2_instance_type_cost(self, instance_type: str, hours: float):
        """
        This method returns the cost of ec2 instance types cost
        @return:
        """
        cost = float(self._aws_pricing.get_price(instance=instance_type, os='Linux',
                                                 region=self._aws_pricing.get_region_name(self.region)))
        return cost * hours

    def get_ebs_cost(self, volume_size: int, volume_type: str, hours: float):
        """
        This method returns the cost of ebs_volume
        @param hours:
        @param volume_size:
        @param volume_type:
        @return:
        """
        cost = float(self._aws_pricing.get_ebs_cost(volume_type=volume_type, region=self.region))
        return cost * volume_size * (hours / self.MONTHLY_HOURS)

    def get_const_prices(self, resource_type: str, hours: int):
        """
        This method gives the cost of const resources
        @param hours:
        @param resource_type:
        @return:
        """
        if resource_type == 'eip':
            return self.IP_HOURLY_COST * hours

    def get_eip_unit_price(self):
        """
        This method returns the ElasticIp Price
        :return:
        :rtype:
        """
        return self.IP_HOURLY_COST

    def get_nat_gateway_unit_price(self, region_name: str):
        """
        This method returns the unit price of NatGateway
        :param region_name:
        :type region_name:
        :return:
        :rtype:
        """
        service_code = 'AmazonEC2'
        filter_dict = [
            {"Field": "productFamily", "Value": "NAT Gateway", "Type": "TERM_MATCH"},
            {"Field": "regionCode", "Value": region_name, "Type": "TERM_MATCH"},
            {"Field": "groupDescription", "Value": "Hourly charge for NAT Gateways", "Type": "TERM_MATCH"},
        ]
        unit_price = self._aws_pricing.get_service_pricing(service_code, filter_dict)
        return round(unit_price, DEFAULT_ROUND_DIGITS)

    def get_ebs_unit_price(self, region_name: str, ebs_type: str):
        """
        This method returns the ebs_type unit price
        :param region_name:
        :type region_name:
        :param ebs_type:
        :type ebs_type:
        :return:
        :rtype:
        """
        service_code = 'AmazonEC2'
        filter_dict = [
            {"Field": "productFamily", "Value": "Storage", "Type": "TERM_MATCH"},
            {"Field": "regionCode", "Value": region_name, "Type": "TERM_MATCH"},
            {"Field": "volumeApiName", "Value": ebs_type, "Type": "TERM_MATCH"},
        ]
        unit_price = self._aws_pricing.get_service_pricing(service_code, filter_dict)
        return round(unit_price, DEFAULT_ROUND_DIGITS)

    def get_rds_price(self, region_name: str, instance_type: str):
        service_code = 'AmazonRDS'
        filter_dict = [
            {"Field": "productFamily", "Value": "Database Instance", "Type": "TERM_MATCH"},
            {"Field": "regionCode", "Value": region_name, "Type": "TERM_MATCH"},
            {"Field": "instanceType", "Value": instance_type, "Type": "TERM_MATCH"}
        ]
        unit_price = self._aws_pricing.get_service_pricing(service_code, filter_dict)
        return round(unit_price, DEFAULT_ROUND_DIGITS)

    def get_snapshot_unit_price(self, region_name: str):
        """
        This method returns the unit price of Ebs Snapshot
        :param region_name:
        :return:
        """
        service_code = 'AmazonEC2'
        filter_dict = [
            {"Field": "regionCode", "Value": region_name, "Type": "TERM_MATCH"},
            {"Field": "productFamily", "Value": "Storage Snapshot", "Type": "TERM_MATCH"},
            {"Field": "snapshotarchivefeetype", "Value": "SnapshotArchiveStorage", "Type": "TERM_MATCH"},
        ]
        unit_price = self._aws_pricing.get_service_pricing(service_code, filter_dict)
        return round(unit_price, DEFAULT_ROUND_DIGITS)

    def get_ec2_price(self, region_name: str, instance_type: str, operating_system: str = None):
        """
        This method returns the unit price of Ec2 Price
        :param operating_system:
        :param region_name:
        :param instance_type:
        :return:
        """
        if not operating_system:
            operating_system = 'Linux/UNIX'
        os_types = {'Linux/UNIX': 'Linux',
                    'Red Hat Enterprise Linux': 'RHEL',
                    'SUSE Linux': 'SUSE',
                    'Ubuntu Pro Linux': 'Ubuntu Pro',
                    'Windows': 'Windows',
                    'Red Hat Enterprise Linux with High Availability': 'Red Hat Enterprise Linux with HA'}
        operating_system_value = "NA"
        for os_type in os_types.keys():
            if os_type.lower() == operating_system.lower():
                operating_system_value = os_types[os_type]
        service_code = 'AmazonEC2'
        filter_dict = [
            {"Field": "regionCode", "Value": region_name, "Type": "TERM_MATCH"},
            {'Type': 'TERM_MATCH', 'Field': 'servicecode', 'Value': 'AmazonEC2'},
            {"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"},
            {"Field": "operatingSystem", "Value": f"{operating_system_value}", "Type": "TERM_MATCH"},
            {"Field": "instanceType", "Value": f"{instance_type}", "Type": "TERM_MATCH"},
            {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
            {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
        ]
        unit_price = self._aws_pricing.get_service_pricing(service_code, filter_dict)
        return round(unit_price, DEFAULT_ROUND_DIGITS)
