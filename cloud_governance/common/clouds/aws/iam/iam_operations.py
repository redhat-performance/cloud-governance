import os

import boto3

from cloud_governance.common.clouds.aws.utils.common_methods import get_boto3_client
from cloud_governance.common.clouds.aws.utils.utils import Utils
from cloud_governance.common.logger.init_logger import logger
from datetime import datetime, timezone


class IAMOperations:

    def __init__(self, iam_client=None):
        self.iam_client = iam_client if iam_client else get_boto3_client('iam')
        self.utils = Utils()
        self.__sts_client = boto3.client('sts')

    @property
    def get_iam_client(self):
        return self.iam_client

    def get_user_tags(self, username: str):
        """
        This method return tags from the iam resources
        @param username:
        @return:
        """
        try:
            user = self.iam_client.get_user(UserName=username)['User']
            if user.get('Tags'):
                return user.get('Tags')
            else:
                return []
        except:
            return []

    def get_roles(self):
        """
        This method returns all roles
        @return:
        """
        return self.utils.get_details_resource_list(func_name=self.iam_client.list_roles, input_tag='Roles',
                                                    check_tag='Marker')

    def get_users(self):
        """
        This method returns all users
        @return:
        """
        return self.utils.get_details_resource_list(self.iam_client.list_users, input_tag='Users', check_tag='Marker')

    def get_account_alias_cloud_name(self):
        """
        This method returns the aws account alias and cloud name
        @return:
        """
        try:
            account_alias = self.iam_client.list_account_aliases()['AccountAliases']
            if account_alias:
                return account_alias[0].upper(), 'AwsCloud'.upper()
        except:
            return os.environ.get('account', '').upper(), 'AwsCloud'.upper()

    def get_iam_users_list(self):
        """
        This method return the IAM users list
        :return:
        """
        iam_users = []
        users = self.get_users()
        for user in users:
            iam_users.append(user.get('UserName'))
        return iam_users

    def get_aws_account_id_name(self):
        """
        This method returns the aws account_id
        :return:
        """
        response = self.__sts_client.get_caller_identity()
        account_id = response['Account']
        return account_id

    def get_role(self, role_name: str):
        """
        This method returns the iam role data
        :param role_name:
        :return:
        """
        role_data = {}
        try:
            role_data = self.iam_client.get_role(RoleName=role_name).get('Role')
        except Exception as err:
            logger.error(err)
        return role_data

    def list_inline_role_policies(self, role_name: str):
        """
        This method returns the iam role inline policies
        :param role_name:
        :return:
        """
        role_policies = []
        try:
            role_policies = self.iam_client.list_role_policies(RoleName=role_name).get('PolicyNames', [])
        except Exception as err:
            logger.error(err)
        return role_policies

    def list_attached_role_policies(self, role_name: str):
        """
        This method returns the iam role attached policies
        :param role_name:
        :return:
        """
        attached_policies = []
        try:
            attached_policies = self.iam_client.list_attached_role_policies(RoleName=role_name).get('AttachedPolicies',
                                                                                                    [])
        except Exception as err:
            logger.error(err)
        return attached_policies

    def delete_role(self, role_name: str):
        """
        This method deletes the iam role
        :param role_name:
        :return:
        """
        try:
            self.iam_client.delete_role(RoleName=role_name)
            return True
        except Exception as err:
            raise err

    def tag_role(self, role_name: str, tags: list):
        """
        This method tags the iam role
        :param role_name:
        :param tags:
        :return:
        """
        try:
            self.iam_client.tag_role(RoleName=role_name, Tags=tags)
            return True
        except Exception as err:
            raise err

    def untag_role(self, role_name: str, tags: list):
        """
        This method untags the iam role
        :param role_name:
        :param tags:
        :return:
        """
        try:
            self.iam_client.untag_role(RoleName=role_name,
                                       TagKeys=[key for tag in tags for key, _ in tag.items() if key == 'Key'])
            return True
        except Exception as err:
            raise err

    def tag_user(self, user_name: str, tags: list):
        """
        This method tags the IAM user.
        :param user_name: The name of the IAM user to tag.
        :param tags: A list of tags to associate with the user.
        :return: True if tagging is successful, otherwise raises an exception.
        """
        try:
            self.iam_client.tag_user(UserName=user_name, Tags=tags)
            return True
        except Exception as err:
            raise err

    def get_iam_users_access_keys(self):
        """
        Retrieves IAM users and summarizes:
            - Access key status (active/inactive)
            - Access key age in days
            - Access key last used in days (or "N/A" if never used)
            - Tags (as a list of dictionaries)
            - Most recent key usage: last_activity_days
            - IAM client region (global context, since IAM is non-regional)
            - IAM user unique ID: ResourceId

        Returns:
            dict: {
                "username": {
                    "Access key 1": [status, age_days, last_used_days],
                    "Access key 2": [...],
                    "last_activity_days": int or "N/A",
                    "tags": [{"Key": "tag_key", "Value": "tag_value"}, ...],
                    "region": "us-east-1",
                    "ResourceId": "AIDAEXAMPLEUSERID"
                },
                ...
            }
        """
        result = {}
        now = datetime.now(timezone.utc)
        region_name = self.iam_client.meta.region_name or "global"

        paginator = self.iam_client.get_paginator('list_users')
        for page in paginator.paginate():
            for user in page['Users']:
                username = user['UserName']
                result[username] = {}
                last_used_days_list = []

                # Access keys
                access_keys = self.iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']
                for idx, key in enumerate(access_keys, start=1):
                    label = f"Access key {idx}"
                    status = key['Status'].lower()
                    age_days = (now - key['CreateDate']).days

                    # Get access key last used
                    try:
                        response = self.iam_client.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
                        last_used_date = response.get('AccessKeyLastUsed', {}).get('LastUsedDate')
                        if last_used_date:
                            last_used_days = (now - last_used_date).days
                            last_used_days_list.append(last_used_days)
                        else:
                            last_used_days = "N/A"
                    except Exception:
                        last_used_days = "N/A"

                    result[username][label] = [status, age_days, last_used_days]

                # Most recent access key activity
                result[username]["last_activity_days"] = min(last_used_days_list) if last_used_days_list else "N/A"

                # Tags as list of dicts
                try:
                    tag_response = self.iam_client.list_user_tags(UserName=username)
                    tags = tag_response.get('Tags', [])
                except Exception:
                    tags = []

                result[username]["tags"] = tags
                result[username]["region"] = region_name
                result[username]["ResourceId"] = user.get('UserId')  # <-- Unique ID
        return result

    def has_active_access_keys(self, username):
        """
        Checks if the given IAM user has any active access keys.
        When no user access key return False
        Args:
            username (str): IAM user name

        Returns:
            bool: True if any access key is active, False otherwise
        """
        try:
            access_keys = self.iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']
        except Exception as e:
            logger.error(f"Failed to list access keys for user '{username}': {e}")
            return False

        for key in access_keys:
            if key.get('Status') == 'Active':
                return True
        return False

    def deactivate_user_access_keys(self, username):
        """
        Deactivates all active access keys for the given IAM user.

        Args:
            username (str): IAM user name
        """
        try:
            access_keys = self.iam_client.list_access_keys(UserName=username)['AccessKeyMetadata']
        except Exception as e:
            logger.error(f"Failed to list access keys for user '{username}': {e}")
            return

        for idx, key in enumerate(access_keys, start=1):
            label = f"Access key {idx}"
            current_status = key['Status'].lower()
            access_key_id = key['AccessKeyId']

            if current_status == 'active':
                try:
                    self.iam_client.update_access_key(
                        UserName=username,
                        AccessKeyId=access_key_id,
                        Status='Inactive'
                    )
                    logger.info(f"{label} deactivated for user '{username}'")
                except Exception as e:
                    logger.error(f"Failed to deactivate {label} for user '{username}': {e}")
            else:
                logger.info(f"{label} is already inactive for user '{username}'")

        logger.info(f"Deactivate access keys for user '{username}' have been processed.")
