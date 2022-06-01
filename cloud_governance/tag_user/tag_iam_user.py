import csv

import boto3

from cloud_governance.common.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger


class TagUser:
    """
    Tag user in the AWS account
    """

    def __init__(self, file_name: str):
        self.iam_client = boto3.client('iam')
        self.get_detail_resource_list = Utils().get_details_resource_list
        self.IAMOperations = IAMOperations()
        self.file_name = file_name

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
                value = row[i].strip().upper()
                if value:
                    tagging[username].append(self.__get_tag(key, value))
        return tagging

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
                user_tags = self.IAMOperations.get_user_tags(username=key)
                tags.append({'Key': 'User', 'Value': key})
                filter_tags = self.__filter_tags_user_tags(user_tags, tags)
                if filter_tags:
                    self.iam_client.tag_user(UserName=key, Tags=filter_tags)
                    logger.info(f'Username :: {key} {filter_tags}')
                    updated_usernames.append(key)
                    count += 1
        logger.info(f'Updated Tags of IAM Users = {count} :: Usernames {updated_usernames}')
        return count
