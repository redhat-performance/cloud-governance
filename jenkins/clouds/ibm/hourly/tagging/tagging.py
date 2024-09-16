import os

LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
IBM_API_KEY = os.environ['IBM_API_KEY']
IBM_API_USERNAME = os.environ['IBM_API_USERNAME']
SPREADSHEET_ID = os.environ['AWS_IAM_USER_SPREADSHEET_ID']
LOGS = os.environ.get('LOGS', 'logs')
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

print('Run IBM tagging on baremetal, vm')

os.system(
    f"""podman run --rm --name cloud-governance -e account="IBM-PERF" -e policy="tag_baremetal" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS} -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e IBM_API_USERNAME="{IBM_API_USERNAME}" -e IBM_API_KEY="{IBM_API_KEY}" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
os.system(
    f"""podman run --rm --name cloud-governance -e account="IBM-PERF" -e policy="tag_vm" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS} -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e IBM_API_USERNAME="{IBM_API_USERNAME}" -e IBM_API_KEY="{IBM_API_KEY}" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
