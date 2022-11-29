import json
import os

import boto3
from moto import mock_ec2, mock_iam

from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'

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
AssumeRolePolicyDocument = json.dumps(assume_role_policy_document)


@mock_ec2
@mock_iam
def test_empty_roles():
    """
    This method tests delete of empty roles
    @return:
    """
    os.environ['policy'] = 'empty_roles'
    iam_client = boto3.client('iam')
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName='CloudGovernanceTestEmptyRole')
    empty_roles = NonClusterZombiePolicy()
    empty_roles.set_dryrun(value='no')
    empty_roles.set_policy(value='empty_roles')
    empty_roles.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    empty_roles._check_resource_and_delete(resource_name='IAM Role',
                                           resource_id='RoleName',
                                           resource_type='CreateRole',
                                           resource=iam_client.list_roles()['Roles'][0],
                                           empty_days=0,
                                           days_to_delete_resource=0)
    roles = iam_client.list_roles()['Roles']
    assert len(roles) == 0


@mock_ec2
@mock_iam
def test_empty_roles_not_delete():
    """
    This method tests not delete of empty roles, if policy=NOT_DELETE
    @return:
    """
    os.environ['policy'] = 'empty_roles'
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestEmptyRole'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'notdelete'}
    ]
    iam_client = boto3.client('iam')
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName='CloudGovernanceTestEmptyRole',
                           Tags=tags)
    empty_roles = NonClusterZombiePolicy()
    empty_roles.set_dryrun(value='no')
    empty_roles.set_policy(value='empty_roles')
    empty_roles.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    empty_roles._check_resource_and_delete(resource_name='IAM Role',
                                           resource_id='RoleName',
                                           resource_type='CreateRole',
                                           resource=iam_client.list_roles()['Roles'][0],
                                           empty_days=0,
                                           days_to_delete_resource=0, tags=tags)
    roles = iam_client.list_roles()['Roles']
    assert len(roles) == 1
