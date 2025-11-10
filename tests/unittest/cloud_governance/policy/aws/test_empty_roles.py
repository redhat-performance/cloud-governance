import json
from datetime import date

from moto import mock_ec2, mock_iam
from unittest.mock import patch

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.common_methods import get_tag_value_from_tags
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.empty_roles import EmptyRoles
from tests.unittest.configs import DRY_RUN_YES, AWS_DEFAULT_REGION, TEST_USER_NAME, CURRENT_DATE, DRY_RUN_NO, \
     PROJECT_NAME

TODAY = date.today().strftime('%Y-%m-%d')

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

managed_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "IAMListPolicy",
            "Effect": "Allow",
            "Action": [
                "iam:List*",
            ],
            "Resource": "*"
        }
    ]
}

policy_document = json.dumps(managed_policy)


def setup_empty_role_with_ip(iam_client, role_name, ip_name, days_count=0):
    """Helper to create an empty role attached to an instance profile."""
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@{days_count}'}]

    # 1. Create the empty role
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=role_name, Tags=tags)

    # 2. Create the instance profile
    iam_client.create_instance_profile(InstanceProfileName=ip_name)

    # 3. Attach the role to the instance profile
    iam_client.add_role_to_instance_profile(InstanceProfileName=ip_name, RoleName=role_name)

    return tags

@mock_ec2
@mock_iam
def test_empty_roles():
    """
    This method tests lists empty roles
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['DAYS_TO_TAKE_ACTION'] = 7
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'
    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}]
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=PROJECT_NAME, Tags=tags)
    # run empty_roles
    assert len(iam_operations.get_roles()) == 1
    empty_roles = EmptyRoles()
    response = empty_roles.run()
    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 1
    assert get_tag_value_from_tags(tags=iam_operations.get_role(role_name=PROJECT_NAME).get('Tags', []),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@1"


@mock_ec2
@mock_iam
def test_empty_roles_dry_run_yes():
    """
    This method tests collects empty roles  on dry_run=yes
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=PROJECT_NAME, Tags=tags)
    # run empty_roles
    empty_roles = EmptyRoles()
    response = empty_roles.run()
    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0
    assert get_tag_value_from_tags(tags=iam_operations.get_role(role_name=PROJECT_NAME).get('Tags', []),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"


@mock_ec2
@mock_iam
def test_empty_roles_delete():
    """
    This method tests delete empty role
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=PROJECT_NAME, Tags=tags)
    iam_operations.tag_role(role_name=PROJECT_NAME, tags=tags)
    # run empty_roles
    empty_roles = EmptyRoles()
    response = empty_roles.run()
    assert len(iam_operations.get_roles()) == 0
    assert len(response) == 1


@mock_ec2
@mock_iam
def test_empty_roles_skip():
    """
    This method tests skip delete of the empty role
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'},
            {'Key': 'policy', 'Value': 'not-delete'}]
    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=PROJECT_NAME, Tags=tags)
    # run empty_roles
    empty_roles = EmptyRoles()
    response = empty_roles.run()
    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 0
    assert get_tag_value_from_tags(tags=iam_operations.get_role(role_name=PROJECT_NAME).get('Tags', []),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"


@mock_ec2
@mock_iam
def test_empty_roles_contains_cluster_tag():
    """
    This method tests role having the live cluster
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'},
            {'Key': 'policy', 'Value': 'not-delete'},
            {'Key': 'kubernetes.io/cluster/test-zombie-cluster', 'Value': f'owned'}]
    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=PROJECT_NAME, Tags=tags)
    # run empty_roles
    empty_roles = EmptyRoles()
    response = empty_roles.run()
    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 0
    assert get_tag_value_from_tags(tags=iam_operations.get_role(role_name=PROJECT_NAME).get('Tags', []),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"


@mock_ec2
@mock_iam
def test_empty_roles_contains_attached_policy():
    """
    This method tests role having attached policy
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=PROJECT_NAME, Tags=tags)
    response = iam_client.create_policy(PolicyName=PROJECT_NAME, PolicyDocument=policy_document).get('Policy')
    iam_client.attach_role_policy(PolicyArn=response.get('Arn'), RoleName=PROJECT_NAME)
    # run empty_roles
    empty_roles = EmptyRoles()
    response = empty_roles.run()
    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 0
    assert get_tag_value_from_tags(tags=iam_operations.get_role(role_name=PROJECT_NAME).get('Tags', []),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"


@mock_ec2
@mock_iam
def test_empty_roles_contains_inline_policy():
    """
    This method tests role having inline policy
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client
    iam_client.create_role(AssumeRolePolicyDocument=AssumeRolePolicyDocument, RoleName=PROJECT_NAME, Tags=tags)
    iam_client.put_role_policy(RoleName=PROJECT_NAME, PolicyName=PROJECT_NAME, PolicyDocument=policy_document)
    # run empty_roles
    empty_roles = EmptyRoles()
    response = empty_roles.run()
    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 0
    assert get_tag_value_from_tags(tags=iam_operations.get_role(role_name=PROJECT_NAME).get('Tags', []),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"

@mock_ec2
@mock_iam
def test_empty_roles_with_instance_profile_live_delete():
    """
    Tests successful detachment of Instance Profile and subsequent deletion.
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'

    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client

    setup_empty_role_with_ip(iam_client,
                             role_name=PROJECT_NAME,
                             ip_name=f"{PROJECT_NAME}-ip",
                             days_count=7)

    assert len(iam_operations.get_roles()) == 1
    assert len(iam_operations.get_instance_profiles_for_role(PROJECT_NAME)) == 1

    empty_roles = EmptyRoles()
    response = empty_roles.run()

    assert len(iam_operations.get_roles()) == 0
    assert len(response) == 1


@mock_ec2
@mock_iam
def test_empty_roles_with_instance_profile_dry_run_check():
    """
    Tests that detachment is skipped in dry_run=yes, and the flow proceeds to the deletion check.
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'

    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client

    setup_empty_role_with_ip(iam_client,
                             role_name=PROJECT_NAME,
                             ip_name=f"{PROJECT_NAME}-ip",
                             days_count=3)

    assert len(iam_operations.get_roles()) == 1

    empty_roles = EmptyRoles()
    response = empty_roles.run()
    print(response)

    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0
    assert len(iam_operations.get_instance_profiles_for_role(PROJECT_NAME)) == 1


@mock_ec2
@mock_iam
@patch('cloud_governance.policy.helpers.aws.aws_policy_operations.AWSPolicyOperations.update_resource_tags')
@patch('cloud_governance.common.clouds.aws.iam.iam_operations.IAMOperations.remove_role_from_instance_profiles',
       return_value=False)
def test_empty_roles_failed_detachment_skip_deletion(mock_remove_role, mock_update_resource_tags):
    """
    Tests the failure flow: If live detachment fails (returns False), deletion and ES logging must be skipped,
    but the tag must be updated.
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 'empty_roles'

    iam_operations = IAMOperations()
    iam_client = iam_operations.get_iam_client

    setup_empty_role_with_ip(iam_client,
                             role_name=PROJECT_NAME,
                             ip_name=f"{PROJECT_NAME}-ip",
                             days_count=0)

    def mock_tag_update_side_effect(tags, resource_id):
        new_tag_value = get_tag_value_from_tags(tags=tags, tag_name='DaysCount')
        iam_client.tag_role(RoleName=resource_id, Tags=[{'Key': 'DaysCount', 'Value': new_tag_value}])

    mock_update_resource_tags.side_effect = mock_tag_update_side_effect

    empty_roles = EmptyRoles()

    response = empty_roles.run()

    assert len(iam_operations.get_roles()) == 1
    assert len(response) == 0

    assert mock_update_resource_tags.called
    assert get_tag_value_from_tags(tags=iam_operations.get_role(role_name=PROJECT_NAME).get('Tags', []),
                                   tag_name='DaysCount') == f"{TODAY}@1"
