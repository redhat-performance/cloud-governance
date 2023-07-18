
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

os.system('echo "Updating the Org level cost billing reports"')

# Cost Explorer upload to ElasticSearch
cost_metric = 'UnblendedCost'  # UnblendedCost/BlendedCost
granularity = 'DAILY'  # DAILY/MONTHLY/HOURLY


common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': 'cloud-governance-global-cost-billing-reports', 'log_level': 'INFO', 'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS, 'COST_CENTER_OWNER': f"{COST_CENTER_OWNER}", 'REPLACE_ACCOUNT_NAME': REPLACE_ACCOUNT_NAME, 'PAYER_SUPPORT_FEE_CREDIT': PAYER_SUPPORT_FEE_CREDIT}
combine_vars = lambda item: f'{item[0]}="{item[1]}"'

common_input_vars['es_index'] = 'cloud-governance-clouds-billing-reports'
common_envs = list(map(combine_vars, common_input_vars.items()))
os.system(f"""podman run --rm --name cloud-governance -e policy="cost_explorer_payer_billings" -e AWS_ACCOUNT_ROLE="{AWS_ACCOUNT_ROLE}" -e account="PERF-DEPT" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(common_envs)} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" quay.io/ebattat/cloud-governance:latest""")


os.system('echo "Run the Spot Analysis report over the account using AWS Athena"')
os.system(f"""podman run --rm --name cloud-governance -e policy="spot_savings_analysis" -e account="pnt-payer" \
-e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_ATHIRUMA_BOT}" \
-e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_ATHIRUMA_BOT}" \
-e es_host="{ES_HOST}" -e es_port="{ES_PORT}" \
-e es_index="cloud-governance-clouds-billing-reports" \
-e S3_RESULTS_PATH="{S3_RESULTS_PATH}" \
-e ATHENA_DATABASE_NAME="{ATHENA_DATABASE_NAME}" \
-e ATHENA_TABLE_NAME="{ATHENA_TABLE_NAME}" \
quay.io/ebattat/cloud-governance:latest""")
