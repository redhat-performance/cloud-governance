import json
import logging

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
                regressions.append({
                    'timestamp': entry.get('timestamp', 'unknown'),
                    'account': entry.get('account', entry.get('account.keyword', 'unknown')),
                    'metrics': changed_metrics,
                })
        return regressions

    def format_slack_blocks(self, account: str, regressions: list) -> list:
        """
        Build Slack Block Kit blocks for a set of regressions.
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
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'Orion detected *{len(regressions)} change point(s)* in account *{account}*.',
                }
            },
            {'type': 'divider'},
        ]

        for regression in regressions:
            ts = regression.get('timestamp', 'unknown')
            metric_lines = []
            for m in regression['metrics']:
                direction = 'increased' if m['percentage_change'] > 0 else 'decreased'
                metric_lines.append(
                    f"*{m['name']}*: {direction} by `{abs(m['percentage_change']):.1f}%` (value: {m['value']})"
                )
            block_text = f"*Date:* {ts}\n" + '\n'.join(metric_lines)
            blocks.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': block_text,
                }
            })

        return blocks

    def post_to_slack(self, blocks: list) -> dict:
        """
        Post blocks to the configured Slack channel. Returns the Slack
        API response dict.
        """
        payload = {
            'channel': self.__slack_channel,
            'blocks': blocks,
        }
        response = requests.post(
            url=self.SLACK_POST_API,
            headers=self.__headers,
            json=payload,
            timeout=30,
        )
        response_data = response.json()
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
