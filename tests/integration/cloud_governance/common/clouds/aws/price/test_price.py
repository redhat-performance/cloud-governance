from cloud_governance.common.clouds.aws.price.price import AWSPrice


def test_get_service_pricing():
    aws_price = AWSPrice()
    service_code = 'AmazonEC2'
    filter_list = [
        {"Field": "regionCode", "Value": 'ap-south-1', "Type": "TERM_MATCH"},
        {"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"},
        {"Field": "operatingSystem", "Value": "Linux", "Type": "TERM_MATCH"},
        {"Field": "instanceType", "Value": "t2.micro", "Type": "TERM_MATCH"},
        {"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"},
    ]
    assert aws_price.get_service_pricing(service_code, filter_list) > 0
