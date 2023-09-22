import typeguard
from pyathena import connect
from pyathena.pandas.cursor import PandasCursor

from cloud_governance.common.clouds.aws.athena.abstract_athena_operations import AbstractAthenaOperations
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp


class PyAthenaOperations(AbstractAthenaOperations):

    def __init__(self, aws_access_key_id: str = None, aws_secret_access_key: str = None):
        super().__init__()
        if aws_secret_access_key and aws_secret_access_key:
            self.conn = connect(s3_staging_dir=self._get_s3_path(), region_name="us-east-1",
                                cursor_class=PandasCursor, aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key).cursor()
        else:
            self.conn = connect(s3_staging_dir=self._get_s3_path(), region_name="us-east-1",
                                cursor_class=PandasCursor).cursor()

    @typeguard.typechecked
    @logger_time_stamp
    def execute_query(self, query_string: str) -> list:
        """
        This method returns list of dicts of athena results
        :param query_string:
        :return:
        """
        try:
            result_set = self.conn.execute(query_string).as_pandas()
            return result_set.to_dict(orient='records')
        except Exception as err:
            raise err
