import os
from operator import le
from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.ec2_stop import EC2Stop

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'


# @mock_aws
# @mock_aws
# def test_ec2_stop():
#     """
#     This method tests, termination of stopped instance more than 30 days and create an image, snapshot
#     @return:
#     """
#     ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
#     default_ami_id = 'ami-03cf127a'
#     tags = [{'Key': 'Name', 'Value': 'CloudGovernanceTestInstance'}, {'Key': 'User', 'Value': 'cloud-governance'}]
#     instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1, TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])['Instances'][0].get('InstanceId')
#     ec2_client.stop_instances(InstanceIds=[instance_id])
#     ec2_stop = EC2Stop()
#     ec2_stop.set_dryrun(value='no')
#     ec2_stop._EC2Stop__fetch_stop_instance(sign=le, instance_days=1, delete_instance_days=0)
#     amis = ec2_client.describe_images(Owners=['self'])['Images']
#     snapshot_id = amis[0].get('BlockDeviceMappings')[0].get('Ebs').get('SnapshotId')
#     snapshots = ec2_client.describe_snapshots(OwnerIds=['self'], SnapshotIds=[snapshot_id])['Snapshots']
#     assert len(snapshots) == len(amis)


@mock_aws
def test_ec2_stop_not_delete():
    """
    This method tests,not termination of stopped instance more than 30 days and create an image, snapshot using Policy=NOT_DELETE
    @return:
    """
    ec2_client = boto3.client('ec2', region_name=os.environ.get('AWS_DEFAULT_REGION'))
    default_ami_id = 'ami-03cf127a'
    tags = [{'Key': 'Name', 'Value': 'CloudGovernanceTestInstance'}, {'Key': 'User', 'Value': 'cloud-governance'}, {'Key': 'policy', 'Value': 'not_delete'}]
    instance_id = ec2_client.run_instances(ImageId=default_ami_id, InstanceType='t2.micro', MaxCount=1, MinCount=1,
                                           TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])['Instances'][
        0].get('InstanceId')
    ec2_client.stop_instances(InstanceIds=[instance_id])
    ec2_stop = EC2Stop()
    ec2_stop.set_dryrun(value='no')
    ec2_stop._EC2Stop__fetch_stop_instance(sign=le, instance_days=1, delete_instance_days=0)
    instances = ec2_client.describe_instances()['Reservations']
    assert len(instances) == 1


@mock_aws
def test_trigger_mail_routes_to_email_tag_when_valid():
    """
    This method tests the mail is routed to a valid Email tag instead of the User tag
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    ec2_stop = EC2Stop()
    ec2_stop._mail = MagicMock()
    ec2_stop._ldap = MagicMock()
    ec2_stop._ldap.get_user_details.return_value = {'displayName': 'John Doe', 'managerId': 'jmanager'}
    tags = [
        {'Key': 'User', 'Value': 'jdoe'},
        {'Key': 'Email', 'Value': 'team-dl@redhat.com'},
        {'Key': 'Name', 'Value': 'test-instance'},
    ]
    ec2_stop._EC2Stop__trigger_mail(tags=tags, stopped_time='2026-01-01', resource_id='i-123', days=20,
                                    instance_id='i-123', message_type='notification')
    _, kwargs = ec2_stop._mail.send_email_postfix.call_args
    assert kwargs['to'] == 'team-dl@redhat.com'
    ec2_stop._ldap.get_user_details.assert_called_with(user_name='jdoe')


@mock_aws
def test_trigger_mail_falls_back_to_user_when_email_tag_missing():
    """
    This method tests the mail falls back to the User tag when Email tag is absent
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    ec2_stop = EC2Stop()
    ec2_stop._mail = MagicMock()
    ec2_stop._ldap = MagicMock()
    ec2_stop._ldap.get_user_details.return_value = {'displayName': 'John Doe', 'managerId': 'jmanager'}
    tags = [
        {'Key': 'User', 'Value': 'jdoe'},
        {'Key': 'Name', 'Value': 'test-instance'},
    ]
    ec2_stop._EC2Stop__trigger_mail(tags=tags, stopped_time='2026-01-01', resource_id='i-123', days=20,
                                    instance_id='i-123', message_type='notification')
    _, kwargs = ec2_stop._mail.send_email_postfix.call_args
    assert kwargs['to'] == 'jdoe'
    ec2_stop._ldap.get_user_details.assert_called_with(user_name='jdoe')
