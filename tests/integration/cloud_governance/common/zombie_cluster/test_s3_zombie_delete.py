import uuid
from datetime import datetime

import boto3

from cloud_governance.common.aws.s3.s3_operations import S3Operations
from cloud_governance.zombie_cluster.zombie_cluster_resouces import ZombieClusterResources

short_random_id = str(uuid.uuid1())[0:4]
BUCKET_NAME = f'integration-test-ocp-{short_random_id}-image-registry'


def create_s3_bucket():
    """
    This method returns the Object S3 client and create a test bucket
    :return:
    """
    s3_resource = boto3.resource('s3', region_name='us-east-1')
    s3_resource.create_bucket(Bucket=BUCKET_NAME)
    bucket_tagging = s3_resource.BucketTagging(BUCKET_NAME)
    tags = [{'Key': 'kubernetes.io/cluster/integration-test-cluster',
             'Value': 'Owned'
             }, {
                'Key': 'Owner',
                'Value': 'integration'
            }, {'Key': 'CreateTime', 'Value': str(datetime.today())}]
    bucket_tagging.put(Tagging={
        'TagSet': tags
    })


def test_s3_zombie_bucket_exists():
    """
    This method checks any zombie s3 buckets are exists are not
    :return:
    """
    create_s3_bucket()
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/integration-test-cluster',
                                                      resource_name='zombie_cluster_s3_bucket')

    assert len(zombie_cluster_resources.zombie_cluster_s3_bucket()) >= 1


def test_s3_zombie_bucket_delete():
    """
    This method delete the s3 zombie bucket
    :return:
    """
    zombie_cluster_resources = ZombieClusterResources(cluster_prefix='kubernetes.io/cluster/', delete=True,
                                                      cluster_tag='kubernetes.io/cluster/integration-test-cluster',
                                                      resource_name='zombie_cluster_s3_bucket')

    zombie_cluster_resources.zombie_cluster_s3_bucket()
    s3_operations = S3Operations(region_name='us-east-1')
    assert not s3_operations.find_bucket(bucket_name=BUCKET_NAME)






