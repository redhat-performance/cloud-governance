import os

ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
ES_USER = os.environ.get('ES_USER', '')
ES_PASSWORD = os.environ.get('ES_PASSWORD', '')
TO_MAIL = os.environ['TO_MAIL']
CC_MAIL = os.environ['CC_MAIL']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ['QUAY_CLOUD_GOVERNANCE_REPOSITORY']

LOGS = os.environ.get('LOGS', 'logs')

# RUN AWS Monthly Policies
print("Run AWS Monthly Policies")
os.system(
    f"""podman run --rm --name cloud-governance --net="host" -e policy="monthly_report" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_user="{ES_USER}" -e es_password="{ES_PASSWORD}" -e to_mail="{TO_MAIL}" -e cc_mail="{CC_MAIL}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
