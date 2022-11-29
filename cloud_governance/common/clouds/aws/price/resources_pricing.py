
from cloud_governance.common.clouds.aws.price.price import AWSPrice
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
        cost = float(self._aws_pricing.get_price(instance=instance_type, os='Linux', region=self._aws_pricing.get_region_name(self.region)))
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

