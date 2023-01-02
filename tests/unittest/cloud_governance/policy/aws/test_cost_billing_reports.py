import datetime
from operator import sub

from cloud_governance.policy.aws.cost_billing_reports import CostBillingReports


def test_get_start_date():
    """
    This method test the start_date
    @return:
    """
    today = datetime.datetime.now()
    CostBillingReports()
    expected_date = today - datetime.timedelta(days=1)
    assert CostBillingReports()._CostBillingReports__get_start_date(end_date=today, operation=sub, days=1) == expected_date
