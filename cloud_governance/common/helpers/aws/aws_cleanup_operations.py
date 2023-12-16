import datetime

import boto3

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.helpers.cleanup_operations import AbstractCleanUpOperations
from cloud_governance.common.logger.init_logger import logger


class AWSCleanUpOperations(AbstractCleanUpOperations):

    def __init__(self):
        super().__init__()
        self._region = self._environment_variables_dict.get('AWS_DEFAULT_REGION', 'us-east-2')
        self.__s3operations = S3Operations(region_name=self._region)
        self._ec2_client = boto3.client('ec2', region_name=self._region)
        self._s3_client = boto3.client('s3')
        self._iam_client = boto3.client('iam')

    def get_tag_name_from_tags(self, tags: list, tag_name: str) -> str:
        """
        This method returns the tag value from the tags
        :param tags:
        :type tags:
        :param tag_name:
        :type tag_name:
        :return:
        :rtype:
        """
        if tags:
            for tag in tags:
                if tag.get('Key').strip().lower() == tag_name.lower():
                    return tag.get('Value').strip()
        return ''

    def get_clean_up_days_count(self, tags: list):
        """
        This method returns the cleanup days count
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        last_used_day = self.get_tag_name_from_tags(tags=tags, tag_name='DaysCount')
        if not last_used_day:
            return 1
        else:
            date, days = last_used_day.split('@')
            if date != str(self.CURRENT_DATE):
                return int(days) + 1
            return 1 if int(days) == 0 else int(days)

    def _delete_resource(self, resource_id: str):
        """
        This method deletes the resource by verifying the policy
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        action = "deleted"
        try:
            if self._policy == 's3_inactive':
                self._s3_client.delete_bucket(Bucket=resource_id)
            elif self._policy == 'empty_roles':
                self._iam_client.delete_role(RoleName=resource_id)
            elif self._policy == 'ebs_unattached':
                self._ec2_client.delete_volume(VolumeId=resource_id)
            elif self._policy == 'ip_unattached':
                self._ec2_client.release_address(AllocationId=resource_id)
            elif self._policy == 'unused_nat_gateway':
                self._ec2_client.delete_nat_gateway(NatGatewayId=resource_id)
            elif self._policy == 'zombie_snapshots':
                self._ec2_client.delete_snapshot(SnapshotId=resource_id)
            elif self._policy == 'ec2_run':
                self._ec2_client.stop_instances(InstanceIds=[resource_id])
                action = "Stopped"
            logger.info(f'{self._policy} {action}: {resource_id}')
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')

    def __remove_tag_key_aws(self, tags: list):
        """
        This method returns the tags that does not contain key startswith aws:
        :param tags:
        :type tags:
        :return:
        :rtype:
        """
        custom_tags = []
        for tag in tags:
            if not tag.get('Key').lower().startswith('aws'):
                custom_tags.append(tag)
        return custom_tags

    def __update_tag_value(self, tags: list, tag_name: str, tag_value: str):
        """
        This method updates the tag_value
        @param tags:
        @param tag_name:
        @param tag_value:
        @return:
        """
        if self._dry_run == "yes":
            tag_value = 0
        tag_value = f'{self.CURRENT_DATE}@{tag_value}'
        found = False
        if tags:
            for tag in tags:
                if tag.get('Key') == tag_name:
                    if tag.get('Value').split("@")[0] != self.CURRENT_DATE:
                        tag['Value'] = tag_value
                    else:
                        if int(tag_value.split("@")[-1]) == 0 or int(tag_value.split("@")[-1]) == 1:
                            tag['Value'] = tag_value
                    found = True
        if not found:
            tags.append({'Key': tag_name, 'Value': tag_value})
        tags = self.__remove_tag_key_aws(tags=tags)
        return tags

    def update_resource_day_count_tag(self, resource_id: str, cleanup_days: int, tags: list, force_tag_update: str = ''):
        """
        This method updates the resource tags
        :param force_tag_update:
        :type force_tag_update:
        :param tags:
        :type tags:
        :param cleanup_days:
        :type cleanup_days:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        tags = self.__update_tag_value(tags=tags, tag_name='DaysCount', tag_value=str(cleanup_days))
        try:
            if self._policy == 's3_inactive':
                self._s3_client.put_bucket_tagging(Bucket=resource_id, Tagging={'TagSet': tags})
            elif self._policy == 'empty_roles':
                self._iam_client.tag_role(RoleName=resource_id, Tags=tags)
            elif self._policy in ('ip_unattached', 'unused_nat_gateway', 'zombie_snapshots', 'ebs_unattached', 'ec2_run'):
                self._ec2_client.create_tags(Resources=[resource_id], Tags=tags)
        except Exception as err:
            logger.info(f'Exception raised: {err}: {resource_id}')
