# Cloud Governance
This tool provides an engineer with a lightweight and flexible framework for 
deploying cloud management policies and OpenShift management capabilities.

**General**

* policies: The policies that run by cloud custodian tool
* tag_cluster_resource: Update cluster tags by cluster name 
* zombie_cluster_resource: Delete cluster's zombies resources

TBD:
* The cloud-governance package is placed in [PyPi](TBD)
* The cloud-governance pipeline is placed in [Jenkins](TBD)

_**Table of Contents**_

<!-- TOC -->
- [Installation](#installation)
- [Update Cluster Tags](#update-cluster-tags)
- [Delete Cluster Zombies](#delete-cluster-zombies)
- [Policies](#policies)
- [Pytest](#pytest)
- [Post Installation](#post-installation)
<!-- /TOC -->


## Installation

```sh
# need to run it as root
aws configure
git clone https://github.com/redhat-performance/cloud-governance
python3 -m venv governance
source governance/bin/activate
python -m pip install --upgrade pip
pip3 install wheel
pip3 install cloud-governance/cloud_governance-1.0.0-py3-none-any.whl

python3
```

##  Update Cluster Tags

```sh
>> from cloud_governance.tag_cluster.run_tag_cluster_resouces import scan_cluster_resource, tag_cluster_resource
>> from time import gmtime, strftime
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
>> scan_cluster_resource(cluster_name=cluster_name)
# update tags 
>> tag_cluster_resource(cluster_name=cluster_name, mandatory_tags=mandatory_tags)
```

## Delete Cluster Zombies

```sh
>> from cloud_governance.zombie_cluster.run_zombie_cluster_resources import zombie_cluster_resource, delete_zombie_cluster_resource
# dry run: scan for zombie clusters resource 
>> zombie_cluster_resource()
# delete zombie clusters resource 
>> delete_zombie_cluster_resource()
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