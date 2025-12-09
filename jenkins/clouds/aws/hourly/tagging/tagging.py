import os
import subprocess
import time

def run_shell_cmd(cmd: str, container_name: str = None):
    """
    This method run the shell command
    :param cmd:
    :type cmd:
    :param container_name: Optional container name to check for cleanup
    :type container_name:
    :return:
    :rtype:
    """
    subprocess.run(cmd, shell=True, check=False)
    # Wait for podman cleanup - check if the specific container is still running
    if container_name:
        max_wait = 10  # Increased for better cleanup
        wait_interval = 0.5
        elapsed = 0
        while elapsed < max_wait:
            # Check if the specific container is still running
            result = subprocess.run(f"podman ps --filter name={container_name} --format '{{{{.Names}}}}' 2>/dev/null",
                                  shell=True, capture_output=True, text=True)
            if not result.stdout.strip():
                # Container is not running, cleanup is done
                break
            time.sleep(wait_interval)
            elapsed += wait_interval
    # Additional safety delay after cleanup completes
    time.sleep(2)

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
        f"""podman run --rm --name cloud-governance-tag-perf-{region} -e account="perf" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_perf}" -e log_level="INFO" -e "AWS_MAX_ATTEMPTS"="5" -e "AWS_RETRY_MODE"="standard" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""",
        container_name=f"cloud-governance-tag-perf-{region}")
    run_shell_cmd(
        f"""podman run --rm --name cloud-governance-tag-psap-{region} -e account="psap" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PSAP}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PSAP}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_psap}" -e log_level="INFO" -e "AWS_MAX_ATTEMPTS"="5" -e "AWS_RETRY_MODE"="standard" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""",
        container_name=f"cloud-governance-tag-psap-{region}")
    run_shell_cmd(
        f"""podman run --rm --name cloud-governance-tag-perfscale-{region} -e account="perf-scale" -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="{AWS_ACCESS_KEY_ID_DELETE_PERF_SCALE}" -e AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY_DELETE_PERF_SCALE}" -e AWS_DEFAULT_REGION="{region}" -e tag_operation="update" -e mandatory_tags="{mandatory_tags_perf_scale}" -e "AWS_MAX_ATTEMPTS"="5" -e "AWS_RETRY_MODE"="standard" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" {QUAY_CLOUD_GOVERNANCE_REPOSITORY}""",
        container_name=f"cloud-governance-tag-perfscale-{region}")
