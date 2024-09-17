# How to run cloud-governance on Tenant Accounts

Steps

1. Create IAM User with Read/Delete Permissions and create S3 bucket.
    1. Follow the instructions [README.md](..%2F..%2F..%2Fiam%2Fclouds%2Faws%2FCloudGovernanceInfra%2FREADME.md).
2. Add kind secret-text to jenkins with below naming conventions
    1. ${account_name}-aws-access-key-id
    2. ${account_name}-aws-secret-key-id
    3. ${account_name}-s3-bucket
3. Create folder named that you want to run the cloud-governance policies and copy the file in templates.
4. Add account_name to account variable in this [PolicyJenkinsfileDaily](../aws/template/PolicyJenkinsfileDaily)
   and [TaggingJenkinsfileHourly](../aws/template/TaggingJenkinsfileHourly).
5. Create two Jenkins jobs by using this two Jenkinsfile
