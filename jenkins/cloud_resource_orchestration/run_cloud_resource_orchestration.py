
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


es_index = CLOUD_RESOURCE_ORCHESTRATION_INDEX

input_vars_to_container = [{'account': 'perf-dept', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF, 'CLOUD_NAME': 'aws'},
                           {'account': 'perf-scale', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE, 'CLOUD_NAME': 'aws'},
                           {'account': 'psap', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PSAP,
                            'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PSAP, 'CLOUD_NAME': 'aws'}]

print('Run LongRun in pre active region')
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'ap-south-1']

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': es_index, 'log_level': 'INFO', 'LDAP_HOST_NAME': LDAP_HOST_NAME,
                     'JIRA_QUEUE': JIRA_QUEUE, 'JIRA_TOKEN': JIRA_TOKEN, 'JIRA_USERNAME': JIRA_USERNAME, 'JIRA_URL': JIRA_URL, 'MANAGEMENT': True, 'special_user_mails': f"{special_user_mails}"}
combine_vars = lambda item: f'{item[0]}="{item[1]}"'
common_envs = list(map(combine_vars, common_input_vars.items()))
for input_vars in input_vars_to_container:
    envs = list(map(combine_vars, input_vars.items()))
    for region in regions:
        os.system(f"""podman run --rm --name cloud_resource_orchestration -e MONITOR="long_run" -e AWS_DEFAULT_REGION="{region}" -e policy="cost_billing_reports" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)}  quay.io/ebattat/cloud-governance:latest""")
