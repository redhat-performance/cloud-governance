variable "S3_BUCKET_NAME" {
  type        = string
  description = "S3 BucketName to store logs"
}

variable "AWS_DEFAULT_REGION" {
  type        = string
  description = "AWS Region default to us-east-2"
  default     = "us-east-2"
}
