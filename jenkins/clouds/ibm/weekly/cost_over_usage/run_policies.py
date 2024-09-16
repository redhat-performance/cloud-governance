import os

USAGE_REPORTS_APIKEY = os.environ['USAGE_REPORTS_APIKEY']
IBM_ACCOUNT_ID = os.environ['IBM_ACCOUNT_ID']
TO_MAIL = ['natashba@redhat.com']
CC_MAIL = ['athiruma@redhat.com', 'ebattat@redhat.com']
USAGE_REPORTS_AUTHTYPE = 'iam'
MAXIMUM_THRESHOLD = 1000
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

os.system(
    f"""podman run --rm --name cloud-governance --net=host -e policy="ibm_cost_over_usage" -e account="IBM-PERF" -e IBM_ACCOUNT_ID="{IBM_ACCOUNT_ID}" -e to_mail="{TO_MAIL}" -e cc_mail="{CC_MAIL}" -e USAGE_REPORTS_APIKEY="{USAGE_REPORTS_APIKEY}" -e USAGE_REPORTS_AUTHTYPE="{USAGE_REPORTS_AUTHTYPE}" -e MAXIMUM_THRESHOLD="{MAXIMUM_THRESHOLD}" -e log_level="INFO" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
