# Cloud Governance

## What is it?

**Cloud Governance** tool provides a lightweight and flexible framework for deploying cloud management policies focusing on cost optimize and security.

This tool support the following policies:
[policy](../../cloud_governance/policy)

[AWS Polices](../../cloud_governance/policy/aws)

* Real time Openshift Cluster cost, User cost
* [instance_idle](../../cloud_governance/policy/aws/cleanup/instance_idle.py): idle ec2 in last 4 days, cpu < 2% & network < 5mb.
* [ec2_run](../../cloud_governance/policy/aws/cleanup/instance_run.py): running ec2.
* [ebs_unattached](../../cloud_governance/policy/aws/ebs_unattached.py): volumes that did not connect to instance, volume in available status.
* [ebs_in_use](../../cloud_governance/policy/aws/ebs_in_use.py): in use volumes.
* [tag_resources](../../cloud_governance/policy/policy_operations/aws/tag_cluster): Update cluster and non cluster resource tags fetching from the user tags or from the mandatory tags
* [zombie_cluster_resource](../../cloud_governance/policy/aws/zombie_cluster_resource.py): Delete cluster's zombie resources
* [tag_non_cluster](../../cloud_governance/policy/policy_operations/aws/tag_non_cluster): tag ec2 resources (instance, volume, ami, snapshot) by instance name
* [tag_iam_user](../../cloud_governance/policy/policy_operations/aws/tag_user): update the user tags from the csv file
* [cost_explorer](../../cloud_governance/policy/aws/cost_explorer.py): Get data from cost explorer and upload to ElasticSearch
* [ip_unattached](../../cloud_governance/policy/aws/ip_unattached.py): Get the unattached IP and delete it after 7 days.
* [s3_inactive](../../cloud_governance/policy/aws/s3_inactive.py): Get the inactive/empty buckets and delete them after 7 days.
* [empty_roles](../../cloud_governance/policy/aws/empty_roles.py): Get empty roles and delete it after 7 days.
* [zombie_snapshots](../../cloud_governance/policy/aws/zombie_snapshots.py): Get the zombie snapshots and delete it after 7 days.
* [nat_gateway_unused](../../cloud_governance/policy/aws/cleanup/unused_nat_gateway.py): Get the unused nat gateways and deletes it after 7 days.
* gitleaks: scan Github repository git leak (security scan)  
* [cost_over_usage](../../cloud_governance/policy/aws/cost_over_usage.py): send mail to aws user if over usage cost

[IBM policies](../../cloud_governance/policy/ibm)

* [tag_baremetal](../../cloud_governance/policy/ibm/tag_baremetal.py): Tag IBM baremetal machines
* [tag_vm](../../cloud_governance/policy/ibm/tag_vm.py): Tga IBM Virtual Machines machines

** You can write your own policy using [Cloud-Custodian](https://cloudcustodian.io/docs/quickstart/index.html)
   and run it (see 'custom cloud custodian policy' in [Policy workflows](#policy-workloads)).


![](../../images/cloud_governance1.png)
![](../../images/demo.gif)

![](../../images/cloud_governance2.png)

Reference:
* The cloud-governance package is placed in [PyPi](https://pypi.org/project/cloud-governance/)
* The cloud-governance container image is placed in [Quay.io](https://quay.io/repository/ebattat/cloud-governance)
![](../../images/cloud_governance3.png)


<!-- Table of contents -->
```{toctree}
installation
configuration
podman
tagging
pod
pytest
postinstallation
```



