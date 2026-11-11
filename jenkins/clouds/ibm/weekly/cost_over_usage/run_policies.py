import os

USAGE_REPORTS_APIKEY = os.environ['USAGE_REPORTS_APIKEY']
IBM_ACCOUNT_ID = os.environ['IBM_ACCOUNT_ID']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
LDAP_FALLBACK_HOSTS = os.environ.get('LDAP_FALLBACK_HOSTS', '')
LDAP_CA_CERT_FILE = os.getenv('LDAP_CA_CERT_FILE', '/etc/cloud-governance/ldap-ca-bundle.pem')
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
    f"""podman run --rm --name cloud-governance --net=host -e policy="ibm_cost_over_usage" -e account="IBM-PERF" -e IBM_ACCOUNT_ID="{IBM_ACCOUNT_ID}" -e to_mail="{TO_MAIL}" -e cc_mail="{CC_MAIL}" -e USAGE_REPORTS_APIKEY="{USAGE_REPORTS_APIKEY}" -e USAGE_REPORTS_AUTHTYPE="{USAGE_REPORTS_AUTHTYPE}" -e MAXIMUM_THRESHOLD="{MAXIMUM_THRESHOLD}" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_user="{ES_USER}" -e es_password="{ES_PASSWORD}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e LDAP_FALLBACK_HOSTS="{LDAP_FALLBACK_HOSTS}" -e LDAP_BIND_DN -e LDAP_BIND_PASSWORD -e LDAP_BASE_DN -v {LDAP_CA_CERT_FILE}:{LDAP_CA_CERT_FILE}:ro -e LDAP_CA_CERT_FILE="{LDAP_CA_CERT_FILE}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
