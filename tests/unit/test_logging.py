from specbridge.logging_setup import redact_text, redact_value


def test_redaction():
    assert "sk-ant-abc" not in redact_text("key sk-ant-abc_123")
    assert "AKIAABCDEFGHIJKLMNOP" not in redact_text("AKIAABCDEFGHIJKLMNOP")
    out = redact_value({"X-API-Key": "secret", "nested": [{"authorization": "Bearer x"}], "ok": 1})
    assert out["X-API-Key"] == "[REDACTED]" and out["nested"][0]["authorization"] == "[REDACTED]"
    assert out["ok"] == 1
