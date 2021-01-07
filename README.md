# Cloud Governance
This tool provides an engineer with a lightweight and flexible framework for 
deploying cloud management policies and OpenShift management capabilities.

**General**

This tool support the following policies:

* ec2_idle: idle ec2
* ebs_unattached: volumes that did not connect to instance, volume in available status 
* tag_cluster_resource: Update cluster tags by input cluster name 
* zombie_cluster_resource: Delete cluster's zombies resources
* tag_ec2_resource: tag ec2 resources (instance, volume, ami, snapshot) by instance name

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
# Need to run it with root privileges
sudo podman pull quay.io/ebattat/cloud-governance
```

## Run Policy Using Podman

#### Run policy per account and region
#### Support policy: 

#### Fill the following environment variables using Podman command:

(mandatory)AWS_ACCESS_KEY_ID=awsaccesskeyid

(mandatory)AWS_SECRET_ACCESS_KEY=awssecretaccesskey

##### Policy name:
(mandatory)policy=ebs_unattached / ec2_idle / tag_cluster_resource / zombie_cluster_resource / tag_ec2_resource

##### Policy logs output
(mandatory)policy_output=s3://redhat-cloud-governance/logs

##### Cluster or instance name:
(policy:tag_cluster_resource)resource_name=ocs-test

##### Cluster or instance tags:
(policy:tag_cluster_resource)mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}"

##### Choose a specific region or all for all the regions, default : us-east-2
(optional)AWS_DEFAULT_REGION=us-east-2/all (default = us-east-2)

##### Choose dry run or not, default yes
(optional)dry_run=yes/no (default = yes)

##### Choose log level, default INFO
(optional)log_level=INFO (default = INFO)

#### Run policy examples
```sh
# policy=ebs_unattached
sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e policy=ebs_unattached -e dry_run=yes -e policy_output=s3://redhat-cloud-governance/logs -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=ec2_idle
sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e policy=ec2_idle -e dry_run=yes -e policy_output=s3://redhat-cloud-governance/logs -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=tag_cluster_resource
sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e policy=tag_cluster_resource -e dry_run=yes -e resource_name=ocs-test -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance

# policy=tag_ec2_resource (no need pass AWS_ACCESS_KEY_ID/ AWS_SECRET_ACCESS_KEY using role)
sudo podman run --rm --name cloud-governance -e AWS_DEFAULT_REGION=us-east-2 -e policy=tag_ec2_resource -e dry_run=no -e resource_name=ocp-orch-perf -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance

# policy=zombie_cluster_resource
sudo podman run --rm --name cloud-governance -e AWS_ACCESS_KEY_ID=awsaccesskeyid -e AWS_SECRET_ACCESS_KEY=awssecretaccesskey -e AWS_DEFAULT_REGION=us-east-2 -e policy=zombie_cluster_resource -e dry_run=yes -e log_level=INFO quay.io/ebattat/cloud-governance

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
sudo podman rmi quay.io/ebattat/cloud-governance
```