import os
from time import gmtime, strftime  # date tag
from ast import literal_eval  # str to dict
from os import listdir
from os.path import isfile, join  # list files
import boto3  # regions
from cloud_governance.common.logger.init_logger import logger, logging
from cloud_governance.tag_cluster.run_tag_cluster_resouces import tag_cluster_resource
from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource

#  env tests
# os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
# #os.environ['AWS_DEFAULT_REGION'] = 'all'
# #os.environ['action'] = 'policy'
# os.environ['action'] = 'tag_cluster_resource'
# os.environ['policy_output'] ='s3://redhat-cloud-governance/logs'
# os.environ['dry_run'] = 'yes'
# os.environ['policy'] = 'ebs_unattached.yml'
# os.environ['cluster_name'] = 'ocs-test'
# os.environ['mandatory_tags'] = "{'Owner': 'Eli Battat','Email': 'ebattat@redhat.com','Purpose': 'test'}"
# os.environ['mandatory_tags'] = ''


def run_action(action: str, region: str, dry_run: str):
    """
    This method run action per region
    :return:
    """
    # Policy
    if action == 'policy':
        # default is dry run
        if dry_run == 'yes':
            dry_run = '--dryrun'
        elif dry_run == 'no':
            dry_run = ''
        else:  # default dry run
            dry_run = '--dryrun'
        policy_output = os.environ['policy_output']
        policy = os.environ['policy']
        # run from local - policies_path = os.path.join(os.path.dirname(__file__), '../' ,f'{action}')
        policies_path = os.path.join(os.path.dirname(__file__), f'{action}')
        if policy == 'all':  # all policy
            policy_files = [f for f in listdir(policies_path) if isfile(join(policies_path, f))]
            for policy in policy_files:
                os.system(f'custodian run {dry_run} -s {policy_output} {policies_path}/{policy}')
        elif policy and policy != 'all':  # single policy
            os.system(f'custodian run {dry_run} -s {policy_output} {policies_path}/{policy}')
    # Tag
    elif action == 'tag_cluster_resource':
        cluster_name = os.environ['cluster_name']
        mandatory_tags = os.environ['mandatory_tags']
        if dry_run == 'no':
            mandatory_tags = literal_eval(mandatory_tags)
            mandatory_tags['Date'] = strftime("%Y/%m/%d %H:%M:%S")
            tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region)
        else:  # default: yes or other
            tag_cluster_resource(cluster_name=cluster_name, region=region)
    # Zombie
    elif action == 'zombie_cluster_resource':
        if dry_run == 'no':
            zombie_cluster_resource(delete=True, region=region)
        else:  # default: yes or other
            zombie_cluster_resource(delete=False, region=region)


def main():
    """
    This is the main for running actions
    :return: the action output
    """
    # environment variables - get while running the docker
    region_env = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
    dry_run = os.environ.get('dry_run', 'yes')
    log_level = os.environ.get('log_level', 'INFO').upper()
    action_env = os.environ['action']
    logger.setLevel(level=log_level)
    if region_env == 'all':
        # must be set for bot03 client default region
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
        ec2 = boto3.client('ec2')
        regions_data = ec2.describe_regions()
        for region in regions_data['Regions']:
            os.environ['AWS_DEFAULT_REGION'] = region['RegionName']
            run_action(action=action_env, region=region['RegionName'], dry_run=dry_run)
    else:
        run_action(action=action_env, region=region_env, dry_run=dry_run)


main()
