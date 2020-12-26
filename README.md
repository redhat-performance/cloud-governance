# Cloud Governance
This tool provides an engineer with a lightweight and flexible framework for 
deploying cloud management policies and OpenShift management capabilities.

**General**

* policies: The policies that run by cloud custodian tool
* tag_cluster_resource: Update cluster tags by cluster name 
* zombie_cluster_resource: Delete cluster's zombies resources

* The cloud-governance package is placed in [PyPi](https://pypi.org/project/cloud-governance/)
* The cloud-governance pipeline is placed in [Jenkins](TBD)

_**Table of Contents**_

<!-- TOC -->
- [Installation](#installation)
- [Update Cluster Tags](#update-cluster-tags)
- [Delete Zombies Clusters](#delete-zombies-clusters)
- [Policies](#policies)
- [Pytest](#pytest)
- [Post Installation](#post-installation)
<!-- /TOC -->


## Installation

```sh
# need to run it as root and aws admin user
aws configure
python3 -m venv governance
source governance/bin/activate
python -m pip install --upgrade pip
pip3 install wheel
pip3 install cloud-governance
python3
```

##  Update Cluster Tags

```sh
>> from cloud_governance.tag_cluster.run_tag_cluster_resouces import scan_cluster_resource, tag_cluster_resource
>> from time import gmtime, strftime
# Choose region
>> region = 'us-east-2'
# Cluster name to be tagged
>> cluster_name = 'test'
# mandatory tags for all cluster resources
>> mandatory_tags = {
        "Owner": "Name",
        "Email": "name@redhat.com",
        "Purpose": "test",
        "Date": strftime("%Y/%m/%d %H:%M:%S")
    }
    
# dry run: scan for cluster resources 
>> scan_cluster_resource(cluster_name=cluster_name, region=region)
# update tags 
>> tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags, region=region)
```

## Delete Zombies Clusters

```sh
>> from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource, delete_zombie_cluster_resource
# Choose region
>> region = 'us-east-2'
# dry run: scan for zombie clusters resource 
>> zombie_cluster_resource(delete=False, region=region)
# delete zombie clusters resource 
>> delete_zombie_cluster_resource(delete=True, region=region)
```

## Policies

ec2_idle.yml
ebs_unattached.yml

Installation steps:
```sh
python3 -m venv custodian
source custodian/bin/activate
(custodian) $ pip install c7n
custodian run --dryrun -s s3://redhat-custodian/logs -l /cloud-custodian/policies /home/user/custodian_policy/ebs_available.yml
deactivate
rm -rf custodian
```

## Pytest

```sh
pip install coverage
pip install pytest
coverage run -m pytest
```

## Post Installation

```sh
deactivate
rm -rf governance
```