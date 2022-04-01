# Cloud Governance

[![Actions Status](https://github.com/redhat-performance/cloud-governance/workflows/Build/badge.svg)](https://github.com/redhat-performance/cloud-governance/actions)
[![Coverage Status](https://coveralls.io/repos/github/redhat-performance/cloud-governance/badge.svg?branch=main)](https://coveralls.io/github/redhat-performance/cloud-governance?branch=main)



![](../../images/cloud_governance1.png)
![](../../images/demo.gif)
This tool provides a lightweight and flexible framework for deploying cloud management policies focusing on 
cost optimize and security.

This tool support the following policies:
[policy](cloud_governance/policy)

* Real time Openshift Cluster cost, User cost
* ec2_idle: idle ec2 in last 2 days, cpu < 5% & network < 10mb [ec2_idle](cloud_governance/policy/ec2_idle.yml)
* ec2_run: running ec2 [ec2_run](cloud_governance/policy/ec2_run.yml)
* ebs_unattached: volumes that did not connect to instance, volume in available status [ebs_unattached](cloud_governance/policy/ebs_unattached.yml)
* ebs_in_use: in use volumes [ebs_in_use](cloud_governance/policy/ebs_in_use.yml)
* tag_cluster_resource: Update cluster tags by input cluster name 
* zombie_cluster_resource: Delete cluster's zombie resources
* tag_ec2_resource: tag ec2 resources (instance, volume, ami, snapshot) by instance name
* gitleaks: scan Github repository git leak (security scan)  

** You can write your own policy using [Cloud-Custodian](https://cloudcustodian.io/docs/quickstart/index.html)
   and run it (see 'custom cloud custodian policy' in [Policy workflows](#policy-workloads)).

First release: Support AWS only
 
![](../../images/cloud_governance2.png)

Reference:
* The cloud-governance package is placed in [PyPi](https://pypi.org/project/cloud-governance/)
* The cloud-governance container image is placed in [Quay.io](https://quay.io/repository/ebattat/cloud-governance)
* The cloud-governance readthedocs link is [ReadTheDocs](https://cloud-governance.readthedocs.io/en/latest/)
![](../../images/cloud_governance3.png)


<!-- Table of contents -->
```{toctree}
installation
configuration
podman
pod
pytest
postinstallation
```



