resource "aws_scheduler_schedule_group" "cloud_sensei_group" {
  name = "CloudSenseiGroup"
  tags = {
    User = "cloudsensei"
  }
}


resource "aws_scheduler_schedule" "cloud_sensi_event_bridge_scheduler" {
  name       = "CloudSenseiScheduler"
  group_name = aws_scheduler_schedule_group.cloud_sensei_group.name

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(30 16 * * ? *)"
  schedule_expression_timezone = "Asia/Kolkata"
  target {
    arn      = module.lambda_function_existing_package_local.lambda_function_arn
    role_arn = aws_iam_role.event_bridge_role.arn
  }

}

resource "aws_iam_role" "event_bridge_role" {

  assume_role_policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = "sts:AssumeRole"
          Effect = "Allow"
          Sid    = ""
          Principal = {
            Service = "scheduler.amazonaws.com"
          },
        },
      ]
    })
    inline_policy {
    name = "CloudSenseiEventBridgeExecutionPolicy"

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action   = ["lambda:InvokeFunction"]
          Effect   = "Allow"
          Resource = [module.lambda_function_existing_package_local.lambda_function_arn,
          "${module.lambda_function_existing_package_local.lambda_function_arn}/*"]
        },
      ]
    })
  }

    tags = {
      User = "cloudsensei"
    }
  name = "CloudSenseiEvenBrideRole"
}
