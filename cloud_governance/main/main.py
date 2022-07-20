
import os
import typeguard
from time import strftime
from ast import literal_eval  # str to dict
import boto3  # regions
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp, logger
from cloud_governance.cost_expenditure.generate_cost_explorer_report import GenerateCostExplorerReport
from cloud_governance.tag_cluster.run_tag_cluster_resouces import tag_cluster_resource, remove_cluster_resources_tags
from cloud_governance.tag_non_cluster.run_tag_non_cluster_resources import tag_non_cluster_resource, remove_tag_non_cluster_resource, tag_na_resources
from cloud_governance.tag_user.run_tag_iam_user import tag_iam_user, run_validate_iam_user_tags
from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource
from cloud_governance.gitleaks.gitleaks import GitLeaks
from cloud_governance.main.es_uploader import ESUploader
from cloud_governance.common.aws.s3.s3_operations import S3Operations
from cloud_governance.zombie_cluster.validate_zombies import ValidateZombies
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_resources import zombie_non_cluster_resource

# env tests
# os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
# os.environ['AWS_DEFAULT_REGION'] = 'all'
# os.environ['policy'] = 'cost_explorer'
# os.environ['validate_type'] = 'tags'
# os.environ['user_tags'] = "['Budget', 'User', 'Owner', 'Manager', 'Environment', 'Project']"
# os.environ['cost_metric'] = ''
# os.environ['start_date'] = ''
# os.environ['end_date'] = ''
# os.environ['granularity'] = ''
# os.environ['policy'] = 'ec2_untag'
# os.environ['policy'] = 'zombie_cluster_resource'
# os.environ['dry_run'] = 'yes'
# os.environ['tag_operation'] = 'read'
# os.environ['service_type'] = 'ec2_zombie_resource_service'
# os.environ['service_type'] = 'iam_zombie_resource_service'
# os.environ['service_type'] = 's3_zombie_resource_service'
# os.environ['resource'] = 'zombie_cluster_elastic_ip'
# os.environ['resource'] = 'zombie_cluster_nat_gateway'
# os.environ['cluster_tag'] = ''
# os.environ['cluster_tag'] = ''
# os.environ['policy_output'] = 's3://redhat-cloud-governance/logs'
# os.environ['policy_output'] = os.path.dirname(os.path.realpath(__file__))
# os.environ['policy'] = 'ebs_unattached'
# os.environ['resource_name'] = 'ocp-test'
# os.environ['user_tag_operation'] = 'read'
# os.environ['remove_tags'] = "['Manager', 'Project','Environment', 'Owner', 'Budget']"
# os.environ['username'] = 'athiruma'
# os.environ['cost_explorer_tags'] = "['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']"
# os.environ['file_name'] = 'tag_user.csv'
# os.environ['file_path'] = ''
# os.environ['mandatory_tags'] = "{'Budget': 'PERF-DEPT'}"
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
    if policy == 'tag_resources':
        cluster_name = os.environ.get('resource_name', '')
        mandatory_tags = os.environ.get('mandatory_tags', {})
        tag_operation = os.environ.get('tag_operation', '')
        if mandatory_tags:
            mandatory_tags = literal_eval(mandatory_tags)  # str to dict
        if tag_operation == 'delete':
            remove_cluster_resources_tags(region=region, cluster_name=cluster_name, input_tags=mandatory_tags)
        else:
            tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region, tag_operation=tag_operation)
    elif policy == 'validate_iam_user_tags':
        es_host = os.environ.get('es_host', '')
        es_port = os.environ.get('es_port', '')
        es_index = os.environ.get('es_index', '')
        validate_type = os.environ.get('validate_type', '')
        user_tags = os.environ.get('user_tags', {})
        if user_tags:
            user_tags = literal_eval(user_tags)
        run_validate_iam_user_tags(es_host=es_host, es_port=es_port, es_index=es_index, validate_type=validate_type, user_tags=user_tags)

    elif policy == 'cost_explorer':
        es_host = os.environ.get('es_host', '')
        es_port = os.environ.get('es_port', '')
        es_index = os.environ.get('es_index', '')
        cost_metric = os.environ.get('cost_metric', '')
        start_date = os.environ.get('start_date', '')
        end_date = os.environ.get('end_date', '')
        granularity = os.environ.get('granularity', '')
        file_name = os.environ.get('file_name', '')
        account = os.environ.get('account', '')
        if account:
            account = account.upper()
        cost_explorer_tags = literal_eval(os.environ.get('cost_explorer_tags', {}))
        if granularity and cost_metric:
            run_cost_explorer = GenerateCostExplorerReport(cost_tags=cost_explorer_tags, es_host=es_host, es_port=es_port, es_index=es_index, cost_metric=cost_metric, file_name=file_name,
                                                           start_date=start_date, end_date=end_date, granularity=granularity, account=account)
        else:
            run_cost_explorer = GenerateCostExplorerReport(cost_tags=cost_explorer_tags, es_host=es_host, es_port=es_port, es_index=es_index, file_name=file_name,
                                                           start_date=start_date, end_date=end_date, account=account)
        run_cost_explorer.upload_tags_cost_to_elastic_search()
    elif policy == 'validate_cluster':
        file_path = os.environ.get('file_path', '')
        file_name = os.environ.get('file_name', '')
        file_path = file_path+file_name
        validate_zombies = ValidateZombies(file_path=file_path, region=region)
        validate_zombies.read_csv()
    elif policy == 'tag_cluster':
        cluster_name = os.environ.get('resource_name', '')
        mandatory_tags = os.environ.get('mandatory_tags', {})
        tag_operation = os.environ.get('tag_operation', '')
        if mandatory_tags:
            mandatory_tags = literal_eval(mandatory_tags)  # str to dict
        if tag_operation == 'delete':
            remove_cluster_resources_tags(region=region, cluster_name=cluster_name, input_tags=mandatory_tags, cluster_only=True)
        else:
            tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region, tag_operation=tag_operation, cluster_only=True )
    elif policy == 'tag_iam_user':
        user_tag_operation = os.environ.get('user_tag_operation', '')
        file_name = os.environ.get('file_name', '')
        username = os.environ.get('username', '')
        remove_keys = os.environ.get('remove_tags', '')
        if remove_keys:
            remove_keys = literal_eval(remove_keys)
        tag_iam_user(user_tag_operation=user_tag_operation, file_name=file_name, remove_keys=remove_keys, username=username)
    elif policy == 'zombie_non_cluster_resource':
        zombie_non_cluster_resource(dry_run=dry_run, region=region)
    elif policy == 'zombie_cluster_resource':
        policy_output = os.environ.get('policy_output', '')
        resource = os.environ.get('resource', '')
        resource_name = os.environ.get('resource_name', '')
        cluster_tag = os.environ.get('cluster_tag', '')
        service_type = os.environ.get('service_type', '')
        if dry_run == 'no':  # delete
            zombie_result = zombie_cluster_resource(delete=True, region=region, resource=resource,
                                                    cluster_tag=cluster_tag, resource_name=resource_name, service_type=service_type)
        else:  # default: yes or other
            zombie_result = zombie_cluster_resource(region=region, resource=resource, cluster_tag=cluster_tag,
                                                    resource_name=resource_name, service_type=service_type)
        if policy_output:
            s3operations = S3Operations(region_name=region)
            logger.info(s3operations.save_results_to_s3(policy=policy.replace('_', '-'), policy_output=policy_output,
                                                        policy_result=zombie_result))
    elif policy == 'tag_non_cluster':
        # instance_name = os.environ['resource_name']
        mandatory_tags = os.environ.get('mandatory_tags', {})
        tag_operation = os.environ.get('tag_operation', '')
        file_name = os.environ.get('file_name', '')
        if file_name:
            file_path = os.environ.get('file_path', '')
            if file_path:
                tag_na_resources(file_name=file_name, region=region, tag_operation=tag_operation, file_path=file_path)
            else:
                tag_na_resources(file_name=file_name, region=region, tag_operation=tag_operation)
        else:
            if mandatory_tags:
                mandatory_tags = literal_eval(mandatory_tags)  # str to dict
            # mandatory_tags['Name'] = instance_name
            if tag_operation == 'delete':
                remove_tag_non_cluster_resource(mandatory_tags=mandatory_tags, region=region, dry_run='no')
            else:
                tag_non_cluster_resource(mandatory_tags=mandatory_tags, region=region, tag_operation=tag_operation)
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
            logger.exception(f'Missing Policy name: "{policies_path}/{policy}.yml"')
            raise Exception(f'Missing Policy name: "{policies_path}/{policy}.yml"')
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
            logger.exception(f'Missing Policy name: {policy}')
            raise Exception(f'Missing Policy name: {policy}')


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
            logger.exception(f'Missing Policy name: "{policy}"')
            raise Exception(f'Missing Policy name: "{policy}"')
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
