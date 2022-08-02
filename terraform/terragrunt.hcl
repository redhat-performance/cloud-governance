locals {
    region_name = get_env("REGION_NAME", "us-east-1")
    role_name = get_env("ROLE_NAME", "")
    account_id = get_env("ACCOUNT_ID", "")
}

terraform {
    before_hook "generate_tfvars"{
      commands = ["apply", "plan"]
      execute = ["python3", "tfvars_generator.py"]
    }
    extra_arguments "attach_var_file_to_inputs" {
        commands = [ "apply", "plan", "destroy" ]
        arguments = [
            "-var-file=./input_vars.tfvars"
        ]
    }
}

generate "provider" {
  path = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents = <<EOF
  provider "aws" {
    region = "${local.region_name}"
    assume_role {
      role_arn = "arn:aws:iam::${local.account_id}:role/${local.role_name}"
    }
  }
  EOF
}
