variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "iam_user" {
  description = "IAM username allowed to assume the role"
  type        = string
}

provider "aws" {

}

output "role_arn" {
  value = aws_iam_role.cloud_governance_ce_read_role.arn
}

output "role_name" {
  value = aws_iam_role.cloud_governance_ce_read_role.name
}

resource "aws_iam_role" "cloud_governance_ce_read_role" {
  name = "CloudGovernanceCostExplorerReadRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${var.aws_account_id}:user/${var.iam_user}"
      }
      Action = "sts:AssumeRole"
    }]
  })

  inline_policy {
    name = "CloudGovernanceCostExplorerReadPolicy"
    policy = file("./../CloudGovernanceCostExplorerReadPolicy.json")
  }
}
