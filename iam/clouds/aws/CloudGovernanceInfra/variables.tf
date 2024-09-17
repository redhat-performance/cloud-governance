variable "IAM_USERNAME" {
  type        = string
  description = "IAM User to run the CloudGovernance"
  default     = null
  validation {
    condition     = var.IAM_USERNAME != "" || var.IAM_USERNAME != null
    error_message = "Provide the IAM_USERNAME"
  }
}

variable "IAM_POLICY_NAME" {
  type        = string
  description = "IAM Policy to se the permissions for CloudGovernance user"
  default     = "CloudGovernanceReadPolicy"
  validation {
    condition     = var.IAM_POLICY_NAME == "CloudGovernanceReadPolicy" || var.IAM_POLICY_NAME == "CloudGovernanceDeletePolicy"
    error_message = "Mismatched policy name, Supported Values: CloudGovernanceReadPolicy, CloudGovernanceDeletePolicy"
  }
}

variable "AWS_DEFAULT_REGION" {
  type        = string
  description = "AWS Region default to us-east-2"
  default     = "us-east-2"
}

variable "S3_BUCKET_NAME" {
  type        = string
  description = "S3 BucketName to store logs"
  default     = null
}
