import os
from time import gmtime, strftime  # date tag
from ast import literal_eval  # str to dict
from os import listdir
from os.path import isfile, join  # list files

from cloud_governance.tag_cluster.run_tag_cluster_resouces import tag_cluster_resource
from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource

# env tests
# os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
# os.environ['action'] = 'tag_cluster_resource'
# os.environ['policies_output'] ='s3://redhat-custodian/logs'
# os.environ['dry_run'] = 'yes'
# os.environ['policy'] = 'ebs_unattached.yml'
# os.environ['action'] = 'tag_cluster_resource'
# os.environ['cluster_name'] = 'ocs-test'
# os.environ['mandatory_tags'] = "{'Owner': 'Eli Battat','Email': 'ebattat@redhat.com','Purpose': 'test'}"
# os.environ['mandatory_tags'] = ''

# environment variables - get while running the docker
region = os.environ['AWS_DEFAULT_REGION']
action = os.environ['action']


def main():
    """
    This is the main for running actions
    :return: the action output
    """
    # Policy
    if action == 'policy':
        dry_run = os.environ['dry_run']
        # default is dry run
        if dry_run == 'yes':
            dry_run = '--dryrun'
        elif dry_run == 'no':
            dry_run = ''
        else:  # default dry run
            dry_run = '--dryrun'
        policies_output = os.environ['policies_output']
        policy = os.environ['policy']
        policies_path = os.path.join(os.path.dirname(__file__), f'{action}')
        if policy == 'all':  # all policies
            policy_files = [f for f in listdir(policies_path) if isfile(join(policies_path, f))]
            for policy in policy_files:
                os.system(f'custodian run {dry_run} -s {policies_output} {policies_path}/{policy}')
        elif policy and policy != 'all': # single policy
            os.system(f'custodian run {dry_run} -s {policies_output} {policies_path}/{policy}')
    # Tag
    elif action == 'tag_cluster_resource':
        cluster_name = os.environ['cluster_name']
        dry_run = os.environ['dry_run']
        mandatory_tags = os.environ['mandatory_tags']
        if dry_run == 'no':
            mandatory_tags = literal_eval(mandatory_tags)
            mandatory_tags['Date'] = strftime("%Y/%m/%d %H:%M:%S")
            tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region)
        else:  # default: yes or other
            tag_cluster_resource(cluster_name=cluster_name, region=region)
    # Zombie
    elif action == 'zombie_cluster_resource':
        dry_run = os.environ['dry_run']
        if dry_run == 'no':
            zombie_cluster_resource(delete=True, region=region)
        else:  # default: yes or other
            zombie_cluster_resource(delete=False, region=region)


main()
