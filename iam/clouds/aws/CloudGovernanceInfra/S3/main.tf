provider "aws" {
  region = var.AWS_DEFAULT_REGION
}

resource "aws_s3_bucket" "cloud-governance-bucket" {
  bucket = var.S3_BUCKET_NAME
}
