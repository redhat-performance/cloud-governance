
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

  assume_role_policy = file("./../CloudGovernanceCostExplorerReadRole.json")
  inline_policy {
    name = "CloudGovernanceCostExplorerReadPolicy"
    policy = file("./../CloudGovernanceCostExplorerReadPolicy.json")
  }

}
