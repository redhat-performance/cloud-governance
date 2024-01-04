import json
from typing import Union

from cloud_governance.common.clouds.aws.s3.s3_operations import S3Operations
from cloud_governance.common.utils.json_datetime_encoder import JsonDateTimeEncoder
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.policy.policy_runners.common.abstract_upload import AbstractUpload


class UploadS3(AbstractUpload):

    def __init__(self):
        super().__init__()
        self._s3operations = S3Operations(region_name=self._region)

    def upload(self, data: Union[list, dict]):
        """
        This method upload data to S3
        :param data:
        :type data:
        :return:
        :rtype:
        """
        if self._policy_output:
            data = json.dumps(data, cls=JsonDateTimeEncoder)
            self._s3operations.save_results_to_s3(policy=self._policy.replace('_', '-'),
                                                  policy_output=self._policy_output, policy_result=data)
            logger.info(f"Uploaded the data s3 Bucket: {self._policy_output}")
