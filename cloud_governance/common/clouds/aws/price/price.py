import os
from datetime import datetime
from time import strftime

import boto3
import json
from pkg_resources import resource_filename

# Search product filter
FLT = '[{{"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"}},' \
      '{{"Field": "operatingSystem", "Value": "{o}", "Type": "TERM_MATCH"}},' \
      '{{"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"}},' \
      '{{"Field": "instanceType", "Value": "{t}", "Type": "TERM_MATCH"}},' \
      '{{"Field": "location", "Value": "{r}", "Type": "TERM_MATCH"}},' \
      '{{"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"}}]'

FLT_VOLUME = '[{{"Field": "volumeType", "Value": "{v}", "Type": "TERM_MATCH"}},' \
             '{{"Field": "location", "Value": "{r}", "Type": "TERM_MATCH"}} ]'


class AWSPrice:
    """
    This class return aws resource price
    """

    def __init__(self):
        # Use AWS Pricing API at US-East-1
        self.__client = boto3.client('pricing', region_name='us-east-1')
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

    # Get current AWS price for an on-demand instance
    def get_price(self, **kwargs):
        """
        This method return price per region
        @return:
        """
        region = kwargs.get('region')
        if kwargs.get('aws_resource') == 'ebs':
            volume_type = kwargs.get('volume_type')
            f = FLT_VOLUME.format(r=region, v=volume_type)
        else:
            instance = kwargs.get('instance')
            os = kwargs.get('os')
            f = FLT.format(r=region, t=instance, o=os)
        try:
            data = self.__client.get_products(ServiceCode='AmazonEC2', Filters=json.loads(f))
            od = json.loads(data['PriceList'][0])['terms']['OnDemand']
            id1 = list(od)[0]
            id2 = list(od[id1]['priceDimensions'])[0]
            return od[id1]['priceDimensions'][id2]['pricePerUnit']['USD']
        except Exception as err:
            return 0

    # Translate region code to region name
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

    def get_ebs_cost(self, volume_type: str, region: str):
        """
        This method return the cost of ebs storage
        @return:
        """
        volume_types = {
            'gp': 'General Purpose',
            'io': 'Provisioned IOPS',
            'st1': 'Throughput Optimized HDD',
            'standard': 'Magnetic',
            'sc1': 'Cold HDD'
        }
        key = ''
        for volume_key, value in volume_types.items():
            if volume_key in volume_type:
                key = value
        return float(self.get_price(region=self.get_region_name(region), volume_type=key, aws_resource='ebs'))

    def get_ec2_price(self, resource: str, item_data: dict):
        """
        This method calculate ec2 cost from launch time or ebs per month in $
        @return:cluster_cost_results
        """
        if resource == 'ec2' and item_data['State']['Name'] == 'running':
            # Get current price for a given 'running' instance, region and os
            ec2_type_cost = '0'
            try:
                ec2_type_cost = self.get_price(region=self.get_region_name(self.region), instance=item_data['InstanceType'], os='Linux')
            except Exception as err:
                return 'NA'
            ec2_lanuch_time = item_data['LaunchTime']
            d1 = datetime.strptime(ec2_lanuch_time, "%Y-%m-%dT%H:%M:%S+00:00")
            d2 = datetime.strptime(strftime("%Y-%m-%dT%H:%M:%S+00:00"), "%Y-%m-%dT%H:%M:%S+00:00")
            diff = d2 - d1
            diff_in_hours = diff.total_seconds() / 3600
            ec2_cost = round(float(ec2_type_cost) * diff_in_hours, 3)
            return round(ec2_cost, 3)
        elif resource == 'ec2' and item_data['State']['Name'] != 'running':
            return '0'
        elif resource == 'ebs':
            ebs_monthly_cost = '0'
            if item_data['VolumeType'] in ('gp2', 'gp3'):
                ebs_monthly_cost = self.get_ebs_cost(volume_type='gp', region=self.region) * item_data['Size']
            elif item_data['VolumeType'] in ('io1', 'io2'):
                ebs_monthly_cost = self.get_ebs_cost(volume_type='io', region=self.region) * item_data['Size']
            elif item_data['VolumeType'] == 'standard':
                ebs_monthly_cost = self.get_ebs_cost(volume_type='standard', region=self.region) * item_data['Size']
            elif item_data['VolumeType'] == 'st1':
                ebs_monthly_cost = self.get_ebs_cost(volume_type='st1', region=self.region) * item_data['Size']
            else:
                if item_data['VolumeType'] == 'sc1':
                    ebs_monthly_cost = self.get_ebs_cost(volume_type='sc1', region=self.region) * item_data['Size']
            return round(ebs_monthly_cost, 3)
