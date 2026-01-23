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
4. Copy the template file and create your local copy:

   cp CloudGovernanceCostExplorerReadRole.json.template CloudGovernanceCostExplorerReadRole.json
   5. Edit `CloudGovernanceCostExplorerReadRole.json` and replace:
   - `YOUR_ACCOUNT_ID` → Your AWS Account ID (e.g., `123456789012`)
   - `YOUR_USERNAME` → Your IAM username (e.g., `user1`)
6. Paste the contents of your edited `CloudGovernanceCostExplorerReadRole.json` file into the trust policy field.
7. Select the **CloudGovernanceCostExplorerReadPolicy** from the list of policies.
8. Enter the RoleName as **CloudGovernanceCostExplorerReadRole**
9. Click on create role. ( Role will be created and listed on roles )

**⚠️ Important:** The `CloudGovernanceCostExplorerReadRole.json` file is in `.gitignore` and should not be committed to version control.


## From Terraform provider

Clone our GitHub repository or copy the folder of **payer_roles**.
if you clone repo path: iam/clouds/aws/payer_roles/terrafom_create_role/
else path: payer_roles/terrafom_create_role/main.tf

Go to folder terraform_create_role and open the terminal.

Configure the aws cli credentialsine
aws configureInstall [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) if you don't have it previously

**Set variables:**

You can provide variables in two ways:

**Option 1: Using terraform.tfvars file (recommended for local use)**l
aws_account_id = "your-account-id"
iam_user       = "your-username"Then run:
terraform init
terraform apply**Option 2: Using command line variables**mmandline
terraform init
terraform apply -var="aws_account_id=your-account-id" -var="iam_user=your-username"**Note:**
- The Terraform configuration uses variables instead of hardcoded values for security.
- Never commit `terraform.tfvars` with real values (it's in `.gitignore`).
- The `main.tf` file generates the assume role policy dynamically from variables.

Then share your **AccountId** and **Role Name**  to the users for accessing the CostExplorer.

To delete the IAM policy through terraform.
```commandline
terraform delete
```
