import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import requests

from cloud_governance.common.orion.slack_notifier import OrionSlackNotifier


class TestOrionSlackNotifier:
    """Test suite for OrionSlackNotifier"""

    # Orion's real JSON output keys metrics as "<config_name>_<metric_of_interest>"
    # and serializes "timestamp" as Unix epoch seconds, not ISO8601 - confirmed
    # against live output. 1782864000/1784073600/1784505600 = 2026-07-01/15/20.
    SAMPLE_ORION_OUTPUT = [
        {
            'timestamp': 1782864000,
            'account': 'PERFSCALE',
            'is_changepoint': False,
            'metrics': {
                'zombieClusterResourceCountIncrease_zombie_cluster_resource_count': {'value': 10, 'percentage_change': 0, 'labels': []},
                'ec2StopCountIncrease_ec2_stop_count': {'value': 5, 'percentage_change': 0, 'labels': []},
            }
        },
        {
            'timestamp': 1784073600,
            'account': 'PERFSCALE',
            'is_changepoint': True,
            'metrics': {
                'zombieClusterResourceCountIncrease_zombie_cluster_resource_count': {'value': 25, 'percentage_change': 150.0, 'labels': []},
                'ec2StopCountIncrease_ec2_stop_count': {'value': 5, 'percentage_change': 0, 'labels': []},
            }
        },
        {
            'timestamp': 1784505600,
            'account': 'PERFSCALE',
            'is_changepoint': True,
            'metrics': {
                'zombieClusterResourceCountIncrease_zombie_cluster_resource_count': {'value': 25, 'percentage_change': 0, 'labels': []},
                'ec2StopCountDecrease_ec2_stop_count': {'value': 2, 'percentage_change': -60.0, 'labels': []},
            }
        },
    ]

    def _write_json_file(self, data):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(data, f)
        f.close()
        return f.name

    def test_parse_orion_json_reads_list(self):
        path = self._write_json_file(self.SAMPLE_ORION_OUTPUT)
        try:
            result = OrionSlackNotifier.parse_orion_json(path)
            assert isinstance(result, list)
            assert len(result) == 3
        finally:
            os.unlink(path)

    def test_parse_orion_json_handles_string_wrapped_json(self):
        """Orion sometimes writes JSON as a string (double-encoded)"""
        path = self._write_json_file(json.dumps(self.SAMPLE_ORION_OUTPUT))
        try:
            result = OrionSlackNotifier.parse_orion_json(path)
            assert isinstance(result, list)
            assert len(result) == 3
        finally:
            os.unlink(path)

    def test_parse_orion_json_returns_empty_for_non_list(self):
        path = self._write_json_file({'not': 'a list'})
        try:
            result = OrionSlackNotifier.parse_orion_json(path)
            assert result == []
        finally:
            os.unlink(path)

    def test_extract_regressions_finds_changepoints_with_nonzero_change(self):
        regressions = OrionSlackNotifier.extract_regressions(self.SAMPLE_ORION_OUTPUT)
        assert len(regressions) == 2

        first = regressions[0]
        assert first['timestamp'] == '2026-07-15'
        assert len(first['metrics']) == 1
        assert first['metrics'][0]['name'] == 'zombieClusterResourceCountIncrease_zombie_cluster_resource_count'
        assert first['metrics'][0]['percentage_change'] == 150.0

        second = regressions[1]
        assert second['timestamp'] == '2026-07-20'
        assert len(second['metrics']) == 1
        assert second['metrics'][0]['name'] == 'ec2StopCountDecrease_ec2_stop_count'
        assert second['metrics'][0]['percentage_change'] == -60.0

    def test_extract_regressions_converts_epoch_timestamp_to_date(self):
        """Orion serializes timestamp as Unix epoch seconds, not ISO8601 - must be readable"""
        data = [
            {
                'timestamp': 1784073600,
                'is_changepoint': True,
                'metrics': {
                    'someMetricIncrease_some_metric': {'value': 10, 'percentage_change': 50.0, 'labels': []},
                }
            }
        ]
        regressions = OrionSlackNotifier.extract_regressions(data)
        assert regressions[0]['timestamp'] == '2026-07-15'

    def test_extract_regressions_skips_non_changepoints(self):
        data = [
            {
                'timestamp': 1782864000,
                'is_changepoint': False,
                'metrics': {
                    'zombieClusterResourceCountIncrease_zombie_cluster_resource_count': {'value': 10, 'percentage_change': 0, 'labels': []},
                }
            }
        ]
        assert OrionSlackNotifier.extract_regressions(data) == []

    def test_extract_regressions_skips_changepoint_with_all_zero_changes(self):
        data = [
            {
                'timestamp': 1782864000,
                'is_changepoint': True,
                'metrics': {
                    'zombieClusterResourceCountIncrease_zombie_cluster_resource_count': {'value': 10, 'percentage_change': 0, 'labels': []},
                }
            }
        ]
        assert OrionSlackNotifier.extract_regressions(data) == []

    def test_extract_regressions_handles_empty_list(self):
        assert OrionSlackNotifier.extract_regressions([]) == []

    def test_format_slack_blocks_produces_header_and_sections(self):
        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='test-channel')
        regressions = [
            {
                'timestamp': '2026-07-15',
                'account': 'PERFSCALE',
                'metrics': [
                    {'name': 'zombieClusterResourceCountIncrease_zombie_cluster_resource_count', 'value': 25, 'percentage_change': 150.0},
                ]
            }
        ]
        blocks = notifier.format_slack_blocks('PERFSCALE', regressions)

        assert blocks[0]['type'] == 'header'
        assert 'PERFSCALE' in blocks[0]['text']['text']
        assert blocks[1]['type'] == 'section'
        assert '1 change point' in blocks[1]['text']['text']
        assert blocks[2]['type'] == 'divider'
        assert blocks[3]['type'] == 'section'
        assert '2026-07-15' in blocks[3]['text']['text']
        assert 'increased' in blocks[3]['text']['text']
        assert '150.0%' in blocks[3]['text']['text']
        # Only the readable config name should show, not the raw composite key
        assert 'zombieClusterResourceCountIncrease' in blocks[3]['text']['text']
        assert 'zombieClusterResourceCountIncrease_zombie_cluster_resource_count' not in blocks[3]['text']['text']

    def test_format_slack_blocks_shows_decrease(self):
        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='test-channel')
        regressions = [
            {
                'timestamp': '2026-07-20',
                'account': 'PERFSCALE',
                'metrics': [
                    {'name': 'ec2StopCountDecrease_ec2_stop_count', 'value': 2, 'percentage_change': -60.0},
                ]
            }
        ]
        blocks = notifier.format_slack_blocks('PERFSCALE', regressions)

        metric_block = blocks[3]
        assert 'decreased' in metric_block['text']['text']
        assert '60.0%' in metric_block['text']['text']
        assert 'ec2StopCountDecrease' in metric_block['text']['text']

    def test_format_slack_blocks_returns_empty_for_no_regressions(self):
        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='test-channel')
        assert notifier.format_slack_blocks('PERFSCALE', []) == []

    def test_channel_name_gets_hash_prefix(self):
        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='my-channel')
        assert notifier._OrionSlackNotifier__slack_channel == '#my-channel'

    def test_channel_name_no_double_hash(self):
        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='#my-channel')
        assert notifier._OrionSlackNotifier__slack_channel == '#my-channel'

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_post_to_slack_sends_correct_payload(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True, 'ts': '1234567890.123456'}
        mock_post.return_value = mock_response

        notifier = OrionSlackNotifier(slack_token='xoxb-test-token', slack_channel='alerts')
        blocks = [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': 'test'}}]
        result = notifier.post_to_slack(blocks)

        assert result['ok'] is True
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs['json']['channel'] == '#alerts'
        assert call_kwargs.kwargs['json']['blocks'] == blocks
        assert 'Bearer xoxb-test-token' in call_kwargs.kwargs['headers']['Authorization']

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_notify_end_to_end_with_regressions(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True}
        mock_post.return_value = mock_response

        path = self._write_json_file(self.SAMPLE_ORION_OUTPUT)
        try:
            notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
            result = notifier.notify(file_path=path, account='PERFSCALE')

            assert result['status'] == 'notified'
            assert result['regressions_count'] == 2
            assert result['slack_ok'] is True
            mock_post.assert_called_once()
        finally:
            os.unlink(path)

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_notify_no_regressions_skips_slack(self, mock_post):
        data = [
            {
                'timestamp': '2026-07-01T00:00:00Z',
                'is_changepoint': False,
                'metrics': {'zombie_cluster_resource_count': {'value': 10, 'percentage_change': 0, 'labels': []}}
            }
        ]
        path = self._write_json_file(data)
        try:
            notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
            result = notifier.notify(file_path=path, account='PERFSCALE')

            assert result['status'] == 'no_regressions'
            mock_post.assert_not_called()
        finally:
            os.unlink(path)

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_notify_reports_slack_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': False, 'error': 'channel_not_found'}
        mock_post.return_value = mock_response

        path = self._write_json_file(self.SAMPLE_ORION_OUTPUT)
        try:
            notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='bad-channel')
            result = notifier.notify(file_path=path, account='PERFSCALE')

            assert result['status'] == 'slack_error'
            assert result['slack_ok'] is False
        finally:
            os.unlink(path)

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_post_to_slack_batches_over_block_limit(self, mock_post):
        """More than 50 blocks must be split across multiple Slack messages"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True}
        mock_post.return_value = mock_response

        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
        # 120 blocks -> ceil(120/50) = 3 messages
        blocks = [notifier._section(f'block {i}') for i in range(120)]
        result = notifier.post_to_slack(blocks)

        assert result['ok'] is True
        assert result['messages_sent'] == 3
        assert mock_post.call_count == 3
        # no single message exceeds the block limit
        for call in mock_post.call_args_list:
            assert len(call.kwargs['json']['blocks']) <= OrionSlackNotifier.SLACK_MAX_BLOCKS

    def test_regression_section_splits_long_text(self):
        """A regression with many metrics must split into multiple sections under the char limit"""
        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
        regression = {
            'timestamp': '2026-07-15T00:00:00Z',
            'metrics': [
                {'name': f'some_long_metric_name_number_{i}', 'value': 12345, 'percentage_change': 42.5}
                for i in range(100)
            ],
        }
        blocks = notifier._regression_section_blocks(regression)

        assert len(blocks) > 1
        for block in blocks:
            assert len(block['text']['text']) <= OrionSlackNotifier.SLACK_MAX_SECTION_CHARS

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_post_to_slack_handles_request_exception(self, mock_post):
        """A network/TLS/DNS failure must be caught, not raised"""
        mock_post.side_effect = requests.RequestException('connection timed out')

        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
        result = notifier.post_to_slack([notifier._section('test')])

        assert result['ok'] is False
        assert result['messages_sent'] == 1

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_post_to_slack_handles_non_json_response(self, mock_post):
        """A non-JSON response body must be caught, not raised"""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError('no JSON could be decoded')
        mock_post.return_value = mock_response

        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
        result = notifier.post_to_slack([notifier._section('test')])

        assert result['ok'] is False

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_post_to_slack_handles_non_dict_json_response(self, mock_post):
        """A valid-JSON-but-non-object response (list/scalar) must not crash on .get()"""
        mock_response = MagicMock()
        mock_response.json.return_value = ['unexpected', 'array']
        mock_post.return_value = mock_response

        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
        result = notifier.post_to_slack([notifier._section('test')])

        assert result['ok'] is False

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_post_to_slack_handles_http_error(self, mock_post):
        """A non-2xx HTTP status must route through the failure path"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError('500 Server Error')
        mock_post.return_value = mock_response

        notifier = OrionSlackNotifier(slack_token='xoxb-test', slack_channel='alerts')
        result = notifier.post_to_slack([notifier._section('test')])

        assert result['ok'] is False
