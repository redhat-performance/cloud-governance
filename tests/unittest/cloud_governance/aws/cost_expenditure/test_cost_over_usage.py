from cloud_governance.policy.aws.cost_over_usage import CostOverUsage


def test_aggregate_user_sum():
    test_df = [{'User': 'test1', 'Cost': 9}, {'User': 'test2', 'Cost': 14}, {'User': 'test2', 'Cost': 19}]
    expected_df = [{'User': 'test1', 'Cost': 9}, {'User': 'test2', 'Cost': 33}]
    cost_over_usage = CostOverUsage()
    actual_df = cost_over_usage.aggregate_user_sum(test_df)
    assert actual_df == expected_df


def test_aggregate_user_sum_instances():
    test_df = [
        {'User': 'test1', 'Cost': 9, 'Instances': [{'InstanceId': 1234}]},
        {'User': 'test1', 'Cost': 9, 'Instances': [{'InstanceId': 1234}]},
        {'User': 'test2', 'Cost': 14},
        {'User': 'test2', 'Cost': 19}
    ]
    cost_over_usage = CostOverUsage()
    actual_df = cost_over_usage.aggregate_user_sum(test_df)

    assert len(actual_df) == 2
    assert actual_df[0]['User'] == 'test1'
    assert actual_df[0]['Cost'] == 18
    assert 'Instances' in actual_df[0]
    assert actual_df[1]['User'] == 'test2'
    assert actual_df[1]['Cost'] == 33
