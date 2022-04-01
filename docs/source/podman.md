# Run Policy Using Podman 
```sh
# policy=ec2_idle
sudo podman run --rm --name cloud-governance -e policy=ec2_idle -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e policy_output=s3://bucket/logs -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=ec2_run
sudo podman run --rm --name cloud-governance -e policy=ec2_run -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e policy_output=s3://bucket/logs -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=ebs_unattached
sudo podman run --rm --name cloud-governance -e policy=ebs_unattached -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e policy_output=s3://bucket/logs -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=ebs_in_use
sudo podman run --rm --name cloud-governance -e policy=ebs_in_use -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e policy_output=s3://bucket/logs -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=zombie_cluster_resource
sudo podman run --rm --name cloud-governance -e policy=zombie_cluster_resource -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e resource=zombie_cluster_elastic_ip -e cluster_tag=kubernetes.io/cluster/test-pd9qq -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=tag_cluster_resource
sudo podman run --rm --name cloud-governance -e policy=tag_cluster_resource -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e resource_name=ocs-test -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance

# policy=tag_ec2 (no need pass AWS_ACCESS_KEY_ID/ AWS_SECRET_ACCESS_KEY using role)
sudo podman run --rm --name cloud-governance -e policy=tag_ec2 -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=no -e resource_name=ocp-orch-perf -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level=INFO -v /etc/localtime:/etc/localtime quay.io/ebattat/cloud-governance

# policy=gitleaks
sudo podman run --rm --name cloud-governance -e policy=gitleaks -e git_access_token=$git_access_token -e git_repo=https://github.com/redhat-performance/cloud-governance -e several_repos=no -e log_level=INFO quay.io/ebattat/cloud-governance

# custom cloud custodian policy (path for custom policy: -v /home/user/custodian_policy:/custodian_policy)
sudo podman run --rm --name cloud-governance -e policy=/custodian_policy/policy.yml -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e policy_output=s3://bucket/logs -e log_level=INFO -v /home/user/custodian_policy:/custodian_policy --privileged quay.io/ebattat/cloud-governance

```
