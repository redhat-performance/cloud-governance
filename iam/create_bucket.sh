# Need to create once dedicate bucket - replace <bucket-name>
# create bucket
aws s3api create-bucket --bucket <bucket-name> --region us-east-2 --create-bucket-configuration LocationConstraint=us-east-2
# create folder logs
aws s3api put-object --bucket <bucket-name> --key logs
# ls bucket
aws s3 ls s3://<bucket-name>