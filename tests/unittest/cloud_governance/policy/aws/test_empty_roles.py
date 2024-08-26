import json

from moto import mock_ec2, mock_iam

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.common_methods import get_tag_value_from_tags
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.empty_roles import EmptyRoles
from tests.unittest.configs import DRY_RUN_YES, AWS_DEFAULT_REGION, TEST_USER_NAME, CURRENT_DATE, DRY_RUN_NO, \
     PROJECT_NAME

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
