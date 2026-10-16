import hashlib
import json
import sys

import pandas as pd

FEATURES = [
    "free_email", "email_site_mismatch", "fee_phrase", "bad_channel", "too_good", "urgency",
    "sensitive_data", "payment_request", "lookalike_domain", "unrealistic_pay",
    "other_scam_pattern", "domain_young", "company_mismatch",
    "llm_asks_money", "llm_asks_docs", "llm_suspicious",
]


def key(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def featurize(raw):
    f, reasons = raw["findings"], raw["reasons"]
    rf, ex = f.get("red_flags", {}), f.get("extra", {})
    ec, da = f.get("email_check") or {}, f.get("domain_age") or {}
    lx, op = raw.get("extract") or {}, raw.get("opinion") or {}
    age = da.get("age_days")
    return {
        "free_email": int(bool(ec.get("is_free_provider"))),
        "email_site_mismatch": int(bool(f.get("email_site_mismatch"))),
        "fee_phrase": int("asks_for_money" in rf),
        "bad_channel": int("unprofessional_channel" in rf),
        "too_good": int("too_good_to_be_true" in rf),
        "urgency": int("urgency" in rf),
        "sensitive_data": int("asks_sensitive_data" in ex),
        "payment_request": int("payment_request" in ex),
        "lookalike_domain": int("lookalike_domain" in ex),
        "unrealistic_pay": int("unrealistic_pay" in ex),
        "other_scam_pattern": int(any(k in ex for k in
                                      ("equipment_check_scam", "paid_internship_offer", "suspicious_tld"))),
        "domain_young": int(age is not None and age < 180),
        "company_mismatch": int(any("does not match sender domain" in r["signal"] for r in reasons)),
        "llm_asks_money": int(bool(lx.get("asks_for_money"))),
        "llm_asks_docs": int(bool(lx.get("asks_for_documents"))),
        "llm_suspicious": int(bool(op.get("is_suspicious"))),
    }


if __name__ == "__main__":
    out_path, *inputs = sys.argv[1:]
    rows = []
    for path in inputs:
        df = pd.read_csv(path)
        for text, label in zip(df["text"], df["label"]):
            try:
                with open(f"experiments/raw/{key(text)}.json", encoding="utf-8") as fh:
                    raw = json.load(fh)
            except FileNotFoundError:
                print("missing raw output for:", text[:60])
                continue
            row = {"key": key(text), "source": path, "label": label, "hand_score": raw["hand_score"]}
            row.update(featurize(raw))
            rows.append(row)
    pd.DataFrame(rows).drop_duplicates(subset="key").to_csv(out_path, index=False)
    print(len(rows), "rows saved to", out_path)