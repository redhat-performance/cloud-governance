
import os

AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
BUCKET = os.environ['BUCKET']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
LOGS = os.environ.get('LOGS', 'logs')


def get_custodian_policies(type: str = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of custodian policies name
    """
    custodian_policies = []
    policies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cloud_governance/policy')
    for (dirpath, dirnames, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not type:
                custodian_policies.append(os.path.splitext(filename)[0])
            elif type and type in filename:
                custodian_policies.append(os.path.splitext(filename)[0])
    return custodian_policies


print('Run all policies pre active region')
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
policies = get_custodian_policies()

for region in regions:
    for policy in policies:
        os.system(f"sudo podman run --rm --name cloud-governance -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY} -e AWS_DEFAULT_REGION={region} -e dry_run=yes -e policy_output=s3://{BUCKET}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance")


print("run gitleaks")
region = 'us-east-1'
policy = 'gitleaks'
os.system(f"sudo podman run --rm --name cloud-governance -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY} -e AWS_DEFAULT_REGION={region} -e git_access_token={GITHUB_TOKEN} -e git_repo=https://github.com/redhat-performance -e several_repos=yes -e policy_output=s3://{BUCKET}/{LOGS}/$region -e log_level=INFO quay.io/ebattat/cloud-governance")
