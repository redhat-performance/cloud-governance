
import os

AWS_ACCESS_KEY_ID_PERF = os.environ['AWS_ACCESS_KEY_ID_PERF']
AWS_SECRET_ACCESS_KEY_PERF = os.environ['AWS_SECRET_ACCESS_KEY_PERF']
AWS_ACCESS_KEY_ID_DELETE_PERF = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF']
AWS_SECRET_ACCESS_KEY_DELETE_PERF = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF']
BUCKET_PERF = os.environ['BUCKET_PERF']
AWS_ACCESS_KEY_ID_PSAP = os.environ['AWS_ACCESS_KEY_ID_PSAP']
AWS_SECRET_ACCESS_KEY_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_PSAP']
AWS_ACCESS_KEY_ID_DELETE_PSAP = os.environ['AWS_ACCESS_KEY_ID_DELETE_PSAP']
AWS_SECRET_ACCESS_KEY_DELETE_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PSAP']
BUCKET_PSAP = os.environ['BUCKET_PSAP']
AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE']
AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE']
BUCKET_PERF_SCALE = os.environ['BUCKET_PERF_SCALE']
AWS_ACCESS_KEY_ID_RH_PERF = os.environ['AWS_ACCESS_KEY_ID_RH_PERF']
AWS_SECRET_ACCESS_KEY_RH_PERF = os.environ['AWS_SECRET_ACCESS_KEY_RH_PERF']
BUCKET_RH_PERF = os.environ['BUCKET_RH_PERF']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
IBM_API_KEY = os.environ['IBM_API_KEY']
IBM_API_USERNAME = os.environ['IBM_API_USERNAME']
SPREADSHEET_ID = os.environ['AWS_IAM_USER_SPREADSHEET_ID']
LOGS = os.environ.get('LOGS', 'logs')

mandatory_tags_perf = {'Budget': 'PERF-DEPT'}
mandatory_tags_psap = {'Budget': 'PSAP'}
mandatory_tags_perf_scale = {'Budget': 'PERF-SCALE'}

print('Run AWS tagging policy pre active region')
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-central-1', 'ap-south-1', 'eu-north-1', 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-3', 'sa-east-1']

for region in regions:
    os.system(f"""podman run --rm --name cloud-governance -e account="perf" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_perf}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" quay.io/ebattat/cloud-governance:latest""")
    os.system(f"""podman run --rm --name cloud-governance -e account="psap" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_psap}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" quay.io/ebattat/cloud-governance:latest""")
    os.system(f"""podman run --rm --name cloud-governance -e account="perf-scale" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_perf_scale}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" quay.io/ebattat/cloud-governance:latest""")


print('Run IBM tagging on baemetal, vm')

os.system(f"""podman run --rm --name cloud-governance -e account="IBM-PERF" -e policy="tag_baremetal" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS} -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e IBM_API_USERNAME="{IBM_API_USERNAME}" -e IBM_API_KEY="{IBM_API_KEY}" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" quay.io/ebattat/cloud-governance:latest""")
os.system(f"""podman run --rm --name cloud-governance -e account="IBM-PERF" -e policy="tag_vm" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v {GOOGLE_APPLICATION_CREDENTIALS}:{GOOGLE_APPLICATION_CREDENTIALS} -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e IBM_API_USERNAME="{IBM_API_USERNAME}" -e IBM_API_KEY="{IBM_API_KEY}" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" quay.io/ebattat/cloud-governance:latest""")
