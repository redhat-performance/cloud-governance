from datetime import datetime

import pytest

from cloud_governance.cloud_resource_orchestration.utils.common_operations import parse_iso_datetime


def test_parse_iso_datetime_plain():
    """Plain ISO datetime string without fractional seconds or timezone offset."""
    assert parse_iso_datetime('2026-07-09T13:00:23') == datetime(2026, 7, 9, 13, 0, 23)


def test_parse_iso_datetime_with_utc_offset():
    """Elasticsearch/OpenSearch serializes a stored `datetime.now(tz=timezone.utc)` back as this format."""
    assert parse_iso_datetime('2026-07-09T13:00:23.548397+00:00') == datetime(2026, 7, 9, 13, 0, 23)


def test_parse_iso_datetime_with_negative_offset():
    assert parse_iso_datetime('2026-07-09T13:00:23.123456-05:00') == datetime(2026, 7, 9, 13, 0, 23)


def test_parse_iso_datetime_with_z_suffix():
    assert parse_iso_datetime('2026-07-09T13:00:23.123456Z') == datetime(2026, 7, 9, 13, 0, 23)


def test_parse_iso_datetime_with_offset_no_fractional_seconds():
    assert parse_iso_datetime('2026-07-09T13:00:23+00:00') == datetime(2026, 7, 9, 13, 0, 23)


def test_parse_iso_datetime_with_fractional_seconds_no_offset():
    assert parse_iso_datetime('2026-07-09T13:00:23.548397') == datetime(2026, 7, 9, 13, 0, 23)


def test_parse_iso_datetime_invalid_raises():
    with pytest.raises(ValueError):
        parse_iso_datetime('not-a-datetime')
