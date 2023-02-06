import time

import boto3
from moto import mock_ec2

from cloud_governance.cloud_resource_orchestration.common.ec2_monitor_operations import EC2MonitorOperations

AWS_DEFAULT_REGION = 'ap-south-1'


@mock_ec2
def test_get_instance_run_hours():
    """"
    This method tests current instance running hours
    """
    default_ami_id = 'ami-03cf127a'
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_monitor_operations = EC2MonitorOperations(region_name=AWS_DEFAULT_REGION)
    tags = [{'Key': 'JiraId', 'Value': 'test'}]
    ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                             TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    time.sleep(5)
    hours, _ = ec2_monitor_operations.get_instance_run_hours(instance=ec2_client.describe_instances()['Reservations'][0]['Instances'][0], jira_id='test')
    assert hours > 0
