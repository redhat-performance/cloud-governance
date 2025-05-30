import os

AWS_ACCESS_KEY_ID_DELETE_PERF = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF']
AWS_SECRET_ACCESS_KEY_DELETE_PERF = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF']
AWS_ACCESS_KEY_ID_DELETE_PSAP = os.environ['AWS_ACCESS_KEY_ID_DELETE_PSAP']
AWS_SECRET_ACCESS_KEY_DELETE_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PSAP']
AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE']
AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
JIRA_URL = os.environ['JIRA_URL']
JIRA_USERNAME = os.environ['JIRA_USERNAME']
JIRA_TOKEN = os.environ['JIRA_TOKEN']
JIRA_QUEUE = os.environ['JIRA_QUEUE']
special_user_mails = os.environ['CLOUD_GOVERNANCE_SPECIAL_USER_MAILS']
CLOUD_RESOURCE_ORCHESTRATION_INDEX = os.environ['CLOUD_RESOURCE_ORCHESTRATION_INDEX']
CRO_REPLACED_USERNAMES = os.environ['CRO_REPLACED_USERNAMES']
CRO_DEFAULT_ADMINS = ['yinsong', 'ebattat', 'natashba']
CRO_PORTAL = os.environ['CRO_PORTAL']
CRO_COST_OVER_USAGE = os.environ['CRO_COST_OVER_USAGE']
CRO_ES_INDEX = os.environ['CRO_ES_INDEX']
AWS_ACCESS_KEY_ID_ATHIRUMA_BOT = os.environ['AWS_ACCESS_KEY_ID_ATHIRUMA_BOT']
AWS_SECRET_ACCESS_KEY_ATHIRUMA_BOT = os.environ['AWS_SECRET_ACCESS_KEY_ATHIRUMA_BOT']
S3_RESULTS_PATH = os.environ['S3_RESULTS_PATH']
ATHENA_DATABASE_NAME = os.environ['ATHENA_DATABASE_NAME']
ATHENA_TABLE_NAME = os.environ['ATHENA_TABLE_NAME']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

es_index = CLOUD_RESOURCE_ORCHESTRATION_INDEX

common_env_vars = {
    'es_host': ES_HOST, 'es_port': ES_PORT, 'CRO_ES_INDEX': CRO_ES_INDEX, 'log_level': 'INFO',
    'LDAP_HOST_NAME': LDAP_HOST_NAME,
    'JIRA_QUEUE': JIRA_QUEUE, 'JIRA_TOKEN': JIRA_TOKEN, 'JIRA_USERNAME': JIRA_USERNAME, 'JIRA_URL': JIRA_URL,
    'CRO_COST_OVER_USAGE': CRO_COST_OVER_USAGE, 'CRO_PORTAL': CRO_PORTAL, 'CRO_DEFAULT_ADMINS': CRO_DEFAULT_ADMINS,
    'CRO_REPLACED_USERNAMES': CRO_REPLACED_USERNAMES,
    'CE_PAYER_INDEX': 'cloud-governance-clouds-billing-reports', 'RUN_ACTIVE_REGIONS': True,
}

input_vars_to_container = [{'account': 'perf-dept', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF, 'PUBLIC_CLOUD_NAME': 'AWS'},
                           {'account': 'perf-scale', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE,
                            'PUBLIC_CLOUD_NAME': 'AWS'},
                           {'account': 'psap', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PSAP,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PSAP, 'PUBLIC_CLOUD_NAME': 'AWS'}]

os.system('echo Run CloudResourceOrchestration in pre active region')

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'CRO_ES_INDEX': CRO_ES_INDEX, 'log_level': 'INFO',
                     'LDAP_HOST_NAME': LDAP_HOST_NAME,
                     'JIRA_QUEUE': JIRA_QUEUE, 'JIRA_TOKEN': JIRA_TOKEN, 'JIRA_USERNAME': JIRA_USERNAME,
                     'JIRA_URL': JIRA_URL,
                     'CRO_COST_OVER_USAGE': CRO_COST_OVER_USAGE, 'CRO_PORTAL': CRO_PORTAL,
                     'CRO_DEFAULT_ADMINS': CRO_DEFAULT_ADMINS, 'CRO_REPLACED_USERNAMES': CRO_REPLACED_USERNAMES,
                     'CE_PAYER_INDEX': 'cloud-governance-clouds-billing-reports', 'RUN_ACTIVE_REGIONS': True,
                     'AWS_DEFAULT_REGION': 'us-east-1', 'AWS_MAX_ATTEMPTS': 5, 'AWS_RETRY_MODE': 'standard',
                     'ATHENA_ACCOUNT_ACCESS_KEY': AWS_ACCESS_KEY_ID_ATHIRUMA_BOT,
                     'ATHENA_ACCOUNT_SECRET_KEY': AWS_SECRET_ACCESS_KEY_ATHIRUMA_BOT,
                     'ATHENA_DATABASE_NAME': ATHENA_DATABASE_NAME, 'ATHENA_TABLE_NAME': ATHENA_TABLE_NAME,
                     'S3_RESULTS_PATH': S3_RESULTS_PATH
                     }
#  Added the AWS_MAX_ATTEMPTS, AWS_RETRY_MODE to handle the RateLimit Exception in aws api calls using boto3
# for more information on throttle api calls: https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html
# AWS Default varibles https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#:~:text=to%20use%20this.-,AWS_MAX_ATTEMPTS,-The%20total%20number

combine_vars = lambda item: f'{item[0]}="{item[1]}"'
common_envs = list(map(combine_vars, common_input_vars.items()))
for input_vars in input_vars_to_container:
    os.system(f"""echo Running on Account {input_vars.get("account").upper()}""")
    envs = list(map(combine_vars, input_vars.items()))
    os.system(
        f"""podman run --net="host" --rm --name  cloud_resource_orchestration -e CLOUD_RESOURCE_ORCHESTRATION="True" -e EMAIL_ALERT="True" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)} {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

AZURE_ACCOUNT_ID = os.environ['AZURE_ACCOUNT_ID']
AZURE_CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
AZURE_TENANT_ID = os.environ['AZURE_TENANT_ID']
AZURE_CLIENT_ID = os.environ['AZURE_CLIENT_ID']
AZURE_SUBSCRIPTION_ID = os.environ['AZURE_SUBSCRIPTION_ID']

os.system("echo Running the Azure CRO")
azure_cro_env = {
    'AZURE_ACCOUNT_ID': AZURE_ACCOUNT_ID, 'AZURE_CLIENT_ID': AZURE_CLIENT_ID,
    'AZURE_TENANT_ID': AZURE_TENANT_ID, 'AZURE_CLIENT_SECRET': AZURE_CLIENT_SECRET,
    'AZURE_SUBSCRIPTION_ID': AZURE_SUBSCRIPTION_ID,
    'account': 'PERF&SCALE', 'PUBLIC_CLOUD_NAME': 'AZURE', 'CLOUD_RESOURCE_ORCHESTRATION': True,
    'EMAIL_ALERT': 'True'
}
azure_cro_env.update(common_env_vars)
envs = list(map(combine_vars, azure_cro_env.items()))
azure_cro = """ podman run --net="host" --rm --name cloud_resource_orchestration """
azure_cro += f" -e {' -e '.join(envs)}  {QUAY_CLOUD_GOVERNANCE_REPOSITORY}"
os.system(azure_cro)
