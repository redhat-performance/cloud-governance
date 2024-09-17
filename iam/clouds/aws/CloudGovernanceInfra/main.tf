module "CreateIAMInfra" {
  source          = "./IAM"
  IAM_POLICY_PATH = "${path.cwd}/${var.IAM_POLICY_NAME}.json"
  IAM_USERNAME    = var.IAM_USERNAME
  IAM_POLICY_NAME = var.IAM_POLICY_NAME
}

module "CreateBucket" {
  source         = "./S3"
  S3_BUCKET_NAME = var.S3_BUCKET_NAME
}
