output "instance_id" {
  value = values(aws_instance.main)[0].id
}

output "user_name" {
  value = aws_iam_user.user.name
}
