
from cloud_governance.common.aws.price.price import AWSPrice


def test_price():
    __aws_price = AWSPrice()
    ec2_type_cost = __aws_price.get_price(__aws_price.get_region_name('us-east-1'), instance='m5.xlarge', os='Linux')
    assert ec2_type_cost
