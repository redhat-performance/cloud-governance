provider "aws" {
  region = var.AWS_DEFAULT_REGION
}

data "aws_caller_identity" "current" {}


resource "local_file" "updated_policy" {
  content  = replace(file(var.IAM_POLICY_PATH), "account_id", data.aws_caller_identity.current.account_id)
  filename = "${path.module}/updated_policy.json"
}

resource "aws_iam_user" "cloud-governance-user" {
  name = var.IAM_USERNAME
}

resource "aws_iam_policy" "cloud-governance-user-policy" {
  name   = var.IAM_POLICY_NAME
  path   = "/"
  policy = local_file.updated_policy.content
}

resource "aws_iam_user_policy_attachment" "user_policy_attach" {
  user       = aws_iam_user.cloud-governance-user.name
  policy_arn = aws_iam_policy.cloud-governance-user-policy.arn
}

resource "aws_iam_access_key" "cloud-governance-access-key" {
  user = aws_iam_user.cloud-governance-user.name
}
