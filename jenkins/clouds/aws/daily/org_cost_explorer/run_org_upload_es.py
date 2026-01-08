import os

AWS_ACCESS_KEY_ID_DELETE_PERF = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF']
AWS_SECRET_ACCESS_KEY_DELETE_PERF = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
COST_SPREADSHEET_ID = os.environ['COST_SPREADSHEET_ID']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
AWS_ACCOUNT_ROLE = os.environ['AWS_ACCOUNT_ROLE']
COST_CENTER_OWNER = os.environ['COST_CENTER_OWNER']
REPLACE_ACCOUNT_NAME = os.environ['REPLACE_ACCOUNT_NAME']
PAYER_SUPPORT_FEE_CREDIT = os.environ['PAYER_SUPPORT_FEE_CREDIT']
AWS_ACCESS_KEY_ID_ATHIRUMA_BOT = os.environ['AWS_ACCESS_KEY_ID_ATHIRUMA_BOT']
AWS_SECRET_ACCESS_KEY_ATHIRUMA_BOT = os.environ['AWS_SECRET_ACCESS_KEY_ATHIRUMA_BOT']
S3_RESULTS_PATH = os.environ['S3_RESULTS_PATH']
ATHENA_DATABASE_NAME = os.environ['ATHENA_DATABASE_NAME']
ATHENA_TABLE_NAME = os.environ['ATHENA_TABLE_NAME']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

# Cloudability env variables

CLOUDABILITY_API = os.environ['CLOUDABILITY_API']
CLOUDABILITY_API_REPORTS_PATH = os.environ['CLOUDABILITY_API_REPORTS_PATH']
CLOUDABILITY_METRICS = os.environ['CLOUDABILITY_METRICS']
CLOUDABILITY_VIEW_ID = os.environ['CLOUDABILITY_VIEW_ID']
APPITO_KEY_ACCESS = os.environ['APPITO_KEY_ACCESS']
APPITO_KEY_SECRET = os.environ['APPITO_KEY_SECRET']
APPITO_ENVID = os.environ['APPITO_ENVID']

os.system('echo "Updating the Org level cost billing reports"')

# Cost Explorer upload to ElasticSearch
cost_metric = 'UnblendedCost'  # UnblendedCost/BlendedCost
granularity = 'DAILY'  # DAILY/MONTHLY/HOURLY

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': 'cloud-governance-global-cost-billing-reports',
                     'log_level': 'INFO', 'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS,
                     'COST_CENTER_OWNER': f"{COST_CENTER_OWNER}", 'REPLACE_ACCOUNT_NAME': REPLACE_ACCOUNT_NAME,
                     'PAYER_SUPPORT_FEE_CREDIT': PAYER_SUPPORT_FEE_CREDIT}
combine_vars = lambda item: f'{item[0]}="{item[1]}"'

common_input_vars['es_index'] = 'cloud-governance-clouds-billing-reports'
common_envs = list(map(combine_vars, common_input_vars.items()))
os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e policy="cost_explorer_payer_billings" -e AWS_ACCOUNT_ROLE="{AWS_ACCOUNT_ROLE}" -e account="PERF-DEPT" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(common_envs)} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

os.system('echo "Run the Spot Analysis report over the account using AWS Athena"')
os.system(f"""podman run --rm --net="host" --name cloud-governance -e policy="spot_savings_analysis" -e account="pnt-payer" \
-e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_ATHIRUMA_BOT}" \
-e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_ATHIRUMA_BOT}" \
-e es_host="{ES_HOST}" -e es_port="{ES_PORT}" \
-e es_index="cloud-governance-clouds-billing-reports" \
-e S3_RESULTS_PATH="{S3_RESULTS_PATH}" \
-e ATHENA_DATABASE_NAME="{ATHENA_DATABASE_NAME}" \
-e ATHENA_TABLE_NAME="{ATHENA_TABLE_NAME}" \
{QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

os.system('echo "Running yearly savings report"')
os.system(f"""podman run --rm --net="host" --name cloud-governance -e policy="yearly_savings_report" \
-e es_host="{ES_HOST}" \
-e es_port="{ES_PORT}" \
-e es_index="cloud-governance-policy-es-index" \
-e log_level="INFO" \
{QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

CONTAINER_NAME = "cloud-governance"
COST_ES_INDEX = "cloud-governance-clouds-billing-reports"
CLOUDABILITY_POLICY = 'cloudability_cost_reports'


def run_shell_cmd(cmd: str):
    """
    This method run the shell command
    :param cmd:
    :type cmd:
    :return:
    :rtype:
    """
    os.system(cmd)


def generate_shell_cmd(policy: str, env_variables: dict, mounted_volumes: str = ''):
    """
    This method returns the shell command
    :param mounted_volumes:
    :type mounted_volumes:
    :param env_variables:
    :type env_variables:
    :param policy:
    :type policy:
    :return:
    :rtype:
    """
    inject_container_envs = ' '.join(list(map(lambda item: f'-e {item[0]}="{item[1]}"', env_variables.items())))
    return (f'podman run --rm --net="host" --name {CONTAINER_NAME} -e policy="{policy}" {inject_container_envs} {mounted_volumes} '
            f'{QUAY_CLOUD_GOVERNANCE_REPOSITORY}')


common_env_vars = {
    'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': COST_ES_INDEX,
    'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS,
    'SPREADSHEET_ID': COST_SPREADSHEET_ID,
}

cloudability_env_vars = {
    'CLOUDABILITY_API': CLOUDABILITY_API,
    'CLOUDABILITY_API_REPORTS_PATH': CLOUDABILITY_API_REPORTS_PATH,
    'CLOUDABILITY_METRICS': CLOUDABILITY_METRICS,
    'CLOUDABILITY_VIEW_ID': CLOUDABILITY_VIEW_ID,
    'APPITO_KEY_ACCESS': APPITO_KEY_ACCESS,
    'APPITO_KEY_SECRET': APPITO_KEY_SECRET,
    'APPITO_ENVID': APPITO_ENVID,
}

mounted_volumes = f" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS}"
cloudability_run_command = generate_shell_cmd(policy=CLOUDABILITY_POLICY,
                                              env_variables={
                                                  **common_env_vars,
                                                  **cloudability_env_vars
                                              }, mounted_volumes=mounted_volumes)

run_shell_cmd(f"echo Running the {CLOUDABILITY_POLICY}")
run_shell_cmd(cloudability_run_command)
