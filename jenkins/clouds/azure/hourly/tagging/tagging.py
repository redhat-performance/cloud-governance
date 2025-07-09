import os

# Read environment variables
AZURE_CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
AZURE_TENANT_ID = os.environ['AZURE_TENANT_ID']
AZURE_CLIENT_ID = os.environ['AZURE_CLIENT_ID']
AZURE_ACCOUNT_ID = os.environ['AZURE_ACCOUNT_ID']
GLOBAL_TAGS = os.environ['GLOBAL_TAGS']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get(
    'QUAY_CLOUD_GOVERNANCE_REPOSITORY',
    'quay.io/cloud-governance/cloud-governance:latest'
)

print('Running the Azure tagging')

# Setup container environment variables
input_vars_to_container = [{
    'account': 'perf-scale-azure',
    'AZURE_CLIENT_ID': AZURE_CLIENT_ID,
    'AZURE_TENANT_ID': AZURE_TENANT_ID,
    'AZURE_CLIENT_SECRET': AZURE_CLIENT_SECRET,
    'AZURE_ACCOUNT_ID': AZURE_ACCOUNT_ID,
    'GLOBAL_TAGS': GLOBAL_TAGS
}]

for input_vars in input_vars_to_container:
    envs = [f"{k}={v}" for k, v in input_vars.items()]
    env_flags = ' '.join([f'-e {env}' for env in envs])
    cmd = f"podman run --rm --name cloud-governance {env_flags} -e policy=tag_azure_resource_group {QUAY_CLOUD_GOVERNANCE_REPOSITORY}"
    os.system(cmd)
