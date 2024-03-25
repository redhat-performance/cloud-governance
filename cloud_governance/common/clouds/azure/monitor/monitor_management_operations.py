import json
from datetime import datetime, timedelta

from azure.core.exceptions import HttpResponseError
from azure.mgmt.monitor import MonitorManagementClient

from cloud_governance.common.clouds.azure.common.common_operations import CommonOperations
from cloud_governance.common.logger.init_logger import logger
from cloud_governance.common.utils.configs import LOOK_BACK_DAYS, UNUSED_DAYS


class MonitorManagementOperations(CommonOperations):

    def __init__(self):
        super().__init__()
        self.__monitor_client = MonitorManagementClient(credential=self._default_creds,
                                                        subscription_id=self._subscription_id)

    def __get_end_date(self):
        """
        This method returns the end date
        :return:
        :rtype:
        """
        return datetime.utcnow()

    def __get_start_date(self):
        """
        This method returns the start date
        :return:
        :rtype:
        """
        return self.__get_end_date() - timedelta(LOOK_BACK_DAYS)

    def get_audit_records(self, resource_id: str, start_date: datetime = None, end_date: datetime = None):
        """
        This method returns the audit record for the resource_id
        :param start_date:
        :type start_date:
        :param end_date:
        :type end_date:
        :param resource_id:
        :type resource_id:
        :return:
        :rtype:
        """
        if not start_date:
            start_date = self.__get_start_date()
        if not end_date:
            end_date = self.__get_end_date()
        try:
            filter_query = f"eventTimestamp ge '{start_date}'" \
                           f" and eventTimestamp le '{end_date}' " \
                           f"and resourceUri eq '{resource_id}'.:code:"
            records = self.__monitor_client.activity_logs.list(filter=filter_query)
            return self._item_paged_iterator(item_paged_object=records, as_dict=True)
        except HttpResponseError as http_error:
            logger.error(http_error)
        except Exception as err:
            logger.error(err)

    def get_resource_metrics(self, resource_id: str, metricnames: str, aggregation: str,
                             timespan: str = None, interval: timedelta = timedelta(days=1), **kwargs):
        """
        This method returns the metrics object of individual resource, default timespan will be last 7 days
        :param resource_id:
        :type resource_id:
        :param metricnames:
        :type metricnames:
        :param aggregation:
        :type aggregation:
        :param timespan:
        :type timespan:
        :param interval:
        :type interval:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        if not timespan:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=UNUSED_DAYS)
            timespan = f'{start_date}/{end_date}'
        response = self.__monitor_client.metrics.list(resource_uri=resource_id, timespan=timespan,
                                                      metricnames=metricnames, aggregation=aggregation,
                                                      result_type='Data', interval=interval,
                                                      **kwargs)
        return response.as_dict()
