import json
import os

import boto3
from pkg_resources import resource_filename


class InstanceTypes:

    def __init__(self):
        self.ec2_client = boto3.client('ec2', region_name='us-east-1')
        self.__client = boto3.client('pricing', region_name='us-east-1')

    def get_instance_types(self, region_name: str):
        """This method fetch all instance types"""
        instance_types = []
        ec2_client = boto3.client('ec2', region_name=region_name)
        response = ec2_client.describe_instance_types()
        instance_types.extend([ins_type['InstanceType'] for ins_type in response.get('InstanceTypes')])
        while 'NextToken' in response:
            response = ec2_client.describe_instance_types(NextToken=response.get('NextToken'))
            instance_types.extend([ins_type['InstanceType'] for ins_type in response.get('InstanceTypes')])
        return sorted(instance_types)

    def get_region_name(self, region_code):
        """
        This method return region name
        @param region_code:
        @return:
        """
        default_region = 'us-east-1'
        endpoint_file = resource_filename('botocore', 'data/endpoints.json')
        try:
            with open(endpoint_file, 'r') as f:
                data = json.load(f)
            return data['partitions'][0]['regions'][region_code]['description']
        except IOError:
            return default_region

    def instance_price(self, region_name: str, instance_type: str):
        """This method give price of instance type in a region"""
        FLT = '[{{"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"}},' \
              '{{"Field": "operatingSystem", "Value": "Linux", "Type": "TERM_MATCH"}},' \
              '{{"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"}},' \
              '{{"Field": "instanceType", "Value": "{t}", "Type": "TERM_MATCH"}},' \
              '{{"Field": "location", "Value": "{r}", "Type": "TERM_MATCH"}},' \
              '{{"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"}}]'
        f = FLT.format(r=self.get_region_name(region_name), t=instance_type)
        try:
            data = self.__client.get_products(ServiceCode='AmazonEC2', Filters=json.loads(f))
            od = json.loads(data['PriceList'][0])['terms']['OnDemand']
            id1 = list(od)[0]
            id2 = list(od[id1]['priceDimensions'])[0]
            return od[id1]['priceDimensions'][id2]['pricePerUnit']['USD']
        except Exception as err:
            return 0

    def instance_prices(self):
        """This method get the instance prices based on instance_type"""
        # regions = self.ec2_client.describe_regions()['Regions']
        # aws_pricing = {}
        # for region in regions:
        region_pricing = {}
        instance_types = self.get_instance_types(region_name='us-west-2')
        for instance_type in instance_types:
            price = self.instance_price(region_name='us-west-2', instance_type=instance_type)
            if float(price) > 0:
                region_pricing[instance_type] = round(float(price), 4)
            # aws_pricing[region['RegionName']] = region_pricing
        with open('instances_price.json', 'w') as file:
            json.dump(region_pricing, file, indent=4)


# InstanceTypes().instance_prices()
