import argparse

import pytest

from atomic_agent.examples.minimal_real_provider_loop import (
    parse_float_or_none,
    parse_int_or_none,
    parse_json_object_or_none,
    parse_stop_or_none,
)


def test_parse_float_or_none_accepts_empty_string_as_unset():
    assert parse_float_or_none("") is None


def test_parse_float_or_none_accepts_finite_float():
    assert parse_float_or_none("0.2") == 0.2


def test_parse_float_or_none_rejects_infinity():
    with pytest.raises(argparse.ArgumentTypeError, match="must be a finite number or empty string"):
        parse_float_or_none("inf")


def test_parse_json_object_or_none_accepts_empty_string_as_unset():
    assert parse_json_object_or_none("") is None


def test_parse_json_object_or_none_accepts_object():
    assert parse_json_object_or_none('{"type":"json_object"}') == {"type": "json_object"}


def test_parse_json_object_or_none_rejects_array():
    with pytest.raises(argparse.ArgumentTypeError, match="must be a JSON object or empty string"):
        parse_json_object_or_none("[]")


def test_parse_json_object_or_none_rejects_null():
    with pytest.raises(argparse.ArgumentTypeError, match="must be a JSON object or empty string"):
        parse_json_object_or_none("null")


def test_parse_stop_or_none_accepts_empty_string_as_unset():
    assert parse_stop_or_none("") is None


def test_parse_stop_or_none_accepts_json_array():
    assert parse_stop_or_none('["END_ACTION"]') == ("END_ACTION",)


def test_parse_stop_or_none_rejects_empty_array():
    with pytest.raises(argparse.ArgumentTypeError, match="must be a non-empty JSON array"):
        parse_stop_or_none("[]")


def test_parse_stop_or_none_rejects_non_string_item():
    with pytest.raises(argparse.ArgumentTypeError, match="must be a non-empty JSON array"):
        parse_stop_or_none("[1]")


def test_parse_int_or_none_accepts_empty_string_as_unset():
    assert parse_int_or_none("") is None


def test_parse_int_or_none_accepts_integer():
    assert parse_int_or_none("20260608") == 20260608


def test_parse_int_or_none_rejects_float_string():
    with pytest.raises(argparse.ArgumentTypeError, match="must be an integer or empty string"):
        parse_int_or_none("1.5")
