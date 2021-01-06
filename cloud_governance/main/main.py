
import os
from time import gmtime, strftime  # date tag
from ast import literal_eval  # str to dict
import boto3  # regions
from cloud_governance.common.logger.init_logger import logger, logging
from cloud_governance.tag_cluster.run_tag_cluster_resouces import tag_cluster_resource
from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource

#  env tests
os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
#os.environ['AWS_DEFAULT_REGION'] = 'all'
#os.environ['policy'] = 'tag_cluster_resource'
#os.environ['policy'] = 'zombie_cluster_resource'
#os.environ['action'] = 'tag_cluster_resource'
os.environ['policy_output'] ='s3://redhat-cloud-governance/logs'
os.environ['dry_run'] = 'yes'
os.environ['policy'] = 'ebs_unattached'
os.environ['cluster_name'] = 'ocs-test'
os.environ['mandatory_tags'] = "{'Owner': 'Eli Battat','Email': 'ebattat@redhat.com','Purpose': 'test'}"
os.environ['mandatory_tags'] = ''


def run_policy(policy: str, region: str, dry_run: str):
    """
    This method run policy per region, first the custom policy and after custodian policy
    :return:
    """
    # Custom policy Tag
    if policy == 'tag_cluster_resource':
        cluster_name = os.environ['cluster_name']
        if dry_run == 'no':
            mandatory_tags = os.environ.get('mandatory_tags', {})
            mandatory_tags = literal_eval(mandatory_tags)
            mandatory_tags['Date'] = strftime("%Y/%m/%d %H:%M:%S")
            tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region)
        else:  # default: yes or other
            tag_cluster_resource(cluster_name=cluster_name, region=region)
    # Custom policy Zombie
    elif policy == 'zombie_cluster_resource':
        if dry_run == 'no':  # delete
            zombie_cluster_resource(delete=True, region=region)
        else:  # default: yes or other
            zombie_cluster_resource(region=region)
    else:  # default policy of cloud custodian - yaml file
        # default is dry run - change it to custodian dry run format
        if dry_run == 'yes':
            dry_run = '--dryrun'
        elif dry_run == 'no':
            dry_run = ''
        else:  # default dry run
            dry_run = '--dryrun'
        policy_output = os.environ['policy_output']
        # run from local - policies_path = os.path.join(os.path.dirname(__file__), '../' ,f'{policy}.yml')
        policy_full_path = f'{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/policy/{policy}.yml'
        if os.path.isfile(policy_full_path):
            os.system(f'custodian run {dry_run} -s {policy_output} {policy_full_path}')
        else:
            raise Exception(f'Missing Policy name: {policy_full_path}')
            logger.exception(f'Missing Policy name: {policy_full_path}')


def main():
    """
    This is the main for running actions
    :return: the action output
    """
    # environment variables - get while running the docker
    region_env = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
    dry_run = os.environ.get('dry_run', 'yes')
    log_level = os.environ.get('log_level', 'INFO').upper()
    policy = os.environ.get('policy', '')
    if not policy:
        raise Exception(f'Missing Policy name: "{policy}"')
        logger.exception(f'Missing Policy name: "{policy}"')
    logger.setLevel(level=log_level)
    if region_env == 'all':
        # must be set for bot03 client default region
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
        ec2 = boto3.client('ec2')
        regions_data = ec2.describe_regions()
        for region in regions_data['Regions']:
            os.environ['AWS_DEFAULT_REGION'] = region['RegionName']
            run_policy(policy=policy, region=region['RegionName'], dry_run=dry_run)
    else:
        run_policy(policy=policy, region=region_env, dry_run=dry_run)


main()
