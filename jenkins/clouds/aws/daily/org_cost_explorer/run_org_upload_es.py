import json
import os

AWS_ACCESS_KEY_ID_DELETE_PERF = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF']
AWS_SECRET_ACCESS_KEY_DELETE_PERF = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
ES_USER = os.environ.get('ES_USER', '')
ES_PASSWORD = os.environ.get('ES_PASSWORD', '')
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
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ['QUAY_CLOUD_GOVERNANCE_REPOSITORY']
QUAY_ORION_REPOSITORY = f'{QUAY_CLOUD_GOVERNANCE_REPOSITORY}-orion'
SLACK_API_TOKEN = os.environ.get('SLACK_API_TOKEN', '')
SLACK_CHANNEL_NAME = os.environ.get('SLACK_CHANNEL_NAME', '')
ORION_COST_CENTER = os.environ.get('ORION_COST_CENTER', '')

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

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_user': ES_USER, 'es_password': ES_PASSWORD,
                     'es_index': 'cloud-governance-global-cost-billing-reports',
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
-e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_user="{ES_USER}" -e es_password="{ES_PASSWORD}" \
-e es_index="cloud-governance-clouds-billing-reports" \
-e S3_RESULTS_PATH="{S3_RESULTS_PATH}" \
-e ATHENA_DATABASE_NAME="{ATHENA_DATABASE_NAME}" \
-e ATHENA_TABLE_NAME="{ATHENA_TABLE_NAME}" \
{QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

os.system('echo "Running yearly savings report for all accounts"')
accounts = ['PSAP', 'PERFSCALE', 'PERF-DEPT']

for account in accounts:
    os.system(f'echo "Running yearly savings report for account {account}"')
    os.system(f"""podman run --rm --net="host" --name cloud-governance -e policy="yearly_savings_report" \
-e PUBLIC_CLOUD_NAME="AWS" \
-e account="{account}" \
-e es_host="{ES_HOST}" \
-e es_port="{ES_PORT}" \
-e es_user="{ES_USER}" \
-e es_password="{ES_PASSWORD}" \
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
    :return: the raw os.system status (0 on success)
    :rtype: int
    """
    return os.system(cmd)


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
    'es_host': ES_HOST, 'es_port': ES_PORT, 'es_user': ES_USER, 'es_password': ES_PASSWORD,
    'es_index': COST_ES_INDEX,
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

if SLACK_API_TOKEN and SLACK_CHANNEL_NAME and ORION_COST_CENTER:
    ORION_COST_ACCOUNT = f'CC{ORION_COST_CENTER}'
    ORION_COST_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))), 'orion-configs', 'cg-cost-regressions.yaml')
    # Must stay in sync with the top-level test names in cg-cost-regressions.yaml.
    # One metric per test block there (not multiple metrics sharing one block):
    # Orion only resolves the "value" field correctly for the first metric in a
    # given test block, silently nulling every metric after it - confirmed live
    # against real data. So one Orion invocation now produces one output/data
    # file pair per test name, which are merged below into a single alert.
    ORION_COST_TEST_NAMES = [
        'totalCostIncrease', 'totalCostDecrease',
        'awsCostIncrease', 'awsCostDecrease',
        'azureCostIncrease', 'azureCostDecrease',
        'ibmCostIncrease', 'ibmCostDecrease',
    ]
    ORION_COST_INDEX = 'cloud-governance-orion-cost-metrics-index'

    es_scheme = 'https' if str(ES_PORT) == '443' else 'http'
    es_auth = f'{ES_USER}:{ES_PASSWORD}@' if ES_USER else ''
    es_server = f'{es_scheme}://{es_auth}{ES_HOST}:{ES_PORT}'
    orion_cost_output_base = f'/tmp/orion-cost-output-{ORION_COST_ACCOUNT}.json'
    orion_cost_data_base = f'/tmp/orion-cost-data-{ORION_COST_ACCOUNT}.csv'
    orion_cost_output_files = [f'/tmp/orion-cost-output-{ORION_COST_ACCOUNT}_{name}.json' for name in ORION_COST_TEST_NAMES]
    orion_cost_data_files = [f'/tmp/orion-cost-data-{ORION_COST_ACCOUNT}-{name}.csv' for name in ORION_COST_TEST_NAMES]
    orion_cost_merged_file = f'/tmp/orion-cost-output-{ORION_COST_ACCOUNT}-merged.json'

    run_shell_cmd('rm -f ' + ' '.join(f'"{f}"' for f in orion_cost_output_files + orion_cost_data_files + [orion_cost_merged_file]))

    run_shell_cmd("echo Running Orion cost metrics rollup")
    rollup_status = run_shell_cmd(
        f"""podman run --rm --net="host" --name cloud-governance -e policy="orion_cost_metrics_rollup" -e orion_cost_center="{ORION_COST_CENTER}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_user="{ES_USER}" -e es_password="{ES_PASSWORD}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

    if rollup_status != 0:
        run_shell_cmd("echo Skipping Orion cost analysis and alert - metrics rollup failed")
    else:
        try:
            run_shell_cmd("echo Running Orion cost regression analysis")
            # Orion exits non-zero (2) when it detects regressions, so its exit
            # status cannot gate the next step; presence of output files, which
            # are written only when analysis completes, is used instead.
            run_shell_cmd(
                f"""podman run --rm --name orion --net="host" -v "{ORION_COST_CONFIG_PATH}":"{ORION_COST_CONFIG_PATH}" -v /tmp:/tmp {QUAY_ORION_REPOSITORY} --es-server="{es_server}" --benchmark-index="{ORION_COST_INDEX}" --metadata-index="{ORION_COST_INDEX}" --hunter-analyze --input-vars='{{"account": "{ORION_COST_ACCOUNT}"}}' --config "{ORION_COST_CONFIG_PATH}" --output-format json --save-output-path "{orion_cost_output_base}" --save-data-path "{orion_cost_data_base}" """)

            merged_data_points = []
            for output_file in orion_cost_output_files:
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        merged_data_points.extend(json.load(f))

            if merged_data_points:
                with open(orion_cost_merged_file, 'w', encoding='utf-8') as f:
                    json.dump(merged_data_points, f)
                run_shell_cmd("echo Running Orion cost Slack alert handler")
                run_shell_cmd(
                    f"""podman run --rm --name cloud-governance --net="host" -v /tmp:/tmp -e account="{ORION_COST_ACCOUNT}" -e policy="orion_alert_handler" -e ORION_OUTPUT_FILE="{orion_cost_merged_file}" -e SLACK_API_TOKEN="{SLACK_API_TOKEN}" -e SLACK_CHANNEL_NAME="{SLACK_CHANNEL_NAME}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
            else:
                run_shell_cmd("echo Skipping Orion cost alert - analysis produced no output")
        finally:
            run_shell_cmd('rm -f ' + ' '.join(f'"{f}"' for f in orion_cost_output_files + orion_cost_data_files + [orion_cost_merged_file]))
else:
    run_shell_cmd("echo Skipping Orion cost-regression detection - SLACK_API_TOKEN/SLACK_CHANNEL_NAME/ORION_COST_CENTER not configured")
