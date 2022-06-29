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

# This command deletes the Zombie Resources by dry_run=no else list out resources
# policy=zombie_cluster_resource
sudo podman run --rm --name cloud-governance -e policy=zombie_cluster_resource -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e resource=zombie_cluster_elastic_ip -e cluster_tag=kubernetes.io/cluster/test-pd9qq -e log_level=INFO quay.io/ebattat/cloud-governance

# policy=cost_explorer
sudo podman run --rm --name cloud-governance -e policy=cost_explorer -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e es_host=elasticsearch_host -e es_port=elasticsearch_port -e es_index=elasticsearch_index -e cost_metric=UnblendedCost -e start_date=start_date -e end_date=end_date -e granularity=DAILY -e cost_explorer_tags="['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']" -e log_level=INFO quay.io/ebattat/cloud-governance:latest
sudo podman run --rm --name cloud-governance -e policy=cost_explorer -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e es_index=elasticsearch_index -e cost_metric=UnblendedCost -e start_date=start_date -e end_date=end_date -e granularity=DAILY -e cost_explorer_tags="['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']" -e file_name=cost_explorer.txt -v /home/cost_explorer.txt:/tmp/cost_explorer.txt -e log_level=INFO quay.io/ebattat/cloud-governance:latest

# policy=validate_iam_user_tags
sudo podman run --rm --name cloud-governance  -e policy=validate_iam_user_tags -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e validate_type=spaces/tags -e user_tags="['Budget', 'User', 'Owner', 'Manager', 'Environment', 'Project']"   -e log_level=INFO quay.io/ebattat/cloud-governance:latest


# policy=gitleaks
sudo podman run --rm --name cloud-governance -e policy=gitleaks -e git_access_token=$git_access_token -e git_repo=https://github.com/redhat-performance/cloud-governance -e several_repos=no -e log_level=INFO quay.io/ebattat/cloud-governance

# custom cloud custodian policy (path for custom policy: -v /home/user/custodian_policy:/custodian_policy)
sudo podman run --rm --name cloud-governance -e policy=/custodian_policy/policy.yml -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=us-east-2 -e dry_run=yes -e policy_output=s3://bucket/logs -e log_level=INFO -v /home/user/custodian_policy:/custodian_policy --privileged quay.io/ebattat/cloud-governance

```
