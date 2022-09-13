
import tempfile
from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from tests.integration.cloud_governance.test_environment_variables import *
from uuid import uuid4

BUCKET = test_environment_variable.get("BUCKET", '')
REGION = test_environment_variable.get("REGION", '')
KEY_TEST = test_environment_variable.get("KEY_TEST", '')
uuid = str(uuid4())
TEMP_FILE = f'cloud-governance-test-{uuid}.txt'


def get_s3_client_object():
    """
    Create Object of S3 resource
    """
    return S3Operations(region_name=REGION)


def test_s3_file_upload():
    """
    This method upload file to s3
    """
    with tempfile.TemporaryDirectory() as temp_local_directory:
        with open(os.path.join(temp_local_directory, TEMP_FILE), 'w') as f:
            f.write('testing file upload')
        s3 = get_s3_client_object()
        s3.upload_file(file_name_path=os.path.join(temp_local_directory, TEMP_FILE),
                       bucket=BUCKET,
                       key=KEY_TEST,
                       upload_file=TEMP_FILE)
        assert s3.file_exist(bucket=BUCKET, key=KEY_TEST, file_name=TEMP_FILE)


def test_s3_file_download():
    """
    This method download file from s3
    """
    with tempfile.TemporaryDirectory() as temp_local_directory:
        s3 = get_s3_client_object()
        s3.download_file(bucket=BUCKET, key=KEY_TEST, download_file=TEMP_FILE,
                         file_name_path=os.path.join(temp_local_directory, TEMP_FILE))
        assert os.path.exists(os.path.join(temp_local_directory, TEMP_FILE))


def test_s3_delete_file():
    """
    This method delete file from s3
    """
    s3 = get_s3_client_object()
    s3.delete_file(bucket=BUCKET, key=KEY_TEST, file_name=TEMP_FILE)
    assert not s3.file_exist(bucket=BUCKET, key=KEY_TEST, file_name=TEMP_FILE)
