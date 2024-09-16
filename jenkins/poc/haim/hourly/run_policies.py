import os

AWS_ACCESS_KEY_ID_APPENG = os.environ['AWS_ACCESS_KEY_ID_APPENG']
AWS_SECRET_ACCESS_KEY_APPENG = os.environ['AWS_SECRET_ACCESS_KEY_APPENG']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
SPREADSHEET_ID = os.environ['AWS_IAM_USER_SPREADSHEET_ID']

LOGS = os.environ.get('LOGS', 'logs')

mandatory_tags_appeng = {'Budget': 'APPENG'}

os.system(f"""echo "Running the tag_iam_user" """)
os.system(
    f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e account="APPENG" -e -e EMAIL_ALERT="False" -e policy="tag_iam_user" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_APPENG}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_APPENG}" -e user_tag_operation="update" -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}"  -e log_level="INFO" quay.io/cloud-governance/cloud-governance:latest""")

os.system(f"""echo "Running the tag_resources" """)
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-central-1', 'ap-south-1', 'eu-north-1',
           'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-3', 'sa-east-1']
for region in regions:
    os.system(
        f"""podman run --rm --name cloud-governance-poc-haim -e account="APPENG" -e EMAIL_ALERT="False" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_APPENG}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_APPENG}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_appeng}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" quay.io/cloud-governance/cloud-governance:latest""")
