output "ACCESS_KEY_ID" {
  value = aws_iam_access_key.cloud-governance-access-key.id
}

output "SECRET_KEY_ID" {
  value     = aws_iam_access_key.cloud-governance-access-key.secret
  sensitive = true
}
