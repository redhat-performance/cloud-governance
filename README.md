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
- [Run Policy Using Podman](#run-policy-using-podman)
- [Run Policy Using Pod](#run-policy-using-pod)
- [Pytest](#pytest)
- [Post Installation](#post-installation)

<!-- /TOC -->

## Installation

#### Download cloud-governance image from quay.io
```sh
# Need to run it with root privileges using podman
sudo podman pull quay.io/ebattat/cloud-governance
```

## Run Policy Using Podman

#### Run policy per account and region
#### Support policy: 

1. ec2_idle - scan account/region for idle ec2

2. ebs_unattached - scan account/region for unattached ebs

3. tag_cluster_resource - tag all cluster resource

4. zombie_cluster_resource - zombie cluster resource

#### Fill the following Parameters in podman command:

(mandatory)AWS_ACCESS_KEY_ID=awsaccesskeyid

(mandatory)AWS_SECRET_ACCESS_KEY=awssecretaccesskey

(mandatory)policy=ebs_unattached / ec2_idle / tag_cluster_resource / zombie_cluster_resource

(mandatory)policy_output=s3://redhat-cloud-governance/logs

(policy:tag_cluster_resource)cluster_name=ocs-test

(policy:tag_cluster_resource)mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}"

(optional)AWS_DEFAULT_REGION=us-east-2/all (default = us-east-2)

(optional)dry_run=yes/no (default = yes)

(optional)log_level=INFO (default = INFO)

#### Run policy
```sh

sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e policy=ebs_unattached -e dry_run=yes -e policy_output=s3://redhat-cloud-governance/logs -e log_level=INFO quay.io/ebattat/cloud-governance

```

## Run Policy Using Pod

#### Run as a pod job via OpenShift

Job Pod: cloud-governance.yaml [cloud-governance.yaml](pod_yaml/cloud-governance.yaml)

Configmaps: cloud_governance_configmap.yaml [cloud_governance_configmap.yaml](pod_yaml/cloud_governance_configmap.yaml)

Quay.io Secret: quayio_secret.sh [quayio_secret.sh](pod_yaml/quayio_secret.sh)

AWS Secret: cloud_governance_secret.yaml [cloud_governance_secret.yaml](pod_yaml/cloud_governance_secret.yaml)

    * Need to convert secret key to base64 [run_base64.py](pod_yaml/run_base64.py)

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