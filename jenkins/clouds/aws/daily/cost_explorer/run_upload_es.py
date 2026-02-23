import os

# OIDC: temporary credentials from AssumeRoleWithWebIdentity in perf-dept (set by Jenkins pipeline)
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_SESSION_TOKEN = os.environ['AWS_SESSION_TOKEN']
# perf-dept: use OIDC credentials directly
AWS_ACCESS_KEY_ID_DELETE_PERF = AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY_DELETE_PERF = AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN_PERF = AWS_SESSION_TOKEN
# psap / perf-scale: use cross-account assumed credentials if set, else OIDC creds
if os.environ.get('AWS_ACCESS_KEY_ID_PSAP'):
    AWS_ACCESS_KEY_ID_DELETE_PSAP = os.environ['AWS_ACCESS_KEY_ID_PSAP']
    AWS_SECRET_ACCESS_KEY_DELETE_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_PSAP']
    AWS_SESSION_TOKEN_PSAP = os.environ['AWS_SESSION_TOKEN_PSAP']
else:
    AWS_ACCESS_KEY_ID_DELETE_PSAP = AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY_DELETE_PSAP = AWS_SECRET_ACCESS_KEY
    AWS_SESSION_TOKEN_PSAP = AWS_SESSION_TOKEN
if os.environ.get('AWS_ACCESS_KEY_ID_PERFSCALE'):
    AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE = os.environ['AWS_ACCESS_KEY_ID_PERFSCALE']
    AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE = os.environ['AWS_SECRET_ACCESS_KEY_PERFSCALE']
    AWS_SESSION_TOKEN_PERFSCALE = os.environ['AWS_SESSION_TOKEN_PERFSCALE']
else:
    AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE = AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE = AWS_SECRET_ACCESS_KEY
    AWS_SESSION_TOKEN_PERFSCALE = AWS_SESSION_TOKEN

ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
special_user_mails = os.environ['CLOUD_GOVERNANCE_SPECIAL_USER_MAILS']
COST_SPREADSHEET_ID = os.environ['COST_SPREADSHEET_ID']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

es_index_perf = 'cloud-governance-cost-explorer-perf'
es_index_psap = 'cloud-governance-cost-explorer-psap'
es_index_perf_scale = 'cloud-governance-cost-explorer-perf-scale'
es_index_global = 'cloud-governance-cost-explorer-global'
cost_tags = ['PurchaseType', 'ChargeType', 'User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name',
             'Email', 'Environment', 'User:Spot', 'TicketId', 'architecture', 'cluster_id']

# Cost Explorer upload to ElasticSearch (OIDC/cross-account temp credentials require session token)
cost_metric = 'UnblendedCost'  # UnblendedCost/BlendedCost
granularity = 'DAILY'  # DAILY/MONTHLY/HOURLY
def session_env(session_token):
    return f' -e AWS_SESSION_TOKEN="{session_token}"' if session_token else ''
os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-dept" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}"{session_env(AWS_SESSION_TOKEN_PERF)} -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_perf}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="psap" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}"{session_env(AWS_SESSION_TOKEN_PSAP)} -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_psap}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-scale" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}"{session_env(AWS_SESSION_TOKEN_PERFSCALE)} -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index={es_index_perf_scale} -e cost_explorer_tags="{cost_tags}" -e granularity={granularity} -e cost_metric="{cost_metric}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

es_index_global = 'cloud-governance-cost-explorer-perf-global-cost'
os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-dept" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}"{session_env(AWS_SESSION_TOKEN_PERF)} -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="psap" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}"{session_env(AWS_SESSION_TOKEN_PSAP)} -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="perf-scale" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}"{session_env(AWS_SESSION_TOKEN_PERFSCALE)} -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{es_index_global}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

input_vars_to_container = [
    {'account': 'perf-dept', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF, 'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF, 'AWS_SESSION_TOKEN': AWS_SESSION_TOKEN_PERF},
    {'account': 'perf-scale', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE, 'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE, 'AWS_SESSION_TOKEN': AWS_SESSION_TOKEN_PERFSCALE},
    {'account': 'psap', 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID_DELETE_PSAP, 'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY_DELETE_PSAP, 'AWS_SESSION_TOKEN': AWS_SESSION_TOKEN_PSAP}
]
common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': 'cloud-governance-global-cost-billing-reports',
                     'log_level': 'INFO', 'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS}
combine_vars = lambda item: f'{item[0]}="{item[1]}"'
common_envs = list(map(combine_vars, common_input_vars.items()))
for input_vars in input_vars_to_container:
    envs = list(map(combine_vars, input_vars.items()))
    os.system(
        f"""podman run --rm --net="host" --name cloud-governance -e policy="cost_billing_reports" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
