output "instance_id" {
  value = values(aws_instance.main)[0].id
}
