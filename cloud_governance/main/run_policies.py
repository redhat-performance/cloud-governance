
import os
from cloud_governance.main.main import get_custodian_policies
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
BUCKET = os.environ['BUCKET']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

print('Run all policies pre active region')
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
policies = get_custodian_policies()

for region in regions:
    for policy in policies:
        os.system(f"sudo podman run --rm --name cloud-governance -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY} -e AWS_DEFAULT_REGION={region} -e dry_run=yes -e policy_output=s3://{BUCKET}/logs/{region} -e log_level=INFO quay.io/ebattat/cloud-governance")


print("run gitleaks")
region = 'us-east-1'
policy = 'gitleaks'
os.system(f"sudo podman run --rm --name cloud-governance -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY} -e AWS_DEFAULT_REGION={region} -e git_access_token={GITHUB_TOKEN} -e git_repo=https://github.com/redhat-performance -e several_repos=yes -e policy_output=s3://{BUCKET}/logs/$region -e log_level=INFO quay.io/ebattat/cloud-governance")
