## Create CloudGovernance Infra in the cloud

#### Requirements

- IAM User: to access cloud resources.
- IAM Policy: Least privilege principle
- S3-Bucket: To store the logs of cloud-governance policy runs.

### Pre-requisites

- Install [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).
- Install AWS CLI and configure IAM Access credentials. (aws configure)

Steps to create Cloud Governance Infra resources:

* Deploy S3 bucket (once for logs)
* Deploy IAM read role (dry_run==yes) IAM_POLICY_NAME=CloudGovernanceReadPolicy
* Deploy IAM delete role (dry_run==no => actions) IAM_POLICY_NAME=CloudGovernanceDeletePolicy

- Download tar `CloudGovernanceInfra.tar` and untar the file.

```shell
curl -L https://github.com/redhat-performance/cloud-governance/raw/main/iam/clouds/aws/CloudGovernanceInfra/CloudGovernanceInfra.tar | tar -xzvf -
```

- Create CloudGovernance Infra: S3_BUCKET. ( Only once)

```shell
export ACCOUNT_NAME="<ACCOUNT_ID>"
export S3_BUCKET_NAME="${ACCOUNT_NAME}-<BUCKET_NAME>"
terraform init
terraform apply -var=S3_BUCKET_NAME="$S3_BUCKET_NAME" -target=module.CreateBucket -auto-approve
```

- Create CloudGovernance Infra: User, Policy

```shell
export IAM_USERNAME="cloud-governance-user"
export IAM_POLICY_NAME="CloudGovernanceReadPolicy"
terraform init
terraform apply -var=IAM_USERNAME="$IAM_USERNAME" -var=IAM_POLICY_NAME="$IAM_POLICY_NAME" -target=module.CreateIAMInfra -auto-approve
```

- To provide ACCESS_KEY_ID and SECRET_KEY_ID run below command

```shell
  terraform output SECRET_KEY_ID
  terraform output ACCESS_KEY_ID

```

- Destroy CloudGovernanceInfra

```shell
terraform destroy -var=S3_BUCKET_NAME="$S3_BUCKET_NAME" -target=module.CreateBucket -auto-approve
terraform destroy -var=IAM_USERNAME="$IAM_USERNAME" -var=IAM_POLICY_NAME="$IAM_POLICY_NAME" -target=module.CreateIAMInfra -auto-approve
```
