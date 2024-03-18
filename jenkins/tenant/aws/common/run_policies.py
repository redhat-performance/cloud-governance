import os
from ast import literal_eval


def get_policies(file_type: str = '.py', exclude_policies: list = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of custodian policies name
    """
    exclude_policies = [] if not exclude_policies else exclude_policies
    custodian_policies = []
    root_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    policies_path = os.path.join(root_folder, 'cloud_governance', 'policy', 'aws')
    for (_, _, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not filename.startswith('__') and filename.endswith(file_type):
                if filename.split('.')[0] not in exclude_policies:
                    if not file_type:
                        custodian_policies.append(os.path.splitext(filename)[0])
                    elif file_type and file_type in filename:
                        custodian_policies.append(os.path.splitext(filename)[0])
    return custodian_policies


exclude_policies = ['cost_explorer', 'optimize_resources_report', 'monthly_report', 'cost_over_usage',
                    'skipped_resources', 'cost_explorer_payer_billings', 'cost_billing_reports', 'spot_savings_analysis']
available_policies = get_policies(exclude_policies=exclude_policies)
# available_policies: Run policies in dry_run="yes" mode


def run_cmd(cmd: str):
    """
    This method run the command
    :param cmd:
    :type cmd:
    :return:
    :rtype:
    """
    os.system(cmd)


def get_container_cmd(env_dict: dict):
    create_container_envs = lambda item: f'-e {item[0]}="{item[1]}"'
    env_list = ' '.join(list(map(create_container_envs, env_dict.items())))
    container_name = "cloud-governance-poc-haim"
    container_run_cmd = f"""
podman run --rm --name "{container_name}" --net="host" {env_list}  quay.io/ebattat/cloud-governance:latest
"""
    return container_run_cmd


access_key = os.environ['access_key']
secret_key = os.environ['secret_key']
s3_bucket = os.environ['s3_bucket']
account_name = os.environ['account_name']
days_to_delete_resource = os.environ.get('days_to_delete_resource', 14)
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
LOGS = os.environ.get('LOGS', 'logs')
ALERT_DRY_RUN = os.environ.get('ALERT_DRY_RUN', False)
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
SPREADSHEET_ID = os.environ['AWS_IAM_USER_SPREADSHEET_ID']
ADMIN_MAIL_LIST = os.environ.get('ADMIN_MAIL_LIST', '')
CLOUD_GOVERNANCE_IMAGE = "quay.io/ebattat/cloud-governance:latest"

policies_in_action = os.environ.get('POLICIES_IN_ACTION', [])
if isinstance(policies_in_action, str):
    policies_in_action = literal_eval(policies_in_action)
policies_not_action = list(set(available_policies) - set(policies_in_action))


regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'ap-south-1', 'eu-north-1', 'eu-west-3', 'eu-west-2',
           'eu-west-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-northeast-1', 'ca-central-1', 'sa-east-1',
           'ap-southeast-1', 'ap-southeast-2', 'eu-central-1']

es_doc_type = '_doc'

container_env_dict = {
    "account": account_name, "AWS_DEFAULT_REGION": "us-east-1", "PUBLIC_CLOUD_NAME": "AWS",
    "AWS_ACCESS_KEY_ID": access_key, "AWS_SECRET_ACCESS_KEY": secret_key,
    "dry_run": "yes", "LDAP_HOST_NAME": LDAP_HOST_NAME, "DAYS_TO_DELETE_RESOURCE": days_to_delete_resource,
    "es_host": ES_HOST, "es_port": ES_PORT,
    "MANAGER_EMAIL_ALERT": "False", "EMAIL_ALERT": "False", "log_level": "INFO",
    'DAYS_TO_TAKE_ACTION': days_to_delete_resource, 'ALERT_DRY_RUN': ALERT_DRY_RUN
}


def run_policies(policies: list, dry_run: str = 'yes'):
    for region in regions:
        container_env_dict.update({"policy_output": f"s3://{s3_bucket}/{LOGS}/{region}", "AWS_DEFAULT_REGION": region,
                                   'dry_run': dry_run})
        for policy in policies:
            container_env_dict.update({"AWS_DEFAULT_REGION": region, 'policy': policy})
            container_cmd = ''
            if policy in ('empty_roles', 's3_inactive') and region == 'us-east-1':
                container_cmd = get_container_cmd(container_env_dict)
            else:
                if policy not in ('empty_roles', 's3_inactive'):
                    container_cmd = get_container_cmd(container_env_dict)
            if container_cmd:
                run_cmd(container_cmd)


run_cmd(f"echo Running the cloud_governance policies with dry_run=yes")
run_cmd(f"echo Polices list: {policies_not_action}")
run_policies(policies=policies_not_action)

run_cmd('echo "Running the CloudGovernance policies with dry_run=no" ')
run_cmd(f"echo Polices list: {policies_in_action}")
run_policies(policies=policies_in_action, dry_run='no')


run_cmd(f"""echo "Running the tag_iam_user" """)
run_cmd(f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e account="{account_name}" -e EMAIL_ALERT="False" -e policy="tag_iam_user" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e user_tag_operation="update" -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}"  -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")


# Run the AggMail

run_cmd(f"""podman run --rm --name cloud-governance-haim --net="host" -e account="{account_name}" -e policy="send_aggregated_alerts" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}"  -e log_level="INFO" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e ADMIN_MAIL_LIST="{ADMIN_MAIL_LIST}" {CLOUD_GOVERNANCE_IMAGE}""")
