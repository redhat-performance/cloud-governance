
import boto3
from moto import mock_ec2

from cloud_governance.cloud_resource_orchestration.aws.long_run.tag_long_run import TagLongRun
from tests.unittest.cloud_resource_orchestration.mocks.mock_jira_operations import jira_mock

AWS_DEFAULT_REGION = 'ap-south-1'


@jira_mock
@mock_ec2
def test_tag_long_run():
    """
    This method tests the tag long run
    """
    default_ami_id = 'ami-03cf127a'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    tags = [{'Key': 'JiraId', 'Value': 'test'}]
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                           TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])['Instances'][0]['InstanceId']
    tag_long_run = TagLongRun(region_name=AWS_DEFAULT_REGION)
    response = tag_long_run.run()
    if response:
        assert response['test'][0] == instance_id
    else:
        assert False
