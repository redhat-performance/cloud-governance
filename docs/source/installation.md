# Installation

#### Download cloud-governance image from quay.io
```sh
# Need to run it with root privileges
sudo podman pull quay.io/ebattat/cloud-governance
```

#### Environment variables description:

(mandatory)AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID

(mandatory)AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY

##### Policy name:
(mandatory)policy=instance_idle / ec2_run / ebs_unattached / ebs_in_use / tag_cluster_resource / zombie_cluster_resource / tag_ec2_resource

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
