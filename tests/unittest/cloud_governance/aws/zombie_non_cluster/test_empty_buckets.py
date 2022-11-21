import os

import boto3
from moto import mock_s3, mock_ec2

from cloud_governance.aws.zombie_non_cluster.run_zombie_non_cluster_policies import NonClusterZombiePolicy

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
@mock_s3
def test_s3_inactive():
    """
    This method tests delete of empty buckets
    @return:
    """
    os.environ['policy'] = 's3_inactive'
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket='cloud-governance-test-s3-empty-delete',
                            CreateBucketConfiguration={'LocationConstraint': 'us-east-2'})
    s3_inactive = NonClusterZombiePolicy()
    s3_inactive.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    s3_inactive._check_resource_and_delete(resource_name='S3 Bucket',
                                           resource_id='Name',
                                           resource_type='CreateBucket',
                                           resource=s3_client.list_buckets()['Buckets'][0],
                                           empty_days=0,
                                           days_to_delete_resource=0)
    buckets = s3_client.list_buckets()['Buckets']
    assert len(buckets) == 0


@mock_ec2
@mock_s3
def test_s3_inactive_not_delete():
    """
    This method tests not delete of empty buckets, if policy=NOT_DELETE
    @return:
    """
    os.environ['policy'] = 's3_inactive'
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestEmptyBucket'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'notdelete'}
    ]
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket='cloud-governance-test-s3-empty-delete',
                            CreateBucketConfiguration={'LocationConstraint': 'us-east-2'})
    s3_client.put_bucket_tagging(Bucket='cloud-governance-test-s3-empty-delete', Tagging={'TagSet': tags})
    s3_inactive = NonClusterZombiePolicy()
    s3_inactive.DAYS_TO_TRIGGER_RESOURCE_MAIL = -1
    s3_inactive._check_resource_and_delete(resource_name='S3 Bucket',
                                           resource_id='Name',
                                           resource_type='CreateBucket',
                                           resource=s3_client.list_buckets()['Buckets'][0],
                                           empty_days=0,
                                           days_to_delete_resource=0,
                                           tags=tags)
    buckets = s3_client.list_buckets()['Buckets']
    assert len(buckets) == 1
