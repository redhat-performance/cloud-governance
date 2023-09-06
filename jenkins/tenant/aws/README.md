# How to run cloud-governance on Tenant Accounts

Steps
1. Create AWS User and attach user by [CloudGovernanceDeletePolicy.json](../../../iam/clouds/aws/CloudGovernanceDeletePolicy.json). [ Note: Replace account_id with actual account id]
2. Create S3 bucket
3. Add kind secret-text to jenkins with below naming conventions
   1. ${account_name}-aws-access-key-id
   2. ${account_name}-aws-secret-key-id
   3. ${account_name}-s3-bucket
4. Create folder named that you want to run the cloud-governance policies and copy the file in templates.
5. Add account_name to account variable in this [PolicyJenkinsfileDaily](../aws/template/PolicyJenkinsfileDaily) and [TaggingJenkinsfileHourly](../aws/template/TaggingJenkinsfileHourly).
6. Create two Jenkins jobs by using this two Jenkinsfile
