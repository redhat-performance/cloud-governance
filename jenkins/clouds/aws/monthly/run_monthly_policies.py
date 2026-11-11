import os

ES_HOST = os.environ['ES_HOST']
ES_PORT = os.environ['ES_PORT']
ES_USER = os.environ.get('ES_USER', '')
ES_PASSWORD = os.environ.get('ES_PASSWORD', '')
TO_MAIL = os.environ['TO_MAIL']
CC_MAIL = os.environ['CC_MAIL']
LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
LDAP_FALLBACK_HOSTS = os.environ.get('LDAP_FALLBACK_HOSTS', '')
LDAP_CA_CERT_FILE = os.getenv('LDAP_CA_CERT_FILE', '/etc/cloud-governance/ldap-ca-bundle.pem')
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ['QUAY_CLOUD_GOVERNANCE_REPOSITORY']

LOGS = os.environ.get('LOGS', 'logs')

# RUN AWS Monthly Policies
print("Run AWS Monthly Policies")
os.system(
    f"""podman run --rm --name cloud-governance --net="host" -e policy="monthly_report" -e es_host="{ES_HOST}" -e es_port="{ES_PORT}" -e es_user="{ES_USER}" -e es_password="{ES_PASSWORD}" -e to_mail="{TO_MAIL}" -e cc_mail="{CC_MAIL}" -e LDAP_HOST_NAME="{LDAP_HOST_NAME}" -e LDAP_FALLBACK_HOSTS="{LDAP_FALLBACK_HOSTS}" -e LDAP_BIND_DN -e LDAP_BIND_PASSWORD -e LDAP_BASE_DN -v {LDAP_CA_CERT_FILE}:{LDAP_CA_CERT_FILE}:ro -e LDAP_CA_CERT_FILE="{LDAP_CA_CERT_FILE}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
