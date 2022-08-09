import os
from operator import le

import boto3
from moto import mock_s3, mock_ec2

from cloud_governance.policy.empty_buckets import EmptyBuckets

os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['dry_run'] = 'no'


@mock_ec2
@mock_s3
def test_empty_buckets():
    """
    This method tests delete of empty buckets
    @return:
    """
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket='cloud-governance-test-s3-empty-delete', CreateBucketConfiguration={'LocationConstraint': 'us-east-2'})
    empty_buckets = EmptyBuckets()
    empty_buckets._EmptyBuckets__delete_empty_bucket(sign=le, bucket_days=0)
    buckets = s3_client.list_buckets()['Buckets']
    assert len(buckets) == 0


@mock_ec2
@mock_s3
def test_empty_buckets_not_delete():
    """
    This method tests not delete of empty buckets, if policy=NOT_DELETE
    @return:
    """
    tags = [
        {'Key': 'Name', 'Value': 'CloudGovernanceTestEmptyBucket'},
        {'Key': 'Owner', 'Value': 'CloudGovernance'},
        {'Key': 'policy', 'Value': 'notdelete'}
    ]
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket='cloud-governance-test-s3-empty-delete', CreateBucketConfiguration={'LocationConstraint': 'us-east-2'})
    s3_client.put_bucket_tagging(Bucket='cloud-governance-test-s3-empty-delete', Tagging={'TagSet': tags})
    empty_buckets = EmptyBuckets()
    empty_buckets._EmptyBuckets__delete_empty_bucket(sign=le, bucket_days=0)
    buckets = s3_client.list_buckets()['Buckets']
    assert len(buckets) == 1
