import tools as t
from pipeline import rule_score, verdict_from_score


def test_fee_phrase_detected():
    assert "asks_for_money" in t.scan_red_flags("Pay registration fee Rs 1500 today")


def test_clean_message_has_no_flags():
    assert t.scan_red_flags("Please attend the interview on Monday") == {}


def test_negation_detected():
    msg = "Flipkart never charges any registration fee"
    assert t.has_negation_near(msg, "registration fee")


def test_sensitive_data_detected():
    out = t.extra_signals("Share your aadhaar and bank account", [])
    assert "asks_sensitive_data" in out


def test_free_email_provider_flag():
    assert t.check_email_domain("hr@gmail.com")["is_free_provider"] is True
    assert t.check_email_domain("hr@infosys.com")["is_free_provider"] is False


def test_verdict_thresholds():
    assert verdict_from_score(0) == "LIKELY_GENUINE"
    assert verdict_from_score(30) == "SUSPICIOUS"
    assert verdict_from_score(60) == "LIKELY_SCAM"


def test_score_is_capped():
    f = {"red_flags": {"asks_for_money": ["x"], "urgency": ["y"]},
         "email_check": {"is_free_provider": True, "email_domain": "gmail.com"},
         "email_site_mismatch": False, "domain_age": None, "website": None,
         "extra": {"asks_sensitive_data": ["otp"], "payment_request": ["upi"]}}
    score, _ = rule_score(f)
    assert score == 100