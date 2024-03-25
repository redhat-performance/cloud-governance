from azure.mgmt.monitor.v2021_05_01.models import Metric, Response


class MockMetric(Metric):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

class MockResponse(Response):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MockMetricOperations:

    def __init__(self):
        self.__metrics = {}

    def create_metric(self, resource_id: str, type: str, name: str, unit: str, timeseries: list, **kwargs):
        name = {'value': name}

        metric = MockMetric(id=resource_id, type=type, name=name, unit=unit, timeseries=timeseries, **kwargs)
        self.__metrics[resource_id] = MockResponse(timespan='', value=[metric])
        return metric

    def list(self, resource_uri: str, **kwargs):
        return self.__metrics[resource_uri]


