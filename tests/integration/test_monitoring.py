import pytest
from unittest.mock import patch, MagicMock
from backend.infra.monitoring.tracing import (
    should_sample,
    redact_pii,
    sanitize_trace_payload,
    trace_request,
    agent_span,
    mark_turn_guardrail,
    mark_turn_error,
    reset_client_for_tests,
    KNOWN_AGENT_SPANS,
)
import subprocess

def test_should_sample_always_on_guardrail_and_error():
    assert should_sample(is_error=True) is True
    assert should_sample(is_guardrail=True) is True
    assert should_sample(latency_s=5.0, slow_threshold_s=5.0) is True

def test_should_sample_normal_rate_approx_5_percent():
    # with seed
    sampled = sum(1 for i in range(1000) if should_sample(seed=f"test_{i}", normal_rate=0.05))
    # Should be around 50 (allow some variance, say 30-70)
    assert 30 <= sampled <= 70

def test_redact_pii_phone_and_email():
    text = "My email is test@example.com and phone is 0912345678."
    redacted = redact_pii(text)
    assert "test@example.com" not in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert "0912345678" not in redacted
    assert "[PHONE_REDACTED]" in redacted
    
    text2 = "Call me at +84912345678 for details."
    assert "+84912345678" not in redact_pii(text2)
    assert "[PHONE_REDACTED]" in redact_pii(text2)

def test_sanitize_trace_payload_nested():
    payload = {
        "user": "tester",
        "contact": ["0912345678", "test@example.com"],
        "metadata": {
            "email": "hello@world.com"
        }
    }
    sanitized = sanitize_trace_payload(payload)
    assert sanitized["user"] == "tester"
    assert sanitized["contact"] == ["[PHONE_REDACTED]", "[EMAIL_REDACTED]"]
    assert sanitized["metadata"]["email"] == "[EMAIL_REDACTED]"

@patch("backend.infra.monitoring.tracing.should_sample")
@patch("backend.infra.monitoring.tracing._get_langfuse")
@patch("backend.infra.monitoring.tracing._enabled", return_value=True)
def test_trace_request_skips_when_not_sampled(mock_enabled, mock_get_langfuse, mock_should_sample):
    mock_should_sample.return_value = False
    mock_langfuse = MagicMock()
    mock_get_langfuse.return_value = mock_langfuse
    reset_client_for_tests()

    with trace_request("test_span", "input data", metadata={"turn": "123"}):
        with agent_span("123", "rewrite_question", input="q") as box:
            box["output"] = "ok"

    mock_langfuse.trace.assert_not_called()
    mock_langfuse.start_observation.assert_not_called()


@patch("backend.infra.monitoring.tracing._get_langfuse")
@patch("backend.infra.monitoring.tracing._enabled", return_value=True)
def test_guardrail_turn_always_traced(mock_enabled, mock_get_langfuse):
    mock_langfuse = MagicMock()
    mock_root = MagicMock()
    mock_langfuse.trace.return_value = mock_root
    mock_get_langfuse.return_value = mock_langfuse
    reset_client_for_tests()

    turn = "guardrail_turn"
    with patch("backend.infra.monitoring.tracing.should_sample", return_value=False):
        mark_turn_guardrail(turn)
        with trace_request("chat", "inject", metadata={"turn": turn}):
            with agent_span(turn, "guardrail_refusal", input="bad") as box:
                box["output"] = "refused"

    mock_langfuse.trace.assert_called_once()


@patch("backend.infra.monitoring.tracing._get_langfuse")
@patch("backend.infra.monitoring.tracing._enabled", return_value=True)
def test_agent_error_turn_flushes_buffered_spans(mock_enabled, mock_get_langfuse):
    mock_langfuse = MagicMock()
    mock_root = MagicMock()
    mock_child = MagicMock()
    mock_root.span.return_value = mock_child
    mock_langfuse.trace.return_value = mock_root
    mock_get_langfuse.return_value = mock_langfuse
    reset_client_for_tests()

    turn = "error_turn"
    with patch("backend.infra.monitoring.tracing.should_sample", return_value=False):
        with trace_request("chat", "Giá FPT?", metadata={"turn": turn}):
            with agent_span(turn, "price_agent", input="FPT") as box:
                box["output"] = {"error": "rate limit"}
            mark_turn_error(turn)

    mock_langfuse.trace.assert_called_once()
    mock_root.span.assert_called()
    mock_child.update.assert_called()
    update_kwargs = mock_child.update.call_args.kwargs
    assert update_kwargs.get("level") == "ERROR"


@patch("backend.infra.monitoring.tracing._get_langfuse")
@patch("backend.infra.monitoring.tracing._enabled", return_value=True)
@patch("backend.infra.monitoring.tracing.should_sample", return_value=True)
def test_trace_request_creates_root_at_start_when_sampled(
    mock_should_sample, mock_enabled, mock_get_langfuse
):
    mock_langfuse = MagicMock()
    mock_root = MagicMock()
    mock_langfuse.trace.return_value = mock_root
    mock_get_langfuse.return_value = mock_langfuse
    reset_client_for_tests()

    with trace_request("chat", "Giá FPT?", metadata={"turn": "sample_turn"}):
        mock_langfuse.trace.assert_called_once()

    mock_root.update.assert_called()
    mock_root.end.assert_called()


@patch("backend.infra.monitoring.tracing._get_langfuse")
@patch("backend.infra.monitoring.tracing._enabled", return_value=True)
def test_record_step_usage_aggregates_per_turn(mock_enabled, mock_get_langfuse):
    from backend.infra.monitoring.tracing import (
        _current_turn,
        _turn_usage_totals,
        record_step_usage,
    )

    reset_client_for_tests()
    token = _current_turn.set("turn_usage_test")
    try:
        record_step_usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        record_step_usage(prompt_tokens=3, completion_tokens=2, total_tokens=5)
        assert _turn_usage_totals["turn_usage_test"]["input"] == 13
        assert _turn_usage_totals["turn_usage_test"]["output"] == 7
        assert _turn_usage_totals["turn_usage_test"]["total"] == 20
    finally:
        _current_turn.reset(token)
        _turn_usage_totals.pop("turn_usage_test", None)


def test_cost_dashboard_script_runs():
    # Run the dashboard script in a subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "scripts/cost_dashboard.py"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", **import_os_env()}
    )
    assert result.returncode == 0
    assert "Dashboard generated" in result.stdout

def import_os_env():
    import os
    return os.environ.copy()
