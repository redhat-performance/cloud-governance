import boto3
from moto import mock_ec2

from cloud_governance.common.clouds.aws.ec2.ec2_operations import EC2Operations

AWS_DEFAULT_REGION = 'ap-south-1'


@mock_ec2
def test_get_ec2_instance_list():
    """
    This method returns the list of ec2 instances
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    assert type(ec2_operations.get_ec2_instance_list()[0]) == dict


@mock_ec2
def test_get_ec2_instance_ids():
    """
    This method tests the return the list instance_ids
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    default_ami_id = 'ami-03cf127a'
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    assert type(ec2_operations.get_ec2_instance_ids()[0]) == str


@mock_ec2
def test_tag_ec2_resources():
    """
    This method tests the method tagged instances by batch wise
    :return:
    """
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_operations = EC2Operations(region=AWS_DEFAULT_REGION)
    tags = [{'Key': 'User', 'Value': 'cloud-governance'}]
    default_ami_id = 'ami-03cf127a'
    for i in range(25):
        ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1)
    resource_ids = ec2_operations.get_ec2_instance_ids()
    assert ec2_operations.tag_ec2_resources(client_method=ec2_client.create_tags, resource_ids=resource_ids, tags=tags) == 2
