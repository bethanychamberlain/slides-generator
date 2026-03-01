"""Tests for ai.py: JSON repair and parsing helpers."""

import json
from ai import _repair_json_string, parse_json_response


# ── _repair_json_string ──────────────────────────────────────────

class TestRepairJsonString:

    def test_escapes_literal_newline_inside_string(self):
        # A literal newline between quotes should become \\n
        raw = '{"text": "line one\nline two"}'
        repaired = _repair_json_string(raw)
        assert json.loads(repaired) == {"text": "line one\nline two"}

    def test_removes_trailing_comma_before_brace(self):
        raw = '{"a": 1, "b": 2,}'
        repaired = _repair_json_string(raw)
        assert json.loads(repaired) == {"a": 1, "b": 2}

    def test_removes_trailing_comma_before_bracket(self):
        raw = '["a", "b",]'
        repaired = _repair_json_string(raw)
        assert json.loads(repaired) == ["a", "b"]

    def test_valid_json_passes_through(self):
        valid = '{"key": "value", "num": 42}'
        assert _repair_json_string(valid) == valid


# ── parse_json_response ──────────────────────────────────────────

class TestParseJsonResponse:

    def test_parses_clean_json(self):
        result = parse_json_response('{"a": 1}')
        assert result == {"a": 1}

    def test_extracts_from_json_fence(self):
        text = 'Here is the result:\n```json\n{"a": 1}\n```\nDone.'
        assert parse_json_response(text) == {"a": 1}

    def test_extracts_from_plain_fence(self):
        text = 'Result:\n```\n{"a": 1}\n```'
        assert parse_json_response(text) == {"a": 1}

    def test_finds_json_block_in_prose(self):
        text = 'The answer is {"key": "value"} as shown above.'
        assert parse_json_response(text) == {"key": "value"}

    def test_returns_none_for_unparseable(self):
        assert parse_json_response("This is not JSON at all.") is None

    def test_repairs_broken_json_inside_fence(self):
        text = '```json\n{"a": 1, "b": 2,}\n```'
        assert parse_json_response(text) == {"a": 1, "b": 2}
