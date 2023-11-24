from datetime import datetime

import boto3

from cloud_governance.common.clouds.aws.cloudtrail.cloudtrail_operations import CloudTrailOperations
from cloud_governance.common.clouds.aws.iam.iam_operations import IAMOperations
from cloud_governance.common.clouds.aws.utils.common_operations import get_tag_name_and_value
from cloud_governance.main.environment_variables import environment_variables


class AbstractClusterTaggingOperations:

    def __init__(self, region_name: str, cluster_name: str):
        self._cluster_name = cluster_name
        self._iam_client = boto3.client('iam')
        self._iam_operations = IAMOperations()
        self.iam_users = self._iam_operations.get_iam_users_list()
        self._mandatory_tags = ['cluster_id', 'User', 'Budget', 'Email']
        self._environment_variables_dict = environment_variables.environment_variables_dict
        self._region_name = region_name if region_name else self._environment_variables_dict.get('AWS_DEFAULT_REGION')
        self._account = self._environment_variables_dict.get('account')
        self._dry_run = self._environment_variables_dict.get('dry_run', 'yes')
        self._run_active_regions = self._environment_variables_dict.get('RUN_ACTIVE_REGIONS')
        self._cluster_prefix = self._environment_variables_dict.get('cluster_prefix', 'kubernetes.io/cluster/')
        self._tag_optional_tags = self._environment_variables_dict.get('TAG_OPTIONAL_TAGS')
        self._optional_tags = self._environment_variables_dict.get('OPTIONAL_TAGS')
        self._gmail_domain = self._environment_variables_dict.get('GMAIL_DOMAIN', 'redhat.com')

    def get_user_name_from_name_tag(self, tags: list):
        """
        This method returns the username from the name tag verified  with iam users
        :param tags:
        :return:
        """
        _, user_name = get_tag_name_and_value(tags=tags, key='User')
        if user_name in self.iam_users:
            return user_name
        else:
            _, name_tag = get_tag_name_and_value(tags=tags, key='Name')
            for user in self.iam_users:
                if user in name_tag:
                    return user
            return None

    def get_username(self, region_name: str, start_time: datetime, resource_id: str, resource_type: str, tags: list):
        """
        This method returns the username
        :param region_name:
        :param start_time:
        :param resource_id:
        :param resource_type:
        :param tags:
        :return:
        """
        iam_username = self.get_user_name_from_name_tag(tags=tags)
        if not iam_username:
            cloudtrail = CloudTrailOperations(region_name=region_name)
            return cloudtrail.get_username_by_instance_id_and_time(start_time=start_time, resource_id=resource_id,
                                                                   resource_type=resource_type, event_type='EventName')
        return iam_username

    def _fill_na_tags(self):
        """
        This method returns the NA tags of optional values
        @return:
        """
        tags = {}
        if self._tag_optional_tags:
            value = 'NA'
            for key in self._optional_tags:
                tags.update({key: value})
        return tags

    def _get_tags_to_update(self, default_tags: dict, new_tags: dict):
        """
        This method returns the tags to be updated in resource tags
        :param default_tags:
        :type default_tags:
        :param new_tags:
        :type new_tags:
        :return:
        :rtype:
        """
        update_tags = {}
        for key, value in new_tags.items():
            if key not in default_tags:
                update_tags.update({key: value})
            else:
                if default_tags.get(key) == 'NA':
                    update_tags.update({key: value})
        return update_tags
