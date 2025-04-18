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
IBM_ACCOUNT_ID_PERFORMANCE_SCALE = os.environ['IBM_ACCOUNT_ID_PERFORMANCE_SCALE']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')


def run_cmd(cmd):
    os.system(cmd)
    os.system('echo "\n\n\n"')


def generate_env_vars(**kwargs):
    items = []
    for k, v in kwargs.items():
        items.append(f'-e {k}="{v}"')
    return ' '.join(items)


def generate_volume_mounts(volume_mounts):
    items = []
    for mount in volume_mounts:
        items.append(f'-v {mount}:"{mount}"')
    return ' '.join(items)


def get_podman_run_cmd(volume_mounts: list = None, **kwargs):
    container_name = "--name cloud-governance"
    if not volume_mounts:
        volume_mounts = []
    if "/etc/localtime" not in volume_mounts:
        volume_mounts.append("/etc/localtime")
    cmd = f"podman run --rm {container_name} {generate_env_vars(**kwargs)} {generate_volume_mounts(volume_mounts)} \
    {QUAY_CLOUD_GOVERNANCE_REPOSITORY}"
    return cmd


# Run tag resources
run_cmd("echo Run tag resources command")
podman_run_cmd = get_podman_run_cmd(policy="tag_resources", account=account,
                                    IBM_CLOUD_API_KEY=IBM_CLOUD_API_KEY,
                                    IBM_CUSTOM_TAGS_LIST=IBM_CUSTOM_TAGS_LIST,
                                    PUBLIC_CLOUD_NAME="IBM",
                                    IBM_ACCOUNT_ID=IBM_ACCOUNT_ID_PERFORMANCE_SCALE,
                                    IBM_API_USERNAME=IBM_API_USERNAME,
                                    IBM_API_KEY=IBM_API_KEY, )
run_cmd(podman_run_cmd)

run_cmd("echo Run IBM tagging on baremetal, vm")

run_cmd("echo Run IBM tag baremetal")
volume_mounts_targets = [GOOGLE_APPLICATION_CREDENTIALS]
tag_custom = [IBM_CUSTOM_TAGS_LIST]
input_env_keys = {'account': account, 'LDAP_HOST_NAME': LDAP_HOST_NAME,
                  'GOOGLE_APPLICATION_CREDENTIALS': GOOGLE_APPLICATION_CREDENTIALS, 'SPREADSHEET_ID': SPREADSHEET_ID,
                  'IBM_API_USERNAME': IBM_API_USERNAME, 'IBM_API_KEY': IBM_API_KEY, 'tag_operation': "update",
                  'log_level': "INFO", 'policy': 'tag_baremetal', "PUBLIC_CLOUD_NAME": "IBM", "tag_custom": tag_custom}

baremetal_cmd = get_podman_run_cmd(volume_mounts=volume_mounts_targets, **input_env_keys)
run_cmd(baremetal_cmd)

run_cmd("echo Run IBM tag Virtual Machines")
input_env_keys['policy'] = 'tag_vm'
virtual_machine_cmd = get_podman_run_cmd(volume_mounts=volume_mounts_targets, **input_env_keys)
run_cmd(virtual_machine_cmd)
