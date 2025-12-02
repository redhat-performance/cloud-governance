module "lambda_function_existing_package_local" {
  source = "terraform-aws-modules/lambda/aws"
  lambda_role = aws_iam_role.cloud_sensei_iam_role.arn
  function_name = "CloudSensei"
  description   = "Daily reporting on Cloud Usage"
  memory_size = 256
  package_type = "Zip"
  tags = {
    User = "cloudsensei"
  }
  timeout = 300
  environment_variables = {
    SLACK_API_TOKEN = var.SLACK_API_TOKEN
    SLACK_CHANNEL_NAME = var.SLACK_CHANNEL_NAME
    RESOURCE_DAYS = var.RESOURCE_DAYS
    SES_HOST_ADDRESS = var.SES_HOST_ADDRESS
    SES_HOST_PORT = var.SES_HOST_PORT
    SES_USER_ID = var.SES_USER_ID
    SES_PASSWORD = var.SES_PASSWORD
    TO_ADDRESS = var.TO_ADDRESS
    CC_ADDRESS = var.CC_ADDRESS
    ES_SERVER = var.ES_SERVER
    SEND_AGG_MAIL = var.SEND_AGG_MAIL
  }
  runtime = "python3.14"
  local_existing_package = "./../CloudSensei.zip"
  handler = "lambda_function.lambda_handler"
  create_package = false
  create_role = false
}

# Create Lambda Role Execution policy, with specified resource permissions
resource "aws_iam_role" "cloud_sensei_iam_role" {

  name = "CloudSenseiLambdaRole"

  assume_role_policy = file("./CloudSenseiLambdaRole.json")
  inline_policy {
    name = "CloudSenseiLambdaPolicy"
    policy = file("./CloudSenseiLambdaPolicy.json")
  }
  tags = {
    User = "cloudsensei"
  }

}
