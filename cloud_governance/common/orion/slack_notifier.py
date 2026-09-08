import json
import logging
import math
import re
from datetime import datetime, timezone, timedelta

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
    # Orion's JSON output re-lists every change point in the entire historical
    # series on every run, not just newly-detected ones. Without a recency
    # cutoff, a change point from months ago would be re-alerted on every
    # single daily run forever. Only surface change points recent enough to
    # plausibly be from "what just happened", not "what Orion has ever seen".
    RECENCY_WINDOW_DAYS = 35
    # Known cloud/service abbreviations that should stay all-caps when a
    # config metric name (e.g. "awsCostIncrease") is humanized for display.
    ACRONYMS = {'aws': 'AWS', 'ibm': 'IBM', 'gcp': 'GCP', 'ec2': 'EC2', 's3': 'S3'}

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
        A numeric-but-malformed value (NaN, +/-inf, out-of-range) fails the
        conversion; fall back to the raw value rather than raising.
        """
        if isinstance(ts, (int, float)):
            try:
                return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d')
            except (ValueError, OverflowError, OSError):
                return str(ts)
        return str(ts)

    @staticmethod
    def extract_regressions(data_points: list, reference_date: datetime = None) -> list:
        """
        Walk the Orion JSON array and pull out recent change points with
        their regressed metrics.

        Change points older than RECENCY_WINDOW_DAYS (relative to
        reference_date, default now) are skipped - see RECENCY_WINDOW_DAYS
        for why. Entries whose timestamp can't be parsed - missing, wrong
        type, or numeric-but-malformed (NaN/+-inf/out-of-range) - are not
        filtered out (fail open: a missed alert is worse than an extra one).

        A metric's percentage_change can be NaN (0 -> 0, no real change -
        skipped) or +/-inf (a zero baseline dividing into a nonzero value -
        kept, but displayed without a misleading "inf%").
        @param data_points: Orion's parsed JSON array
        @param reference_date: reference point for the recency cutoff (for tests); defaults to now (UTC)
        """
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)
        cutoff = reference_date - timedelta(days=OrionSlackNotifier.RECENCY_WINDOW_DAYS)

        regressions = []
        for entry in data_points:
            if not entry.get('is_changepoint'):
                continue
            timestamp = entry.get('timestamp')
            if isinstance(timestamp, (int, float)):
                try:
                    entry_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                except (ValueError, OverflowError, OSError):
                    entry_date = None
                if entry_date is not None and entry_date < cutoff:
                    continue
            metrics = entry.get('metrics', {})
            changed_metrics = []
            for metric_name, metric_data in metrics.items():
                pct = metric_data.get('percentage_change', 0)
                if isinstance(pct, float) and math.isnan(pct):
                    continue
                if pct != 0:
                    changed_metrics.append({
                        'name': metric_name,
                        'value': metric_data.get('value'),
                        'percentage_change': pct if (isinstance(pct, float) and math.isinf(pct)) else round(pct, 2),
                    })
            if changed_metrics:
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

    @staticmethod
    def _humanize_metric_name(name: str) -> str:
        """
        Turn a config metric name (e.g. "awsCostIncrease" or
        "zombieClusterResourceCountIncrease") into a readable label
        ("AWS Cost", "Zombie Cluster Resource Count") for display.
        """
        base = re.sub(r'(Increase|Decrease)$', '', name)
        spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', base)
        words = spaced.split()
        return ' '.join(OrionSlackNotifier.ACRONYMS.get(w.lower(), w.capitalize()) for w in words)

    @staticmethod
    def _estimate_baseline(value, pct):
        """
        Best-effort "before" level implied by the current value and
        percentage_change (value = baseline * (1 + pct/100)). None if it
        can't be computed (missing value, or an exact -100% change where
        the baseline is mathematically undefined from these two numbers
        alone).
        """
        if value is None:
            return None
        denominator = 1 + pct / 100
        if denominator == 0:
            return None
        return value / denominator

    @staticmethod
    def _format_metric_line(display_name: str, pct, value) -> str:
        """
        Describe one metric's change point in terms of the shift it
        represents (before -> after), not just a bare percentage - a lasting
        step to a new level is the whole point of change-point detection,
        as opposed to a single noisy data point.
        """
        direction = 'increased' if pct > 0 else 'decreased'
        if isinstance(pct, float) and math.isinf(pct):
            # A zero baseline makes the percentage mathematically undefined
            # (division by zero) - showing "inf%" would be misleading.
            detail = 'increased from a zero baseline (new)' if pct > 0 else 'decreased to zero'
            return f"*{display_name}*: {detail}"
        baseline = OrionSlackNotifier._estimate_baseline(value, pct)
        if baseline is None or value is None:
            return f"*{display_name}*: {direction} by `{abs(pct):.1f}%`"
        return f"*{display_name}*: {direction} from ~{round(baseline):,} to {value:,} ({pct:+.1f}%, sustained)"

    def _regression_section_blocks(self, regression: dict) -> list:
        """
        Build the section block(s) for one regression, splitting the text
        across multiple sections if it would exceed the per-section char
        limit (a regression with many metrics can produce a long body).
        """
        ts = regression.get('timestamp', 'unknown')
        lines = [f"*Date:* {ts}"]
        for m in regression['metrics']:
            # Orion's JSON output keys metrics as "<config_name>_<metric_of_interest>"
            # (e.g. "zombieClusterResourceCountIncrease_zombie_cluster_resource_count").
            # Config metric names are plain camelCase with no underscores, so the part
            # before the first underscore is always just the readable config name.
            display_name = self._humanize_metric_name(m['name'].split('_', 1)[0])
            lines.append(self._format_metric_line(display_name, m['percentage_change'], m['value']))

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

    def notify(self, file_path: str, account: str, reference_date: datetime = None) -> dict:
        """
        End-to-end: parse Orion output, extract regressions, post to Slack.
        @param reference_date: reference point for the recency cutoff (for tests); defaults to now (UTC)
        Returns a summary dict.
        """
        data_points = self.parse_orion_json(file_path)
        regressions = self.extract_regressions(data_points, reference_date=reference_date)

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
