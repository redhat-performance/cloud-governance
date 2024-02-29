from azure.mgmt.monitor.models import EventData

from tests.unittest.mocks.azure.common_operations import CustomItemPaged


class MockEventData(EventData):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MockActivityLogsOperations:

    def __init__(self):
        super().__init__()
        self.__audit_logs = []

    def list(self, filter: str, **kwargs):
        """
        This method returns the list of EventData
        :param filter:
        :type filter:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        return CustomItemPaged(resource_list=self.__audit_logs)

    def create_log(self, **kwargs):
        """
        This method creates audit log entry
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        record = MockEventData(**kwargs)
        self.__audit_logs.append(record)
        return record
