## Run AWS Policy Using Podman 
```sh
# policy=instance_idle
sudo podman run --rm --name cloud-governance -e policy="instance_idle" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/ebattat/cloud-governance"

# policy=ec2_run
sudo podman run --rm --name cloud-governance -e policy="ec2_run" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/ebattat/cloud-governance"

# select policy ['ec2_stop', 's3_inactive', 'empty_roles', 'ip_unattached', 'nat_gateway_unused', 'zombie_snapshots']
sudo podman run --rm --name cloud-governance -e policy="policy" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes"  -e log_level="INFO" "quay.io/ebattat/cloud-governance"

# policy=ebs_unattached
sudo podman run --rm --name cloud-governance -e policy="ebs_unattached" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/ebattat/cloud-governance"

# policy=ebs_in_use
sudo podman run --rm --name cloud-governance -e policy="ebs_in_use" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" "quay.io/ebattat/cloud-governance"

# policy=zombie_cluster_resource
sudo podman run --rm --name cloud-governance -e policy="zombie_cluster_resource" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e resource="zombie_cluster_elastic_ip" -e cluster_tag="kubernetes.io/cluster/test-pd9qq" -e log_level="INFO" "quay.io/ebattat/cloud-governance"

# policy=tag_resources
sudo podman run --rm --name cloud-governance -e policy="tag_resources" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e tag_operation="read/update/delete" -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/ebattat/cloud-governance"

# policy=tag_non_cluster
sudo podman run --rm --name cloud-governance -e policy="tag_non_cluster" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e tag_operation="read/update/delete" -e mandatory_tags="{'Owner': 'Name','Email': 'name@redhat.com','Purpose': 'test'}" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/ebattat/cloud-governance"

# policy=tag_iam_user
sudo podman run --rm --name cloud-governance -e policy="tag_iam_user" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e user_tag_operation="read/update/delete" -e remove_tags="['Environment', 'Test']" -e username="test_username" -e file_name="tag_user.csv"  -e log_level="INFO" -v "/home/user/tag_user.csv":"/tmp/tag_user.csv" --privileged "quay.io/ebattat/cloud-governance"

# policy=cost_explorer
sudo podman run --rm --name cloud-governance -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e es_host="$elasticsearch_host" -e es_port="$elasticsearch_port" -e es_index="$elasticsearch_index" -e cost_metric=UnblendedCost -e start_date="$start_date" -e end_date="$end_date" -e granularity="DAILY" -e cost_explorer_tags="['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']" -e log_level="INFO" "quay.io/ebattat/cloud-governance:latest"
sudo podman run --rm --name cloud-governance -e policy="cost_explorer" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e es_index="elasticsearch_index" -e cost_metric="UnblendedCost" -e start_date="$start_date" -e end_date="$end_date" -e granularity="DAILY" -e cost_explorer_tags="['User', 'Budget', 'Project', 'Manager', 'Owner', 'LaunchTime', 'Name', 'Email']" -e file_name="cost_explorer.txt" -v "/home/cost_explorer.txt":"/tmp/cost_explorer.txt" -e log_level="INFO" "quay.io/ebattat/cloud-governance:latest"

# policy=validate_iam_user_tags
sudo podman run --rm --name cloud-governance  -e policy="validate_iam_user_tags" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e validate_type="spaces/tags" -e user_tags="['Budget', 'User', 'Owner', 'Manager', 'Environment', 'Project']"   -e log_level="INFO" "quay.io/ebattat/cloud-governance:latest"

# policy=gitleaks
sudo podman run --rm --name cloud-governance -e policy="gitleaks" -e git_access_token="$git_access_token" -e git_repo="https://github.com/redhat-performance/cloud-governance" -e several_repos="no" -e log_level="INFO" "quay.io/ebattat/cloud-governance"

# custom cloud custodian policy (path for custom policy: -v /home/user/custodian_policy:/custodian_policy)
sudo podman run --rm --name cloud-governance -e policy="/custodian_policy/policy.yml" -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_DEFAULT_REGION="us-east-2" -e dry_run="yes" -e policy_output="s3://bucket/logs" -e log_level="INFO" -v "/home/user/custodian_policy":"/custodian_policy" --privileged "quay.io/ebattat/cloud-governance"

```

## Run IBM Policy Using Podman

```sh
# policy=tag_baremetal
podman run --rm --name cloud-governance -e policy="tag_baremetal" -e account="$account" -e IBM_API_USERNAME="$IBM_API_USERNAME" -e IBM_API_KEY="$IBM_API_KEY" -e SPREADSHEET_ID="$SPREADSHEET_ID" -e GOOGLE_APPLICATION_CREDENTIALS="$GOOGLE_APPLICATION_CREDENTIALS" -v $GOOGLE_APPLICATION_CREDENTIALS:$GOOGLE_APPLICATION_CREDENTIALS -e LDAP_USER_HOST="$LDAP_USER_HOST" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/ebattat/cloud-governance:latest"

# tag=tab_vm
podman run --rm --name cloud-governance -e policy="tag_vm" -e account="$account" -e IBM_API_USERNAME="$IBM_API_USERNAME" -e IBM_API_KEY="$IBM_API_KEY" -e SPREADSHEET_ID="$SPREADSHEET_ID" -e GOOGLE_APPLICATION_CREDENTIALS="$GOOGLE_APPLICATION_CREDENTIALS" -v $GOOGLE_APPLICATION_CREDENTIALS:$GOOGLE_APPLICATION_CREDENTIALS -e LDAP_USER_HOST="$LDAP_USER_HOST" -e tag_operation="update" -e log_level="INFO" -v "/etc/localtime":"/etc/localtime" "quay.io/ebattat/cloud-governance:latest"

```