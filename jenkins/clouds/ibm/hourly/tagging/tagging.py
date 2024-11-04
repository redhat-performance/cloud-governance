import os

LDAP_HOST_NAME = os.environ['LDAP_HOST_NAME']
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
IBM_API_KEY = os.environ['IBM_API_KEY']
IBM_API_USERNAME = os.environ['IBM_API_USERNAME']
SPREADSHEET_ID = os.environ['AWS_IAM_USER_SPREADSHEET_ID']
IBM_CUSTOM_TAGS_LIST = os.environ['IBM_CUSTOM_TAGS_LIST']
IBM_CLOUD_API_KEY = os.environ['IBM_CLOUD_API_KEY']
LOGS = os.environ.get('LOGS', 'logs')
account = os.environ['account']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')


def run_cmd(cmd):
    os.system(cmd)


def generate_env_vars(**kwargs):
    items = []
    for k, v in kwargs.items():
        items.append(f'-e {k}="{v}"')
    return ' '.join(items)


def generate_volume_mounts(volume_mounts):
    items = []
    for mount in volume_mounts:
        items.append(f'-v {mount}="{mount}"')
    return ' '.join(items)


def get_podman_run_cmd(volume_mounts: list = None, **kwargs):
    container_name = "--name cloud-governance"
    if not volume_mounts:
        volume_mounts = []
    if "/etc/localtime" not in volume_mounts:
        volume_mounts.append("/etc/localtime")
    cmd = f"podman run --rm {container_name} {generate_env_vars(**kwargs)} {generate_volume_mounts(volume_mounts)} {QUAY_CLOUD_GOVERNANCE_REPOSITORY}"
    return cmd


run_cmd('Run IBM tagging on baremetal, vm')

run_cmd("Run IBM tag baremetal")
volume_mounts_targets = [GOOGLE_APPLICATION_CREDENTIALS]

input_env_keys = {'account': account, 'LDAP_HOST_NAME': LDAP_HOST_NAME,
                  'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS, 'SPREADSHEET_ID': SPREADSHEET_ID,
                  'IBM_API_USERNAME': IBM_API_USERNAME, 'IBM_API_KEY': IBM_API_KEY, 'tag_operation': "update",
                  'log_level': "INFO", 'policy': 'tag_baremetal'}

baremetal_cmd = get_podman_run_cmd(volume_mounts=volume_mounts_targets, **input_env_keys)
run_cmd(baremetal_cmd)

run_cmd("Run IBM tag Virtual Machines")
input_env_keys['policy'] = 'tag_vm'
virtual_machine_cmd = get_podman_run_cmd(volume_mounts=volume_mounts_targets, **input_env_keys)
run_cmd(virtual_machine_cmd)

# Run tag resources
run_cmd("Run tag resources command")
podman_run_cmd = get_podman_run_cmd(policy="tag_resources", account=account,
                                    IBM_CLOUD_API_KEY=IBM_CLOUD_API_KEY,
                                    IBM_CUSTOM_TAGS_LIST=IBM_CUSTOM_TAGS_LIST)
run_cmd(podman_run_cmd)
