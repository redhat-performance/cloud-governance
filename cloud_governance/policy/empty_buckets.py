import operator
from operator import ge

from botocore.exceptions import ClientError

from cloud_governance.common.logger.init_logger import logger
from cloud_governance.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy


class EmptyBuckets(NonClusterZombiePolicy):

    BUCKET_DAYS = 7

    def __init__(self):
        super().__init__()

    def run(self):
        """
        This method return all Empty buckets and delete if dry_run no
        @return:
        """
        return self.__delete_empty_bucket(bucket_days=self.BUCKET_DAYS, sign=ge)

    def __delete_empty_bucket(self, bucket_days: int, sign: operator = ge):
        """
        This method delete the empty bucket morethan 30 days
        @param bucket_days:
        @param sign:
        @return:
        """
        zombie_buckets = {}
        zombie_buckets_data = []
        buckets = self._s3_client.list_buckets()['Buckets']
        active_clusters = self._zombie_cluster.all_cluster_instance()
        for bucket in buckets:
            age = self._calculate_days(create_date=bucket.get('CreationDate'))
            if sign(age, bucket_days):
                try:
                    bucket_data = self._s3_client.list_objects_v2(Bucket=bucket.get('Name'))
                    if not bucket_data.get('Contents'):
                        try:
                            bucket_tags = self._s3_client.get_bucket_tagging(Bucket=bucket.get('Name'))
                            tags = bucket_tags.get('TagSet')
                        except ClientError:
                            tags = []
                        if not self._check_live_cluster_tag(tags, active_clusters.values()):
                            zombie_buckets[bucket.get('Name')] = tags
                            zombie_buckets_data.append([bucket.get('Name'),
                                                        str(bucket.get('CreationDate')),
                                                        str(age),
                                                        self._get_policy_value(tags=tags)
                                                        ])
                except Exception as err:
                    logger.info(f'{err}, {bucket.get("Name")}')
        if self._dry_run == 'no':
            for zombie_bucket, tags in zombie_buckets.items():
                if self._get_policy_value(tags=tags) != 'NOTDELETE':
                    try:
                        self._s3_client.delete_bucket(Bucket=zombie_bucket)
                        logger.info(f'Bucket is deleted {zombie_bucket}')
                    except Exception as err:
                        logger.info(f'Exception raised: {err}: {zombie_bucket}')
        return zombie_buckets_data
