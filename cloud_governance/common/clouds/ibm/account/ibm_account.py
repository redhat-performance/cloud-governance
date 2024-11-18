import datetime
import os

import SoftLayer
import pandas as pd
from ibm_platform_services import UsageReportsV4
from retry import retry
from typeguard import typechecked

from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class IBMAccount:
    """
    This class contains IBM softlayer client and methods
    For Usage reports need to export
    export USAGE_REPORTS_URL=<SERVICE_URL>
    export USAGE_REPORTS_AUTHTYPE=iam
    export USAGE_REPORTS_APIKEY=<API_KEY>
    """

    START_DATE = 1
    END_DATE = 16
    RETRIES = 3
    DELAY = 30

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__API_USERNAME = self.__environment_variables_dict.get('IBM_API_USERNAME', '')
        self.__API_KEY = self.__environment_variables_dict.get('IBM_API_KEY', '')
        try:
            if self.__API_KEY and self.__API_USERNAME:
                self.__sl_client = SoftLayer.create_client_from_env(username=self.__API_USERNAME,
                                                                    api_key=self.__API_KEY, timeout=self.DELAY)
                self.short_account_id = str(self.__API_USERNAME.split('_')[0])
            if self.__environment_variables_dict.get('USAGE_REPORTS_APIKEY'):
                self.__service_client = UsageReportsV4.new_instance()
        except Exception as err:
            raise err
        self.account = self.__environment_variables_dict.get('account', '')
        self.__account_id = self.__environment_variables_dict.get('IBM_ACCOUNT_ID', '')

        self.__gsheet_id = self.__environment_variables_dict.get('SPREADSHEET_ID', '')
        self.__gsheet_client = GoogleDriveOperations()
        self.__ldap_host_name = self.__environment_variables_dict.get('LDAP_HOST_NAME', '')
        self.__ldap = LdapSearch(ldap_host_name=self.__ldap_host_name)

    def get_sl_client(self):
        """
        This method return the softlayer client
        @return:
        """
        return self.__sl_client

    @typechecked
    def __organise_user_tags(self, tags: dict):
        """
        This method organise the tags from the gsheet
        @param tags:
        @return:
        """
        user_tags = []
        for tag, value in tags.items():
            if value.strip():
                value = value.replace('/', '-')
                user_tags.append(f'{tag.strip().lower()}:{value.strip().lower()}')
        return user_tags

    @typechecked
    def get_user_tags_from_gsheet(self, username: str, user_email: str = '', file_path: str = '/tmp/'):
        """
        This method return the user tags from the gsheet
        @param user_email:
        @param username:
        @param file_path:
        @return:
        """
        file_name = os.path.join(file_path, f'{self.account}.csv')
        if not os.path.exists(file_name):
            self.__gsheet_client.download_spreadsheet(spreadsheet_id=self.__gsheet_id, sheet_name=self.account,
                                                      file_path=file_path)
        if os.path.exists(file_name):
            df = pd.read_csv(file_name)
            df.fillna('', inplace=True)
            if user_email:
                df.set_index('_Email', inplace=True)
                user = username.split('@')[0]
            else:
                df.set_index('User', inplace=True)
                user = username.split('_')[1].split('@')[0]
            try:
                tags = dict(df.loc[username])
            except KeyError:
                tags = {}
            tags['User'] = user
        else:
            tags = {}
            if '@redhat.com' in username:
                tags = {'User': username.split('_')[-1].split('@')[0]}
        for key in list(tags.keys()):
            if key.startswith('_'):
                tags.pop(key)
        if tags:
            ldap_data = self.__ldap.get_user_details(user_name=tags['User'])
            if ldap_data:
                tags['Owner'] = ldap_data['FullName']
                tags['Manager'] = ldap_data['managerName']
        return self.__organise_user_tags(tags)

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @typechecked
    @logger_time_stamp
    def get_monthly_invoices(self, month: int, year: int):
        _filter = {
            'invoices': {
                'closedDate': {
                    'operation': 'betweenDate',
                    'options': [
                        {'name': 'startDate', 'value': [f'{month} / {self.START_DATE} / {year}']},
                        {'name': 'endDate', 'value': [f'{month} / {self.END_DATE} / {year}']}
                    ]
                }
            }
        }
        invoice_mask = "mask[id, closedDate, typeCode, createDate]"
        invoice_list = self.__sl_client.call('SoftLayer_Account', 'getInvoices', mask=invoice_mask, filter=_filter,
                                             iter=True)
        invoice_data = {}
        for invoice in invoice_list:
            if invoice.get('typeCode') == 'RECURRING':
                invoice_item_mask = f"""mask[id, createDate, recurringFee, parentId, categoryCode, description, hostName, domainName, invoiceId, resourceTableId, productItemId]"""
                invoice_items = self.__sl_client.call('SoftLayer_Billing_Invoice', 'getItems', id=invoice.get('id'),
                                                      iter=True, mask=invoice_item_mask)
                invoice_data[invoice.get('id')] = invoice_items
        return invoice_data

    @retry(exceptions=Exception, tries=RETRIES, delay=DELAY)
    @logger_time_stamp
    def get_users(self):
        """
        This method returns all the users of the ibm cloud
        @return:
        """
        user_mask = "email"
        users = self.__sl_client.call('SoftLayer_Account', 'getUsers', mask=user_mask, iter=True)
        if users:
            return [user['email'].split('@')[0] for user in users]
        else:
            return []

    @typechecked
    @logger_time_stamp
    def get_invoice_data(self, month: int, year: int):
        """
        This method return invoice data
        @return:
        """
        users = self.get_users()
        data = self.get_monthly_invoices(month, year)
        hostname_data = {}
        parent_id_data = {}
        description_id_data = {}
        for invoice_id, invoices in data.items():
            for invoice in invoices:
                parent_id = invoice.get('parentId')
                item_id = invoice.get('id')
                recurring_fee = float(invoice.get('recurringFee', 0))
                description = invoice.get('description')
                username = [user for user in users if user in description]
                if not parent_id:
                    if 'hostName' in invoice:
                        hostname_data[item_id] = f"""{invoice.get('hostName')}.{invoice.get('domainName')}"""
                    else:
                        hostname_data[item_id] = f"""{invoice.get('categoryCode')}"""
                if parent_id:
                    parent_id_data[parent_id] = parent_id_data.get(parent_id, 0) + recurring_fee
                else:
                    parent_id_data[item_id] = parent_id_data.get(item_id, 0) + recurring_fee
                if username:
                    description_id_data.setdefault(parent_id, set()).add(
                        f'{username[0]}-{"-".join(description.split()[:2])}')
        for parent_id, username in description_id_data.items():
            hostname_data[parent_id] = list(username)[0]
        combine_invoice_data = {}
        co = 0
        for key, value in parent_id_data.items():
            if value > 0:
                if hostname_data.get(key).lower() in combine_invoice_data:
                    combine_invoice_data[hostname_data.get(key).lower()]['cost'] += value
                else:
                    combine_invoice_data[hostname_data.get(key).lower()] = {
                        'fqdn': hostname_data.get(key).lower(),
                        'cost': value
                    }
                co += value
        return combine_invoice_data, users

    @logger_time_stamp
    def get_next_recurring_invoice(self):
        """This method returns the next recurring invoice"""
        invoice_items = self.__sl_client.call('SoftLayer_Account', 'getNextInvoiceTotalRecurringAmount', iter=True)
        return float(invoice_items[0]) if invoice_items else 0

    @logger_time_stamp
    def get_daily_usage(self, month: int, year: int):
        """
        This method get IBM monthly usage
        @param month:
        @param year:
        @return:
        """
        billing_month = str(year) + '-' + str(month)  # yyyy-mm
        account_summary = self.__service_client.get_account_summary(account_id=self.__account_id,
                                                                    billingmonth=billing_month,
                                                                    timeout=self.DELAY).get_result()
        return account_summary
