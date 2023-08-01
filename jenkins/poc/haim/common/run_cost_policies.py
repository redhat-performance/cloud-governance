import os

access_key = os.environ['access_key']
secret_key = os.environ['secret_key']
s3_bucket = os.environ['s3_bucket']
account_name = os.environ['account_name']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']


cost_tags = ['PurchaseType', 'ChargeType', 'User', 'Budget', 'Project', 'Manager', 'Owner',
             'LaunchTime', 'Name', 'Email', 'Environment', 'User:Spot']
cost_metric = 'UnblendedCost'  # UnblendedCost/BlendedCost
granularity = 'DAILY'  # DAILY/MONTHLY/HOURLY
cost_explorer_index = 'cloud-governance-haim-cost-explorer-global-index'
os.system(f"""echo "Running the CloudGovernance CostExplorer Policies" """)
os.system(f"""podman run --rm --name cloud-governance --net="host" -e AWS_DEFAULT_REGION="us-east-1" -e account="{account_name}" -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="{access_key}" -e AWS_SECRET_ACCESS_KEY="{secret_key}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_index="{cost_explorer_index}" -e cost_explorer_tags="{cost_tags}" -e granularity="{granularity}" -e cost_metric="{cost_metric}" -e log_level="INFO" quay.io/ebattat/cloud-governance:latest""")
