import json
from unittest import skip

from moto import mock_iam, mock_ec2
import boto3

from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.policy.aws.zombie_cluster_resource import ZombieClusterResources

EC2_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ec2:Describe*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "elasticloadbalancing:Describe*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:ListMetrics",
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:Describe*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "autoscaling:Describe*",
            "Resource": "*"
        }
    ]
}


@mock_ec2
@mock_iam
def test_delete_iam_cluster_role():
    """
    This method tests the role is deleted or not
    --> This method is not working because of Describing the role_policies have empty list
    :return:
    """
    iam_resource = boto3.client('iam')
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    tags = [
        {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'unitest'}
    ]
    iam_resource.create_role(AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
                             RoleName='unittest-ocp-test-worker-role', Tags=tags)
    policy_output = iam_resource.create_policy(PolicyName='unittest-ocp-test-worker-policy',
                                               PolicyDocument=json.dumps(EC2_POLICY), Tags=tags)
    iam_resource.attach_role_policy(RoleName='unittest-ocp-test-worker-role', PolicyArn=policy_output['Policy']['Arn'])

    iam_resource.create_instance_profile(InstanceProfileName='unittest-ocp-test-worker-profile', Tags=tags)
    iam_resource.add_role_to_instance_profile(InstanceProfileName='unittest-ocp-test-worker-profile',
                                              RoleName='unittest-ocp-test-worker-role')

    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      resource_name='zombie_cluster_role', force_delete=True)
    zombie_cluster_resources.zombie_cluster_role()
    iam_roles = Utils().get_details_resource_list(func_name=iam_resource.list_roles, input_tag='Roles',
                                                  check_tag='Marker')
    find = False
    for role in iam_roles:
        if role['RoleName'] == 'unittest-ocp-test-worker-role':
            find = True
            break
    assert not find


@mock_ec2
@mock_iam
def test_not_delete_iam_cluster_role():
    """
    This method tests the role is not deleted
    --> This method is not working because of Describing the role_policies have empty list
    :return:
    """
    iam_resource = boto3.client('iam')
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    tags = [
        {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'unitest'}
    ]
    iam_resource.create_role(AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
                             RoleName='unittest-ocp-test-worker-role', Tags=tags)
    policy_output = iam_resource.create_policy(PolicyName='unittest-ocp-test-worker-policy',
                                               PolicyDocument=json.dumps(EC2_POLICY), Tags=tags)
    iam_resource.attach_role_policy(RoleName='unittest-ocp-test-worker-role', PolicyArn=policy_output['Policy']['Arn'])

    iam_resource.create_instance_profile(InstanceProfileName='unittest-ocp-test-worker-profile', Tags=tags)
    iam_resource.add_role_to_instance_profile(InstanceProfileName='unittest-ocp-test-worker-profile',
                                              RoleName='unittest-ocp-test-worker-role')

    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      resource_name='zombie_cluster_role')
    zombie_cluster_resources.zombie_cluster_role()
    iam_roles = Utils().get_details_resource_list(func_name=iam_resource.list_roles, input_tag='Roles',
                                                  check_tag='Marker')
    find = False
    for role in iam_roles:
        if role['RoleName'] == 'unittest-ocp-test-worker-role':
            find = True
            break
    assert find


@mock_ec2
@mock_iam
@skip(reason='Skipping the zombie cluster user')
def test_delete_iam_cluster_user():
    """
    This method tests the user has successfully deleted or not
    :return:
    """
    iam_resource = boto3.client('iam')
    tags = [
        {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'unitest'}
    ]
    iam_resource.create_user(UserName='unittest-ocp', Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      resource_name='zombie_cluster_user', force_delete=True)
    zombie_cluster_resources.zombie_cluster_user()
    iam_users = iam_resource.list_users()['Users']
    find = False
    for role in iam_users:
        if role['UserName'] == 'unittest-ocp':
            find = True
            break
    assert not find


@mock_ec2
@mock_iam
@skip(reason='Skipping the zombie cluster user')
def test_not_delete_iam_cluster_user():
    """
    This method tests the user has not deleted
    :return:
    """
    iam_resource = boto3.client('iam')
    tags = [
        {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
        {'Key': 'Owner', 'Value': 'unitest'}
    ]
    iam_resource.create_user(UserName='unittest-ocp', Tags=tags)
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      resource_name='zombie_cluster_user')
    zombie_cluster_resources.zombie_cluster_user()
    iam_users = iam_resource.list_users()['Users']
    find = False
    for role in iam_users:
        if role['UserName'] == 'unittest-ocp':
            find = True
            break
    assert find
