from dataclasses import dataclass
from datetime import datetime

import pytz

from cloud_governance.common.clouds.cloudability.templates.cloudability_dimensions import COST_USAGE_REPORT_DIMENSIONS, \
    COST_USAGE_REPORT_METRICS


@dataclass
class CostUsageReportData:
    ResourceName: str
    OfferingType: str
    UsageFamily: str
    InstanceCategory: str
    UsageType: str
    ItemDescription: str
    Region: str
    ServiceName: str
    StartDate: str
    CostCenter: str
    AccountName: str
    AccountId: str
    PublicCloudName: str
    Cost: float
    timestamp: datetime
    ResourcePlanId: str
    IndexId: str = ""
    ReportGenerate: str = ""

    def __init__(self, report_generated_type: str, **kwargs):
        for k, v in kwargs.items():
            if k in COST_USAGE_REPORT_DIMENSIONS:
                key = COST_USAGE_REPORT_DIMENSIONS.get(k)
            elif k in COST_USAGE_REPORT_METRICS:
                key = COST_USAGE_REPORT_METRICS.get(k)
                v = float(v)
            else:
                key = k
            setattr(self, key, v)
        self.IndexId = f'{report_generated_type}-{self.StartDate}-{self.ResourceName}-{self.AccountId}'
        self.timestamp = datetime.strptime(self.StartDate, '%Y-%m-%d')
        self.ReportGenerate = report_generated_type

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items()}
