import json
import boto3
import jira

ssm_client = boto3.client('ssm', region_name='us-east-1')
APPROVED = 'APPROVED'
REJECT = 'REJECT'
REFINEMENT = '61'
CLOSED = '41'
JIRA_TOKEN = 'JIRA_TOKEN'
JIRA_PROJECT = 'JIRA_PROJECT'
JIRA_API_SERVER = 'JIRA_API_SERVER'
CRO_ADMINS = ['athiruma@redhat.com', 'natashba@redhat.com', 'ebattat@redhat.com']


def get_receive_mail_details(event_data):
    """
    This method returns the received mail data
    :param event_data:
    :return:
    # """
    records = event_data.get('Records')
    mail_details = []
    if records:
        for record in records:
            if record.get('eventSource') == 'aws:ses':
                ses_data = record.get('ses')
                common_headers = ses_data.get('mail', {}).get('commonHeaders', {})
                if common_headers:
                    mail_details.append({
                        'from': ses_data.get('mail', {}).get('source'),
                        'to': common_headers.get('to'),
                        'subject': common_headers.get('subject')
                    })
    return mail_details


def lambda_handler(event, context):
    """
    This lambda function is to approve the user budget by Email Receiving
    :param event:
    :param context:
    :return:
    """
    try:
        parameters = ssm_client.get_parameters(Names=[JIRA_TOKEN, JIRA_PROJECT, JIRA_API_SERVER], WithDecryption=True)['Parameters']
        if parameters:
            output_parameters = {}
            for parameter in parameters:
                output_parameters[parameter.get('Name')] = parameter.get('Value')
            jira_auth_token = output_parameters.get(JIRA_TOKEN)
            jira_server_api = output_parameters.get(JIRA_API_SERVER)
            jira_project = output_parameters.get(JIRA_PROJECT)
            jira_conn = jira.JIRA(server=jira_server_api, token_auth=jira_auth_token)
            mail_results = get_receive_mail_details(event)
            for mail_result in mail_results:
                action, ticket = mail_result.get('subject').split(';')
                manager_mail = mail_result.get('from')
                ticket_id = f'{jira_project}-{ticket}'
                issue = jira_conn.issue(id=ticket_id)
                jira_description = jira_conn.issue(ticket_id).fields.description
                fields = {}
                for filed_value in jira_description.split('\n'):
                    if filed_value:
                        if ':' in filed_value:
                            key, value = filed_value.strip().split(':', 1)
                            fields[key.strip()] = value.strip()
                CRO_ADMINS.append(fields.get('ManagerApprovalAddress'))
                if manager_mail in CRO_ADMINS:
                    jira_description += f'\nApprovedManager: {mail_result.get("from")}\n'
                    if action.upper() == APPROVED:
                        issue.update(description=jira_description, comment=f'From: {manager_mail}\nApproved\nPlease refer to your manager, in case any issues')
                        jira_conn.transition_issue(issue=ticket_id, transition=REFINEMENT)
                        return {
                            'statusCode': 204,
                            'body': json.dumps(f'Approved the TicketId: {ticket}, by Manager: {manager_mail}')
                        }
                    else:
                        if action.upper() == REJECT:
                            jira_conn.transition_issue(issue=ticket_id, transition=CLOSED, comment=f'From: {manager_mail}\nRejected\nPlease refer to your manager, in case any issues')
                        return {
                            'statusCode': 204,
                            'body': json.dumps(f'Rejected the TicketId: {ticket}, by Manager: {manager_mail}')
                        }
                else:
                    issue.update(comment=f'From: {manager_mail}\n{manager_mail.split("@")[0]} is not authorized to perform this action')
                    return {
                        'statusCode': 500,
                        'body': json.dumps(f'{manager_mail} is not authorized to perform this action')
                    }

        else:
            return {
                'statusCode': 400,
                'body': json.dumps(f'Jira Token not found in the parameter store')
            }
    except Exception as err:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Something went wrong {err}')
        }
