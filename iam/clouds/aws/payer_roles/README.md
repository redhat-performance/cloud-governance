## Create IAM Assume Role

# From AWS Console

### Go to **IAM** Service

#### Create a IAM Policy

1. Click on **Policies**
2. Click on **Create Policy**
3. Switch to JSON tab and paste the contents of CloudGovernanceCostExplorerReadPolicy.
4. Click on Next: Tags
5. Click on Next: Review
6. Enter the Policy name as CloudGovernanceCostExplorerReadPolicy
7. Click on **Create Policy**. ( Policy will be created and listed on Policies )

#### Create the IAM Role

1. Click on **Roles**
2. Click on **Create Role**
3. Select the **Custom trust policy** from Trusted identity type.
4. Paste the contents of *CloudGovernanceCostExplorerReadRole.json* file. \
&nbsp;&nbsp;Note: Replace username with **IAM User** name, and AccountId with the **AWS AccountId**
5. Select the **CloudGovernanceCostExplorerReadPolicy** from the list of policies.
6. Enter the RoleName as **CloudGovernanceCostExplorerReadRole**
7. Click on create role. ( Role will be created and listed on roles )


## From Terraform provider

Clone our GitHub repository or copy the folder of **payer_roles**.
if you clone repo path: iam/clouds/aws/payer_roles/terrafom_create_role/
else path: payer_roles/terrafom_create_role/main.tf

Go to folder terraform_create_role and open the terminal.

Configure the aws cli credentials
```commandline
aws configure
```

Install [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) if you don't have it previously

Run the following commands to create the IAM Role and attach policy to it.
```commandline
terraform init
terraform apply
```

Note: Replace username with **IAM User** name, and AccountId with the **AWS AccountId** on the CloudGovernanceCostExplorerReadRole

Then share your **AccountId** and **Role Name**  to the users for accessing the CostExplorer.

To delete the IAM policy through terraform.
```commandline
terraform delete
```