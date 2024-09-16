[![PyPI Latest Release](https://img.shields.io/pypi/v/cloud-governance.svg)](https://pypi.org/project/cloud-governance/)
[![Container Repository on Quay](https://quay.io/repository/projectquay/quay/status "Container Repository on Quay")](https://quay.io/repository/cloud-governance/cloud-governance?tab=tags)
[![Actions Status](https://github.com/redhat-performance/cloud-governance/actions/workflows/Build.yml/badge.svg)](https://github.com/redhat-performance/cloud-governance/actions)[![Coverage Status](https://coveralls.io/repos/github/redhat-performance/cloud-governance/badge.svg?branch=main)](https://coveralls.io/github/redhat-performance/cloud-governance?branch=main)
[![Documentation Status](https://readthedocs.org/projects/cloud-governance/badge/?version=latest)](https://cloud-governance.readthedocs.io/en/latest/?badge=latest)
[![python](https://img.shields.io/pypi/pyversions/cloud-governance.svg?color=%2334D058)](https://pypi.org/project/cloud-governance)
[![License](https://img.shields.io/pypi/l/cloud-governance.svg)](https://github.com/redhat-performance/cloud-governance/blob/main/LICENSE)

# Cloud Governance

![](images/cloud_governance.png)

## What is it?

**Cloud Governance** tool provides a lightweight and flexible framework for deploying cloud management policies focusing
on cost optimize and security.
We have implemented several pruning policies. \
When monitoring the resources, we found that most of the cost leakage is from available volumes, unused NAT gateways,
and unattached Public IPv4 addresses (Starting from February 2024, public IPv4 addresses are chargeable whether they are
used or not).

This tool support the following policies:
[policy](cloud_governance/policy)

[AWS Polices](cloud_governance/policy/aws)

* Real time Openshift Cluster cost, User cost
* [instance_idle](cloud_governance/policy/aws/cleanup/instance_idle.py): Monitor the idle instances based on the
  instance metrics for the last 7 days.
    * CPU Percent < 2%
    * Network < 5KiB
* [instance_run](cloud_governance/policy/aws/cleanup/instance_run.py): List the running ec2 instances.
* [unattached_volume](cloud_governance/policy/aws/cleanup/unattached_volume.py): Identify and remove the available EBS
  volumes.
* [zombie_cluster_resource](cloud_governance/policy/aws/zombie_cluster_resource.py): Identify the non-live cluster
  resource and delete those resources by resolving dependency. We are deleting more than 20 cluster resources.
    * Ebs, Snapshots, AMI, Load Balancer
    * VPC, Subnets, Route tables, DHCP, Internet Gateway, NatGateway, Network Interface, ElasticIp, Network ACL,
      Security Group, VPC Endpoint
    * S3
    * IAM User, IAM Role
* [ip_unattached](cloud_governance/policy/aws/ip_unattached.py): Identify the unattached public IPv4 addresses.
* [zombie_snapshots](cloud_governance/policy/aws/zombie_snapshots.py): Identify the snapshots, which are abandoned by
  the AMI.
* [unused_nat_gateway](cloud_governance/policy/aws/cleanup/unused_nat_gateway.py): Identify the unused NatGateway by
  monitoring the active connection count.
* [s3_inactive](cloud_governance/policy/aws/s3_inactive.py): Identify the empty s3 buckets, causing the resource quota
  issues.
* [empty_roles](cloud_governance/policy/aws/empty_roles.py): Identify the empty roles that do not have any attached
  policies to them.
* [ebs_in_use](cloud_governance/policy/aws/ebs_in_use.py): list in use volumes.
* [tag_resources](cloud_governance/policy/policy_operations/aws/tag_cluster): Update cluster and non cluster resource
  tags fetching from the user tags or from the mandatory tags
* [tag_non_cluster](cloud_governance/policy/policy_operations/aws/tag_non_cluster): tag ec2 resources (instance, volume,
  ami, snapshot) by instance name
* [tag_iam_user](cloud_governance/policy/policy_operations/aws/tag_user): update the user tags from the csv file
* [cost_explorer](cloud_governance/policy/aws/cost_explorer.py): Get data from cost explorer and upload to ElasticSearch

* gitleaks: scan GitHub repository git leak (security scan)
* [cost_over_usage](cloud_governance/policy/aws/cost_over_usage.py): send mail to aws user if over usage cost

[Azure policies](cloud_governance/policy/azure)

* [instance_idle](cloud_governance/policy/azure/cleanup/instance_idle.py): Monitor the idle instances based on the
  instance metrics.
    * CPU Percent < 2%
    * Network < 5KiB
* [unattached_volume](cloud_governance/policy/azure/cleanup/unattached_volume.py): Identify and remove the available
  disks.
* [ip_unattached](cloud_governance/policy/azure/cleanup/ip_unattached.py): Identify the unattached public IPv4
  addresses.
* [unused_nat_gateway](cloud_governance/policy/azure/cleanup/unused_nat_gateway.py): Identify the unused NatGateway by
  monitoring the active connection count.

[IBM policies](cloud_governance/policy/ibm)

* [tag_baremetal](cloud_governance/policy/ibm/tag_baremetal.py): Tag IBM baremetal machines
* [tag_vm](cloud_governance/policy/ibm/tag_vm.py): Tga IBM Virtual Machines machines

** You can write your own policy using [Cloud-Custodian](https://cloudcustodian.io/docs/quickstart/index.html)
and run it (see 'custom cloud custodian policy' in [Policy workflows](#policy-workloads)).

![](images/cloud_governance1.png)
![](images/demo.gif)

![](images/cloud_governance2.png)

Reference:

* The cloud-governance package is placed in [PyPi](https://pypi.org/project/cloud-governance/)
* The cloud-governance container image is placed in [Quay.io](https://quay.io/repository/ebattat/cloud-governance)
* The cloud-governance readthedocs link is [ReadTheDocs](https://cloud-governance.readthedocs.io/en/latest/)
  ![](images/cloud_governance3.png)

_**Table of Contents**_

<!-- TOC -->

- [Installation](#installation)
- [Configuration](#configuration)
- [Run AWS Policy Using Podman](#run-aws-policy-using-podman)
- [Run IBM Policy Using Podman](#run-ibm-policy-using-podman)
- [Run Policy Using Pod](#run-policy-using-pod)
- [Pytest](#pytest)
- [Post Installation](#post-installation)

<!-- /TOC -->

## Installation

#### Download cloud-governance image from quay.io

```sh
# Need to run it with root privileges
sudo podman pull quay.io/cloud-governance/cloud-governance
```

#### Environment variables description:

(mandatory)AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID

(mandatory)AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY

##### Policy name:

(mandatory)policy=instance_idle / instance_run / ebs_unattached / ebs_in_use / tag_cluster_resource /
zombie_cluster_resource / tag_ec2_resource

##### Policy logs output

(mandatory)policy_output=s3://redhat-cloud-governance/logs

##### Cluster or instance name:

(mandatory policy:tag_cluster_resource)resource_name=ocs-test

##### Cluster or instance tags:

(mandatory policy:tag_cluster_resource)mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}"

##### gitleaks

(mandatory policy: gitleaks)git_access_token=$git_access_token
(mandatory policy: gitleaks)git_repo=https://github.com/redhat-performance/cloud-governance
(optional policy: gitleaks)several_repos=yes/no (default = no)

##### Choose a specific region or all for all the regions, default : us-east-2

(optional)AWS_DEFAULT_REGION=us-east-2/all (default = us-east-2)

##### Choose dry run or not, default yes

(optional)dry_run=yes/no (default = yes)

##### Choose log level, default INFO

(optional)log_level=INFO (default = INFO)

#### LDAP hostname to fetch mail records

LDAP_HOST_NAME=ldap.example.com

#### Enable Google Drive API in console and create Service account

GOOGLE_APPLICATION_CREDENTIALS=$pwd/service_account.json

# Configuration

### AWS Configuration

#### Create a user and a bucket

* Create user with [IAM](iam/clouds)
* Create a logs bucket [create_bucket.sh](iam/clouds/aws/create_bucket.sh)

### IBM Configuration

* Create classic infrastructure API key

## Run AWS Policy Using Podman

```sh
# policy=instance_idle
sudo podman run --rm --name cloud-governance -e policy="instance_idle" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance"

# policy=instance_run
sudo podman run --rm --name cloud-governance -e policy="instance_run" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance"

# select policy ['ec2_stop', 's3_inactive', 'empty_roles', 'ip_unattached', 'unused_nat_gateway', 'zombie_snapshots']
sudo podman run --rm --name cloud-governance -e policy="policy" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes"  -e log_level="INFO" "quay.io/cloud-governance/cloud-governance"

# policy=ebs_unattached
sudo podman run --rm --name cloud-governance -e policy="ebs_unattached" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance"

# policy=ebs_in_use
sudo podman run --rm --name cloud-governance -e policy="ebs_in_use" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance"

# policy=zombie_cluster_resource
sudo podman run --rm --name cloud-governance -e policy="zombie_cluster_resource" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e resource="zombie_cluster_elastic_ip" -e cluster_tag="kubernetes.io/cluster/test-pd9qq" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance"

# policy=tag_resources
sudo podman run --rm --name cloud-governance -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e tag_operation="read/update/delete" -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/cloud-governance/cloud-governance"

# policy=tag_non_cluster
sudo podman run --rm --name cloud-governance -e policy="tag_non_cluster" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e tag_operation="read/update/delete" -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/cloud-governance/cloud-governance"

# policy=tag_iam_user
sudo podman run --rm --name cloud-governance -e policy="tag_iam_user" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e user_tag_operation="read/update/delete" -e remove_tags="['Environment', 'Test']" -e username="test_username" -e file_name="tag_user.csv"  -e log_level="INFO" -v "/home/user/tag_user.csv":"/tmp/tag_user.csv" --privileged "quay.io/cloud-governance/cloud-governance"

# policy=cost_explorer
sudo podman run --rm --name cloud-governance -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e es_host="$elasticsearch_host" -e es_port="$elasticsearch_port" -e es_index="$elasticsearch_index" -e cost_metric=UnblendedCost -e start_date="$start_date" -e end_date="$end_date" -e granularity="DAILY" -e cost_explorer_tags="['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance:latest"
sudo podman run --rm --name cloud-governance -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e es_index="elasticsearch_index" -e cost_metric="UnblendedCost" -e start_date="$start_date" -e end_date="$end_date" -e granularity="DAILY" -e cost_explorer_tags="['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']" -e file_name="cost_explorer.txt" -v "/home/cost_explorer.txt":"/tmp/cost_explorer.txt" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance:latest"

# policy=validate_iam_user_tags
sudo podman run --rm --name cloud-governance  -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e validate_type="spaces/tags" -e user_tags="['Budget', 'User', 'Owner', 'Manager', 'Environment', 'Project']"   -e log_level="INFO" "quay.io/cloud-governance/cloud-governance:latest"

# policy=gitleaks
sudo podman run --rm --name cloud-governance -e policy="gitleaks" -e git_access_token="$git_access_token" -e git_repo="https://github.com/redhat-performance/cloud-governance" -e several_repos="no" -e log_level="INFO" "quay.io/cloud-governance/cloud-governance"

# custom cloud custodian policy (path for custom policy: -v /home/user/custodian_policy:/custodian_policy)
sudo podman run --rm --name cloud-governance -e policy="/custodian_policy/policy.yml" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" -v "/home/user/custodian_policy":"/custodian_policy" --privileged "quay.io/cloud-governance/cloud-governance"

```

## Run IBM Policy Using Podman

```sh
# policy=tag_baremetal
podman run --rm --name cloud-governance -e policy="tag_baremetal" -e account="$account" -e IBM_API_USERNAME="$IBM_API_USERNAME" -e IBM_API_KEY="$IBM_API_KEY" -e SPREADSHEET_ID="$SPREADSHEET_ID" -e GOOGLE_APPLICATION_CREDENTIALS="$GOOGLE_APPLICATION_CREDENTIALS" -v $GOOGLE_APPLICATION_CREDENTIALS:$GOOGLE_APPLICATION_CREDENTIALS -e LDAP_USER_HOST="$LDAP_USER_HOST" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/cloud-governance/cloud-governance:latest"

# tag=tab_vm
podman run --rm --name cloud-governance -e policy="tag_vm" -e account="$account" -e IBM_API_USERNAME="$IBM_API_USERNAME" -e IBM_API_KEY="$IBM_API_KEY" -e SPREADSHEET_ID="$SPREADSHEET_ID" -e GOOGLE_APPLICATION_CREDENTIALS="$GOOGLE_APPLICATION_CREDENTIALS" -v $GOOGLE_APPLICATION_CREDENTIALS:$GOOGLE_APPLICATION_CREDENTIALS -e LDAP_USER_HOST="$LDAP_USER_HOST" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/cloud-governance/cloud-governance:latest"

```

## Run Policy Using Pod

#### Run as a pod job via OpenShift

Job Pod: [cloud-governance.yaml](pod_yaml/cloud-governance.yaml)

Configmaps: [cloud_governance_configmap.yaml](pod_yaml/cloud_governance_configmap.yaml)

Quay.io Secret: [quayio_secret.sh](pod_yaml/quayio_secret.sh)

AWS Secret: [cloud_governance_secret.yaml](pod_yaml/cloud_governance_secret.yaml)

    * Need to convert secret key to base64 [run_base64.py](pod_yaml/run_base64.py)

## Pytest

##### Cloud-governance integration tests using pytest

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
sudo podman rmi quay.io/cloud-governance/cloud-governance
```
