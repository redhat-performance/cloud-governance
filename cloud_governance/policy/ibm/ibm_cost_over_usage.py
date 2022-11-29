import datetime
from ast import literal_eval

from cloud_governance.common.clouds.ibm.account.ibm_account import IBMAccount
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix
from cloud_governance.main.environment_variables import environment_variables


class IBMCostOverUsage:
    """
    This class fetches the ibm cost usage weekly and alert the admins
    """

    EXCLUDE_RESOURCES = ['bare metal servers and attached services', 'virtual server for vpc']
    MAXIMUM_THRESHOLD = 1000

    def __init__(self):
        super().__init__()
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__ibm_account = IBMAccount()
        self.__mail_message = MailMessage()
        self.__mail = Postfix()
        self.__maximum_threshold = self.__environment_variables_dict.get('MAXIMUM_THRESHOLD', '')
        if self.__maximum_threshold:
            self.__maximum_threshold = self.MAXIMUM_THRESHOLD
        self._to_mail = literal_eval(self.__environment_variables_dict.get('to_mail', '[]'))
        self._cc_mail = literal_eval(self.__environment_variables_dict.get('cc_mail', '[]'))

    def get_current_usage(self, month: int, year: int):
        """
        This method gets current usage
        @return:
        """
        usage_data = self.__ibm_account.get_daily_usage(month=month, year=year)
        if usage_data:
            usage_resources = usage_data.get('account_resources')
            usage_details = []
            for resource in usage_resources:
                usage_details.append({'Name': resource.get('resource_name'), 'Cost': resource.get('billable_cost')})
            return usage_details
        return []

    def check_cost_over_usage(self):
        """
        This method check the over usage of the resources
        @return:
        """
        date = datetime.datetime.now()
        month, year = date.month, date.year
        usage_resources = self.get_current_usage(month=month, year=year)
        cost_over_usage_resources = []
        for resource in usage_resources:
            if resource.get('Name').lower() not in self.EXCLUDE_RESOURCES:
                if resource.get('Cost') > int(self.__maximum_threshold):
                    cost_over_usage_resources.append(resource)
        if cost_over_usage_resources:
            subject, body = self.__mail_message.ibm_cost_over_usage(data=self.format_into_html_data(resources=cost_over_usage_resources), month=month, year=year)
            self.__mail.send_email_postfix(subject=subject, to=self._to_mail, cc=self._cc_mail, content=body, message_type='alert_admin', mime_type='html')
            logger.info('Mail sent successfully')

    def format_into_html_data(self, resources: list):
        """
        This method format the data into HTML list form
        @param resources:
        @return:
        """
        start_dt, end_dt = '<dt>', '</dt>'
        start_dl, end_dl = '<dd>', '</dd>'
        start_b, end_b = '<b>', '</b>'
        html_list = ['<dl>']
        for resource in resources:
            start_list = f'{start_dt}{start_b}{resource.get("Name")}{end_b}{end_dt}'
            start_list += f'{start_dl}- {resource.get("Cost")} ${end_dl}'
            html_list.append(start_list)
        html_list.append('</dt>')
        return "\n".join(html_list)

    def run(self):
        """
        This method run the ibm cost_over usage
        @return:
        """
        self.check_cost_over_usage()
