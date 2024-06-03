import os.path

from jinja2 import Environment, FileSystemLoader

from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.main.environment_variables import environment_variables


class MailMessage:

    RESTRICTION = 'Do not reply this email. If you need more information, please reach out to us in the slack channel - #perf-dept-public-clouds.'
    FOOTER = '<div style="color:gray">---<br />Thanks, <br />Cloud GovernanceTeam</div>'

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.account = self.__environment_variables_dict.get('account', '').upper()
        self.policy = self.__environment_variables_dict.get('policy', '')
        self.region = self.__environment_variables_dict.get('AWS_DEFAULT_REGION', '')
        self.__LDAP_HOST_NAME = self.__environment_variables_dict.get('LDAP_HOST_NAME')
        self.__ldap_search = LdapSearch(ldap_host_name=self.__LDAP_HOST_NAME)
        self.__public_cloud_name = self.__environment_variables_dict.get('PUBLIC_CLOUD_NAME')
        self.__portal = self.__environment_variables_dict.get('CRO_PORTAL', '')
        self.__cro_duration_days = self.__environment_variables_dict.get('CRO_DURATION_DAYS')
        self.__LDAP_HOST_NAME = self.__environment_variables_dict.get('LDAP_HOST_NAME')
        self.__ldap_search = LdapSearch(ldap_host_name=self.__LDAP_HOST_NAME)
        self.__templates_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        self.env_loader = Environment(loader=FileSystemLoader(self.__templates_path))

    def get_user_ldap_details(self, user_name: str):
        """
        This method return user details from ldap
        :param user_name:
        :return:
        """
        user_details = self.__ldap_search.get_user_details(user_name=user_name)
        if user_details:
            return user_details.get('displayName')
        else:
            return None

    def ec2_stop(self, name: str, days: int, image_id: str, delete_instance_days: int, instance_name: str,
                 resource_id: str, stopped_time: str, ec2_type: str, **kwargs):
        extra_purse = ''
        if kwargs.get("extra_purse"):
            extra_purse = f', Cost {round(kwargs.get("extra_purse"), 3)} $ '
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

Instance: {instance_name}: {resource_id}( InstanceType:{ec2_type}{extra_purse}) in {self.region} region in account: {self.account} was stopped on {stopped_time}, it stopped state more than {days} days.
{message}
{content}

{self.RESTRICTION}

Best regards,
Cloud-governance Team""".strip()
        return subject, body

    def ec2_idle(self, name: str, days: int, notification_days: int, stop_days: int, instance_name: str,
                 resource_id: str, ec2_type: str, **kwargs):
        extra_purse = ''
        if kwargs.get('extra_purse'):
            extra_purse = f', Cost {round(kwargs.get("extra_purse"), 3)} $ '
        subject = f'cloud-governance alert: ec2-idle'
        if days == notification_days:
            cause = f'This instance will be stopped in {stop_days-days} days if no further action is taken'
            content = 'If you do not want it to be deleted, please "Policy=Not_Delete" or "Policy=ski"p tag to this instance.'
        else:
            cause = f'This instance will be stopped.'
            content = 'In future cloud-governance will not stop it add "Policy=Not_Delete" or "Policy=skip" tag to your instance'
        body = f"""
Hi {name},

Instance: {instance_name}: {resource_id} ( InstanceType:{ec2_type}{extra_purse}) in {self.region} on account: {self.account} is idle more than {days} days.
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

{self.__environment_variables_dict.get('account')} IAM User: {user} has missing tags
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
Your AWS user:{user} in account:{self.__environment_variables_dict.get('account')} cost was {user_usage}$ in the last week.
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
        extra_purse = ''
        if kwargs.get('extra_purse'):
            extra_purse = f'(Cost {round(kwargs.get("extra_purse"), 3)} $)'
        if 'empty' in self.policy:
            reason = 'empty'
        if 'zombie' in self.policy:
            reason = 'unused'
        subject = f'cloud-governance alert: {self.policy}'
        if days == notification_days:
            cause = f'This {resource_type} will be deleted in {delete_days-days} days if no further action is taken'
            content = f'If you do not want to be deleted, please add "Policy=Not_Delete" or "Policy=skip" tag to this {resource_type}.'
        elif kwargs.get('msgadmins'):
            cause = f'This {resource_type} will be deleted in {delete_days - kwargs.get("msgadmins")} days if no further action is taken'
            content = f'If you do not want to be deleted, please add "Policy=Not_Delete" or "Policy=skip" tag to this {resource_type}.'
        else:
            cause = f'This {resource_type} will be deleted due to it was {reason} more than {delete_days} days.'
            content = f'In future cloud-governance will not delete your {resource_type} add "Policy=Not_Delete" or "Policy=skip" tag to your {resource_type}s'
        body = f"""
Hi {name},

{resource_type.upper()}: {resource_name}: {resource_id} {extra_purse} in {self.region} region in account: {self.account} has been in {reason} for more than {days} days.
{cause}
{content}
If you already added the tag, please ignore this mail.

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
            cause = f'Cloud-governance will delete those {self.policy}s in the {delete_days-days} days.'
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

    def monthly_html_mail_message(self, data: str):
        """
        This method returns the description of the monthly resources
        @return:
        """
        subject = 'Cloud-Governance Monthly Report'
        body = f"""
<div class="greeting">
    <p>Hi All,</p>
</div>

<div class="body">
    <p>You can find below <a href="https://github.com/redhat-performance/cloud-governance" style="text-decoration:none;">cloud-governance</a> summary monthly report:</p>
    {data}
    <p>For more details open Cloud-Governance <a href="http://grafana.intlab.perf-infra.lab.eng.rdu2.redhat.com/" style="text-decoration:none;" target="_blank">Grafana</a>. [ user/password: cloud_governance ]</p>
    <p>Do not reply to this email, in case of any further questions. Please reach out to us in the slack channel - <span style="color:red">#perf-dept-public-clouds.<span>'</p>
</div>
<div style="color:gray" class="footer">
    <address>
        --<br/>
        Best Regards,<br/>
        Cloud-governance Team<br/>
    </address>
</div>
""".strip()
        return subject, body

    def ibm_cost_over_usage(self, data: str, month: int, year: int):
        """
        This method returns the mail message of cost over usage
        @return:
        """
        subject = 'Cloud-Governance IBM Cost Over Usage'
        body = f"""
        <div class="greeting">
            <p>Hi,</p>
        </div>

        <div class="body">
            <p>This following services were over limit</p>
            {data}
            <p>For more details open IBM Billing <a href="https://cloud.ibm.com/billing/usage?month={year}-{month}/" style="text-decoration:none;" target="_blank">Console</a>.</p>
            <p>Do not reply to this email, in case of any further questions. Please reach out to us in the slack channel -  <span style="color:red">#perf-dept-public-clouds.<span>'</p>
        </div>
        <div>
            <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/IBM_Cloud_logo.png"/>
        </div>
        <div style="color:gray" class="footer">
            <address>
                --<br/>
                Best Regards,<br/>
                Cloud-governance Team<br/>
            </address>
        </div>
        """.strip()
        return subject, body

    def cro_monitor_alert_message(self, days: int, user: str, ticket_id: str):
        """
        This method return the CRO Alert Message
        :param days:
        :param user:
        :param ticket_id:
        :return:
        """
        ticket_id = ticket_id.split('-')[-1]
        subject = f'[Action required] Cloud Resources Budget request Ticket Expiring in {days} days'
        user_display_name = self.get_user_ldap_details(user_name=user)
        body = f"""
                <div>
                    <p>Hi {user_display_name},</p>
                </div>
                <div>
                    <p>You project budget request ( TicketId: {ticket_id} ) will be expired in {days} days.</p>
                    <p>You can extend the project duration in the following url {self.__portal}/extend_duration or terminate the instances</p>
                    <p>Visit the <a href="{self.__portal}">wiki page</a> to get more information</p>
                </div>
                {self.FOOTER}
""".strip()
        return subject, body

    def cro_cost_over_usage(self, **kwargs):
        """
        This method returns the subject, body for cost over usage
        :param kwargs:
        :return:
        """
        cloud_name = kwargs.get('CloudName', 'NA').upper()
        over_usage_cost = kwargs.get('OverUsageCost', 'NA')
        full_name = kwargs.get('FullName', '')
        if not full_name:
            full_name = kwargs.get('to')
        user_cost = round(kwargs.get('Cost', 0), 3)
        subject = f' [Action required]: Cloud Resources Open Budget Request'
        if user_cost > over_usage_cost:
            message = f"it's over $ {over_usage_cost}."
        else:
            message = f"it may over $ {over_usage_cost} in next few days."
        body = f"""
        <div>
        Hi {full_name},
        </div><br/>
        <div>
            Your {cloud_name} cost usage in the last {self.__cro_duration_days} days is $ {user_cost} and {message}<br/>
            You must open the project ticket in the following <a href="{self.__portal}">Link</a>.<br />
            After submitting a ticket, you must add Tag (TicketId:#) to every active resource that is related to the project ticket.<br/>

            If you have any questions, please let us know in slack channel #perf-dept-public-clouds
        <div><br/><br/>
        {self.FOOTER}
"""
        return subject, body

    def cro_request_for_manager_approval(self, manager: str, request_user: str, cloud_name: str, ticket_id: str, description: dict, **kwargs):
        """
        This method returns the message for manager, regarding user approval
        :param description:
        :param ticket_id:
        :param manager:
        :param request_user:
        :param cloud_name:
        :return:
        """
        subject = '[Action required]: Cloud Resources Budget Request Approval'
        manager_full_name = self.get_user_ldap_details(user_name=manager)
        user_full_name = self.get_user_ldap_details(user_name=request_user)
        ticket_id = ticket_id.split('-')[-1]
        context = {'manager': manager, 'manager_full_name': manager_full_name, 'user_full_name': user_full_name,
                   'ticket_id': ticket_id, 'portal': self.__portal, 'request_user': request_user, 'description': description,
                   'footer': self.FOOTER}
        template_loader = self.env_loader.get_template('cro_request_for_manager_approval.j2')
        context['extra_message'] = kwargs.get('extra_message', '')
        body = template_loader.render(context)
        return subject, body

    def cro_send_user_alert_to_add_tags(self, user: str, ticket_ids: list):
        """
        This method return the subject, body for adding tags
        :param user:
        :param ticket_ids:
        :return:
        """
        subject = '[Action required]: Add TicketId tag'
        ticket_ids = "\n".join([f"<li>{val}</li>" for idx, val in enumerate(ticket_ids)])
        user_display_name = self.get_user_ldap_details(user_name=user)
        body = f"""
        <div>Hi {user_display_name},</div>
        <p>You have the following <b>Approved</b> JIRA Ticket-Ids</p>
        <ul>{ticket_ids}</ul><br />
        Currently, there are several instances running over budget, kindly review and tag instances with TicketId: #</p>
        <br />Please find the below attached document.<br />
        </div><br />
        {self.FOOTER}
        """
        return subject, body

    def cro_send_closed_alert(self, user: str, ticket_id: str):
        """
        This method send cro ticket close alert
        :param user:
        :param ticket_id:
        :return:
        """
        subject = 'Closing Cloud Budget Request ticket'
        ticket_id = ticket_id.split('-')[-1]
        user_full_name = self.get_user_ldap_details(user_name=user)
        body = f"""
        <div>Hi {user_full_name},</div><br />
            <div>
            Your cloud budget request ( TicketId: {ticket_id} ) duration expired and the ticket auto closed.<br />
            You can find the summary in <a href="{self.__portal}/wiki/clouds">Portal</a>.<br />
            </div><br /><br/>
        {self.FOOTER}
        """
        return subject, body

    def filter_resources_on_days(self, resources: dict):
        """
        This method return the resources based on the days
        :param resources:
        :param days:
        :return:
        """
        resources_by_days = {}
        for policy_name, resource_data in resources.items():
            for region_name, policy_region_data in resource_data.items():
                for data_item in policy_region_data:
                    resources_by_days.setdefault(data_item.get('Days'), []).append(data_item)
        return resources_by_days

    def get_data_in_html_table_format(self, resources: dict):
        """
        This method returns user policy alerts in HTML table format
        :param resources:
        :return:
        """
        style = """
                    <style>
                    #customers {
                    font-family: Verdana, Helvetica, sans-serif;
                    border-collapse: collapse;
                    width: 100%;
                    }

                    #customers td, #customers th {
                    border: 2px solid #000;
                    padding: 8px;
                    align: left;
                    }

                    #customers tr:nth-child(even){background-color: #dddddd;}

                    #customers tr:hover {background-color: #B9D9B7;}

                    #customers th {
                    padding-top: 12px;
                    padding-bottom: 12px;
                    text-align: left;
                    background-color: #04AA6D;
                    color: white;
                    }
                    </style>
                """
        html_table_format = f"""{style}<table id="customers">"""
        thead_values = ['Policy', 'Region', 'ResourceId', 'Name', 'Action', 'DeletedDay']
        th_elements = ''.join([f'<th>{value}</th>' for value in thead_values])
        html_table_format += f'<thead><tr>{th_elements}</tr></thead><tbody>'
        for days, resource_data in resources.items():
            resource_data = sorted(resource_data, key=lambda item: (item.get('Policy'), item.get('Region')))
            for resource in resource_data:
                html_table_format += '<tr>'
                for th_value in thead_values:
                    if 'Deleted' == resource.get(th_value):
                        html_table_format += f"<td>{resource.get(th_value)} &#128465;</td>"
                    else:
                        html_table_format += f"""<td>{resource.get(th_value)}</td>"""
                html_table_format += '</tr>'
        html_table_format += '</tbody></table>'
        return html_table_format

    def get_agg_policies_mail_message(self, user: str, user_resources: dict):
        """
        This method returns the message for the aggregated alert of all policies
        :param user:
        :param user_resources:
        :return:
        """
        display_name = self.get_user_ldap_details(user_name=user)
        resources_by_days = self.filter_resources_on_days(resources=user_resources)
        table_data = self.get_data_in_html_table_format(resources=resources_by_days)
        display_name = display_name if display_name else user
        subject = f'Cloud Governance: Policy Alerts'
        body = f"""
        <div>
            <p>Hi {display_name},</p>
        </div>
        <div>
            <p>You can find below your unused resources in the {self.__public_cloud_name} account ({self.account}).</p>
            <p>If you want to keep them, please add "Policy=Not_Delete" or "Policy=skip" tag for each resource</p>
            {table_data}
        </div>
        <p>{self.RESTRICTION}</p>
        {self.FOOTER}
"""
        return subject, body

    def cro_monitor_budget_remain_alert(self, ticket_id: str, budget: int, user: str, used_budget: int, remain_budget: int):
        """
        This method returns subject, body for the budget remain alert
        :param ticket_id:
        :param budget:
        :param user:
        :param used_budget:
        :param remain_budget:
        :return:
        """
        ticket_id = ticket_id.split('-')[-1]
        subject = f'[Action required] Cloud Resources Budget Remain'
        user_display_name = self.get_user_ldap_details(user_name=user)
        template_loader = self.env_loader.get_template('cro_monitor_budget_remain_alert.j2')
        context = {'name': user_display_name, 'ticket_id': ticket_id, 'portal': self.__portal,
                   'budget': budget, 'used_budget': used_budget, 'remain_budget': remain_budget, 'footer': self.FOOTER}
        body = template_loader.render(context)
        return subject, body

    def cro_monitor_budget_remain_high_alert(self, ticket_id: str, budget: int, user: str, used_budget: int, remain_budget: int):
        """
        This method returns subject, body for the budget completed high alert
        :param ticket_id:
        :param budget:
        :param user:
        :param used_budget:
        :param remain_budget:
        :return:
        """
        ticket_id = ticket_id.split('-')[-1]
        subject = f'[Action required] Cloud Resources Budget Remain'
        user_display_name = self.get_user_ldap_details(user_name=user)
        if remain_budget < 0:
            remain_budget *= -1
        template_loader = self.env_loader.get_template('cro_monitor_budget_remain_high_alert.j2')
        context = {'name': user_display_name, 'ticket_id': ticket_id, 'portal': self.__portal,
                   'budget': budget, 'used_budget': used_budget, 'remain_budget': remain_budget,
                   'footer': self.FOOTER}
        body = template_loader.render(context)
        return subject, body

    def get_policy_alert_message(self, policy_data: list, user: str = ''):
        """
        This method returns the policy alert message
        :return:
        :rtype:
        """
        if user:
            display_name = self.get_user_ldap_details(user_name=user)
            user = display_name if display_name else user
        subject = f"Cloud Governance: {self.account} Policy Alerts"
        template_loader = self.env_loader.get_template('policy_alert_agg_message.j2')
        columns = ['User', 'PublicCloud', 'policy', 'RegionName', 'ResourceId', 'Name', 'DeleteDate']
        context = {'records': policy_data, 'columns': columns, 'User': user, 'account': self.account, 'cloud_name': self.__public_cloud_name}
        body = template_loader.render(context)
        return subject, body
