import datetime
import os

import pytest

from cloud_governance.common.clouds.aws.price.price import AWSPrice


@pytest.mark.skip(reason='Read Only')
def test_price():
    __aws_price = AWSPrice()
    ec2_type_cost = __aws_price.get_price(region=__aws_price.get_region_name('us-east-1'), instance='m5.xlarge', os='Linux')
    assert ec2_type_cost


@pytest.mark.skip(reason='Read Only')
def test_ebs_price():
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
    __aws_price = AWSPrice()
    ec2_type_cost = __aws_price.get_ec2_price(resource='ebs', item_data={'VolumeType': 'gp2', 'Size': 10})
    assert ec2_type_cost


@pytest.mark.skip(reason='Read Only')
def test_ec2_price():
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
    __aws_price = AWSPrice()
    item_data = {
        'InstanceType': 't2.micro',
        'LaunchTime': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        'State': {
            'Name': 'running'
        }
    }
    ec2_type_cost = __aws_price.get_ec2_price(resource='ec2', item_data=item_data)
    assert ec2_type_cost >= 0
