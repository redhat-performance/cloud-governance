import boto3
import typeguard

from cloud_governance.common.clouds.aws.athena.abstract_athena_operations import AbstractAthenaOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class BotoClientAthenaOperations(AbstractAthenaOperations):
    """
    This class performs the aws athena operations
    """

    def __init__(self):
        super().__init__()
        self.__athena_client = boto3.client('athena', region_name='us-east-1')

    @typeguard.typechecked
    @logger_time_stamp
    def execute_query(self, query_string: str):
        """
        This method executes the query and returns the s3_path, QueryExecutionId
        Limit: Continuously check the s3 bucket that file is created or not using the QueryExecutionId
        :param query_string:
        :return:
        """
        try:
            s3_path = self.__s3_results_path
            logger.debug(f"Query Output path: s3_path/{self.CURRENT_DATE}")
            result = self.__athena_client.start_query_execution(
                QueryString=query_string,
                ResultConfiguration={
                    "OutputLocation": s3_path,
                }
            )
            if result:
                bucket, key = self.__s3_results_path.replace("s3://", "").split('/')
                return {
                    'QueryExecutionId': result.get('QueryExecutionId'),
                    's3_key': s3_path,
                    's3_csv_path': f'{s3_path}/{result.get("QueryExecutionId")}.csv',
                    'bucket': bucket,
                    'key': f'{key}/{self.CURRENT_DATE}',
                    'file_name': f'{result.get("QueryExecutionId")}.csv'
                }
        except Exception as err:
            logger.error(err)
        return {}
