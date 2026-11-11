import os

AZURE_CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
AZURE_TENANT_ID = os.environ['AZURE_TENANT_ID']
AZURE_CLIENT_ID = os.environ['AZURE_CLIENT_ID']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
ES_USER = os.environ.get('ES_USER', '')
ES_PASSWORD = os.environ.get('ES_PASSWORD', '')
COST_SPREADSHEET_ID = os.environ['COST_SPREADSHEET_ID']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
AZURE_ACCOUNT_ID = os.environ['AZURE_ACCOUNT_ID']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
LDAP_FALLBACK_HOSTS = os.environ.get('LDAP_FALLBACK_HOSTS', '')
LDAP_CA_CERT_FILE = os.getenv('LDAP_CA_CERT_FILE', '/etc/cloud-governance/ldap-ca-bundle.pem')
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ['QUAY_CLOUD_GOVERNANCE_REPOSITORY']

print('Running the Azure cost billing reports')
input_vars_to_container = [{'account': 'perf-scale-azure', 'AZURE_CLIENT_ID': AZURE_CLIENT_ID,
                            'AZURE_TENANT_ID': AZURE_TENANT_ID, 'AZURE_CLIENT_SECRET': AZURE_CLIENT_SECRET,
                            'AZURE_ACCOUNT_ID': AZURE_ACCOUNT_ID}]

common_input_vars = {'es_host': ES_HOST, 'es_port': ES_PORT, 'es_user': ES_USER, 'es_password': ES_PASSWORD,
                     'es_index': 'cloud-governance-clouds-billing-reports',
                     'log_level': 'INFO', 'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS,
                     'LDAP_HOST_NAME': LDAP_HOST_NAME, 'LDAP_FALLBACK_HOSTS': LDAP_FALLBACK_HOSTS}
combine_vars = lambda item: f'{item[0]}="{item[1]}"'
common_envs = list(map(combine_vars, common_input_vars.items()))
ldap_flags = f'-e LDAP_BIND_DN -e LDAP_BIND_PASSWORD -e LDAP_BASE_DN -v {LDAP_CA_CERT_FILE}:{LDAP_CA_CERT_FILE}:ro -e LDAP_CA_CERT_FILE="{LDAP_CA_CERT_FILE}"'
for input_vars in input_vars_to_container:
    envs = list(map(combine_vars, input_vars.items()))
    os.system(
        f"""podman run --rm --net="host" --name cloud-governance -e policy="cost_billing_reports" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)} {ldap_flags} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
    os.system(
        f"""podman run --rm --net="host" --name cloud-governance -e COST_CENTER_OWNER="Shai" -e policy="cost_billing_reports" -e TOTAL_ACCOUNTS="True" -e SPREADSHEET_ID="{COST_SPREADSHEET_ID}" -e {' -e '.join(envs)} -e {' -e '.join(common_envs)} {ldap_flags} -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
