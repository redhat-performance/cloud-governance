from unittest.mock import MagicMock

from cloud_governance.common.clouds.aws.cost_explorer.cost_explorer_operations import CostExplorerOperations


def _make_cost_response():
    """Build a mock Cost Explorer response."""
    return {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2024-01-01', 'End': '2024-01-31'},
                'Total': {'UnblendedCost': {'Amount': '100.50', 'Unit': 'USD'}},
                'Groups': []
            }
        ],
        'GroupDefinitions': [],
        'DimensionValueAttributes': []
    }


def _make_cost_explorer(mock_client: MagicMock = None) -> CostExplorerOperations:
    """Build a CostExplorerOperations instance backed by a mocked ce_client, injected
    directly via the constructor instead of patching the boto3 module."""
    mock_client = mock_client if mock_client is not None else MagicMock()
    return CostExplorerOperations(ce_client=mock_client), mock_client


def test_get_cost_and_usage_within_14_months():
    """Test that dates within 14 months are not adjusted."""
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.return_value = _make_cost_response()
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    # Test with date range within 14 months (not adjusted)
    start_date = '2025-06-15'  # Mid-month date
    end_date = '2026-07-01'

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # Verify the API was called with the original start_date (not adjusted)
    mock_client.get_cost_and_usage.assert_called()
    call_args = mock_client.get_cost_and_usage.call_args
    assert call_args[1]['TimePeriod']['Start'] == '2025-06-15'
    assert result['ResultsByTime']


def test_get_cost_and_usage_beyond_14_months_adjusts_date():
    """Test that start_date is adjusted to first day of month for >14 month queries."""
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.return_value = _make_cost_response()
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    # Test with date range beyond 14 months (should be adjusted)
    start_date = '2025-01-15'  # Mid-month date
    end_date = '2026-07-01'    # >14 months from start

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # Verify the API was called with adjusted start_date (first day of month)
    mock_client.get_cost_and_usage.assert_called()
    call_args = mock_client.get_cost_and_usage.call_args
    assert call_args[1]['TimePeriod']['Start'] == '2025-01-01'  # Adjusted to first day
    assert result['ResultsByTime']


def test_get_cost_and_usage_beyond_14_months_already_first_day():
    """Test that start_date on first day of month is not changed even for >14 month queries."""
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.return_value = _make_cost_response()
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    # Test with date range beyond 14 months but already on first day
    start_date = '2025-01-01'  # Already first day
    end_date = '2026-07-01'    # >14 months from start

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # Verify the API was called with original start_date (no adjustment needed)
    mock_client.get_cost_and_usage.assert_called()
    call_args = mock_client.get_cost_and_usage.call_args
    assert call_args[1]['TimePeriod']['Start'] == '2025-01-01'
    assert result['ResultsByTime']


def test_get_cost_and_usage_exactly_14_months():
    """Test boundary condition: exactly 14 months should not trigger adjustment."""
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.return_value = _make_cost_response()
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    # Exactly 14 months apart
    start_date = '2025-05-15'
    end_date = '2026-07-15'

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # Should not adjust (exactly 14 months)
    mock_client.get_cost_and_usage.assert_called()
    call_args = mock_client.get_cost_and_usage.call_args
    assert call_args[1]['TimePeriod']['Start'] == '2025-05-15'
    assert result['ResultsByTime']


def test_get_cost_and_usage_15_months_triggers_adjustment():
    """Test that 15 months triggers date adjustment."""
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.return_value = _make_cost_response()
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    # 15 months apart
    start_date = '2025-04-20'
    end_date = '2026-07-20'

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # Should adjust to first day of month (>14 months)
    mock_client.get_cost_and_usage.assert_called()
    call_args = mock_client.get_cost_and_usage.call_args
    assert call_args[1]['TimePeriod']['Start'] == '2025-04-01'  # Adjusted
    assert result['ResultsByTime']


def test_get_cost_and_usage_with_pagination():
    """Test that date adjustment works correctly with pagination."""
    mock_client = MagicMock()

    # First response with NextPageToken
    first_response = _make_cost_response()
    first_response['NextPageToken'] = 'token123'

    # Second response without NextPageToken
    second_response = _make_cost_response()

    mock_client.get_cost_and_usage.side_effect = [first_response, second_response]
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    # Date range beyond 14 months
    start_date = '2025-02-15'
    end_date = '2026-07-01'

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # Both calls should use the adjusted date
    assert mock_client.get_cost_and_usage.call_count == 2
    for call in mock_client.get_cost_and_usage.call_args_list:
        assert call[1]['TimePeriod']['Start'] == '2025-02-01'  # Adjusted
    assert len(result['ResultsByTime']) == 2  # Combined results


def test_get_cost_and_usage_error_handling():
    """Test that errors are handled gracefully even with date adjustment logic."""
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.side_effect = Exception("AWS API Error")
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    # Date range beyond 14 months
    start_date = '2025-03-10'
    end_date = '2026-07-01'

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # Should return empty result structure on error
    assert result['ResultsByTime'] == []
    assert result['GroupDefinitions'] == []
    assert result['DimensionValueAttributes'] == []


def test_get_cost_and_usage_reversed_date_range_does_not_crash():
    """Test that an end_date before start_date (negative months_diff) does not raise
    and simply skips the >14 month adjustment."""
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.return_value = _make_cost_response()
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    start_date = '2026-07-01'
    end_date = '2025-01-01'  # before start_date -> negative months_diff

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # No adjustment should be attempted; original start_date is passed through
    mock_client.get_cost_and_usage.assert_called()
    call_args = mock_client.get_cost_and_usage.call_args
    assert call_args[1]['TimePeriod']['Start'] == '2026-07-01'
    assert result['ResultsByTime']


def test_get_cost_and_usage_non_date_format_input_is_handled_gracefully():
    """Regression guard: the >14 month adjustment logic parses start_date/end_date with
    datetime.strptime(..., '%Y-%m-%d'). If a caller ever passes a value that isn't a
    plain 'YYYY-MM-DD' string (e.g. a stringified datetime with a time component), the
    parsing raises ValueError. This is currently caught by the method's broad except
    block, so no AWS call is made and an empty result is returned instead of raising.
    This test documents that behavior so a future change to the parsing logic doesn't
    silently start raising for existing callers.
    """
    mock_client = MagicMock()
    mock_client.get_cost_and_usage.return_value = _make_cost_response()
    cost_explorer, mock_client = _make_cost_explorer(mock_client)

    start_date = '2025-01-15 00:00:00'  # not '%Y-%m-%d', would fail strptime
    end_date = '2026-07-01'

    result = cost_explorer.get_cost_and_usage_from_aws(
        start_date=start_date,
        end_date=end_date,
        granularity='MONTHLY'
    )

    # The malformed input is swallowed by the except block: no AWS call is made
    # and an empty, well-formed result structure is returned.
    mock_client.get_cost_and_usage.assert_not_called()
    assert result == {'ResultsByTime': [], 'DimensionValueAttributes': [], 'GroupDefinitions': []}
