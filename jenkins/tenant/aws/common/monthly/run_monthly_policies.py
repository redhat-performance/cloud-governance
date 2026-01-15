import os

account_name = os.environ['account_name']
ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']

# QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
#                                                   'quay.io/cloud-governance/cloud-governance')
QUAY_CLOUD_GOVERNANCE_REPOSITORY = 'quay.io/rh-ee-pragchau/cloud-governance:latest'

os.system(f"""echo "Running yearly savings report for account {account_name}" """)
os.system(f"""podman run --rm --net="host" --name cloud-governance -e policy="yearly_savings_report" \
-e PUBLIC_CLOUD_NAME="AWS" \
-e account="{account_name}" \
-e es_host="{ES_HOST}" \
-e es_port="{ES_PORT}" \
-e es_index="cloud-governance-policy-es-index" \
-e log_level="INFO" \
{QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
