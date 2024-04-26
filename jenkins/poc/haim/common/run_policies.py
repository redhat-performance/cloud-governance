
import os
from ast import literal_eval

policies_in_action = ['ebs_unattached', 'ip_unattached', 'zombie_snapshots', 'unused_nat_gateway', 's3_inactive', 'empty_roles']
policies_not_in_action = ['ec2_stop', 'instance_idle', 'zombie_cluster_resource']

access_key = os.environ['access_key']
secret_key = os.environ['secret_key']
s3_bucket = os.environ['s3_bucket']
account_name = os.environ['account_name']
days_to_delete_resource = os.environ.get('days_to_delete_resource', 14)
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
LOGS = os.environ.get('LOGS', 'logs')
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
SPREADSHEET_ID = os.environ['AWS_IAM_USER_SPREADSHEET_ID']

regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-central-1', 'ap-south-1', 'eu-north-1',
           'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-3', 'sa-east-1']

es_doc_type = '_doc'

os.system(f"""echo Running the cloud_governance policies with dry_run=yes""")
os.system(f"echo Polices list: {policies_not_in_action}")
for region in regions:
    for policy in policies_not_in_action:
        os.system(f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e MANAGER_EMAIL_ALERT="False" -e EMAIL_ALERT="False" -e account="{account_name}" -e policy="{policy}" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e AWS_DEFAULT_REGION="{region}" -e dry_run="yes" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e policy_output="s3://{s3_bucket}/{LOGS}/{region}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        if policy == 'zombie_cluster_resource':
            os.system(f"""podman run --rm --name cloud-governance-poc-haim -e upload_data_es="upload_data_es" -e account="{account_name}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_doc_type="{es_doc_type}" -e bucket="{s3_bucket}" -e policy="{policy}" -e AWS_DEFAULT_REGION="{region}" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")

os.system('echo "Running the CloudGovernance policies with dry_run=no" ')
os.system(f"echo Polices list: {policies_in_action}")
for region in regions:
    for policy in policies_in_action:
        if policy in ('empty_roles', 's3_inactive') and region == 'us-east-1':
            os.system(f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e MANAGER_EMAIL_ALERT="False" -e EMAIL_ALERT="False" -e account="{account_name}" -e policy="{policy}" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e AWS_DEFAULT_REGION="{region}" -e dry_run="no" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e policy_output="s3://{s3_bucket}/{LOGS}/{region}" -e DAYS_TO_DELETE_RESOURCE="{days_to_delete_resource}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        elif policy not in ('empty_roles', 's3_inactive'):
            os.system(f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e MANAGER_EMAIL_ALERT="False" -e EMAIL_ALERT="False" -e account="{account_name}" -e policy="{policy}" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e AWS_DEFAULT_REGION="{region}" -e dry_run="no" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e policy_output="s3://{s3_bucket}/{LOGS}/{region}" -e DAYS_TO_DELETE_RESOURCE="{days_to_delete_resource}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")

os.system(f"""echo "Running the tag_iam_user" """)
os.system(f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e account="{account_name}" -e EMAIL_ALERT="False" -e policy="tag_iam_user" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e user_tag_operation="update" -e SPREADSHEET_ID="{SPREADSHEET_ID}" -e GOOGLE_APPLICATION_CREDENTIALS="{GOOGLE_APPLICATION_CREDENTIALS}" -v "{GOOGLE_APPLICATION_CREDENTIALS}":"{GOOGLE_APPLICATION_CREDENTIALS}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}"  -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
