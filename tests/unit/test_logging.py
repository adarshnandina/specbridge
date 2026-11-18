from specbridge.logging_setup import redact_text, redact_value

# Key-shaped fixtures are assembled at runtime so secret scanners never see a literal.
FAKE_ANT = "sk-" + "ant-"
FAKE_AWS = "AK" + "IA" + "ABCDEFGHIJKLMNOP"


def test_redaction():
    assert FAKE_ANT + "abc" not in redact_text(f"key {FAKE_ANT}abc_123")
    assert FAKE_AWS not in redact_text(FAKE_AWS)
    out = redact_value({"X-API-Key": "secret", "nested": [{"authorization": "Bearer x"}], "ok": 1})
    assert out["X-API-Key"] == "[REDACTED]" and out["nested"][0]["authorization"] == "[REDACTED]"
    assert out["ok"] == 1
