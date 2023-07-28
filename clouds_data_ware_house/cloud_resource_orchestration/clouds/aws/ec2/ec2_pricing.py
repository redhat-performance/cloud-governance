
import os
import json
import boto3
from pkg_resources import resource_filename


class EC2Pricing:
    """
    This class gets spot/on-demand instance type pricing
    """
    def __init__(self, output_path: str):
        self.region_name = 'us-west-2'
        self.ec2_client = boto3.client('ec2', region_name=self.region_name)
        # region_name must be 'us-east-1'
        self.__client = boto3.client('pricing', region_name='us-east-1')
        self.output_path = output_path

    def get_region_code(self):
        """
        This method returns region code
        @return:
        """
        endpoint_file = resource_filename('botocore', 'data/endpoints.json')
        try:
            with open(endpoint_file, 'r') as f:
                data = json.load(f)
            return data['partitions'][0]['regions'][self.region_name]['description']
        except IOError:
            return 'US West (Oregon)'

    def get_instance_types(self):
        """
        This method returns all instance types
        @return:
        """
        instance_types = []
        response = self.ec2_client.describe_instance_types()
        instance_types.extend([ins_type['InstanceType'] for ins_type in response.get('InstanceTypes')])
        while 'NextToken' in response:
            response = self.ec2_client.describe_instance_types(NextToken=response.get('NextToken'))
            instance_types.extend([ins_type['InstanceType'] for ins_type in response.get('InstanceTypes')])
        return sorted(instance_types)

    def ec2_prices(self, price_type):
        """
        This method returns ec2 on-demand/spot prices per instance type
        @param price_type: on-demand/spot method
        @return:
        """
        region_pricing = {}
        instance_types = self.get_instance_types()
        for instance_type in instance_types:
            price = price_type(instance_type=instance_type)
            # print(instance_type, price)
            if float(price) > 0:
                region_pricing[instance_type] = round(float(price), 4)
        with open(os.path.join(self.output_path, f'{price_type.__name__}.json'), 'w') as file:
            json.dump(region_pricing, file, indent=4)

    def ec2_spot_price(self, instance_type: str):
        """
        This method returns ec2 spot price per instance type/ AvailabilityZone
        @param instance_type:
        @return:
        """
        try:
            data = self.ec2_client.describe_spot_price_history(InstanceTypes=[instance_type], MaxResults=1, ProductDescriptions=['Linux/UNIX (Amazon VPC)'], AvailabilityZone=f'{self.region_name}a')
            return data['SpotPriceHistory'][0]['SpotPrice']
        except Exception as err:
            return 0

    def ec2_spot_prices(self):
        """
        This method returns spot instance price per instance type
        @return:
        """
        self.ec2_prices(price_type=self.ec2_spot_price)

    def ec2_on_demand_price(self, instance_type: str):
        """
        This method returns ec2 on-demand price per instance type/ region
        @param instance_type:
        @return:
        """
        FLT = '[{{"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"}},' \
              '{{"Field": "operatingSystem", "Value": "Linux", "Type": "TERM_MATCH"}},' \
              '{{"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"}},' \
              '{{"Field": "instanceType", "Value": "{t}", "Type": "TERM_MATCH"}},' \
              '{{"Field": "location", "Value": "{r}", "Type": "TERM_MATCH"}},' \
              '{{"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"}}]'
        f = FLT.format(r=self.get_region_code(), t=instance_type)
        try:
            data = self.__client.get_products(ServiceCode='AmazonEC2', Filters=json.loads(f))
            od = json.loads(data['PriceList'][0])['terms']['OnDemand']
            id1 = list(od)[0]
            id2 = list(od[id1]['priceDimensions'])[0]
            return od[id1]['priceDimensions'][id2]['pricePerUnit']['USD']
        except Exception as err:
            return 0

    def ec2_on_demand_prices(self):
        """
        This method returns ec2 on-demand price per instance_type
        @return:
        """
        self.ec2_prices(price_type=self.ec2_on_demand_price)
