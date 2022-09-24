import csv
import os
import re
from ast import literal_eval

import boto3
import pandas as pd

from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.google_drive.google_drive_operations import GoogleDriveOperations
from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix


class TagUser:
    """
    Tag user in the AWS account
    """

    def __init__(self, file_name: str):
        self.iam_client = boto3.client('iam')
        self.get_detail_resource_list = Utils().get_details_resource_list
        self.IAMOperations = IAMOperations()
        self.file_name = file_name
        self.__SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '')
        self.__ldap_host_name = os.environ.get('LDAP_HOST_NAME', '')
        self.__ldap = LdapSearch(ldap_host_name=self.__ldap_host_name)
        self._special_user_mails = self.__literal_eval(os.environ.get('special_user_mails', '{}'))
        if self.__SPREADSHEET_ID:
            self.__google_drive_operations = GoogleDriveOperations()
            self.__sheet_name = os.environ.get('account', '')
            self.__mail = Postfix()


    def __literal_eval(self, data: any):
        if data:
            return literal_eval(data)
        return data

    def __cluster_user(self, tags: list):
        """
        This method check the user is cluster or not
        @param tags:
        @return:
        """
        for tag in tags:
            if 'kubernetes.io/cluster' in tag.get('Key'):
                return True
        return False

    def __write_into_csv_file(self, tag_keys: list, tag_values: dict):
        """
        This method create a csv file and append data into it
        @param tag_keys:
        @param tag_values:
        @return:
        """
        with open(self.file_name, 'w') as file:
            file.write('Username, ')
            if 'Username' in tag_keys:
                tag_keys.remove('Username')
            for index, tag in enumerate(tag_keys):
                file.write(f'{tag}, ')
            file.write('\n')
            tag_keys = list(tag_keys)
            for key, values in tag_values.items():
                values = dict(sorted(values.items()))
                file.write(f'{key}, ')
                if 'Username' in values:
                    values.pop('Username')
                for tag_key in tag_keys:
                    if tag_key in values:
                        file.write(f'{values.get(tag_key)}, ')
                    else:
                        file.write(' , ')
                file.write('\n')

    def generate_user_csv(self):
        """
        This method generates the User csv
        @return:
        """
        users = self.get_detail_resource_list(func_name=self.iam_client.list_users, input_tag='Users',
                                              check_tag='Marker')
        tag_keys = set()
        tag_values = {}
        for user in users:
            user_name = user.get('UserName')
            if '-' not in user_name:
                user_tags = self.IAMOperations.get_user_tags(username=user_name)
                tag_values[user_name] = {}
                for tag in user_tags:
                    if not self.__cluster_user(tags=user_tags):
                        key = tag.get('Key')
                        if key == "Name":
                            key = 'Username'
                        value = tag.get('Value')
                        tag_keys.add(key)
                        tag_values[user_name][key] = value
                    else:
                        del tag_values[user_name]
                        break
        tag_keys = list(sorted(tag_keys))
        self.__write_into_csv_file(tag_keys=tag_keys, tag_values=tag_values)
        with open(self.file_name) as file:
            logger.info(file.read())

    def __filter_tags_user_tags(self, user_tags: list, append_tags: list):
        """
        This method filter the tad of user ad updated tags of user
        @param user_tags:
        @param append_tags:
        @return:
        """
        add_tags = []
        if user_tags:
            for append_tag in append_tags:
                found = False
                for user_tag in user_tags:
                    if user_tag.get('Key').strip() == append_tag.get('Key').strip():
                        if user_tag.get('Value').strip() == append_tag.get('Value').strip():
                            found = True
                if not found:
                    add_tags.append(append_tag)
        else:
            add_tags.extend(append_tags)
        return add_tags

    def __get_tag(self, key, value):
        """
        This method creates a pair of Key Value pair
        @param key:
        @param value:
        @return:
        """
        return {'Key': key, 'Value': value}

    def __get_json_data(self, header: list, rows: list):
        """
        This method convert data list into dictionary
        @param header:
        @param rows:
        @return:
        """
        tagging = {}
        for row in rows:
            username = row[0].strip()
            tagging[username] = []
            for i in range(1, len(row)):
                key = header[i].strip()
                value = row[i].strip().upper().replace('\'', ' ')
                if value:
                    tagging[username].append(self.__get_tag(key, value))
        return tagging

    def get_user_details_from_ldap(self, user_name: str):
        """
        This method get user details from ldap
        @param user_name:
        @return:
        """
        user_name = user_name if user_name not in self._special_user_mails else self._special_user_mails[user_name]
        ldap_data = self.__ldap.get_user_details(user_name=user_name.lower())
        if ldap_data:
            return [{'Key': 'Owner', 'Value': re.sub('\W+', ' ', ldap_data.get('FullName').upper())},
                    {'Key': 'Manager', 'Value': re.sub('\W+', ' ', ldap_data.get('managerName').upper())}]
        return []

    def update_user_tags(self):
        """
        This method updates the user tags from the csv file
        @return:
        """
        count = 0
        updated_usernames = []
        with open(self.file_name) as file:
            csvreader = csv.reader(file)
            header = next(csvreader)
            rows = []
            for row in csvreader:
                rows.append(row)
            json_data = self.__get_json_data(header, rows)
            for key, tags in json_data.items():
                try:
                    user_tags = self.IAMOperations.get_user_tags(username=key)
                    tags.append({'Key': 'User', 'Value': key})
                    tags.extend(self.get_user_details_from_ldap(user_name=key))
                    filter_tags = self.__filter_tags_user_tags(user_tags, tags)
                    if filter_tags:
                        self.iam_client.tag_user(UserName=key, Tags=filter_tags)
                        logger.info(f'Username :: {key} {filter_tags}')
                        updated_usernames.append(key)
                        count += 1
                except Exception as err:
                    logger.info(err)
        logger.info(f'Updated Tags of IAM Users = {count} :: Usernames {updated_usernames}')
        return count

    def __format_tags(self, username: str, headers: list):
        tags = {'User': username}
        user_tags = self.IAMOperations.get_user_tags(username=username)
        for user_tag in user_tags:
            if user_tag.get('Key') in headers:
                tags[user_tag.get('Key').strip()] = user_tag.get('Value').strip()
        return tags

    def delete_update_user_from_doc(self):
        """
        This method removes IAM user if not in the IAM list
        @return:
        """
        iam_file = pd.read_csv(self.file_name)
        iam_users = [user['UserName'] for user in self.IAMOperations.get_users()]
        csv_iam_users = list(iam_file['User'])
        for index, user in enumerate(csv_iam_users):
            if user not in iam_users:
                self.__google_drive_operations.delete_rows(spreadsheet_id=self.__SPREADSHEET_ID,
                                                           sheet_name=self.__sheet_name, row_number=index + 1)
                logger.info(f'removed user {user}')
        append_data = []
        for user in iam_users:
            if '-' not in user:
                if user not in csv_iam_users:
                    tags = self.__format_tags(username=user, headers=list(iam_file.columns))
                    df2 = pd.DataFrame.from_dict([tags])
                    iam_file = pd.concat([iam_file, df2], ignore_index=True)
                    iam_file = iam_file.fillna('')
                    append_data.append(list(iam_file.iloc[-1]))
                    if len(tags) < len(list(iam_file.columns)):
                        self.__trigger_mail(user=user)
        if append_data:
            response = self.__google_drive_operations.append_values(spreadsheet_id=self.__SPREADSHEET_ID,
                                                                    sheet_name=self.__sheet_name, values=append_data)
            if response:
                logger.info(f'Updated the users in the spreadsheet')

    def __trigger_mail(self, user: str):
        """
        This method send mail
        @param user:
        @return:
        """
        to = user if user not in self._special_user_mails else self._special_user_mails[user]
        ldap_data = self.__ldap.get_user_details(user_name=to)
        cc = [os.environ.get("account_admin", '')]
        name = to
        if ldap_data:
            cc.append(f'{ldap_data.get("managerId")}@redhat.com')
            name = ldap_data.get('displayName')
        subject, body = MailMessage().iam_user_add_tags(name=name, user=user, spreadsheet_id=self.__SPREADSHEET_ID)
        self.__mail.send_email_postfix(to=to, content=body, subject=subject, cc=cc)
