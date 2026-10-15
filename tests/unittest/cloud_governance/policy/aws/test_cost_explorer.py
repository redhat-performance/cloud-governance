from types import SimpleNamespace

from cloud_governance.policy.aws.cost_explorer import CostExplorer


def _make_cost_explorer(account: str, es_index: str):
    ce = CostExplorer.__new__(CostExplorer)
    ce._CostExplorer__account = account
    ce._CostExplorer__cost_explorer = SimpleNamespace(CE_COST_TYPES={'CHARGETYPE': 'RECORD_TYPE', 'PURCHASETYPE': 'PURCHASE_TYPE'})
    ce._elastic_upload = SimpleNamespace(es_index=es_index, account=account)
    ce.cost_metric = 'UnblendedCost'
    return ce


def _groups(start_time: str, key: str, amount: str):
    return {
        'TimePeriod': {'Start': start_time},
        'Groups': [
            {'Keys': [key], 'Metrics': {'UnblendedCost': {'Amount': amount}}}
        ]
    }


def test_orion_uuid_set_for_purchasetype_include_on_global_index():
    ce = _make_cost_explorer(account='PSAP', es_index='cloud-governance-cost-explorer-perf-global-cost')
    data = ce.filter_data_by_tag(_groups('2026-09-01', 'On Demand Instances', '88.127'), tag='PURCHASETYPE', savings_plan=ce.INCLUDE)
    assert data[0]['orion_uuid'] == 'PSAP-2026-09-01'


def test_orion_uuid_not_set_for_other_tags():
    ce = _make_cost_explorer(account='PSAP', es_index='cloud-governance-cost-explorer-perf-global-cost')
    data = ce.filter_data_by_tag(_groups('2026-09-01', 'alice', '10.0'), tag='Owner', savings_plan=ce.INCLUDE)
    assert 'orion_uuid' not in data[0]


def test_orion_uuid_not_set_for_savings_plan_exclude():
    ce = _make_cost_explorer(account='PSAP', es_index='cloud-governance-cost-explorer-perf-global-cost')
    data = ce.filter_data_by_tag(_groups('2026-09-01', 'On Demand Instances', '88.127'), tag='PURCHASETYPE', savings_plan=ce.EXCLUDE)
    assert 'orion_uuid' not in data[0]


def test_orion_uuid_not_set_on_non_global_index():
    ce = _make_cost_explorer(account='PSAP', es_index='cloud-governance-cost-explorer-psap')
    data = ce.filter_data_by_tag(_groups('2026-09-01', 'On Demand Instances', '88.127'), tag='PURCHASETYPE', savings_plan=ce.INCLUDE)
    assert 'orion_uuid' not in data[0]


def test_orion_uuid_normalizes_perf_scale_account_name():
    ce = _make_cost_explorer(account='PERF-SCALE', es_index='cloud-governance-cost-explorer-perf-global-cost')
    data = ce.filter_data_by_tag(_groups('2026-09-01', 'On Demand Instances', '88.127'), tag='PURCHASETYPE', savings_plan=ce.INCLUDE)
    assert data[0]['orion_uuid'] == 'PERFSCALE-2026-09-01'
