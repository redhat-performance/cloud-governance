import os
from ast import literal_eval

account_name = os.environ['account_name']
AZURE_CLIENT_SECRET = os.environ['client_secret']
AZURE_TENANT_ID = os.environ['tenant_id']
AZURE_ACCOUNT_ID = os.environ['account_id']
AZURE_CLIENT_ID = os.environ['client_id']
AZURE_SUBSCRIPTION_ID = os.environ['subscription_id']
days_to_delete_resource = os.environ.get('days_to_delete_resource', 7)
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
LOGS = os.environ.get('LOGS', 'logs')
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')


def get_policies(file_type: str = '.py', exclude_policies: list = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of custodian policies name
    """
    exclude_policies = [] if not exclude_policies else exclude_policies
    custodian_policies = []
    root_folder = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
    policies_path = os.path.join(root_folder, 'cloud_governance', 'policy', 'azure')
    for (_, _, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not filename.startswith('__') and filename.endswith(file_type):
                if filename.split('.')[0] not in exclude_policies:
                    if not file_type:
                        custodian_policies.append(os.path.splitext(filename)[0])
                    elif file_type and file_type in filename:
                        custodian_policies.append(os.path.splitext(filename)[0])
    return custodian_policies


GLOBAL_COST_POLICIES = ['cost_billing_reports', 'tag_azure_resource_group']
available_policies = get_policies(exclude_policies=GLOBAL_COST_POLICIES)


# # available_policies: Run policies in dry_run="yes" mode


def run_cmd(cmd: str):
    """
    This method runs the shell command
    :param cmd:
    :type cmd:
    :return:
    :rtype:
    """
    os.system(cmd)


def get_container_cmd(env_dict: dict):
    env_list = ' '.join(list(map(lambda item: f'-e {item[0]}="{item[1]}"', env_dict.items())))
    container_name = "cloud-governance"
    container_run_cmd = f"""podman run --rm --name "{container_name}" --net="host" {env_list}  {QUAY_CLOUD_GOVERNANCE_REPOSITORY}"""
    return container_run_cmd


policies_in_action = os.environ.get('POLICIES_IN_ACTION', [])
if isinstance(policies_in_action, str):
    policies_in_action = literal_eval(policies_in_action)
policies_not_action = list(set(available_policies) - set(policies_in_action))

container_env_dict = {
    "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
    "AZURE_TENANT_ID": AZURE_TENANT_ID,
    "AZURE_ACCOUNT_ID": AZURE_ACCOUNT_ID,
    "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
    "AZURE_SUBSCRIPTION_ID": AZURE_SUBSCRIPTION_ID,
    "account": account_name,
    "PUBLIC_CLOUD_NAME": "Azure",
    "dry_run": "yes",
    "LDAP_HOST_NAME": LDAP_HOST_NAME,
    "DAYS_TO_DELETE_RESOURCE": days_to_delete_resource,
    "es_host": ES_HOST, "es_port": ES_PORT,
    "MANAGER_EMAIL_ALERT": "False", "EMAIL_ALERT": "False", "log_level": "INFO",
    'DAYS_TO_TAKE_ACTION': days_to_delete_resource,
}


def run_policies(policies: list, dry_run: str = 'yes'):
    container_env_dict.update({})
    for policy in policies:
        container_env_dict.update({'dry_run': dry_run, 'policy': policy})
        container_cmd = get_container_cmd(container_env_dict)
        run_cmd(container_cmd)


# Running the polices in dry_run=yes

run_cmd(f"echo Running the cloud_governance policies with dry_run=yes")
run_cmd(f"echo Polices list: {policies_not_action}")
run_policies(policies=policies_not_action)

# Running the polices in dry_run=no

run_cmd('echo "Running the CloudGovernance policies with dry_run=no" ')
run_cmd(f"echo Polices list: {policies_in_action}")
run_policies(policies=policies_in_action, dry_run='no')
