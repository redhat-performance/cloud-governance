import boto3
from moto import mock_ec2, mock_cloudtrail, mock_iam

from cloud_governance.cloud_resource_orchestration.clouds.aws.ec2.tag_cro_instances import TagCROInstances
from cloud_governance.main.environment_variables import environment_variables
from tests.unittest.cloud_governance.cloud_resource_orchestration.mocks.mock_jira import mock_jira

AWS_DEFAULT_REGION = 'ap-south-1'


@mock_iam
@mock_cloudtrail
@mock_jira
@mock_ec2
def test_tag_cro_instances():
    """
    This method tests the tagging of cro instances
    :return:
    """
    environment_variables_dict = environment_variables.environment_variables_dict
    environment_variables_dict['JIRA_TOKEN'] = '123456mock'
    tags = [{'Key': 'TicketId', 'Value': '1'}]
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    tag_cro_instances = TagCROInstances(region_name=AWS_DEFAULT_REGION)
    actual_response = tag_cro_instances.run()
    expected_response = 1
    assert len(actual_response) == expected_response
