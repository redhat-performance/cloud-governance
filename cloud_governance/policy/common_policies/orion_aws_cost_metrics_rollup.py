from datetime import datetime, timezone, date, timedelta
import time

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class OrionAwsCostMetricsRollup:
    """
    Rolls up daily AWS Cost Explorer data for the perf-scale AWS accounts into
    one document per account per day, so Orion (change-point regression
    detection) can watch each account's daily spend as its own time series.

    Source is the shared AWS cost-explorer index, which stores the SAME total
    spend broken out ~28 ways (15 cost_explorer_tags dimensions x 2
    savings_plan copies) - each combination a complete partition of the same
    total. A query that doesn't pin exactly one (tag, savings_plan) pair
    over-counts accordingly; see CANONICAL_TAG/CANONICAL_SAVINGS_PLAN.

    Writes into the same destination index as OrionCostMetricsRollup
    (cloud-governance-orion-cost-metrics-index). That index therefore holds
    two unrelated series distinguished purely by the 'account' field's naming
    convention: 'CC<number>' is the other rollup's cost-center-month entity,
    a plain AWS account name (PSAP/PERFSCALE/PERF-DEPT) is this rollup's
    account-day entity. Reuse was a deliberate choice (verified no schema or
    query-scoping risk - Orion's metadata filter is enforced server-side
    per account before any metric is read) over provisioning a second index
    for what the two series have semantically in common (a daily/monthly
    cost total) rather than how they differ.
    """

    # Read from explicitly, rather than the shared 'es_index' env var, so the
    # source index this rollup reads from is unaffected by whatever es_index a
    # given invocation happens to default to.
    SOURCE_ES_INDEX = 'cloud-governance-cost-explorer-perf-global-cost'
    # The only 3 accounts with real data in the source index (a legacy
    # duplicate spelling, PERF-SCALE, also appears but went stale in
    # 2026-02 - deliberately excluded by not including it here).
    ACCOUNTS = ['PSAP', 'PERFSCALE', 'PERF-DEPT']
    # The source index holds every (cost_explorer_tags x savings_plan)
    # combination as a separate copy of the same total spend - exactly one
    # pair must be pinned, or totals over-count ~15x / ~2x. purchasetype is
    # AWS-defined (immune to internal tagging-policy drift, unlike
    # project/owner/etc.) and has the fewest docs of the non-undercounting
    # dimensions. savings_plan=include (not exclude) matters beyond
    # consistency: exclude drops Savings-Plan rows entirely, which were a
    # real share of spend in 2022-23 and could be again.
    CANONICAL_TAG = 'purchasetype'
    CANONICAL_SAVINGS_PLAN = 'include'
    # AWS Cost Explorer re-fetches and upserts a rolling 31-day window on
    # every source-policy run, so the most recent few days are provisional
    # and under-report until they settle - confirmed live (every account's
    # reported cost roughly halves on the most recent day). Only roll up
    # through (today - LAG_DAYS) to avoid treating a provisional day as a
    # real drop.
    LAG_DAYS = 3
    # Re-roll this many trailing days on every incremental run (not just new
    # days) so late corrections AWS makes within its own 31-day re-fetch
    # window are picked up here too.
    ROLLING_WINDOW_DAYS = 31

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__elastic_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port) if self.__es_host else None
        # Defaults to the same index OrionCostMetricsRollup writes to (see
        # class docstring) but is independently overridable, so the two
        # rollups' destinations can never be coupled by a shared env var.
        self.__destination_es_index = self.__environment_variables_dict.get('orion_aws_cost_es_index', 'cloud-governance-orion-cost-metrics-index')
        self.__custom_start_date = self.__environment_variables_dict.get('orion_aws_cost_rollup_start_date', '')
        self.__custom_end_date = self.__environment_variables_dict.get('orion_aws_cost_rollup_end_date', '')

    @staticmethod
    def __today():
        return datetime.now(timezone.utc).date()

    @classmethod
    def __trailing_window(cls):
        """
        Return (start, end) date strings for the trailing ROLLING_WINDOW_DAYS-day
        window ending LAG_DAYS days before today - the incremental mode run
        daily in production, which re-processes the recent past on every run
        so late AWS corrections land.
        """
        end = cls.__today() - timedelta(days=cls.LAG_DAYS)
        start = end - timedelta(days=cls.ROLLING_WINDOW_DAYS - 1)
        return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

    @classmethod
    def __clamp_end_date(cls, end_date: str) -> str:
        """
        Clamp a requested end_date so it never includes provisional (not yet
        settled) days, regardless of what a manual backfill asks for.
        @param end_date: requested end date string (YYYY-MM-DD)
        @return: end_date, or (today - LAG_DAYS) if end_date is later than that
        """
        latest_safe = (cls.__today() - timedelta(days=cls.LAG_DAYS)).strftime('%Y-%m-%d')
        return min(end_date, latest_safe)

    def __split_date_range_by_month(self, start_date: str, end_date: str):
        """
        Split a date range into monthly (start, end) string chunks, to avoid
        querying ES with an unbounded date range and ensure incremental progress.
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
        Build the day/account spend aggregation query for a date range.

        Filters to the 3 tracked accounts and pins exactly one
        (tag, savings_plan) pair - see CANONICAL_TAG/CANONICAL_SAVINGS_PLAN -
        to avoid the source index's ~28x duplication.
        @param start_date: Start date string (YYYY-MM-DD)
        @param end_date: End date string (YYYY-MM-DD)
        @return: ES query dict
        """
        return {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"terms": {"account.keyword": self.ACCOUNTS}},
                        {"term": {"tag.keyword": self.CANONICAL_TAG}},
                        {"term": {"savings_plan.keyword": self.CANONICAL_SAVINGS_PLAN}},
                        {"range": {"timestamp": {"gte": start_date, "lte": end_date, "format": "yyyy-MM-dd"}}}
                    ]
                }
            },
            "aggs": {
                "by_day": {
                    "date_histogram": {"field": "timestamp", "calendar_interval": "day", "format": "yyyy-MM-dd"},
                    "aggs": {
                        "by_account": {
                            "terms": {"field": "account.keyword", "size": len(self.ACCOUNTS)},
                            "aggs": {"spend": {"sum": {"field": "Cost"}}}
                        }
                    }
                }
            }
        }

    def __parse_response(self, response: dict):
        """
        Walk the day -> account aggregation buckets and build one rollup
        document per account per day present in the response. A day with no
        matching docs for a given account produces no bucket (and so no
        document) for that account - Orion builds its series from whichever
        documents exist, so a gap is simply a missing point, not a zero.
        @param response: the 'aggregations' dict returned by post_query(result_agg=True)
        @return: list of rollup documents
        """
        documents = []
        if not response or 'by_day' not in response:
            return documents

        for day_bucket in response.get('by_day', {}).get('buckets', []):
            day = day_bucket.get('key_as_string', '')[:10]
            if not day:
                continue
            for account_bucket in day_bucket.get('by_account', {}).get('buckets', []):
                account = account_bucket.get('key')
                if account not in self.ACCOUNTS:
                    continue
                spend = account_bucket.get('spend', {}).get('value') or 0
                documents.append({
                    'account': account,
                    'timestamp': f'{day}T00:00:00Z',
                    'total_cost': round(spend),
                    'uuid': f'{account}-{day}',
                })
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
        Query and upsert rollup documents for a date range.
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
        Roll up per-account daily AWS spend into one document per account per day.

        If start_date/end_date are given (directly, or via the
        orion_aws_cost_rollup_start_date/orion_aws_cost_rollup_end_date env
        vars), backfills that range (clamped to exclude provisional days).
        Otherwise, re-rolls the trailing ROLLING_WINDOW_DAYS-day window ending
        LAG_DAYS days before today - the incremental mode run daily in
        production, which keeps recently-settled days fresh as AWS's own
        corrections land.
        @param start_date: Optional start date string (YYYY-MM-DD)
        @param end_date: Optional end date string (YYYY-MM-DD)
        @return: dict summarizing what was written
        """
        if not self.__elastic_operations:
            logger.warning('ES not configured, skipping Orion AWS cost metrics rollup')
            return {'status': 'no_upload', 'message': 'ES not configured'}

        # Separate direct input from configured defaults
        # If either direct boundary is provided, both must come exclusively from direct (don't mix with config)
        if start_date is not None or end_date is not None:
            if bool(start_date) != bool(end_date):
                logger.warning(f'Ignoring partial date range (start_date={start_date}, end_date={end_date}); both must be provided together. Falling back to incremental mode.')
                start_date = ''
                end_date = ''
        else:
            start_date = self.__custom_start_date
            end_date = self.__custom_end_date
            if bool(start_date) != bool(end_date):
                logger.warning(f'Ignoring partial date range from config (start_date={start_date}, end_date={end_date}); both must be set to backfill. Falling back to incremental mode.')
                start_date = ''
                end_date = ''

        if start_date and end_date:
            end_date = self.__clamp_end_date(end_date)
            logger.info(f'Backfilling Orion AWS cost metrics rollup from {start_date} to {end_date}')
            monthly_ranges = self.__split_date_range_by_month(start_date, end_date)
            total_documents = 0
            for i, (month_start, month_end) in enumerate(monthly_ranges, 1):
                logger.info(f'Processing month {i}/{len(monthly_ranges)}: {month_start} to {month_end}')
                total_documents += self.__process_date_range(month_start, month_end)
                if i < len(monthly_ranges):
                    time.sleep(0.5)
            logger.info(f'Orion AWS cost metrics rollup backfill complete: {total_documents} documents written')
            return {'status': 'success', 'documents_written': total_documents, 'start_date': start_date, 'end_date': end_date}

        window_start, window_end = self.__trailing_window()
        logger.info(f'Running incremental Orion AWS cost metrics rollup for {window_start} to {window_end}')
        total_documents = self.__process_date_range(window_start, window_end)
        logger.info(f'Orion AWS cost metrics rollup complete for {window_start} to {window_end}: {total_documents} documents written')
        return {'status': 'success', 'documents_written': total_documents, 'start_date': window_start, 'end_date': window_end}
