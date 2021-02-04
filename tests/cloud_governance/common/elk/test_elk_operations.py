
from cloud_governance.common.elk.elk_operations import ElkOperations


def test_get_s3_latest_policy_file():
    region = 'us-east-1'
    elk_operations = ElkOperations(region=region)
    assert elk_operations._ElkOperations__get_s3_latest_policy_file(policy='ec2-idle', region=region)


def test_get_last_s3_policy_content():
    region = 'us-east-1'
    elk_operations = ElkOperations(region=region)
    assert elk_operations._ElkOperations__get_last_s3_policy_content(policy='ec2-idle', region=region)