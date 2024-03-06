from datetime import datetime, timedelta

from google.cloud import bigquery
from typeguard import typechecked

from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables

import google.auth


class GoogleAccount:
    """
    This class is for Google account operations
    """

    RETRIES = 3

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__client = None
        if self.__environment_variables_dict.get('GOOGLE_APPLICATION_CREDENTIALS'):
            self.__creds, _ = google.auth.default()
            self.__client = bigquery.Client()

    @typechecked()
    @logger_time_stamp
    def get_dates(self, diff_days: int):
        """
        This method returns the start and end date
        :param diff_days:
        :return:
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=diff_days)
        return start_date, end_date

    @typechecked()
    @logger_time_stamp
    def query_list(self, queries: list):
        """
        This method returns the query results that scans from the BigQuery
        :param queries:
        :return:
        """
        queries_results = []
        for idx, query in enumerate(queries):
            parent_job = self.__client.query(query)
            results = parent_job.result()  # Waits for job to complete.
            query_rows = []
            for row in results:
                query_rows.append(dict(row))
            queries_results.append(query_rows)
        return queries_results
