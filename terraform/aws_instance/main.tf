
resource "random_id" "uuid" {
  byte_length = 8
}

resource "aws_iam_user" "user"{
  name = "CloudGovernanceTest${random_id.uuid.hex}"

  tags = {
    "kubernetes.io/cluster/CloudGovernanceTest${random_id.uuid.hex}" = "owned"
    Purpose = "integration-test"
  }
}


resource "aws_instance" "main" {
  for_each = var.instance_details
  instance_type = each.value.instance_type
  ami = each.value.image_id
  tags = each.value.tags
}
