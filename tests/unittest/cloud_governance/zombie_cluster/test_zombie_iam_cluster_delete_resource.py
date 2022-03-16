import json

from moto import mock_iam, mock_ec2
import boto3

from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources


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


# @mock_ec2
# @mock_iam
# def test_delete_iam_cluster_role():
#     """
#     This method tests the role is deleted or not
#     --> This method is not working because of Describing the role_policies have empty list
#     :return:
#     """
#     iam_resource = boto3.client('iam')
#     assume_role_policy_document = {
#                                     "Version": "2012-10-17",
#                                     "Statement": [
#                                         {
#                                             "Sid": "",
#                                             "Effect": "Allow",
#                                             "Principal": {
#                                                 "Service": "ec2.amazonaws.com"
#                                             },
#                                             "Action": "sts:AssumeRole"
#                                         }
#                                     ]
#                                 }
#     tags = [
#                 {'Key': 'kubernetes.io/cluster/unittest-test-cluster', 'Value': 'Owned'},
#                 {'Key': 'Owner', 'Value': 'unitest'}
#         ]
#     iam_resource.create_role(AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
#                              RoleName='unittest-ocp-test-role', Tags=tags)
#     policy_output = iam_resource.create_policy(PolicyName='unittest-ocp-test-policy', PolicyDocument=json.dumps(EC2_POLICY), Tags=tags)
#     ps = iam_resource.attach_role_policy(RoleName='unittest-ocp-test-role', PolicyArn=policy_output['Policy']['Arn'])
#
#     iam_resource.create_instance_profile(InstanceProfileName='unittest-ocp-test-profile', Tags=tags)
#     iam_resource.add_role_to_instance_profile(InstanceProfileName='unittest-ocp-test-profile',
#                                               RoleName='unittest-ocp-test-role')
#     zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
#                                                       cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
#                                                       resource_name='zombie_cluster_role')
#     rs1 = iam_resource.list_role_policies(RoleName='unittest-ocp-test-role')
#     rs = iam_resource.list_roles()
#     ss = iam_resource.delete_role_policy(RoleName='unittest-ocp-test-role', PolicyName='unittest-ocp-test-policy')
#     pq = Utils().get_details_resource_list(func_name=iam_resource.list_policies, input_tag='Policies', check_tag='Marker')
#     zombie_cluster_resources. zombie_cluster_role()
#     roles = iam_resource.get_role(RoleName='unittest-ocp-test-role')
#     iam_roles = iam_resource.list_roles()['Roles']
#     find = False
#     for role in iam_roles:
#         if role['RoleName'] == 'unittest-ocp-test-role':
#             find = True
#             break
#     assert not find


@mock_ec2
@mock_iam
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
    iam_roles = iam_resource.list_users()['Users']
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/unittest-test-cluster',
                                                      resource_name='zombie_cluster_user')
    zombie_cluster_resources.zombie_cluster_user()
    iam_roles = iam_resource.list_users()['Users']
    find = False
    for role in iam_roles:
        if role['UserName'] == 'unittest-ocp':
            find = True
            break
    assert not find



