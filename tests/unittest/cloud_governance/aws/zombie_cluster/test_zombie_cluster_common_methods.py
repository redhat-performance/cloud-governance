import logging
from unittest.mock import patch, MagicMock

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_operations.aws.zombie_cluster.zombie_cluster_common_methods import \
    ZombieClusterCommonMethods


def _make_instance(region='us-east-1'):
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'zombie_cluster_resource'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    with mock_aws():
        return ZombieClusterCommonMethods(region=region)


@mock_aws
def test_get_tags_of_zombie_resources_elbv1_error_logs(caplog):
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'zombie_cluster_resource'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    zcm = ZombieClusterCommonMethods(region='us-east-1')
    zcm.elb_client = MagicMock()
    zcm.elb_client.describe_tags.side_effect = ClientError(
        {'Error': {'Code': 'LoadBalancerNotFound', 'Message': 'not found'}}, 'DescribeTags')
    resources = [{'LoadBalancerName': 'test-lb'}]
    with caplog.at_level(logging.INFO):
        result = zcm._get_tags_of_zombie_resources(
            resources=resources, resource_id_name='LoadBalancerName',
            zombies={'test-lb': 'cluster-tag'}, aws_service='elbv1')
    assert result == []
    assert 'elbv1 describe_tags error for test-lb' in caplog.text


@mock_aws
def test_get_tags_of_zombie_resources_elbv2_error_logs(caplog):
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'zombie_cluster_resource'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    zcm = ZombieClusterCommonMethods(region='us-east-1')
    zcm.elbv2_client = MagicMock()
    zcm.elbv2_client.describe_tags.side_effect = ClientError(
        {'Error': {'Code': 'LoadBalancerNotFound', 'Message': 'not found'}}, 'DescribeTags')
    resources = [{'ResourceArn': 'arn:aws:elasticloadbalancing:us-east-1:123456:loadbalancer/test'}]
    with caplog.at_level(logging.INFO):
        result = zcm._get_tags_of_zombie_resources(
            resources=resources, resource_id_name='ResourceArn',
            zombies={'arn:aws:elasticloadbalancing:us-east-1:123456:loadbalancer/test': 'cluster-tag'},
            aws_service='elbv2')
    assert result == []
    assert 'elbv2 describe_tags error' in caplog.text


@mock_aws
def test_get_tags_of_zombie_resources_role_error_logs(caplog):
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'zombie_cluster_resource'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    zcm = ZombieClusterCommonMethods(region='us-east-1')
    zcm.iam_client = MagicMock()
    zcm.iam_client.get_role.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchEntity', 'Message': 'role not found'}}, 'GetRole')
    resources = [{'RoleName': 'test-role'}]
    with caplog.at_level(logging.INFO):
        result = zcm._get_tags_of_zombie_resources(
            resources=resources, resource_id_name='RoleName',
            zombies={'test-role': 'cluster-tag'}, aws_service='role')
    assert result == []
    assert 'iam get_role error for test-role' in caplog.text


@mock_aws
def test_get_tags_of_zombie_resources_user_error_logs(caplog):
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'zombie_cluster_resource'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    zcm = ZombieClusterCommonMethods(region='us-east-1')
    zcm.iam_client = MagicMock()
    zcm.iam_client.get_user.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchEntity', 'Message': 'user not found'}}, 'GetUser')
    resources = [{'UserName': 'test-user'}]
    with caplog.at_level(logging.INFO):
        result = zcm._get_tags_of_zombie_resources(
            resources=resources, resource_id_name='UserName',
            zombies={'test-user': 'cluster-tag'}, aws_service='user')
    assert result == []
    assert 'iam get_user error for test-user' in caplog.text


@mock_aws
def test_get_tags_of_zombie_resources_bucket_error_logs(caplog):
    environment_variables.environment_variables_dict['dry_run'] = 'yes'
    environment_variables.environment_variables_dict['policy'] = 'zombie_cluster_resource'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    zcm = ZombieClusterCommonMethods(region='us-east-1')
    zcm.s3_client = MagicMock()
    zcm.s3_client.get_bucket_tagging.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchTagSet', 'Message': 'no tags'}}, 'GetBucketTagging')
    resources = [{'BucketName': 'test-bucket'}]
    with caplog.at_level(logging.INFO):
        result = zcm._get_tags_of_zombie_resources(
            resources=resources, resource_id_name='BucketName',
            zombies={'test-bucket': 'cluster-tag'}, aws_service='bucket')
    assert result == []
    assert 's3 get_bucket_tagging error for test-bucket' in caplog.text


@mock_aws
def test_get_tags_of_zombie_resources_tag_update_error_logs(caplog):
    environment_variables.environment_variables_dict['dry_run'] = 'no'
    environment_variables.environment_variables_dict['policy'] = 'zombie_cluster_resource'
    environment_variables.environment_variables_dict['LDAP_HOST_NAME'] = ''
    environment_variables.environment_variables_dict['DAYS_TO_DELETE_RESOURCE'] = 7
    zcm = ZombieClusterCommonMethods(region='us-east-1')
    zcm.ec2_client = MagicMock()
    zcm.ec2_client.create_tags.side_effect = ClientError(
        {'Error': {'Code': 'InvalidResourceID', 'Message': 'bad id'}}, 'CreateTags')
    resources = [{
        'InstanceId': 'i-12345',
        'Tags': [
            {'Key': 'kubernetes.io/cluster/test-cluster', 'Value': 'owned'},
            {'Key': 'ClusterDeleteDays', 'Value': '1'}
        ]
    }]
    with caplog.at_level(logging.INFO):
        result = zcm._get_tags_of_zombie_resources(
            resources=resources, resource_id_name='InstanceId',
            zombies={'i-12345': 'test-cluster'}, aws_service='ec2')
    assert result == []
    assert 'resource tag update error for i-12345' in caplog.text


def test_trigger_mail_routes_to_email_tag_when_valid():
    """
    This method tests the mail is routed to a valid Email tag instead of the User tag
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    zcm = _make_instance()
    zcm._mail = MagicMock()
    zcm._ldap = MagicMock()
    zcm._ldap.get_user_details.return_value = {'displayName': 'John Doe', 'managerId': 'jmanager'}
    tags = [
        {'Key': 'User', 'Value': 'jdoe'},
        {'Key': 'Email', 'Value': 'team-dl@redhat.com'},
        {'Key': 'Name', 'Value': 'test-cluster'},
    ]
    zcm.trigger_mail(tags=tags, resource_id='test-cluster', days=4, resources=['i-123'],
                     message_type='notification')
    _, kwargs = zcm._mail.send_email_postfix.call_args
    assert kwargs['to'] == 'team-dl@redhat.com'
    zcm._ldap.get_user_details.assert_called_with(user_name='jdoe')


def test_trigger_mail_falls_back_to_user_when_email_tag_missing():
    """
    This method tests the mail falls back to the User tag when Email tag is absent
    """
    environment_variables.environment_variables_dict['ALLOWED_EMAIL_DOMAINS'] = ['@redhat.com']
    zcm = _make_instance()
    zcm._mail = MagicMock()
    zcm._ldap = MagicMock()
    zcm._ldap.get_user_details.return_value = {'displayName': 'John Doe', 'managerId': 'jmanager'}
    tags = [
        {'Key': 'User', 'Value': 'jdoe'},
        {'Key': 'Name', 'Value': 'test-cluster'},
    ]
    zcm.trigger_mail(tags=tags, resource_id='test-cluster', days=4, resources=['i-123'],
                     message_type='notification')
    _, kwargs = zcm._mail.send_email_postfix.call_args
    assert kwargs['to'] == 'jdoe'
    zcm._ldap.get_user_details.assert_called_with(user_name='jdoe')
