

import os

GCP_DATABASE_NAME = os.environ['GCP_DATABASE_NAME']
GCP_DATABASE_TABLE_NAME = os.environ['GCP_DATABASE_TABLE_NAME']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
COST_SPREADSHEET_ID = os.environ['COST_SPREADSHEET_ID']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']

print('Running the GCP cost billing reports')

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': 'cloud-governance-clouds-billing-reports',
                     'log_level': 'INFO', 'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS,
                     'PUBLIC_CLOUD_NAME': 'GCP', 'SPREADSHEET_ID': COST_SPREADSHEET_ID,
                     'GCP_DATABASE_NAME': GCP_DATABASE_NAME, 'GCP_DATABASE_TABLE_NAME': GCP_DATABASE_TABLE_NAME}

combine_vars = lambda item: f'{item[0]}="{item[1]}"'
common_envs = list(map(combine_vars, common_input_vars.items()))
os.system(f"""podman run --rm --name cloud-governance -e policy="cost_billing_reports" -e {' -e '.join(common_envs)} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" quay.io/ebattat/cloud-governance:latest""")
