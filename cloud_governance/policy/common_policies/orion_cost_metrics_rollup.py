from datetime import datetime, timezone, date
import time

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class OrionCostMetricsRollup:
    """
    Rolls up multi-cloud monthly billing data for a single cost center into one
    document per month, so Orion (change-point regression detection) can watch
    the cost center's total spend - and each cloud's spend - as its own time
    series.

    Source is the shared multi-cloud billing index, which stores one row per
    account per month per cloud, fed daily by the per-cloud cost-report jobs.
    """

    # Read from explicitly, rather than the shared 'es_index' env var, so the
    # source index this rollup reads from is unaffected by whatever es_index a
    # given invocation happens to default to.
    SOURCE_ES_INDEX = 'cloud-governance-clouds-billing-reports'
    # Only these policies carry real per-account monthly spend in the source
    # index (AWS via payer billings, the other clouds via cost billing reports).
    # spot_savings_analysis and cloudability_cost_reports rows are excluded -
    # they are different metrics and would otherwise double-count / distort spend.
    SPEND_POLICIES = ['cost_explorer_payer_billings', 'cost_billing_reports']
    # Map the source CloudName values onto the per-cloud metric field names.
    # AWSCLOUD is a stray legacy label folded into aws_cost so nothing is lost.
    CLOUD_FIELD_MAP = {
        'AWS': 'aws_cost',
        'AWSCLOUD': 'aws_cost',
        'AZURE': 'azure_cost',
        'GCP': 'gcp_cost',
        'IBM Cloud': 'ibm_cost',
    }
    PER_CLOUD_FIELDS = ['aws_cost', 'azure_cost', 'gcp_cost', 'ibm_cost']

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__elastic_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port) if self.__es_host else None
        self.__destination_es_index = self.__environment_variables_dict.get('orion_cost_es_index', 'cloud-governance-orion-cost-metrics-index')
        cost_center = self.__environment_variables_dict.get('orion_cost_center', '')
        self.__cost_center = int(cost_center) if str(cost_center).strip() else None
        self.__custom_start_date = self.__environment_variables_dict.get('orion_cost_rollup_start_date', '')
        self.__custom_end_date = self.__environment_variables_dict.get('orion_cost_rollup_end_date', '')

    @staticmethod
    def __first_of_current_month():
        """First day of the current UTC month - the boundary of 'in progress'."""
        return datetime.now(timezone.utc).date().replace(day=1)

    @staticmethod
    def __last_completed_month():
        """
        Return (start, end) date strings for the most recently completed month
        (i.e. the month before the current one).
        """
        first_current = OrionCostMetricsRollup.__first_of_current_month()
        # subtracting a day drops into the previous month; day=1 gives its start
        last_month_end = date(first_current.year, first_current.month, 1)
        # step back one day into the previous month
        prev = last_month_end.fromordinal(last_month_end.toordinal() - 1)
        prev_start = prev.replace(day=1)
        return prev_start.strftime('%Y-%m-%d'), prev.strftime('%Y-%m-%d')

    def __build_query(self, start_date: str, end_date: str):
        """
        Build the month/cloud spend aggregation query for a date range.

        Filters to the configured cost center, the spend-bearing policies, and
        Actual > 0 (which also drops the forecast rows, whose Actual is 0).
        @param start_date: Start date string (YYYY-MM-DD)
        @param end_date: End date string (YYYY-MM-DD)
        @return: ES query dict
        """
        return {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"CostCenter": self.__cost_center}},
                        {"terms": {"policy.keyword": self.SPEND_POLICIES}},
                        {"range": {"Actual": {"gt": 0}}},
                        {"range": {"start_date": {"gte": start_date, "lte": end_date, "format": "yyyy-MM-dd"}}}
                    ]
                }
            },
            "aggs": {
                "by_month": {
                    "date_histogram": {"field": "start_date", "calendar_interval": "month", "format": "yyyy-MM-dd"},
                    "aggs": {
                        "by_cloud": {
                            "terms": {"field": "CloudName.keyword", "size": 20},
                            "aggs": {"spend": {"sum": {"field": "Actual"}}}
                        },
                        "total": {"sum": {"field": "Actual"}}
                    }
                }
            }
        }

    def __parse_response(self, response: dict):
        """
        Walk the month -> cloud aggregation buckets and build one rollup
        document per completed month. The current (in-progress) month is
        skipped: it is still accruing, so its partial total would look like a
        spurious drop to the change-point detector.
        @param response: the 'aggregations' dict returned by post_query(result_agg=True)
        @return: list of rollup documents
        """
        documents = []
        if not response or 'by_month' not in response:
            return documents

        first_current = self.__first_of_current_month().strftime('%Y-%m-%d')

        for month_bucket in response.get('by_month', {}).get('buckets', []):
            month_start = month_bucket.get('key_as_string', '')[:10]
            if not month_start:
                continue
            # skip the in-progress current (and any future) month
            if month_start >= first_current:
                continue
            document = {field: 0 for field in self.PER_CLOUD_FIELDS}
            for cloud_bucket in month_bucket.get('by_cloud', {}).get('buckets', []):
                field = self.CLOUD_FIELD_MAP.get(cloud_bucket.get('key'))
                if field:
                    document[field] += round(cloud_bucket.get('spend', {}).get('value') or 0)
            total = month_bucket.get('total', {}).get('value') or 0
            document['total_cost'] = round(total)
            month_label = month_start[:7]  # YYYY-MM
            document['uuid'] = f'CC{self.__cost_center}-{month_label}'
            document['timestamp'] = f'{month_start}T00:00:00Z'
            document['account'] = f'CC{self.__cost_center}'
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
        Roll up cost-center monthly spend into one document per completed month.

        If start_date/end_date are given (directly, or via the
        orion_cost_rollup_start_date/orion_cost_rollup_end_date env vars),
        backfills that range. Otherwise, rolls up just the most recently
        completed month - the incremental mode run daily in production, which
        keeps the just-closed month fresh as late billing adjustments land.
        @param start_date: Optional start date string (YYYY-MM-DD)
        @param end_date: Optional end date string (YYYY-MM-DD)
        @return: dict summarizing what was written
        """
        if not self.__elastic_operations:
            logger.warning('ES not configured, skipping Orion cost metrics rollup')
            return {'status': 'no_upload', 'message': 'ES not configured'}

        if self.__cost_center is None:
            logger.warning('orion_cost_center not configured, skipping Orion cost metrics rollup')
            return {'status': 'skipped', 'message': 'orion_cost_center not configured'}

        if not start_date:
            start_date = self.__custom_start_date
        if not end_date:
            end_date = self.__custom_end_date

        if bool(start_date) != bool(end_date):
            logger.warning(f'Ignoring partial date range (start_date={start_date}, end_date={end_date}); both must be set to backfill. Falling back to incremental mode.')

        if start_date and end_date:
            logger.info(f'Backfilling Orion cost metrics rollup from {start_date} to {end_date}')
            total_documents = self.__process_date_range(start_date, end_date)
            logger.info(f'Orion cost metrics rollup backfill complete: {total_documents} documents written')
            return {'status': 'success', 'documents_written': total_documents, 'start_date': start_date, 'end_date': end_date}

        month_start, month_end = self.__last_completed_month()
        logger.info(f'Running incremental Orion cost metrics rollup for {month_start[:7]}')
        total_documents = self.__process_date_range(month_start, month_end)
        logger.info(f'Orion cost metrics rollup complete for {month_start[:7]}: {total_documents} documents written')
        return {'status': 'success', 'documents_written': total_documents, 'month': month_start[:7]}
