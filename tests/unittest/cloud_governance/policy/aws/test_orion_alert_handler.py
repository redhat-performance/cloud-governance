import json
import os
import tempfile
from unittest.mock import patch, MagicMock

from cloud_governance.policy.common_policies.orion_alert_handler import OrionAlertHandler


class TestOrionAlertHandler:
    """Test suite for OrionAlertHandler policy wrapper"""

    SAMPLE_DATA = [
        {
            'timestamp': '2026-07-15T00:00:00Z',
            'account': 'PERFSCALE',
            'is_changepoint': True,
            'metrics': {
                'zombie_cluster_resource_count': {'value': 25, 'percentage_change': 150.0, 'labels': []},
            }
        }
    ]

    def _make_handler(self, env_overrides=None):
        base_env = {
            'account': 'PERFSCALE',
            'SLACK_API_TOKEN': 'xoxb-test-token',
            'SLACK_CHANNEL_NAME': 'cg-alerts',
            'ORION_OUTPUT_FILE': '/tmp/orion-output.json',
        }
        if env_overrides:
            base_env.update(env_overrides)
        with patch('cloud_governance.policy.common_policies.orion_alert_handler.environment_variables') as mock_env:
            mock_env.environment_variables_dict = base_env
            return OrionAlertHandler()

    def test_run_skips_when_output_file_not_set(self):
        handler = self._make_handler({'ORION_OUTPUT_FILE': ''})
        result = handler.run()
        assert result['status'] == 'skipped'
        assert 'ORION_OUTPUT_FILE' in result['message']

    def test_run_skips_when_slack_token_missing(self):
        handler = self._make_handler({'SLACK_API_TOKEN': ''})
        result = handler.run()
        assert result['status'] == 'skipped'
        assert 'Slack' in result['message']

    def test_run_skips_when_slack_channel_missing(self):
        handler = self._make_handler({'SLACK_CHANNEL_NAME': ''})
        result = handler.run()
        assert result['status'] == 'skipped'
        assert 'Slack' in result['message']

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_run_posts_to_slack_when_regressions_found(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True}
        mock_post.return_value = mock_response

        f = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.SAMPLE_DATA, f)
        f.close()

        try:
            handler = self._make_handler({'ORION_OUTPUT_FILE': f.name})
            result = handler.run()

            assert result['status'] == 'notified'
            assert result['regressions_count'] == 1
            mock_post.assert_called_once()
        finally:
            os.unlink(f.name)

    @patch('cloud_governance.common.orion.slack_notifier.requests.post')
    def test_run_no_regressions_does_not_post(self, mock_post):
        no_regression_data = [
            {
                'timestamp': '2026-07-01T00:00:00Z',
                'is_changepoint': False,
                'metrics': {'zombie_cluster_resource_count': {'value': 10, 'percentage_change': 0, 'labels': []}}
            }
        ]

        f = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(no_regression_data, f)
        f.close()

        try:
            handler = self._make_handler({'ORION_OUTPUT_FILE': f.name})
            result = handler.run()

            assert result['status'] == 'no_regressions'
            mock_post.assert_not_called()
        finally:
            os.unlink(f.name)
