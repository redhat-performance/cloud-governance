import operator
from operator import ge

import boto3
from botocore.exceptions import ClientError

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EmptyBuckets(NonClusterZombiePolicy):
    """
    This class sends an alert mail for empty bucket to the user after 4 days and delete after 7 days.
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method return all Empty buckets and delete if dry_run no
        @return:
        """
        return self.__delete_empty_bucket()

    def __delete_empty_bucket(self):
        """
        This method delete the empty bucket more than 7 days
        @return:
        """
        empty_buckets = []
        buckets = self._s3_client.list_buckets()['Buckets']
        for bucket in buckets:
            bucket_empty = False
            empty_days = 0
            bucket_name = bucket.get('Name')
            try:
                try:
                    bucket_tags = self._s3_client.get_bucket_tagging(Bucket=bucket_name)
                    tags = bucket_tags.get('TagSet')
                except ClientError:
                    tags = []
                bucket_data = self._s3_client.list_objects_v2(Bucket=bucket_name)
                if not bucket_data.get('Contents'):
                    if not self._check_cluster_tag(tags=tags):
                        if not self._get_tag_name_from_tags(tags=tags, tag_name='Name'):
                            tags.append({'Key': 'Name', 'Value': bucket_name})
                        empty_days = self._get_resource_last_used_days(tags=tags)
                        bucket_empty = True
                        if not self._get_tag_name_from_tags(tags=tags, tag_name='User'):
                            region = self._s3_client.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                            self._cloudtrail.set_cloudtrail(region_name=region)
                        empty_bucket = self._check_resource_and_delete(resource_name='S3 Bucket', resource_id='Name', resource_type='CreateBucket', resource=bucket, empty_days=empty_days, days_to_delete_resource=self.DAYS_TO_DELETE_RESOURCE, tags=tags)
                        if empty_bucket:
                            empty_buckets.append([bucket.get('Name'), self._get_tag_name_from_tags(tags=tags, tag_name='User'), str(bucket.get('CreationDate')), str(empty_days), self._get_policy_value(tags=tags)])
                else:
                    empty_days = 0
                self._update_resource_tags(resource_id=bucket_name, tags=tags, left_out_days=empty_days, resource_left_out=bucket_empty)
            except Exception as err:
                logger.info(f'{err}, {bucket.get("Name")}')
        return empty_buckets
