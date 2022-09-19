import os


class MailMessage:

    RESTRICTION = 'Please dont replay this email'

    def __init__(self):
        self.account = os.environ.get('account', '')
        self.region = os.environ.get('AWS_DEFAULT_REGION', '')

    def ec2_stop(self, days: int, image_id: str, delete_instance_days: int, instance_name: str, resource_id: str, stopped_time: str):
        subject = f'cloud-governance alert: delete ec2-stop more than {days} days'
        content = 'This instance will be deleted after 30 days.\nPlease add Policy=Not_Delete to your tags for skipping this policy. If you already added ignore this email.'
        message = ''
        if image_id != '':
            content = f'You can find a image of the deleted image under AMI: {image_id}'
            message = f'This instance will be deleted due to it was stopped more than {delete_instance_days} days.'
        body = f"""
Greetings AWS User,

Instance: {instance_name}: {resource_id} in {self.region} on AWS account: {self.account} was stopped on {stopped_time}, it stopped more than {days} days.  
{message}
{content}
{self.RESTRICTION}

Best regards,
Thirumalesh
Cloud-governance Team""".strip()
        return subject, body

    def ec2_idle(self, days: int, notification_days: int, stop_days: int, instance_name: str, resource_id: str):
        if days == notification_days:
            subject = f'cloud-governance alert:  ec2-idle is {notification_days} days'
            cause = f'This instance will be stopped if it is idle {stop_days} days'
            content = 'If you want that cloud-governance will not stop it add Policy=Not_Delete tag to your instance. '
        else:
            subject = f'cloud-governance alert: Stopped ec2-idle more than {stop_days} days'
            cause = f'This instance will be stopped.'
            content = 'In future cloud-governance will not stop it add Policy=Not_Delete tag to your instance'
        body = f"""
Greetings AWS User,

Instance: {instance_name}: {resource_id} in {self.region} on AWS account: {self.account} is idle more than {days} days.
{cause}
{content}
If you already added the Policy=Not_Delete tag ignore this mail.
{self.RESTRICTION}

Best Regards,
Thirumalesh
Cloud-governance Team""".strip()
        return subject, body

    def iam_user_add_tags(self, user: str, spreadsheet_id: str):
        subject = f'cloud-governance alert: Missing tags in AWS IAM User'
        body = f"""
Greetings AWS User,

{os.environ.get('account')} IAM User: {user} has missing tags 
Please add the tags in the spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}.
If you already filled the tags, please ignore the mail.
{self.RESTRICTION}

Best Regards
Thirumalesh
Cloud-governance Team""".strip()
        return subject, body

    def aws_user_over_usage_cost(self, user: str, usage_cost: int):
        """
        This method send subject, body to over usage cost
        @return:
        """
        subject = f'cloud-governance alert: Last 7 days cost report'
        body = f"""
Greetings AWS User,

{os.environ.get('account')} IAM User: {user} has used the amount of {usage_cost} in the last 7 days.
{self.RESTRICTION}

Best Regards
Thirumalesh
Cloud-governance Team""".strip()
        return subject, body
