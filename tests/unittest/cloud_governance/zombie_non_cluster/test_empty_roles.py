import json
import os

import boto3
from moto import mock_ec2, mock_iam
from cloud_governance.policy.empty_roles import EmptyRoles

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
    iam_client = boto3.client('iam')
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName='CloudGovernanceTestEmptyRole')
    empty_roles = EmptyRoles()
    empty_roles.run()
    roles = iam_client.list_roles()['Roles']
    assert len(roles) == 0


@mock_ec2
@mock_iam
def test_empty_roles_not_delete():
    """
    This method tests not delete of empty roles, if policy=NOT_DELETE
    @return:
    """
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestEmptyRole'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'notdelete'}
    ]
    iam_client = boto3.client('iam')
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName='CloudGovernanceTestEmptyRole', Tags=tags)
    empty_roles = EmptyRoles()
    empty_roles.run()
    roles = iam_client.list_roles()['Roles']
    assert len(roles) == 1
