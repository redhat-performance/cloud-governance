import os

LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
IBM_API_KEY = os.environ['IBM_API_KEY']
IBM_API_USERNAME = os.environ['IBM_API_USERNAME']
SPREADSHEET_ID = os.environ['IAM_USER_SPREADSHEET_ID']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
LOGS = os.environ.get('LOGS', 'logs')
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

print('Run IBM Cost Invoice upload monthly')

es_index = 'cloud-governance-ibm-invoice-cost'

os.system(
    f"""podman run --rm --net="host" --name cloud-governance -e account="IBM-PERF" -e policy="ibm_cost_report" -e es_index="{es_index}" -e es_port="{ES_PORT}" -e es_host="{ES_HOST}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS} -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e IBM_API_USERNAME="{IBM_API_USERNAME}" -e IBM_API_KEY="{IBM_API_KEY}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
