import os

from jinja2 import Environment, FileSystemLoader, Template


def inject_variables():
    """
    This method injects the variables into the jinja file and create a json file
    :return:
    """
    account_id = os.environ.get('ACCOUNT_ID', 1)
    aws_region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    if account_id:
        with open('CloudSenseiLambdaPolicy.j2') as file:
            template_loader = Template(file.read())
            with open('./CloudSenseiLambdaPolicy.json', 'w') as write_file:
                write_file.write(template_loader.render({'ACCOUNT_ID': account_id, 'AWS_DEFAULT_REGION': aws_region}))
    else:
        print("AccountId is missing")
    resource_days = os.environ.get('RESOURCE_DAYS', '7')
    slack_api_token = os.environ.get('slack_api_token', '')
    slack_channel_name = os.environ.get('SLACK_CHANNEL_NAME', '')
    ses_host_address = os.environ.get('SES_HOST_ADDRESS', '')
    ses_host_port = int(os.environ.get('SES_HOST_PORT', '0'))
    ses_user_id = os.environ.get('SES_USER_ID', '')
    ses_password = os.environ.get('SES_PASSWORD', '')
    to_addresses = os.environ.get('TO_ADDRESS', '')
    cc_addresses = os.environ.get('CC_ADDRESS', '')
    send_agg_mail = os.environ.get('SEND_AGG_MAIL')
    es_server = os.environ.get('ES_SERVER')
    context = f'AWS_DEFAULT_REGION="{aws_region}"'
    if resource_days:
        context = f'RESOURCE_DAYS="{resource_days}"'
    if slack_api_token and slack_channel_name:
        context += f'\nSLACK_API_TOKEN="{slack_api_token}"\nSLACK_CHANNEL_NAME="{slack_channel_name}"'
    if ses_host_address and ses_host_port and ses_password and ses_password:
        context += f'\nSES_HOST_ADDRESS="{ses_host_address}"' \
                   f'\nSES_HOST_PORT="{ses_host_port}"' \
                   f'\nSES_USER_ID="{ses_user_id}"' \
                   f'\nSES_PASSWORD="{ses_password}"'
    if to_addresses:
        context += f'\nTO_ADDRESS="{to_addresses}"'
    if cc_addresses:
        context += f'\nCC_ADDRESS="{cc_addresses}"'
    if send_agg_mail:
        context += f'\nSEND_AGG_MAIL="{send_agg_mail}"'
    if es_server:
        context += f'\nES_SERVER="{es_server}"'
    with open('./input_vars.tfvars', 'w') as write_tf_vars:
        write_tf_vars.write(context)


inject_variables()
