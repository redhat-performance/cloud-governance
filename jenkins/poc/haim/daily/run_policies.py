
import os


AWS_ACCESS_KEY_ID_APPENG = os.environ['AWS_ACCESS_KEY_ID_APPENG']
AWS_SECRET_ACCESS_KEY_APPENG = os.environ['AWS_SECRET_ACCESS_KEY_APPENG']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
LOGS = os.environ.get('LOGS', 'logs')
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
BUCKET_APPENG = os.environ['BUCKET_APPENG']


def get_policies(type: str = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of policies name
    """
    policies = []
    policies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'cloud_governance', 'policy', 'aws')
    for (dirpath, dirnames, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not filename.startswith('__') and (filename.endswith('.yml') or filename.endswith('.py')):
                if not type:
                    policies.append(os.path.splitext(filename)[0])
                elif type and type in filename:
                    policies.append(os.path.splitext(filename)[0])
    return policies


regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-central-1', 'ap-south-1', 'eu-north-1', 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-3', 'sa-east-1']
policies = get_policies()
not_action_policies = ['cost_explorer', 'cost_over_usage', 'monthly_report', 'cost_billing_reports', 'cost_explorer_payer_billings']
run_policies = list(set(policies) - set(not_action_policies))
run_policies.sort()


os.system(f"""echo Running the cloud_governance policies: {run_policies}""")
os.system(f"""echo "Running the CloudGovernance policies" """)
for region in regions:
    for policy in run_policies:
        if policy in ('empty_roles', 's3_inactive') and region == 'us-east-1':
            os.system(f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e MANAGER_EMAIL_ALERT="False" -e EMAIL_ALERT="False" -e account="APPENG" -e policy="{policy}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_APPENG}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_APPENG}" -e AWS_DEFAULT_REGION="{region}" -e dry_run="no" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e policy_output="s3://{BUCKET_APPENG}/{LOGS}/{region}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
        else:
            os.system(f"""podman run --rm --name cloud-governance-poc-haim --net="host" -e MANAGER_EMAIL_ALERT="False" -e EMAIL_ALERT="False" -e account="APPENG" -e policy="{policy}" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_APPENG}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_APPENG}" -e AWS_DEFAULT_REGION="{region}" -e dry_run="no" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e policy_output="s3://{BUCKET_APPENG}/{LOGS}/{region}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")


cost_tags = ['PurchaseType', 'ChargeType', 'User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email', 'Environment', 'User:Spot']
cost_metric = 'UnblendedCost'  # UnblendedCost/BlendedCost
granularity = 'DAILY'  # DAILY/MONTHLY/HOURLY
cost_explorer_index = 'cloud-governance-haim-cost-explorer-global-index'
os.system(f"""echo "Running the CloudGovernance CostExplorer Policies" """)
os.system(f"""podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION="us-east-1" -e account="appeng" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_APPENG}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_APPENG}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{cost_explorer_index}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
