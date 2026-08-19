import json
import logging
from datetime import datetime, timezone

import requests


logger = logging.getLogger(__name__)


class OrionSlackNotifier:
    """
    Parses Orion JSON output and posts regression alerts to Slack.

    Orion's --output-format json produces a JSON array of data points.
    Each entry has an "is_changepoint" flag and a "metrics" dict where
    non-zero "percentage_change" values indicate detected regressions.
    """

    SLACK_POST_API = 'https://slack.com/api/chat.postMessage'
    # Slack Block Kit limits: max 50 blocks per message, max 3000 chars
    # per section's mrkdwn text.
    SLACK_MAX_BLOCKS = 50
    SLACK_MAX_SECTION_CHARS = 3000

    def __init__(self, slack_token: str, slack_channel: str):
        self.__slack_token = slack_token
        self.__slack_channel = f'#{slack_channel}' if not slack_channel.startswith('#') else slack_channel
        self.__headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.__slack_token}'
        }

    @staticmethod
    def parse_orion_json(file_path: str) -> list:
        """
        Read and parse Orion JSON output file. Orion saves one file per
        test as <base>_<test_name>.json containing a JSON array.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, str):
            data = json.loads(data)
        return data if isinstance(data, list) else []

    @staticmethod
    def _format_timestamp(ts) -> str:
        """
        Orion serializes the timestamp field as Unix epoch seconds in its
        JSON output, not ISO8601 - convert to a readable date for display.
        """
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d')
        return str(ts)

    @staticmethod
    def extract_regressions(data_points: list) -> list:
        """
        Walk the Orion JSON array and pull out change points with their
        regressed metrics.
        """
        regressions = []
        for entry in data_points:
            if not entry.get('is_changepoint'):
                continue
            metrics = entry.get('metrics', {})
            changed_metrics = []
            for metric_name, metric_data in metrics.items():
                pct = metric_data.get('percentage_change', 0)
                if pct != 0:
                    changed_metrics.append({
                        'name': metric_name,
                        'value': metric_data.get('value'),
                        'percentage_change': round(pct, 2),
                    })
            if changed_metrics:
                timestamp = entry.get('timestamp')
                regressions.append({
                    'timestamp': OrionSlackNotifier._format_timestamp(timestamp) if timestamp is not None else 'unknown',
                    'account': entry.get('account', entry.get('account.keyword', 'unknown')),
                    'metrics': changed_metrics,
                })
        return regressions

    @staticmethod
    def _section(text: str) -> dict:
        """Build a single mrkdwn section block."""
        return {'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}

    def _regression_section_blocks(self, regression: dict) -> list:
        """
        Build the section block(s) for one regression, splitting the text
        across multiple sections if it would exceed the per-section char
        limit (a regression with many metrics can produce a long body).
        """
        ts = regression.get('timestamp', 'unknown')
        lines = [f"*Date:* {ts}"]
        for m in regression['metrics']:
            direction = 'increased' if m['percentage_change'] > 0 else 'decreased'
            # Orion's JSON output keys metrics as "<config_name>_<metric_of_interest>"
            # (e.g. "zombieClusterResourceCountIncrease_zombie_cluster_resource_count").
            # Config metric names are plain camelCase with no underscores, so the part
            # before the first underscore is always just the readable config name.
            display_name = m['name'].split('_', 1)[0]
            lines.append(
                f"*{display_name}*: {direction} by `{abs(m['percentage_change']):.1f}%` (value: {m['value']})"
            )

        blocks = []
        current, current_len = [], 0
        for line in lines:
            # +1 accounts for the joining newline
            if current and current_len + len(line) + 1 > self.SLACK_MAX_SECTION_CHARS:
                blocks.append(self._section('\n'.join(current)))
                current, current_len = [], 0
            current.append(line)
            current_len += len(line) + 1
        if current:
            blocks.append(self._section('\n'.join(current)))
        return blocks

    def format_slack_blocks(self, account: str, regressions: list) -> list:
        """
        Build Slack Block Kit blocks for a set of regressions. Section text
        is split to respect the per-section character limit; batching to the
        per-message block limit is handled separately in post_to_slack.
        """
        if not regressions:
            return []

        blocks = [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f'Orion Regression Alert: {account}',
                }
            },
            self._section(f'Orion detected *{len(regressions)} change point(s)* in account *{account}*.'),
            {'type': 'divider'},
        ]

        for regression in regressions:
            blocks.extend(self._regression_section_blocks(regression))

        return blocks

    def _batch_blocks(self, blocks: list) -> list:
        """Split a flat block list into chunks within the per-message limit."""
        return [
            blocks[i:i + self.SLACK_MAX_BLOCKS]
            for i in range(0, len(blocks), self.SLACK_MAX_BLOCKS)
        ]

    def post_to_slack(self, blocks: list) -> dict:
        """
        Post blocks to the configured Slack channel, batching to stay within
        the per-message block limit. Returns a summary dict with an overall
        'ok' flag and the number of messages sent.
        """
        batches = self._batch_blocks(blocks)
        all_ok = True
        for batch in batches:
            response_data = self._post_single_message(batch)
            if not response_data.get('ok'):
                all_ok = False
        return {'ok': all_ok, 'messages_sent': len(batches)}

    def _post_single_message(self, blocks: list) -> dict:
        """
        Post a single Slack message. Network, TLS/DNS, and non-JSON response
        failures are caught and normalized to {'ok': False, ...} so a delivery
        failure never crashes the caller.
        """
        payload = {
            'channel': self.__slack_channel,
            'blocks': blocks,
        }
        try:
            response = requests.post(
                url=self.SLACK_POST_API,
                headers=self.__headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException as err:
            logger.error('Slack request failed: %s', err)
            return {'ok': False, 'error': 'request_failed'}
        except ValueError as err:
            logger.error('Slack response was not valid JSON: %s', err)
            return {'ok': False, 'error': 'invalid_response'}
        if not isinstance(response_data, dict):
            logger.error('Slack response was not a JSON object: %r', response_data)
            return {'ok': False, 'error': 'invalid_response'}
        if not response_data.get('ok'):
            logger.error('Slack API error: %s', response_data.get('error', 'unknown'))
        return response_data

    def notify(self, file_path: str, account: str) -> dict:
        """
        End-to-end: parse Orion output, extract regressions, post to Slack.
        Returns a summary dict.
        """
        data_points = self.parse_orion_json(file_path)
        regressions = self.extract_regressions(data_points)

        if not regressions:
            logger.info('No regressions found for account %s', account)
            return {'status': 'no_regressions', 'account': account}

        logger.info('Found %d regression(s) for account %s', len(regressions), account)
        blocks = self.format_slack_blocks(account, regressions)
        response = self.post_to_slack(blocks)

        return {
            'status': 'notified' if response.get('ok') else 'slack_error',
            'account': account,
            'regressions_count': len(regressions),
            'slack_ok': response.get('ok', False),
        }
