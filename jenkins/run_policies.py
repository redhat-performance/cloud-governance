
import os

AWS_ACCESS_KEY_ID_PERF = os.environ['AWS_ACCESS_KEY_ID_PERF']
AWS_SECRET_ACCESS_KEY_PERF = os.environ['AWS_SECRET_ACCESS_KEY_PERF']
AWS_ACCESS_KEY_ID_DELETE_PERF = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF']
AWS_SECRET_ACCESS_KEY_DELETE_PERF = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF']
BUCKET_PERF = os.environ['BUCKET_PERF']
AWS_ACCESS_KEY_ID_PSAP = os.environ['AWS_ACCESS_KEY_ID_PSAP']
AWS_SECRET_ACCESS_KEY_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_PSAP']
AWS_ACCESS_KEY_ID_DELETE_PSAP = os.environ['AWS_ACCESS_KEY_ID_DELETE_PSAP']
AWS_SECRET_ACCESS_KEY_DELETE_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PSAP']
BUCKET_PSAP = os.environ['BUCKET_PSAP']
AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE']
AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE']
BUCKET_PERF_SCALE = os.environ['BUCKET_PERF_SCALE']
AWS_ACCESS_KEY_ID_RH_PERF = os.environ['AWS_ACCESS_KEY_ID_RH_PERF']
AWS_SECRET_ACCESS_KEY_RH_PERF = os.environ['AWS_SECRET_ACCESS_KEY_RH_PERF']
BUCKET_RH_PERF = os.environ['BUCKET_RH_PERF']
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
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-central-1', 'ap-south-1', 'eu-north-1', 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-3', 'sa-east-1']
policies = get_custodian_policies()

for region in regions:
    for policy in policies:
        # Delete zombie cluster resource every night
        if policy == 'zombie_cluster_resource':
            os.system(f"sudo podman run --rm --name cloud-governance -e account='perf' -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_DELETE_PERF} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_DELETE_PERF} -e AWS_DEFAULT_REGION={region} -e dry_run=no -e policy_output=s3://{BUCKET_PERF}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance:latest")
            os.system(f"sudo podman run --rm --name cloud-governance -e account='psap' -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_DELETE_PSAP} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_DELETE_PSAP} -e AWS_DEFAULT_REGION={region} -e dry_run=no -e policy_output=s3://{BUCKET_PSAP}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance:latest")
            os.system(f"sudo podman run --rm --name cloud-governance -e account='perf-scale' -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE} -e AWS_DEFAULT_REGION={region} -e dry_run=no -e policy_output=s3://{BUCKET_PERF_SCALE}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance:latest")
        os.system(f"sudo podman run --rm --name cloud-governance -e account='perf' -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_PERF} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_PERF} -e AWS_DEFAULT_REGION={region} -e dry_run=yes -e policy_output=s3://{BUCKET_PERF}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance:latest")
        os.system(f"sudo podman run --rm --name cloud-governance -e account='psap' -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_PSAP} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_PSAP} -e AWS_DEFAULT_REGION={region} -e dry_run=yes -e policy_output=s3://{BUCKET_PSAP}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance:latest")
        os.system(f"sudo podman run --rm --name cloud-governance -e account='rh-perf' -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_RH_PERF} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_RH_PERF} -e AWS_DEFAULT_REGION={region} -e dry_run=yes -e policy_output=s3://{BUCKET_RH_PERF}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance:latest")
        os.system(f"sudo podman run --rm --name cloud-governance -e account='rh-perf' -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_RH_PERF} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_RH_PERF} -e AWS_DEFAULT_REGION={region} -e dry_run=yes -e policy_output=s3://{BUCKET_RH_PERF}/{LOGS}/{region} -e log_level=INFO quay.io/ebattat/cloud-governance:latest")


# Gitleaks run on github not related to any aws account
print("run gitleaks")
region = 'us-east-1'
policy = 'gitleaks'
os.system(f"sudo podman run --rm --name cloud-governance -e policy={policy} -e AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID_PERF} -e AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY_PERF} -e AWS_DEFAULT_REGION={region} -e git_access_token={GITHUB_TOKEN} -e git_repo=https://github.com/redhat-performance -e several_repos=yes -e policy_output=s3://{BUCKET_PERF}/{LOGS}/$region -e log_level=INFO quay.io/ebattat/cloud-governance:latest")
