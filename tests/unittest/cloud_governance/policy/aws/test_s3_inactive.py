import tempfile

import boto3
from moto import mock_s3, mock_ec2

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.clouds.aws.utils.common_methods import get_tag_value_from_tags
from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.aws.s3_inactive import S3Inactive
from tests.unittest.configs import DRY_RUN_YES, AWS_DEFAULT_REGION, TEST_USER_NAME, CURRENT_DATE, DRY_RUN_NO, \
    DEFAULT_AMI_ID, INSTANCE_TYPE_T2_MICRO


@mock_ec2
@mock_s3
def test_s3_inactive():
    """
    This method tests lists empty buckets
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 's3_inactive'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}]
    s3_client = boto3.client('s3', region_name=AWS_DEFAULT_REGION)
    s3_client.create_bucket(Bucket=TEST_USER_NAME, CreateBucketConfiguration={'LocationConstraint': AWS_DEFAULT_REGION})
    s3_client.put_bucket_tagging(Bucket=TEST_USER_NAME, Tagging={'TagSet': tags})
    s3_operations = S3Operations(region_name=AWS_DEFAULT_REGION)
    # run s3_inactive
    s3_inactive = S3Inactive()
    response = s3_inactive.run()
    assert len(s3_operations.list_buckets()) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 1
    assert get_tag_value_from_tags(tags=s3_operations.get_bucket_tagging(bucket_name=TEST_USER_NAME),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@1"


@mock_ec2
@mock_s3
def test_s3_inactive_dry_run_yes():
    """
    This method tests collects empty buckets  on dry_run=yes
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_YES
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 's3_inactive'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    s3_client = boto3.client('s3', region_name=AWS_DEFAULT_REGION)
    s3_client.create_bucket(Bucket=TEST_USER_NAME, CreateBucketConfiguration={'LocationConstraint': AWS_DEFAULT_REGION})
    s3_client.put_bucket_tagging(Bucket=TEST_USER_NAME, Tagging={'TagSet': tags})
    s3_operations = S3Operations(region_name=AWS_DEFAULT_REGION)
    # run s3_inactive
    s3_inactive = S3Inactive()
    response = s3_inactive.run()
    assert len(s3_operations.list_buckets()) == 1
    assert len(response) == 1
    assert response[0]['CleanUpDays'] == 0
    assert get_tag_value_from_tags(tags=s3_operations.get_bucket_tagging(bucket_name=TEST_USER_NAME),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"


@mock_ec2
@mock_s3
def test_s3_inactive_delete():
    """
    This method tests delete s3 empty bucket
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 's3_inactive'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    s3_client = boto3.client('s3', region_name=AWS_DEFAULT_REGION)
    s3_client.create_bucket(Bucket=TEST_USER_NAME, CreateBucketConfiguration={'LocationConstraint': AWS_DEFAULT_REGION})
    s3_client.put_bucket_tagging(Bucket=TEST_USER_NAME, Tagging={'TagSet': tags})
    s3_operations = S3Operations(region_name=AWS_DEFAULT_REGION)
    # run s3_inactive
    s3_inactive = S3Inactive()
    response = s3_inactive.run()
    assert len(s3_operations.list_buckets()) == 0
    assert len(response) == 1


@mock_ec2
@mock_s3
def test_s3_inactive_skip():
    """
    This method tests skip delete of the s3 empty bucket
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 's3_inactive'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'},
            {'Key': 'policy', 'Value': 'not-delete'}]
    s3_client = boto3.client('s3', region_name=AWS_DEFAULT_REGION)
    s3_client.create_bucket(Bucket=TEST_USER_NAME, CreateBucketConfiguration={'LocationConstraint': AWS_DEFAULT_REGION})
    s3_client.put_bucket_tagging(Bucket=TEST_USER_NAME, Tagging={'TagSet': tags})
    s3_operations = S3Operations(region_name=AWS_DEFAULT_REGION)
    # run s3_inactive
    s3_inactive = S3Inactive()
    response = s3_inactive.run()
    assert len(s3_operations.list_buckets()) == 1
    assert len(response) == 0
    assert get_tag_value_from_tags(tags=s3_operations.get_bucket_tagging(bucket_name=TEST_USER_NAME),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"


@mock_ec2
@mock_s3
def test_s3_inactive_contains_cluster_tag():
    """
    This method tests s3 bucket having the live cluster
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 's3_inactive'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'},
            {'Key': 'policy', 'Value': 'not-delete'},
            {'Key': 'kubernetes.io/cluster/test-zombie-cluster', 'Value': f'owned'}]
    s3_client = boto3.client('s3', region_name=AWS_DEFAULT_REGION)
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                             MaxCount=1, MinCount=1, TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    s3_client.create_bucket(Bucket=TEST_USER_NAME, CreateBucketConfiguration={'LocationConstraint': AWS_DEFAULT_REGION})
    s3_client.put_bucket_tagging(Bucket=TEST_USER_NAME, Tagging={'TagSet': tags})
    s3_operations = S3Operations(region_name=AWS_DEFAULT_REGION)
    # run s3_inactive
    s3_inactive = S3Inactive()
    response = s3_inactive.run()
    assert len(s3_operations.list_buckets()) == 1
    assert len(response) == 0
    assert get_tag_value_from_tags(tags=s3_operations.get_bucket_tagging(bucket_name=TEST_USER_NAME),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"


@mock_ec2
@mock_s3
def test_s3_inactive_contains_data():
    """
    This method tests s3 bucket having the live cluster
    @return:
    """
    environment_variables.environment_variables_dict['dry_run'] = DRY_RUN_NO
    environment_variables.environment_variables_dict['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
    environment_variables.environment_variables_dict['policy'] = 's3_inactive'
    tags = [{'Key': 'User', 'Value': TEST_USER_NAME}, {'Key': 'DaysCount', 'Value': f'{CURRENT_DATE}@7'}]
    s3_client = boto3.client('s3', region_name=AWS_DEFAULT_REGION)
    ec2_client = boto3.client('ec2', region_name=AWS_DEFAULT_REGION)
    ec2_client.run_instances(ImageId=DEFAULT_AMI_ID, InstanceType=INSTANCE_TYPE_T2_MICRO,
                             MaxCount=1, MinCount=1, TagSpecifications=[{'ResourceType': 'instance', 'Tags': tags}])
    s3_client.create_bucket(Bucket=TEST_USER_NAME, CreateBucketConfiguration={'LocationConstraint': AWS_DEFAULT_REGION})
    s3_client.put_bucket_tagging(Bucket=TEST_USER_NAME, Tagging={'TagSet': tags})
    s3_operations = S3Operations(region_name=AWS_DEFAULT_REGION)
    with tempfile.NamedTemporaryFile(suffix='.txt') as file:
        file_name = file.name.split('/')[-1]
        s3_operations.upload_file(file_name_path=file.name, key='test', bucket=TEST_USER_NAME, upload_file=file_name)
    # run s3_inactive
    s3_inactive = S3Inactive()
    response = s3_inactive.run()
    assert len(s3_operations.list_buckets()) == 1
    assert len(response) == 0
    assert get_tag_value_from_tags(tags=s3_operations.get_bucket_tagging(bucket_name=TEST_USER_NAME),
                                   tag_name='DaysCount') == f"{CURRENT_DATE}@0"
