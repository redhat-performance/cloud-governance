import os

USAGE_REPORTS_APIKEY = os.environ['USAGE_REPORTS_APIKEY']
IBM_ACCOUNT_ID = os.environ['IBM_ACCOUNT_ID']
ES_HOST = os.environ.get('ES_HOST', '')
ES_PORT = os.environ.get('ES_PORT', '')
ES_USER = os.environ.get('ES_USER', '')
ES_PASSWORD = os.environ.get('ES_PASSWORD', '')
TO_MAIL = ['natashba@redhat.com']
CC_MAIL = ['yinsong@redhat.com', 'ebattat@redhat.com', 'pragchau@redhat.com']
USAGE_REPORTS_AUTHTYPE = 'iam'
MAXIMUM_THRESHOLD = 1000
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ['QUAY_CLOUD_GOVERNANCE_REPOSITORY']

os.system(
    f"""podman run --rm --name cloud-governance --net=host -e policy="ibm_cost_over_usage" -e account="IBM-PERF" -e IBM_ACCOUNT_ID="{IBM_ACCOUNT_ID}" -e to_mail="{TO_MAIL}" -e cc_mail="{CC_MAIL}" -e USAGE_REPORTS_APIKEY="{USAGE_REPORTS_APIKEY}" -e USAGE_REPORTS_AUTHTYPE="{USAGE_REPORTS_AUTHTYPE}" -e MAXIMUM_THRESHOLD="{MAXIMUM_THRESHOLD}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_user="{ES_USER}" -e es_password="{ES_PASSWORD}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
