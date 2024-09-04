resource "aws_instance" "main" {
  for_each      = var.instance_details
  instance_type = each.value.instance_type
  ami           = each.value.image_id
  tags          = each.value.tags
  subnet_id     = each.value.subnet_id
}
