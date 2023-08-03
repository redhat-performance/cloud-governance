
from datetime import datetime, timedelta


class ElasticSearchQueries:
    """
    This class having the ElasticSearch Queries used in the cloud-resource-orchestration
    """

    def __init__(self, cro_duration_days: int = 30):
        self.current_end_date = datetime.utcnow()
        self.current_start_date = self.current_end_date - timedelta(days=cro_duration_days)

    def get_all_in_progress_tickets(self, match_conditions: list = None, fields: list = None,  **kwargs):
        """
        This method returns all the in progress tickets
        :param fields:
        :param match_conditions: # [{"term": {"key": "value"}}, {"term": {"key": "value"}}]
        :param kwargs:
        :return:
        """
        if not match_conditions:
            match_conditions = []
        query = \
            {  # check user opened the ticket in elastic_search
                "query": {
                    "bool": {
                        "must": [
                            {"terms": {"ticket_id_state.keyword": ['in-progress']}},
                            *match_conditions,
                        ],
                        "filter": {
                            "range": {
                                "timestamp": {
                                    "format": "yyyy-MM-dd",
                                    "lte": str(self.current_end_date.date()),
                                    "gte": str(self.current_start_date.date()),
                                }
                            }
                        }
                    }
                },
            }
        if fields:
            query['_source'] = fields
        return query

    def get_all_closed_tickets(self, match_conditions: list = None, fields: list = None):
        """
        This method returns the closed tickets
        :return:
        :return:
        """
        if not match_conditions:
            match_conditions = []
        query = \
            {  # check user opened the ticket in elastic_search
                "query": {
                    "bool": {
                        "must": [
                            {"terms": {"ticket_id_state.keyword": ['closed']}},
                            *match_conditions,
                        ],
                        "filter": {
                            "range": {
                                "timestamp": {
                                    "format": "yyyy-MM-dd",
                                    "lte": str(self.current_end_date.date()),
                                    "gte": str(self.current_start_date.date()),
                                }
                            }
                        }
                    }
                },
            }
        if fields:
            query['_source'] = fields
        return query
