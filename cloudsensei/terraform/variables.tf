variable "SLACK_API_TOKEN" {
  type = string
  description = "Slack OAuth Token"
  default = null
}

variable "SLACK_CHANNEL_NAME" {
  type = string
  description = "Slack Channel id/name"
  default = null
}

variable "AWS_DEFAULT_REGION" {
  default = "us-east-1"
}

variable "ACCOUNT_ID" {
  default = null
}

variable "RESOURCE_DAYS" {
  type = number
  default = 7
}

variable "SES_HOST_ADDRESS" {
  type = string
  default = null
}

variable "SES_HOST_PORT" {
  type = number
  default = null
}
variable "SES_USER_ID" {
  type = string
  default = null
}
variable "SES_PASSWORD" {
  type = string
  default = null
}

variable "TO_ADDRESS" {
  type = string
  default = null
}
variable "CC_ADDRESS" {
  type = string
  default = null
}

variable "SEND_AGG_MAIL" {
  type = string
  default = "no"
}

variable "ES_SERVER" {
  type = string
  default = null
}
