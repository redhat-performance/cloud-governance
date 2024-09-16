import os

AZURE_CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
AZURE_TENANT_ID = os.environ['AZURE_TENANT_ID']
AZURE_CLIENT_ID = os.environ['AZURE_CLIENT_ID']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
COST_SPREADSHEET_ID = os.environ['COST_SPREADSHEET_ID']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
AZURE_ACCOUNT_ID = os.environ['AZURE_ACCOUNT_ID']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

print('Running the Azure cost billing reports')
input_vars_to_container = [{'account': 'perf-scale-azure', 'AZURE_CLIENT_ID': AZURE_CLIENT_ID,
                            'AZURE_TENANT_ID': AZURE_TENANT_ID, 'AZURE_CLIENT_SECRET': AZURE_CLIENT_SECRET,
                            'AZURE_ACCOUNT_ID': AZURE_ACCOUNT_ID}]

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_index': 'cloud-governance-clouds-billing-reports',
                     'log_level': 'INFO', 'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS}
combine_vars = lambda item: f'{item[0]}="{item[1]}"'
common_envs = list(map(combine_vars, common_input_vars.items()))
for input_vars in input_vars_to_container:
    envs = list(map(combine_vars, input_vars.items()))
    os.system(
        f"""podman run --rm --name cloud-governance -e policy="cost_billing_reports" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
    os.system(
        f"""podman run --rm --name cloud-governance -e COST_CENTER_OWNER="Shai" -e policy="cost_billing_reports" -e TOTAL_ACCOUNTS="True" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
