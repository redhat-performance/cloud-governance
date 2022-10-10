import os
from ast import literal_eval
from copy import deepcopy

import boto3

from cloud_governance.common.ldap.ldap_search import LdapSearch
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.mails.mail_message import MailMessage
from cloud_governance.common.mails.postfix import Postfix


class ZombieClusterCommonMethods:

    DAYS_TO_TRIGGER_RESOURCE_MAIL = 4
    DAYS_TO_DELETE_RESOURCE = 7

    def __init__(self, region: str):
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.ec2_resource = boto3.resource('ec2', region_name=region)
        self.elb_client = boto3.client('elb', region_name=region)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.__ldap_host_name = os.environ.get('LDAP_HOST_NAME', '')
        self._special_user_mails = os.environ.get('special_user_mails', '{}')
        self._account_admin = os.environ.get('account_admin', '')
        self._ldap = LdapSearch(ldap_host_name=self.__ldap_host_name)
        self._mail = Postfix()
        self._mail_description = MailMessage()

    def _literal_eval(self, data: any):
        tags = {}
        if data:
            tags = literal_eval(data)
        return tags

    def _get_tag_name_from_tags(self, tags: list, tag_name: str):
        """
        This method return tag_name from resource_tags
        @param tags:
        @param tag_name:
        @return:
        """
        if tags:
            for tag in tags:
                if tag.get('Key') == tag_name:
                    return tag.get('Value')
        return ''

    def _get_zombie_cluster_user_tag(self, zombies: dict, resources: list, resource_id: str, tag: str = 'Tags'):
        """
        This method returns the zombie_cluster tag and with user_tag i.e {cluster_tag: user_name}
        @param zombies:
        @param resources:
        @param resource_id:
        @return:
        """
        zombie_cluster_user_tag = {}
        for resource in resources:
            zombie_id = resource.get(resource_id)
            if zombie_id in zombies:
                zombie_cluster_user_tag[zombies[zombie_id]] = self._get_tag_name_from_tags(tags=resource.get(tag), tag_name='User')
        return zombie_cluster_user_tag

    def _get_tags_of_zombie_resources(self, resources: list, resource_id_name: str, zombies: dict, aws_service: str, aws_tag: str = 'Tags'):
        """
        This method return tags of the resource i.e {resource_id: tags}
        @param resources:
        @param tags:
        @return:
        """
        resources_tags = {}
        for resource in resources:
            resource_id = resource.get(resource_id_name)
            if resource.get(aws_tag):
                old_tags = deepcopy(resource.get(aws_tag))
                tags = resource.get(aws_tag)[:]
                empty_days = self._get_tag_name_from_tags(tags=tags, tag_name='EmptyDays')
                if empty_days:
                    if resource_id in zombies:
                        tags = self._update_resource_tags(tags=tags, tag_name='EmptyDays', tag_value=str(int(empty_days) + 1))
                    else:
                        tags = self._update_resource_tags(tags=tags, tag_name='EmptyDays', tag_value=str(0))
                else:
                    if resource_id in zombies:
                        tags = self._update_resource_tags(tags=tags, tag_name='EmptyDays', tag_value=str(1))
                if old_tags != tags:
                    if aws_service == 'ec2':
                        self.ec2_client.create_tags(Resources=[resource_id], Tags=tags)
                if resource_id in zombies:
                    resources_tags[resource_id] = tags
        return resources_tags

    def _update_resource_tags(self, tags: list, tag_name: str, tag_value: str):
        """
        This method updates tags of the resource
        @param tags:
        @param tag_name:
        @param tag_value:
        @param resource_id:
        @return:
        """
        found = False
        if tags:
            for tag in tags:
                if tag.get('Key') == tag_name:
                    tag['Value'] = str(tag_value)
                    found = True
            if not found:
                tags.append({'Key': tag_name, 'Value': str(tag_value)})
            return tags
        return [{'Key': tag_name, 'Value': str(tag_value)}]

    def _get_empty_days(self, tags: list) -> int:
        """
        This method return the EmptyDays tag
        @param tags:
        @return:
        """
        empty_days = self._get_tag_name_from_tags(tags=tags, tag_name='EmptyDays')
        if not empty_days:
            empty_days = 1
        else:
            empty_days = int(empty_days) + 1
        return empty_days

    def _trigger_mail(self, tags: list, resource_id: str, days: int, resource_type: str, resources: list):
        """
        This method send triggering mail
        @param tags:
        @param resource_id:
        @return:
        """
        try:
            special_user_mails = self._literal_eval(self._special_user_mails)
            user, resource_name = self._get_tag_name_from_tags(tags=tags, tag_name='User'), self._get_tag_name_from_tags(tags=tags, tag_name='Name')
            if not resource_name:
                resource_name = self._get_tag_name_from_tags(tags=tags, tag_name='cg-Name')
            to = user if user not in special_user_mails else special_user_mails[user]
            ldap_data = self._ldap.get_user_details(user_name=to)
            cc = []  # [self._account_admin, f'{ldap_data.get("managerId")}@redhat.com']
            name = to
            if ldap_data:
                name = ldap_data.get('displayName')
            subject, body = self._mail_description.resource_message(name=name, days=days,
                                                                    notification_days=self.DAYS_TO_TRIGGER_RESOURCE_MAIL,
                                                                    delete_days=self.DAYS_TO_DELETE_RESOURCE,
                                                                    resource_name=resource_name, resource_id=resource_id,
                                                                    resource_type=resource_type, resources=resources)
            self._mail.send_email_postfix(to=to, content=body, subject=subject, cc=cc, resource_id=resource_id)
        except Exception as err:
            logger.info(err)

