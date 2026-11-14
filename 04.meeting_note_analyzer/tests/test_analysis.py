import json
from types import SimpleNamespace
from unittest.mock import Mock

from openai import APITimeoutError
import httpx
import pytest

from models import meeting_analyzer


def mock_completion(monkeypatch, content, *, finish_reason="stop", refusal=None):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[
        SimpleNamespace(
            finish_reason=finish_reason,
            message=SimpleNamespace(content=content, refusal=refusal),
        )
    ])
    monkeypatch.setattr(meeting_analyzer, "_get_client", lambda: client)
    return client.chat.completions.create


def test_model_returns_one_validated_result_with_follow_ups(
    monkeypatch, meeting_record, analysis, follow_ups
):
    result = {**analysis, "follow_ups": follow_ups}
    complete = mock_completion(monkeypatch, json.dumps(result))
    actual = meeting_analyzer.analyze_meeting(
        meeting_record["transcript"], meeting_record["participants"], meeting_record["title"]
    )
    assert actual == result
    complete.assert_called_once()
    assert isinstance(json.dumps(actual), str)


@pytest.mark.parametrize(
    "fault",
    ["invalid-json", "missing-follow-ups", "invalid-date", "bad-score", "truncated", "refused"],
)
def test_invalid_model_output_is_an_error(monkeypatch, analysis, follow_ups, fault):
    result = {**analysis, "follow_ups": follow_ups}
    finish_reason = "stop"
    refusal = None
    if fault == "missing-follow-ups":
        del result["follow_ups"]
    elif fault == "invalid-date":
        result["action_items"][0]["due_date"] = "2026-02-30"
    elif fault == "bad-score":
        result["topics"][0]["relevance_score"] = 1.5
    elif fault == "truncated":
        finish_reason = "length"
    elif fault == "refused":
        refusal = "Refused"
    content = "{" if fault == "invalid-json" else json.dumps(result)
    complete = mock_completion(
        monkeypatch, content, finish_reason=finish_reason, refusal=refusal
    )
    with pytest.raises(meeting_analyzer.InvalidAnalysis):
        meeting_analyzer.analyze_meeting("Alice: Publish the roadmap.", ["Alice"])
    complete.assert_called_once()


def test_model_timeout_remains_a_provider_error(monkeypatch):
    complete = mock_completion(monkeypatch, None)
    complete.side_effect = APITimeoutError(request=httpx.Request("POST", "https://example.invalid"))
    with pytest.raises(meeting_analyzer.AnalysisUnavailable):
        meeting_analyzer.analyze_meeting("Alice: Publish the roadmap.", ["Alice"])


def test_missing_model_configuration_is_explicit(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(meeting_analyzer.AnalysisUnavailable):
        meeting_analyzer.analyze_meeting("Alice: Publish the roadmap.", ["Alice"])
