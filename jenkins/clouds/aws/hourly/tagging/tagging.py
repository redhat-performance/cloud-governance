import os
import subprocess
import time

def run_shell_cmd(cmd: str):
    """
    This method run the shell command
    :param cmd:
    :type cmd:
    :return:
    :rtype:
    """
    # Use subprocess.run instead of os.system for better process management in CentOS Stream 9
    subprocess.run(cmd, shell=True, check=False)
    # Small delay to allow podman cleanup to complete
    time.sleep(0.5)

AWS_ACCESS_KEY_ID_DELETE_PERF = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF']
AWS_SECRET_ACCESS_KEY_DELETE_PERF = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF']
AWS_ACCESS_KEY_ID_DELETE_PSAP = os.environ['AWS_ACCESS_KEY_ID_DELETE_PSAP']
AWS_SECRET_ACCESS_KEY_DELETE_PSAP = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PSAP']
AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE = os.environ['AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE']
AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE = os.environ['AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE']
QUAY_CLOUD_GOVERNANCE_REPOSITORY = os.environ.get('QUAY_CLOUD_GOVERNANCE_REPOSITORY',
                                                  'quay.io/cloud-governance/cloud-governance:latest')

LOGS = os.environ.get('LOGS', 'logs')

mandatory_tags_perf = {'Budget': 'PERF-DEPT'}
mandatory_tags_psap = {'Budget': 'PSAP'}
mandatory_tags_perf_scale = {'Budget': 'PERF-SCALE'}

print('Run AWS tagging policy pre active region')
regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'ap-south-1', 'eu-north-1', 'eu-west-3', 'eu-west-2',
           'eu-west-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-northeast-1', 'ca-central-1', 'sa-east-1',
           'ap-southeast-1', 'ap-southeast-2', 'eu-central-1']

for region in regions:
    run_shell_cmd(
        f"""podman run --rm --name cloud-governance -e account="perf" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_perf}" -e log_level="INFO" -e "AWS_MAX_ATTEMPTS"="5" -e "AWS_RETRY_MODE"="standard" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
    run_shell_cmd(
        f"""podman run --rm --name cloud-governance -e account="psap" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_psap}" -e log_level="INFO" -e "AWS_MAX_ATTEMPTS"="5" -e "AWS_RETRY_MODE"="standard" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
    run_shell_cmd(
        f"""podman run --rm --name cloud-governance -e account="perf-scale" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_perf_scale}" -e "AWS_MAX_ATTEMPTS"="5" -e "AWS_RETRY_MODE"="standard" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""")
