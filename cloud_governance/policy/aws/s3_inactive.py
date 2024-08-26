
from cloud_governance.policy.helpers.aws.aws_policy_operations import AWSPolicyOperations


class S3Inactive(AWSPolicyOperations):
    """
    This class sends an alert mail for empty bucket to the user after 4 days and delete after 7 days.
    """

    RESOURCE_ACTION = 'Delete'

    def __init__(self):
        super().__init__()
        self.__global_active_cluster_ids = self._get_global_active_cluster_ids()

    def run_policy_operations(self):
        """
        This method returns all Empty buckets
        :return:
        :rtype:
        """
        empty_buckets = []
        s3_buckets = self._s3operations.list_buckets()
        for bucket in s3_buckets:
            bucket_name = bucket.get('Name')
            tags = self._s3operations.get_bucket_tagging(bucket_name)
            cleanup_result = False
            cluster_tag = self._get_cluster_tag(tags=tags)
            cleanup_days = 0
            s3_contents = self._s3operations.get_bucket_contents(bucket_name=bucket_name)
            if (cluster_tag not in self.__global_active_cluster_ids and len(s3_contents) == 0
                    and self.get_skip_policy_value(tags=tags) not in ('NOTDELETE', 'SKIP')):
                cleanup_days = self.get_clean_up_days_count(tags=tags)
                cleanup_result = self.verify_and_delete_resource(resource_id=bucket_name, tags=tags,
                                                                 clean_up_days=cleanup_days)
                region = self._s3operations.get_bucket_location(bucket_name=bucket_name)
                resource_data = self._get_es_schema(resource_id=bucket_name,
                                                    user=self.get_tag_name_from_tags(tags=tags, tag_name='User'),
                                                    skip_policy=self.get_skip_policy_value(tags=tags),
                                                    cleanup_days=cleanup_days,
                                                    dry_run=self._dry_run,
                                                    name=bucket_name,
                                                    region=region,
                                                    cleanup_result=str(cleanup_result),
                                                    resource_action=self.RESOURCE_ACTION,
                                                    cloud_name=self._cloud_name,
                                                    resource_type='EmptyBucket',
                                                    resource_state="Empty",
                                                    unit_price=0)
                empty_buckets.append(resource_data)
            if not cleanup_result:
                self.update_resource_day_count_tag(resource_id=bucket_name, cleanup_days=cleanup_days, tags=tags)

        return empty_buckets
