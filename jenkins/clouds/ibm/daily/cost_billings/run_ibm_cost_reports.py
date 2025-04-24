import os

LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
IBM_API_KEY_PERFORMANCE_SCALE = os.environ['IBM_API_KEY_PERFORMANCE_SCALE']
IBM_API_USERNAME_PERFORMANCE_SCALE = os.environ['IBM_API_USERNAME_PERFORMANCE_SCALE']
USAGE_REPORTS_APIKEY_PERFORMANCE_SCALE = os.environ['USAGE_REPORTS_APIKEY_PERFORMANCE_SCALE']
IBM_ACCOUNT_ID_PERFORMANCE_SCALE = os.environ['IBM_ACCOUNT_ID_PERFORMANCE_SCALE']
IBM_API_USERNAME_CERTIFICATION_CE = os.environ['IBM_API_USERNAME_CERTIFICATION_CE']
IBM_API_KEY_CERTIFICATION_CE = os.environ['IBM_API_KEY_CERTIFICATION_CE']
IBM_ACCOUNT_ID_CERTIFICATION_CE = os.environ['IBM_ACCOUNT_ID_CERTIFICATION_CE']
USAGE_REPORTS_APIKEY_CERTIFICATION_CE = os.environ['USAGE_REPORTS_APIKEY_CERTIFICATION_CE']
SPREADSHEET_ID = os.environ['COST_SPREADSHEET_ID']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
LOGS = os.environ.get('LOGS', 'logs')
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

print('Run IBM Cost Forecast, Budget upload monthly')

es_index = 'cloud-governance-clouds-billing-reports'

key_list = [{"account": "performance-scale", "IBM_API_USERNAME": IBM_API_USERNAME_PERFORMANCE_SCALE,
             "IBM_API_KEY": IBM_API_KEY_PERFORMANCE_SCALE,
             "USAGE_REPORTS_APIKEY": USAGE_REPORTS_APIKEY_PERFORMANCE_SCALE,
             "IBM_ACCOUNT_ID": IBM_ACCOUNT_ID_PERFORMANCE_SCALE},
            {"account": "certification-ce", "IBM_API_USERNAME": IBM_API_USERNAME_CERTIFICATION_CE,
             "IBM_API_KEY": IBM_API_KEY_CERTIFICATION_CE, "USAGE_REPORTS_APIKEY": USAGE_REPORTS_APIKEY_CERTIFICATION_CE,
             "IBM_ACCOUNT_ID": IBM_ACCOUNT_ID_CERTIFICATION_CE}]

for keys in key_list:
    os.system(
        f"""podman run --rm --name cloud-governance -e account="{keys.get('account')}" -e COST_CENTER_OWNER="Shai" -e policy="cost_billing_reports" -e es_index="{es_index}" -e es_port="{ES_PORT}" -e es_host="{ES_HOST}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS} -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e "IBM_API_USERNAME"="{keys.get('IBM_API_USERNAME')}" -e IBM_API_KEY="{keys.get('IBM_API_KEY')}" -e USAGE_REPORTS_APIKEY="{keys.get('USAGE_REPORTS_APIKEY')}" -e IBM_ACCOUNT_ID="{keys.get('IBM_ACCOUNT_ID')}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

# Cloudability reports
# Cloudability env variables
CLOUDABILITY_API = os.environ['CLOUDABILITY_API']
CLOUDABILITY_API_REPORTS_PATH = os.environ['CLOUDABILITY_API_REPORTS_PATH']
CLOUDABILITY_METRICS = os.environ['CLOUDABILITY_METRICS']
CLOUDABILITY_VIEW_ID = os.environ['CLOUDABILITY_VIEW_ID']
APPITO_KEY_ACCESS = os.environ['APPITO_KEY_ACCESS']
APPITO_KEY_SECRET = os.environ['APPITO_KEY_SECRET']
APPITO_ENVID = os.environ['APPITO_ENVID']


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
    return (f'podman run --rm --name cloud-governance -e policy="{policy}" {inject_container_envs} {mounted_volumes} '
            f'{QUAY_CLOUD_GOVERNANCE_REPOSITORY}')


def run_shell_cmd(cmd: str):
    """
    This method runs the shell command
    :param cmd:
    :type cmd:
    :return:
    :rtype:
    """
    os.system(cmd)


cloudability_env_vars = {
    'CLOUDABILITY_API': CLOUDABILITY_API,
    'CLOUDABILITY_API_REPORTS_PATH': CLOUDABILITY_API_REPORTS_PATH,
    'CLOUDABILITY_METRICS': CLOUDABILITY_METRICS,
    'CLOUDABILITY_VIEW_ID': CLOUDABILITY_VIEW_ID,
    'APPITO_KEY_ACCESS': APPITO_KEY_ACCESS,
    'APPITO_KEY_SECRET': APPITO_KEY_SECRET,
    'APPITO_ENVID': APPITO_ENVID,
    "IBM_ACCOUNT_ID": IBM_ACCOUNT_ID_PERFORMANCE_SCALE,
    "es_host": ES_HOST,
    "es_port": ES_PORT,
    "es_index": "cloudability-cloud-governance-ibm-cost-usage-reports",
    "PUBLIC_CLOUD_NAME": "IBM"
}
CLOUDABILITY_POLICY = "cost_usage_reports"
mounted_volumes = f" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS}"
cloudability_run_command = generate_shell_cmd(policy=CLOUDABILITY_POLICY,
                                              env_variables={
                                                  **cloudability_env_vars
                                              }, mounted_volumes=mounted_volumes)

run_shell_cmd(f"echo Running the {CLOUDABILITY_POLICY}")
run_shell_cmd(cloudability_run_command)
