import boto3
from moto import mock_ec2

from cloud_governance.common.clouds.aws.utils.utils import Utils


@mock_ec2
def test_tag_aws_resources():
    """
    This method tag aws resources
    :return:
    """
    region_name = 'ap-south-1'
    ec2_client = boto3.client('ec2', region_name=region_name)
    common_utils = Utils(region=region_name)
    resource_ids = []
    for num in range(30):
        instance_id = ec2_client.run_instances(MinCount=1, MaxCount=1)['Instances'][0]['InstanceId']
        resource_ids.append(instance_id)
    expected_res = common_utils.tag_aws_resources(ec2_client.create_tags, tags=[{'Key': 'User', 'Value': 'test'}], resource_ids=resource_ids)
    assert expected_res == 2
