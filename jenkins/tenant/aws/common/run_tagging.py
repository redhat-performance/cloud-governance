import os

access_key = os.environ['access_key']
secret_key = os.environ['secret_key']
account_name = os.environ['account_name']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance')

LOGS = os.environ.get('LOGS', 'logs')

mandatory_tags_appeng = {'Budget': account_name}

os.system(f"""echo "Running the tag_resources" """)
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'ap-south-1', 'eu-north-1', 'eu-west-3', 'eu-west-2',
           'eu-west-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-northeast-1', 'ca-central-1', 'sa-east-1',
           'ap-southeast-1', 'ap-southeast-2', 'eu-central-1']
for region in regions:
    os.system(
        f"""podman run --rm --name cloud-governance-poc-haim -e account="{account_name}" -e EMAIL_ALERT="False" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_appeng}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
