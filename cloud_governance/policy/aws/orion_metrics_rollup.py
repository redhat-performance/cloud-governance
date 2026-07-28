from datetime import datetime, timezone, date, timedelta
import time

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class OrionMetricsRollup:
    """
    Rolls up per-resource policy execution data from the policy ES index into
    one document per account per day, for a fixed set of tracked policies, so
    Orion (change-point regression detection) can watch each metric as its own
    time series.
    """

    # Read from explicitly, rather than the shared 'es_index' env var: for any
    # policy in cost_policies (this one included), that var defaults to the
    # cost-billing index, not the policy index this rollup needs to read from.
    SOURCE_ES_INDEX = 'cloud-governance-policy-es-index'
    # Per-policy resource counts are restricted to these. monitored_policies_savings
    # is NOT restricted to these - see __build_query for why.
    TRACKED_POLICIES = ['zombie_cluster_resource', 's3_inactive', 'ec2_stop', 'unused_access_key', 'delete_access_key']

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__elastic_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port) if self.__es_host else None
        self.__destination_es_index = self.__environment_variables_dict.get('orion_metrics_es_index', 'cloud-governance-orion-metrics-index')
        self.__custom_start_date = self.__environment_variables_dict.get('orion_rollup_start_date', '')
        self.__custom_end_date = self.__environment_variables_dict.get('orion_rollup_end_date', '')

    def __split_date_range_by_month(self, start_date: str, end_date: str):
        """
        Split a date range into monthly (start, end) string chunks, to avoid
        querying ES with an unbounded date range.
        @param start_date: Start date string (YYYY-MM-DD)
        @param end_date: End date string (YYYY-MM-DD)
        @return: list of (month_start, month_end) string tuples
        """
        if not start_date or not end_date:
            raise ValueError(f"Both start_date and end_date must be provided. Got: start_date={start_date}, end_date={end_date}")

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        monthly_ranges = []
        current_start = start

        while current_start <= end:
            if current_start.month == 12:
                current_end = date(current_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                current_end = date(current_start.year, current_start.month + 1, 1) - timedelta(days=1)
            if current_end > end:
                current_end = end
            monthly_ranges.append((current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d")))
            if current_end.month == 12:
                current_start = date(current_end.year + 1, 1, 1)
            else:
                current_start = date(current_end.year, current_end.month + 1, 1)

        return monthly_ranges

    def __build_query(self, start_date: str, end_date: str):
        """
        Build the account/day/policy aggregation query for a single date-range chunk.

        Deliberately does not filter by policy at the top level: none of the
        tracked policies populate TotalYearlySavings (confirmed against
        production data - they're risk/hygiene policies, not
        idle-resource-elimination policies), so monitored_policies_savings is
        summed across all policies for the account/day, while by_policy below
        restricts the per-policy counts to just the tracked set via 'include'.
        @param start_date: Start date string (YYYY-MM-DD)
        @param end_date: End date string (YYYY-MM-DD)
        @return: ES query dict
        """
        return {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"timestamp": {"gte": start_date, "lte": end_date, "format": "yyyy-MM-dd"}}}
                    ]
                }
            },
            "aggs": {
                "by_account": {
                    "terms": {"field": "account.keyword", "size": 1000},
                    "aggs": {
                        "by_day": {
                            "date_histogram": {"field": "timestamp", "calendar_interval": "day", "format": "yyyy-MM-dd"},
                            "aggs": {
                                "by_policy": {
                                    "terms": {"field": "policy.keyword", "include": self.TRACKED_POLICIES, "size": len(self.TRACKED_POLICIES)}
                                },
                                "total_savings": {
                                    "sum": {"field": "TotalYearlySavings", "missing": 0}
                                }
                            }
                        }
                    }
                }
            }
        }

    def __parse_response(self, response: dict):
        """
        Walk the account -> day aggregation buckets and build one rollup
        document per account per day.
        @param response: the 'aggregations' dict returned by post_query(result_agg=True)
        @return: list of rollup documents
        """
        documents = []
        if not response or 'by_account' not in response:
            return documents

        for account_bucket in response.get('by_account', {}).get('buckets', []):
            account = account_bucket.get('key')
            for day_bucket in account_bucket.get('by_day', {}).get('buckets', []):
                day = day_bucket.get('key_as_string', '')[:10]
                if not day:
                    continue
                document = {f'{policy}_count': 0 for policy in self.TRACKED_POLICIES}
                for policy_bucket in day_bucket.get('by_policy', {}).get('buckets', []):
                    policy_name = policy_bucket.get('key')
                    if policy_name in self.TRACKED_POLICIES:
                        document[f'{policy_name}_count'] = policy_bucket.get('doc_count', 0)
                savings = day_bucket.get('total_savings', {}).get('value') or 0
                document['monitored_policies_savings'] = round(savings)
                document['uuid'] = f'{account}-{day}'
                document['timestamp'] = f'{day}T00:00:00Z'
                document['account'] = account
                documents.append(document)
        return documents

    def __upsert_document(self, document: dict):
        """
        Create or update a single rollup document, keyed by its deterministic uuid.
        @param document: rollup document, must include a 'uuid' key
        """
        doc_id = document['uuid']
        try:
            if self.__elastic_operations.verify_elastic_index_doc_id(index=self.__destination_es_index, doc_id=doc_id):
                self.__elastic_operations.update_elasticsearch_index(
                    index=self.__destination_es_index,
                    id=doc_id,
                    metadata=document
                )
            else:
                self.__elastic_operations.upload_to_elasticsearch(
                    index=self.__destination_es_index,
                    data=document,
                    id=doc_id
                )
        except Exception as err:
            logger.warning(f"Update check failed for {doc_id}, trying create: {err}")
            self.__elastic_operations.upload_to_elasticsearch(
                index=self.__destination_es_index,
                data=document,
                id=doc_id
            )

    def __process_date_range(self, start_date: str, end_date: str):
        """
        Query and upsert rollup documents for a single date-range chunk.
        @param start_date: Start date string (YYYY-MM-DD)
        @param end_date: End date string (YYYY-MM-DD)
        @return: number of documents written
        """
        query = self.__build_query(start_date=start_date, end_date=end_date)
        response = self.__elastic_operations.post_query(
            query=query,
            es_index=self.SOURCE_ES_INDEX,
            result_agg=True
        )
        documents = self.__parse_response(response)
        for document in documents:
            self.__upsert_document(document)
        return len(documents)

    @logger_time_stamp
    def run(self, start_date: str = None, end_date: str = None):
        """
        Roll up per-resource policy data into one document per account per day.

        If start_date/end_date are given (directly, or via the
        orion_rollup_start_date/orion_rollup_end_date env vars), backfills that
        range, chunked by month. Otherwise, rolls up just the current UTC date
        - the daily incremental mode used in production, run right after that
        day's policy jobs complete.
        @param start_date: Optional start date string (YYYY-MM-DD)
        @param end_date: Optional end date string (YYYY-MM-DD)
        @return: dict summarizing what was written
        """
        if not self.__elastic_operations:
            logger.warning('ES not configured, skipping Orion metrics rollup')
            return {'status': 'no_upload', 'message': 'ES not configured'}

        if not start_date:
            start_date = self.__custom_start_date
        if not end_date:
            end_date = self.__custom_end_date

        if bool(start_date) != bool(end_date):
            logger.warning(f'Ignoring partial date range (start_date={start_date}, end_date={end_date}); both must be set to backfill. Falling back to daily mode.')

        if start_date and end_date:
            logger.info(f'Backfilling Orion metrics rollup from {start_date} to {end_date}')
            monthly_ranges = self.__split_date_range_by_month(start_date, end_date)
            total_documents = 0
            for i, (month_start, month_end) in enumerate(monthly_ranges, 1):
                logger.info(f'Processing month {i}/{len(monthly_ranges)}: {month_start} to {month_end}')
                total_documents += self.__process_date_range(month_start, month_end)
                if i < len(monthly_ranges):
                    time.sleep(0.5)
            logger.info(f'Orion metrics rollup backfill complete: {total_documents} documents written')
            return {'status': 'success', 'documents_written': total_documents, 'start_date': start_date, 'end_date': end_date}

        today = datetime.now(timezone.utc).date().strftime('%Y-%m-%d')
        logger.info(f'Running daily Orion metrics rollup for {today}')
        total_documents = self.__process_date_range(today, today)
        logger.info(f'Orion metrics rollup complete for {today}: {total_documents} documents written')
        return {'status': 'success', 'documents_written': total_documents, 'date': today}
