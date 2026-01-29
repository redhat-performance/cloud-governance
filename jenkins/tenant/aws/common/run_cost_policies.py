import os

access_key = os.environ['access_key']
secret_key = os.environ['secret_key']
account_name = os.environ['account_name']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
ES_INDEX = os.environ.get('ES_INDEX', None)

# QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
#                                                   'quay.io/cloud-governance/cloud-governance')
QUAY_CLOUD_GOVERNANCE_REPOSITORY = 'quay.io/rh-ee-pragchau/cloud-governance:latest'

cost_tags = ['PurchaseType', 'ChargeType', 'User', 'Budget', 'Project', 'Manager', 'Owner',
             'LaunchTime', 'Name', 'Email', 'Environment', 'User:Spot', 'cluster_id']
cost_metric = 'UnblendedCost'  # UnblendedCost/BlendedCost
granularity = 'DAILY'  # DAILY/MONTHLY/HOURLY
cost_explorer_index = 'cloud-governance-haim-cost-explorer-global-index'

# Set es_index if given
env_es_index = f'-e es_index="{ES_INDEX}"' if ES_INDEX else f'-e es_index="{cost_explorer_index}"'

os.system(f"""echo "Running the CloudGovernance CostExplorer Policies" """)
os.system(
    f"""podman run --rm --name cloud-governance --net="host" -e AWS_DEFAULT_REGION="us-east-1" -e account="{account_name}" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e es_host="{ES_HOST}" {env_es_index} -e es_port="{ES_PORT}"  -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")

os.system(f"""echo "Running yearly savings report for account {account_name}" """)
os.system(f"""podman run --rm --net="host" --name cloud-governance -e policy="yearly_savings_report" \
-e PUBLIC_CLOUD_NAME="AWS" \
-e account="{account_name}" \
-e es_host="{ES_HOST}" \
-e es_port="{ES_PORT}" \
-e es_index="cloud-governance-policy-es-index" \
-e log_level="INFO" \
{QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
