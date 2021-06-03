
import os
import typeguard
from time import strftime
from ast import literal_eval  # str to dict
import boto3  # regions
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp, logger
from cloud_governance.tag_cluster.run_tag_cluster_resouces import tag_cluster_resource, tag_ec2_resource
from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource
from cloud_governance.gitleaks.gitleaks import GitLeaks
from cloud_governance.main.es_uploader import ESUploader
from cloud_governance.common.aws.s3.s3_operations import S3Operations

# env tests
# os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
# os.environ['AWS_DEFAULT_REGION'] = 'all'
# os.environ['policy'] = 'tag_ec2'
# os.environ['policy'] = 'ec2_untag'
#os.environ['policy'] = 'zombie_cluster_resource'
#os.environ['dry_run'] = 'yes'
#os.environ['resource'] = 'zombie_cluster_elastic_ip'
# os.environ['resource'] = 'zombie_cluster_nat_gateway'
# os.environ['cluster_tag'] = 'kubernetes.io/cluster/464-pd9qq'
# os.environ['policy_output'] = 's3://redhat-cloud-governance/logs'
# os.environ['policy_output'] = os.path.dirname(os.path.realpath(__file__))
# os.environ['policy'] = 'ebs_unattached'
# os.environ['resource_name'] = 'ocp-orch-perf'
# os.environ['resource_name'] = 'ocs-test'
# os.environ['mandatory_tags'] = "{'Owner': 'name','Email': 'name@redhat.com','Purpose': 'test'}"
# os.environ['mandatory_tags'] = ''
# os.environ['policy'] = 'gitleaks'
# os.environ['git_access_token'] = ''
# os.environ['git_repo'] = 'https://github.com/redhat-performance'
# os.environ['several_repos'] = 'yes'
# os.environ['git_repo'] = 'https://github.com/redhat-performance/pulpperf'
# os.environ['git_repo'] = 'https://github.com/gitleakstest/gronit'
# os.environ['upload_data_elk'] = 'upload_data_elk'

log_level = os.environ.get('log_level', 'INFO').upper()
logger.setLevel(level=log_level)


def get_custodian_policies(type: str = None):
    """
    This method return a list of policies name without extension, that can filter by type
    @return: list of custodian policies name
    """
    custodian_policies = []
    # path for debug only
    # policies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'policy')
    # policies_path working only inside the docker
    policies_path = os.path.join(os.path.dirname(__file__), 'policy')
    for (dirpath, dirnames, filenames) in os.walk(policies_path):
        for filename in filenames:
            if not type:
                custodian_policies.append(os.path.splitext(filename)[0])
            elif type and type in filename:
                custodian_policies.append(os.path.splitext(filename)[0])
    return custodian_policies


@logger_time_stamp
@typeguard.typechecked
def run_policy(account: str, policy: str, region: str, dry_run: str):
    """
    This method run policy per region, first the custom policy and after custodian policy
    :return:
    """
    # Custom policy Tag Cluster
    if policy == 'tag_cluster_resource':
        cluster_name = os.environ['resource_name']
        if dry_run == 'no':
            mandatory_tags = os.environ.get('mandatory_tags', {})
            mandatory_tags = literal_eval(mandatory_tags)  # str to dict
            mandatory_tags['Date'] = strftime("%Y/%m/%d %H:%M:%S")
            tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region)
        else:  # default: yes or other
            tag_cluster_resource(cluster_name=cluster_name, region=region)
    # Custom policy Zombie Cluster
    elif policy == 'zombie_cluster_resource':
        policy_output = os.environ.get('policy_output', '')
        resource = os.environ.get('resource', '')
        cluster_tag = os.environ.get('cluster_tag', '')
        if dry_run == 'no':  # delete
            zombie_result = zombie_cluster_resource(delete=True, region=region, resource=resource, cluster_tag=cluster_tag)
        else:  # default: yes or other
            zombie_result = zombie_cluster_resource(region=region, resource=resource, cluster_tag=cluster_tag)
        if policy_output:
            s3operations = S3Operations(region_name=region)
            logger.info(s3operations.save_results_to_s3(policy=policy.replace('_', '-'), policy_output=policy_output, policy_result=zombie_result))
    elif policy == 'tag_ec2':
        instance_name = os.environ['resource_name']
        mandatory_tags = os.environ.get('mandatory_tags', {})
        mandatory_tags = literal_eval(mandatory_tags)  # str to dict
        mandatory_tags['Name'] = instance_name
        mandatory_tags['Date'] = strftime("%Y/%m/%d %H:%M:%S")
        if dry_run == 'no':
            response = tag_ec2_resource(instance_name=instance_name, mandatory_tags=mandatory_tags, region=region)
        else:
            response = tag_ec2_resource(instance_name=instance_name, mandatory_tags=mandatory_tags, region=region)
        logger.info(response)
    elif policy == 'gitleaks':
        git_access_token = os.environ.get('git_access_token')
        git_repo = os.environ.get('git_repo')
        several_repos = os.environ.get('several_repos', '')
        policy_output = os.environ.get('policy_output', '')
        try:
            if several_repos == 'yes':
                git_leaks = GitLeaks(git_access_token=git_access_token,
                                     git_repo=git_repo,
                                     several_repos=True)
            else:
                git_leaks = GitLeaks(git_access_token=git_access_token,
                                     git_repo=git_repo)
            policy_result = git_leaks.scan_repo()
            logger.info(policy_result)
            if policy_output:
                s3operations = S3Operations(region_name=region)
                logger.info(s3operations.save_results_to_s3(policy=policy, policy_output=policy_output,
                                                policy_result=policy_result))

        except Exception as err:
            logger.exception(f'BadCredentialsException : {err}')
    # custodian policy - check if its a custodian policy
    elif any(policy == item for item in get_custodian_policies()):
        # default is dry run - change it to custodian dry run format
        if dry_run == 'yes':
            dry_run = '--dryrun'
        elif dry_run == 'no':
            dry_run = ''
        else:  # default dry run
            dry_run = '--dryrun'
        policy_output = os.environ.get('policy_output', '')
        # policies_path working only inside the docker
        # run from local - policies_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'policy', f'{policy}.yml')
        policies_path = os.path.join(os.path.dirname(__file__), 'policy')
        if os.path.isfile(f'{policies_path}/{policy}.yml'):
            os.system(f'custodian run {dry_run} -s {policy_output} {policies_path}/{policy}.yml')
        else:
            raise Exception(f'Missing Policy name: "{policies_path}/{policy}.yml"')
            logger.exception(f'Missing Policy name: "{policies_path}/{policy}.yml"')
    else:  # local policy
        # default is dry run - change it to custodian dry run format
        if dry_run == 'yes':
            dry_run = '--dryrun'
        elif dry_run == 'no':
            dry_run = ''
        else:  # default dry run
            dry_run = '--dryrun'
        policy_output = os.environ.get('policy_output', '')
        # run from local - policies_path = os.path.join(os.path.dirname(__file__), '../' ,f'{policy}.yml')
        if os.path.isfile(policy):
            os.system(f'custodian run {dry_run} -s {policy_output} {policy}')
        else:
            raise Exception(f'Missing Policy name: {policy}')
            logger.exception(f'Missing Policy name: {policy}')


@logger_time_stamp
def main():
    """
    This main run 2 processes:
    1. ES uploader
    2. Run policy
    :return: the action output
    """
    # environment variables - get while running the docker
    region_env = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
    dry_run = os.environ.get('dry_run', 'yes')

    account = os.environ.get('account', '')
    policy = os.environ.get('policy', '')
    upload_data_es = os.environ.get('upload_data_es', '')
    es_host = os.environ.get('es_host', '')
    es_port = os.environ.get('es_port', '')
    es_index = os.environ.get('es_index', '')
    es_doc_type = os.environ.get('es_doc_type', '')
    bucket = os.environ.get('bucket', '')

    # 1. ELK Uploader
    if upload_data_es:
        input_data = {'es_host': es_host,
                      'es_port': int(es_port),
                      'es_index': es_index,
                      'es_doc_type': es_doc_type,
                      'es_add_items': {'account': account},
                      'bucket': bucket,
                      'logs_bucket_key': 'logs',
                      's3_file_name': 'resources.json',
                      'region': region_env,
                      'policy': policy,
                      }
        elk_uploader = ESUploader(**input_data)
        elk_uploader.upload_to_es(account=account)
    # 2. POLICY
    else:
        if not policy:
            raise Exception(f'Missing Policy name: "{policy}"')
            logger.exception(f'Missing Policy name: "{policy}"')
        if region_env == 'all':
            # must be set for boto3 client default region
            # os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
            ec2 = boto3.client('ec2')
            regions_data = ec2.describe_regions()
            for region in regions_data['Regions']:
                # logger.info(f"region: {region['RegionName']}")
                os.environ['AWS_DEFAULT_REGION'] = region['RegionName']
                run_policy(account=account, policy=policy, region=region['RegionName'], dry_run=dry_run)
        else:
            run_policy(account=account, policy=policy, region=region_env, dry_run=dry_run)


main()
