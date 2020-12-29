import os
from ast import literal_eval  # str to dict

from cloud_governance.tag_cluster.run_tag_cluster_resouces import scan_cluster_resource, tag_cluster_resource
from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource, delete_zombie_cluster_resource
from time import gmtime, strftime

#os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
region = os.environ['AWS_DEFAULT_REGION']
#os.environ['action'] = 'scan_cluster_resource'
action = os.environ['action']
#os.environ['cluster_name'] = 'ocs-test'
cluster_name = os.environ['cluster_name']

#os.environ['mandatory_tags'] = "{'Owner': 'Eli Battat','Email': 'ebattat@redhat.com','Purpose': 'test'}"
mandatory_tags = os.environ['mandatory_tags']
mandatory_tags = literal_eval(mandatory_tags)
mandatory_tags['Date'] = strftime("%Y/%m/%d %H:%M:%S")


def main():
    if action == 'scan_cluster_resource':
        scan_cluster_resource(cluster_name=cluster_name, region=region)
    elif action == 'tag_cluster_resource':
        tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region)
    elif action == 'zombie_cluster_resource':
        zombie_cluster_resource(delete=False, region=region)
    elif action == 'delete_zombie_cluster_resource':
        delete_zombie_cluster_resource(delete=True, region=region)


main()
