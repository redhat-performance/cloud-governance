
from datetime import datetime, timedelta
import time
import pandas as pd
from cloud_governance.main.environment_variables import environment_variables

from elasticsearch_dsl import Search
from elasticsearch import Elasticsearch
from typeguard import typechecked

from cloud_governance.common.elasticsearch.elasticsearch_exceptions import ElasticSearchDataNotUploaded
from cloud_governance.common.logger.logger_time_stamp import logger_time_stamp, logger


class ElasticSearchOperations:
    """
    This class related to ElasticSearch operations
    """

    # sleep time between checks is 10 sec
    SLEEP_TIME = 10
    # ElasticSearch fetch data of last 15 minutes
    ES_FETCH_MIN_TIME = 15
    # max search results
    MAX_SEARCH_RESULTS = 1000
    MIN_SEARCH_RESULTS = 100

    def __init__(self, es_host: str, es_port: str, region: str = '', bucket: str = '', logs_bucket_key: str = '',
                 timeout: int = 2000):
        self.__environment_variables_dict = environment_variables.environment_variables_dict
        self.__es_host = es_host
        self.__es_port = es_port
        self.__region = region
        self.__timeout = int(self.__environment_variables_dict.get('ES_TIMEOUT')) if self.__environment_variables_dict.get('ES_TIMEOUT') else timeout
        self.__es = Elasticsearch([{'host': self.__es_host, 'port': self.__es_port}], timeout=self.__timeout, max_retries=2)

    def __elasticsearch_get_index_hits(self, index: str, uuid: str = '', workload: str = '', fast_check: bool = False,
                                       id: bool = False):
        """
        This method search for data per index in last 2 minutes and return the number of docs or zero
        :param index:
        :param workload: need only if there is different timestamp parameter in Elasticsearch
        :param id: True to return the doc ids
        :param fast_check: return fast response
        :return:
        """
        """
        :return:
        """
        ids = []
        # https://github.com/elastic/elasticsearch-dsl-py/issues/49
        self.__es.indices.refresh(index=index)
        # timestamp name in Elasticsearch is different
        search = Search(using=self.__es, index=index).filter('range', timestamp={
            'gte': f'now-{self.ES_FETCH_MIN_TIME}m', 'lt': 'now'})
        # reduce the search result
        if fast_check:
            search = search[0:self.MIN_SEARCH_RESULTS]
        else:
            search = search[0:self.MAX_SEARCH_RESULTS]
        search_response = search.execute()
        if search_response.hits:
            if uuid:
                count_hits = 0
                for row in search_response:
                    if type(row['uuid']) == str:
                        # uperf return str
                        current_uuid = row['uuid']
                    else:
                        current_uuid = row['uuid'][0]
                    if current_uuid == uuid:
                        if fast_check:
                            return 1
                        ids.append(row.meta.id)
                        count_hits += 1
                if id:
                    return ids
                else:
                    return count_hits
            else:
                return len(search_response.hits)
        else:
            return 0

    @typechecked()
    @logger_time_stamp
    def verify_elasticsearch_data_uploaded(self, index: str, uuid: str = '', workload: str = '',
                                           fast_check: bool = False):
        """
        The method wait till data upload to elastic search and wait if there is new data, search in last 15 minutes
        :param index:
        :param uuid: the current workload uuid
        :param workload: workload name only if there is a different timestamp parameter name in elasticsearch
        :param fast_check: return response on first doc
        :return:
        """
        current_wait_time = 0
        current_hits = 0
        # waiting for any hits
        while current_wait_time <= self.__timeout:
            # waiting for new hits
            new_hits = self.__elasticsearch_get_index_hits(index=index, uuid=uuid, workload=workload,
                                                           fast_check=fast_check)
            if current_hits < new_hits:
                logger.info(f'Data with index: {index} and uuid={uuid} was uploaded to ElasticSearch successfully')
                return self.__elasticsearch_get_index_hits(index=index, uuid=uuid, workload=workload, id=True,
                                                           fast_check=fast_check)
            # sleep for x seconds
            time.sleep(self.SLEEP_TIME)
            current_wait_time += self.SLEEP_TIME
        raise ElasticSearchDataNotUploaded

    @typechecked()
    def upload_to_elasticsearch(self, index: str, data: dict, doc_type: str = '_doc', es_add_items: dict = None, **kwargs):
        """
        This method is upload json data into elasticsearch
        :param index: index name to be stored in elasticsearch
        :param data: data must me in dictionary i.e. {'key': 'value'}
        :param doc_type:
        :param es_add_items:
        :return:
        """
        # read json to dict
        json_path = ""

        # Add items
        if es_add_items:
            for key, value in es_add_items.items():
                data[key] = value

        # utcnow - solve timestamp issue
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow()  # datetime.now()

        # Upload data to elastic search server
        try:
            if isinstance(data, dict):  # JSON Object
                self.__es.index(index=index, doc_type=doc_type, body=data, **kwargs)
            else:  # JSON Array
                for record in data:
                    self.__es.index(index=index, doc_type=doc_type, body=record, **kwargs)
            return True
        except Exception as err:
            raise err

    @typechecked()
    def update_elasticsearch_index(self, index: str, id: str, metadata: dict = ''):
        """
        This method update existing index
        :param index: index name
        :param id: The specific index id
        :param metadata: The metadata for enrich that existing index according to id
        :return:
        """
        self.__es.update(index=index, id=id, body={"doc": metadata})

    @typechecked()
    @logger_time_stamp
    def get_elasticsearch_index_by_id(self, index: str, id: str):
        """
        This method return elastic search index data by id
        :param index: index name
        :param id: The specific index id
        :return:
        """
        return self.__es.get(index=index, id=id)

    @typechecked()
    @logger_time_stamp
    def get_index_hits(self, days: int, index: str):
        """
        This method return the last days data from elastic search
        @param days:
        @param index:
        @return:
        """
        search = Search(using=self.__es, index=index).filter('range', timestamp={'gte': f'now-{days}d', 'lt': 'now'})
        search = search[0:self.MAX_SEARCH_RESULTS]
        search_response = search.execute()
        df = pd.DataFrame()
        for row in search_response:
            df = pd.concat([df, pd.DataFrame([row.to_dict()])], ignore_index=True).fillna({})
        return df.to_dict('records')

    @typechecked()
    @logger_time_stamp
    def get_query_data_between_range(self, start_datetime: datetime, end_datetime: datetime):
        """
        This method returns the query to fetch the data in between ranges
        @return:
        """
        query = {
            "query": {
                "bool": {
                    "filter": {
                        "range": {
                            "timestamp": {
                                "format": "yyyy-MM-dd HH:mm:ss"
                            }
                        }
                    }
                }
            }
        }
        query['query']['bool']['filter']['range']['timestamp']['lte'] = str(end_datetime.replace(microsecond=0))
        query['query']['bool']['filter']['range']['timestamp']['gte'] = str(start_datetime.replace(microsecond=0))
        return query

    @typechecked()
    @logger_time_stamp
    def fetch_data_between_range(self, es_index: str, start_datetime: datetime, end_datetime: datetime):
        """
        This method fetches the data in between range
        @param es_index:
        @param start_datetime:
        @param end_datetime:
        @return:
        """
        if self.__es.indices.exists(index=es_index):
            query_body = self.get_query_data_between_range(start_datetime=start_datetime, end_datetime=end_datetime)
            data = self.__es.search(index=es_index, body=query_body, doc_type='_doc').get('hits')
            if data:
                return data['hits']
        return []

    @typechecked()
    @logger_time_stamp
    def delete_data_in_between_in_es(self, es_index: str, start_datetime: datetime, end_datetime: datetime):
        """
        This method deletes the data in between two ranges
        @param es_index:
        @param start_datetime:
        @param end_datetime:
        @return:
        """
        if self.__es.indices.exists(index=es_index):
            query_body = self.get_query_data_between_range(start_datetime=start_datetime, end_datetime=end_datetime)
            logger.info(f'Clearing data from {start_datetime} to  {end_datetime} ')
            return self.__es.delete_by_query(index=es_index, body=query_body)

    @typechecked()
    @logger_time_stamp
    def delete_data_in_es(self, es_index: str):
        """
        This method delete the data in the index
        @param es_index: index_name
        @return:
        """
        if self.__es.indices.exists(index=es_index):
            return self.__es.indices.delete(index=es_index)
