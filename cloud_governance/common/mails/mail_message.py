import os


class MailMessage:
    RESTRICTION = 'Do not reply this email. If you need more clarification, please reach out to us in the coreos slack channel -  #perf-dept-public-clouds.'

    def __init__(self):
        self.account = os.environ.get('account', '')
        self.policy = os.environ.get('policy', '')
        self.region = os.environ.get('AWS_DEFAULT_REGION', '')

    def ec2_stop(self, name: str, days: int, image_id: str, delete_instance_days: int, instance_name: str,
                 resource_id: str, stopped_time: str, ec2_type: str, **kwargs):
        subject = f'cloud-governance alert: ec2-stop'
        content = 'If you do not want it to be deleted, please add "Policy=Not_Delete" or "Policy=skip" tag to this instance.'
        message = f'This instance will be deleted in the {delete_instance_days-days} days if no further action is taken.'
        if kwargs.get('msgadmins'):
            message = f'This instance will be deleted in the {delete_instance_days - days} days if no further action is taken.'
        elif image_id != '':
            content = f'You can find a image of the deleted instance under AMI: {image_id}'
            message = f'This instance will be deleted due to it was in stopped state more than {delete_instance_days} days.'
        body = f"""
Hi {name},

Instance: {instance_name}: {resource_id}( InstanceType:{ec2_type} ) in {self.region} region in account: {self.account} was stopped on {stopped_time}, it stopped state more than {days} days.  
{message}
{content}

{self.RESTRICTION}

Best regards,
Cloud-governance Team""".strip()
        return subject, body

    def ec2_idle(self, name: str, days: int, notification_days: int, stop_days: int, instance_name: str,
                 resource_id: str, ec2_type: str):
        subject = f'cloud-governance alert:  ec2-idle'
        if days == notification_days:
            cause = f'This instance will be stopped in {stop_days-days} days if no further action is taken'
            content = 'If you do not want it to be deleted, please "Policy=Not_Delete" or "Policy=ski"p tag to this instance.'
        else:
            cause = f'This instance will be stopped.'
            content = 'In future cloud-governance will not stop it add "Policy=Not_Delete" or "Policy=skip" tag to your instance'
        body = f"""
Hi {name},

Instance: {instance_name}: {resource_id} ( InstanceType:{ec2_type} ) in {self.region} on account: {self.account} is idle more than {days} days.
{cause}
{content}
If you already added the tag, please ignore this mail.

{self.RESTRICTION}

Best Regards,
Cloud-governance Team""".strip()
        return subject, body

    def iam_user_add_tags(self, name: str, user: str, spreadsheet_id: str):
        subject = f'cloud-governance alert: Missing tags in AWS IAM User'
        body = f"""
Hi {name},

{os.environ.get('account')} IAM User: {user} has missing tags 
Please add the tags in the spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}.
If you already filled the tags, please ignore the mail.

{self.RESTRICTION}

Best Regards
Cloud-governance Team""".strip()
        return subject, body

    def aws_user_over_usage_cost(self, user: str, usage_cost: int, name: str, user_usage: int):
        """
        This method send subject, body to over usage cost
        @return:
        """
        subject = f'cloud-governance alert: last week cost over usage {usage_cost}$ per user'
        body = f"""
Hi {name},
Your AWS user:{user} in account:{os.environ.get('account')} cost was {user_usage}$ in the last week. 
Please verify that you are using all the resources.
Please verify that you are using all the resources in attached {user}_resource.json file.

{self.RESTRICTION}

Best Regards,
Cloud-governance Team""".strip()
        return subject, body

    def resource_message(self, name: str, days: int, notification_days: int, delete_days: int, resource_name: str, resource_id: str, resource_type: str, resources: list = [], **kwargs):
        """
        This method prepare mail message based on resource_type and return subject, body
        @param resources:
        @param name:
        @param days:
        @param notification_days:
        @param delete_days:
        @param resource_name:
        @param resource_id:
        @param resource_type:
        @return:
        """
        resource_type = resource_type.capitalize()
        reason = self.policy.split('_')[-1]
        if 'empty' in self.policy:
            reason = 'empty'
        if 'zombie' in self.policy:
            reason = 'Unused'
        subject = f'cloud-governance alert: {self.policy}'
        if days == notification_days:
            cause = f'This {resource_type} will be deleted in  {delete_days-days} days if no further action is taken'
            content = f'If you do not want to be deleted, please add "Policy=Not_Delete" or "Policy=skip" tag to this {resource_type}.'
        elif kwargs.get('msgadmins'):
            cause = f'This {resource_type} will be deleted in  {delete_days - kwargs.get("msgadmins")} days if no further action is taken'
            content = f'If you do not want to be deleted, please add "Policy=Not_Delete" or "Policy=skip" tag to this {resource_type}.'
        else:
            cause = f'This {resource_type} will be deleted due to it was {reason} more than {delete_days} days.'
            content = f'In future cloud-governance will not delete your {resource_type} add "Policy=Not_Delete" or "Policy=skip" tag to your {resource_type}s'
        extra_data = ''
        if resources:
            extra_data = f'Cluster Undeleted Resources: {sorted(resources)}'
        body = f"""
Hi {name},

<b>{resource_type}</b>: {resource_name}: {resource_id} in {self.region} region in account: {self.account} has been in {reason} state for more than {days} days.
{cause}
{content}
If you already added the tag, please ignore this mail.

{extra_data}

{self.RESTRICTION}

Best Regards,
Cloud-governance Team""".strip()
        return subject, body

    def zombie_cluster_mail_message(self, name: str, days: int, notification_days: int, resource_name: str, delete_days: int):
        """
        This method prepare mail message based on resource_type and return subject, body
        @param delete_days:
        @param name:
        @param days:
        @param notification_days:
        @param resource_name:
        @return:
        """
        subject = f'Cloud-governance policy alert: {self.policy}'
        if days == notification_days:
            cause = f'Cloud-governance will delete those {self.policy}s in the  {delete_days-days} days.'
        else:
            cause = f'Those {self.policy}s will be deleted.'
        body = f"""
Hi {name},

There are zombie resources that related to your terminated cluster: {resource_name}, region: {self.region}, AWS account: {self.account}
You can find your {self.policy}s in the attached file: {resource_name.replace('/', '-')}.json
{cause}

{self.RESTRICTION}

Best Regards,
Cloud-governance Team""".strip()
        return subject, body
