# Cloud Governance
This tool provides an engineer with a lightweight and flexible framework for 
deploying cloud management policies and OpenShift management capabilities.

**General**

This tool support the following actions:

* policy: Run policy per account and region
* tag_cluster_resource: Update cluster tags by cluster name 
* zombie_cluster_resource: Delete cluster's zombies resources

each action run in seperate container using podman

Reference:
* The cloud-governance package is placed in [PyPi](https://pypi.org/project/cloud-governance/)
* The cloud-governance image is placed in [Quay.io](https://quay.io/repository/ebattat/cloud-governance)
* The cloud-governance pipeline is placed in [Jenkins](TBD)

_**Table of Contents**_

<!-- TOC -->
- [Installation](#installation)
- [Policy](#policy)
- [Update Cluster Tags](#update-cluster-tags)
- [Delete Zombies Clusters](#delete-zombies-clusters)
- [Pytest](#pytest)
- [Post Installation](#post-installation)

<!-- /TOC -->

## Installation

#### Download cloud-governance image from quay.io
```sh
# Need to run it with root privileges using podman
sudo podman pull quay.io/ebattat/cloud-governance
```

## Policy
#### Run policy per account and region
#### Existing policies: 

1. ec2_idle.yml - scan account/region for idle ec2

2. ebs_unattached.yml - scan account/region for unattached ebs

#### Fill the following Parameters in podman command:

AWS_ACCESS_KEY_ID=awsaccesskeyid

AWS_SECRET_ACCESS_KEY=awssecretaccesskey

AWS_DEFAULT_REGION=us-east-2/all

action=policy

dry_run=yes/no

policy_output=s3://redhat-cloud-governance/logs

policy=ebs_unattached.yml/all

log_level=INFO

#### Run one policy
```sh

sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e action=policy -e dry_run=yes -e policy_output=s3://redhat-cloud-governance/logs -e policy=ebs_unattached.yml -e log_level=INFO quay.io/ebattat/cloud-governance

```

#### Run all policies
```sh

sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e action=policy -e dry_run=yes -e policy_output=s3://redhat-cloud-governance/logs -e policy=all -e log_level=INFO quay.io/ebattat/cloud-governance

```
##  Update Cluster Tags
#### Update cluster tags by cluster name 
#### Fill the following Parameters in podman command:

AWS_ACCESS_KEY_ID=awsaccesskeyid

AWS_SECRET_ACCESS_KEY=awssecretaccesskey

AWS_DEFAULT_REGION=us-east-2/all

action=tag_cluster_resource

dry_run=yes

cluster_name=ocs-test

mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}"

log_level=INFO

#### Update Cluster Tags
```sh
sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e action=tag_cluster_resource -e dry_run=yes -e cluster_name=ocs-test -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO quay.io/ebattat/cloud-governance

```

## Delete Zombies Clusters
#### Delete cluster's zombies resources
#### Fill the following Parameters in podman command:

AWS_ACCESS_KEY_ID=awsaccesskeyid

AWS_SECRET_ACCESS_KEY=awssecretaccesskey

AWS_DEFAULT_REGION=us-east-2/all

action=zombie_cluster_resource

dry_run=yes

log_level=INFO

#### Delete Zombies Clusters
```sh
sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e action=zombie_cluster_resource -e dry_run=yes -e log_level=INFO quay.io/ebattat/cloud-governance
```

## Pytest

```sh
python3 -m venv governance
source governance/bin/activate
(governance) $ python -m pip install --upgrade pip
(governance) $ pip install coverage
(governance) $ pip install pytest
(governance) $ git clone https://github.com/redhat-performance/cloud-governance
(governance) $ cd cloud-governance
(governance) $ coverage run -m pytest
(governance) $ deactivate
rm -rf *governance*
```

## Post Installation

#### Delete cloud-governance image
```sh
sudo podman rmi quay.io/ebattat/cloud-governance
```