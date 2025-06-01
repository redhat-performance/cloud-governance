This tool support the following policies:
[policy](cloud_governance/policy)

[AWS Polices](cloud_governance/policy/aws)

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
* [unused_access_key](cloud_governance/policy/aws/unused_access_key.py): Identify user with unused active access key, causing the security issue
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
* [tag_resources](./cloud_governance/policy/ibm/tag_resources.py): Tag IBM resources
  list of supported IBM Resources

- resource_instances
- virtual_servers
- schematics_workspaces
- classic_baremetals
- classic_virtual_machines

Environment Variables required:

| KeyName                    | Value  | Description                                                                |
|----------------------------|--------|----------------------------------------------------------------------------|
| IBM_CUSTOM_TAGS_LIST       | string | pass string with separated with comma. i.e: "cost-center: test, env: test" |
| RESOURCE_TO_TAG (optional) | string | pass the resource name to tag. ex: virtual_servers                         |
| IBM_CLOUD_API_KEY          | string | IBM Cloud API Key                                                          |
| IBM_API_KEY                | string | IBM Classic infrastructure key ( SoftLayer )                               |
| IBM_API_USERNAME           | string | IBM API Username ( SoftLayer )                                             |
| IBM_ACCOUNT_ID             | string | IBM Account Id                                                             |

  ```shell
  # Run tag_resources policy in IBM Cloud
  podman run --rm --name cloud-governance \
  -e PUBLIC_CLOUD_NAME="IBM" \
  -e policy="tag_resources" \
  -e account="${ACCOUNT_NAME}" \
  -e IBM_CLOUD_API_KEY="${IBM_CLOUD_API_KEY}" \
  -e IBM_CUSTOM_TAGS_LIST="cost-center:675, env:test" \
  -e IBM_ACCOUNT_ID="${IBM_ACCOUNT_ID}" \
  -e IBM_API_USERNAME="${IBM_API_USERNAME}" \
  -e IBM_API_KEY="${IBM_API_KEY}" \
  quay.io/cloud-governance/cloud-governance:latest
  ```
