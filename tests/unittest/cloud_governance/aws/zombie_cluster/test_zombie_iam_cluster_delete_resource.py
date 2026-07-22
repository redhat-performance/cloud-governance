import json
import pytest
from moto import mock_aws
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


@mock_aws
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

    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
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


@mock_aws
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

    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
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


@mock_aws
@pytest.mark.skip(reason='Skipping the zombie cluster user')
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
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


@mock_aws
@pytest.mark.skip(reason='Skipping the zombie cluster user')
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
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix=["kubernetes.io/cluster", "sigs.k8s.io/cluster-api-provider-aws/cluster"], delete=True,
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


# ---------------------------------------------------------------------------
# Role return type fix + cross-prefix IAM detection
# ---------------------------------------------------------------------------

CLUSTER_PREFIX_IAM = ['kubernetes.io/cluster', 'sigs.k8s.io/cluster-api-provider-aws/cluster']
CLUSTER_NAME_IAM = 'unittest-test-cluster-abc123'
K8S_TAG_IAM = f'kubernetes.io/cluster/{CLUSTER_NAME_IAM}'
CAPA_TAG_IAM = f'sigs.k8s.io/cluster-api-provider-aws/cluster/{CLUSTER_NAME_IAM}'
REGION_IAM = 'us-east-2'


@mock_aws
def test_zombie_cluster_role_returns_dict():
    """zombie_cluster_role should return a dict (not list) as the first element of the tuple."""
    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX_IAM, delete=False, region=REGION_IAM)
    zombies, _ = zcr.zombie_cluster_role()
    assert isinstance(zombies, dict)


@mock_aws
def test_iam_role_cross_prefix_not_zombie():
    """
    IAM role tagged with sigs.k8s.io prefix, EC2 instance with kubernetes.io prefix.
    Same cluster name — role should NOT be detected as zombie.
    """
    ec2_client = boto3.client('ec2', region_name=REGION_IAM)
    ec2_resource = boto3.resource('ec2', region_name=REGION_IAM)
    iam_client = boto3.client('iam', region_name=REGION_IAM)

    vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    subnet = ec2_client.create_subnet(VpcId=vpc['Vpc']['VpcId'], CidrBlock='10.0.1.0/24')

    ec2_resource.create_instances(
        ImageId='ami-03cf127a', MinCount=1, MaxCount=1,
        SubnetId=subnet['Subnet']['SubnetId'],
        TagSpecifications=[{'ResourceType': 'instance',
                           'Tags': [{'Key': K8S_TAG_IAM, 'Value': 'owned'}]}]
    )

    assume_role_doc = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},
                       "Action": "sts:AssumeRole"}]
    })
    role_name = f'{CLUSTER_NAME_IAM}-worker-role'
    iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=assume_role_doc,
        Tags=[{'Key': CAPA_TAG_IAM, 'Value': 'owned'}]
    )

    zcr = ZombieClusterResources(cluster_prefix=CLUSTER_PREFIX_IAM, delete=False, region=REGION_IAM)
    zombies, _ = zcr.zombie_cluster_role()

    assert role_name not in zombies
