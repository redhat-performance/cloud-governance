import datetime

import boto3
from moto import mock_s3

from cloud_governance.main.environment_variables import environment_variables
from cloud_governance.policy.policy_runners.aws.upload_s3 import UploadS3


@mock_s3
def test_upload_s3_list():
    """
    This method tests the data to be uploaded to s3
    :return:
    :rtype:
    """
    bucket_name = "cloud_governance_unitest"
    s3_client = boto3.client('s3')
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'})
    environment_variables.environment_variables_dict["policy_output"] = f"s3://{bucket_name}/tests"

    data = [
        datetime.datetime.now(), "unitest", "cloud_governance"
    ]
    upload_s3 = UploadS3()
    upload_s3.upload(data=data)
    assert len(s3_client.list_objects_v2(Bucket=bucket_name).get('Contents')) == 1


@mock_s3
def test_upload_s3_dict():
    """
    This method tests the data to be uploaded to s3
    :return:
    :rtype:
    """
    bucket_name = "cloud_governance_unitest"
    s3_client = boto3.client('s3')
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'})
    environment_variables.environment_variables_dict["policy_output"] = f"s3://{bucket_name}/tests"

    data = {
        "timestamp": datetime.datetime.now(),
        "policy": "test_unitest",
        "runner": "cloud_governance",
        "results": [
            {"date": datetime.datetime.now()},
            {"ResourceId": bucket_name, "CreateDate": datetime.datetime.now().date()}
        ]
    }
    upload_s3 = UploadS3()
    upload_s3.upload(data=data)
    assert len(s3_client.list_objects_v2(Bucket=bucket_name).get('Contents')) == 1
