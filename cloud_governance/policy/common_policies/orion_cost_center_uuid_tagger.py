from datetime import datetime, timezone, date

from cloud_governance.common.elasticsearch.elasticsearch_operations import ElasticSearchOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp
from cloud_governance.main.environment_variables import environment_variables


class OrionCostCenterUuidTagger:
    """
    Tags existing cost-center billing rows with orion_uuid/account in place on
    the shared multi-cloud billing index, so Orion can read monthly cost-center
    regressions directly from it.

    orion_uuid is shared across all clouds for a (cost center, month); total
    metrics sum everything sharing it, per-cloud metrics add a CloudName
    filter on top of the same uuid. Backfill is a direct run(start_date,
    end_date) call, not env-var-driven - it's one update_by_query, no more
    work than that.
    """

    SOURCE_ES_INDEX = 'cloud-governance-clouds-billing-reports'
    SPEND_POLICIES = ['cost_explorer_payer_billings', 'cost_billing_reports']

    def __init__(self):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_host = self.__environment_variables_dict.get('es_host', '')
        self.__es_port = self.__environment_variables_dict.get('es_port', '')
        self.__elastic_operations = ElasticSearchOperations(es_host=self.__es_host, es_port=self.__es_port) if self.__es_host else None
        cost_center = self.__environment_variables_dict.get('orion_cost_center', '')
        self.__cost_center = int(cost_center) if str(cost_center).strip() else None

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
        first_current = OrionCostCenterUuidTagger.__first_of_current_month()
        last_month_end = date(first_current.year, first_current.month, 1)
        prev = last_month_end.fromordinal(last_month_end.toordinal() - 1)
        prev_start = prev.replace(day=1)
        return prev_start.strftime('%Y-%m-%d'), prev.strftime('%Y-%m-%d')

    def __build_query(self, start_date: str, end_date: str):
        """
        Build the query selecting this cost center's spend-bearing rows for a date range.
        @param start_date: Start date string (YYYY-MM-DD)
        @param end_date: End date string (YYYY-MM-DD)
        @return: ES query dict
        """
        return {
            "bool": {
                "filter": [
                    {"term": {"CostCenter": self.__cost_center}},
                    {"terms": {"policy.keyword": self.SPEND_POLICIES}},
                    {"range": {"Actual": {"gt": 0}}},
                    {"range": {"start_date": {"gte": start_date, "lte": end_date, "format": "yyyy-MM-dd"}}}
                ]
            }
        }

    @staticmethod
    def __build_script(cost_center: int):
        """
        Sets orion_uuid/account from the already-known cost_center (a script
        param, not read from the document) and the row's start_date.
        start_date's format isn't consistent across writers (some include a
        time component) - the first 7 chars ("YYYY-MM") are robust to both.
        @param cost_center: the configured cost center (int)
        @return: ES script dict
        """
        return {
            "source": (
                "ctx._source.account = 'CC' + params.cost_center; "
                "ctx._source.orion_uuid = 'CC' + params.cost_center + '-' + "
                "ctx._source.start_date.toString().substring(0, 7);"
            ),
            "params": {"cost_center": cost_center}
        }

    @logger_time_stamp
    def run(self, start_date: str = None, end_date: str = None):
        """
        Tag this cost center's billing rows with orion_uuid/account.

        If start_date/end_date are both given, tags that range (one-off
        backfill). Otherwise, tags just the most recently completed month -
        the incremental mode run daily in production, which keeps the
        just-closed month tagged as late billing adjustments land.
        @param start_date: Optional start date string (YYYY-MM-DD)
        @param end_date: Optional end date string (YYYY-MM-DD)
        @return: dict summarizing what was tagged
        """
        if not self.__elastic_operations:
            logger.warning('ES not configured, skipping Orion cost-center uuid tagging')
            return {'status': 'no_upload', 'message': 'ES not configured'}

        if self.__cost_center is None:
            logger.warning('orion_cost_center not configured, skipping Orion cost-center uuid tagging')
            return {'status': 'skipped', 'message': 'orion_cost_center not configured'}

        if bool(start_date) != bool(end_date):
            logger.warning(f'Ignoring partial date range (start_date={start_date}, end_date={end_date}); both must be provided together. Falling back to incremental mode.')
            start_date = None
            end_date = None

        if not (start_date and end_date):
            start_date, end_date = self.__last_completed_month()
            logger.info(f'Running incremental Orion cost-center uuid tagging for CC{self.__cost_center}, {start_date[:7]}')
        else:
            logger.info(f'Backfilling Orion cost-center uuid tagging for CC{self.__cost_center}, {start_date} to {end_date}')

        query = self.__build_query(start_date=start_date, end_date=end_date)
        script = self.__build_script(self.__cost_center)
        result = self.__elastic_operations.update_by_query(es_index=self.SOURCE_ES_INDEX, query=query, script=script)
        updated = result.get('updated', 0) if isinstance(result, dict) else 0
        logger.info(f'Orion cost-center uuid tagging complete for CC{self.__cost_center} ({start_date} to {end_date}): {updated} documents tagged')
        return {'status': 'success', 'documents_tagged': updated, 'start_date': start_date, 'end_date': end_date}
