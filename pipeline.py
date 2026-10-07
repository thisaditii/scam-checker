import json
import time

import tldextract
from dotenv import load_dotenv
from langchain_groq import ChatGroq

import tools as t
from schemas import LLMOutput, ScamReport, Evidence

load_dotenv()

MODEL_NAME = "openai/gpt-oss-120b"
llm = ChatGroq(model=MODEL_NAME, temperature=0)
structured_llm = llm.with_structured_output(LLMOutput)


def base_domain(value: str) -> str:
    """'https://www.infosys.com/careers' -> 'infosys.com'"""
    ext = tldextract.extract(value)
    return f"{ext.domain}.{ext.suffix}" if ext.domain and ext.suffix else ""


# ---------- Step A: run all tools (uses no tokens) ----------
def run_tools(message: str) -> dict:
    message = message[:3000]
    entities = t.extract_entities(message)
    entities["urls"] = [u.rstrip(".,)") for u in entities["urls"]]

    findings = {
        "entities": entities,
        "red_flags": t.scan_red_flags(message),
        "email_check": None,
        "domain_age": None,
        "website": None,
        "email_site_mismatch": False,
    }

    emails = entities["emails"]
    if emails:
        findings["email_check"] = t.check_email_domain(emails[0])

    company_domain = ""
    if entities["urls"]:
        company_domain = base_domain(entities["urls"][0])
    if not company_domain:
        for e in emails:
            d = e.split("@")[-1].lower()
            if d not in t.FREE_PROVIDERS:
                company_domain = base_domain(d)
                break

    if company_domain:
        findings["domain_age"] = t.check_domain_age(company_domain)
        findings["website"] = t.check_website(company_domain)

    if emails and entities["urls"]:
        e_dom = base_domain(emails[0].split("@")[-1])
        u_dom = base_domain(entities["urls"][0])
        if e_dom and u_dom and e_dom != u_dom and e_dom not in t.FREE_PROVIDERS:
            findings["email_site_mismatch"] = True

    # ----- NEW: extra signals -----
    email_domains = [e.split("@")[-1].lower() for e in emails]
    findings["extra"] = t.extra_signals(message, email_domains)

    # ignore money phrases that appear inside warnings ("never charges any registration fee")
    rf = findings["red_flags"]
    if "asks_for_money" in rf:
        kept = [p for p in rf["asks_for_money"] if not t.has_negation_near(message, p)]
        if kept:
            rf["asks_for_money"] = kept
        else:
            del rf["asks_for_money"]

    return findings


# ---------- Step B: rule-based score (uses no tokens) ----------
def rule_score(f: dict):
    score = 0
    reasons = []

    def add(points, signal, severity, tool):
        nonlocal score
        score += points
        reasons.append({"signal": signal, "severity": severity, "source_tool": tool})

    rf = f["red_flags"]
    if "asks_for_money" in rf:
        add(35, f"Asks for money: {', '.join(rf['asks_for_money'])}", "HIGH", "red_flag_scan")
    if "unprofessional_channel" in rf:
        add(15, f"Unprofessional contact channel: {', '.join(rf['unprofessional_channel'])}", "MEDIUM", "red_flag_scan")
    if "too_good_to_be_true" in rf:
        add(20, f"Too-good-to-be-true claims: {', '.join(rf['too_good_to_be_true'])}", "MEDIUM", "red_flag_scan")
    if "urgency" in rf:
        add(10, f"Pressure or urgency: {', '.join(rf['urgency'])}", "LOW", "red_flag_scan")

    ec = f["email_check"]
    if ec and ec["is_free_provider"]:
        add(20, f"Sender uses a free email provider ({ec['email_domain']})", "MEDIUM", "email_check")

    if f["email_site_mismatch"]:
        add(15, "Email domain does not match the website domain in the message", "MEDIUM", "email_check")

    da = f["domain_age"]
    if da:
        age = da.get("age_days")
        if age is None:
            add(5, f"Domain age for {da['domain']} could not be verified", "LOW", "domain_age")
        elif age < 90:
            add(30, f"Company domain {da['domain']} is only {age} days old", "HIGH", "domain_age")
        elif age < 180:
            add(15, f"Company domain {da['domain']} is only {age} days old", "MEDIUM", "domain_age")

    ws = f["website"]
    if ws:
        status = ws.get("status")
        if status in (401, 403, 429):
            pass  # site blocks bots, so this tells us nothing
        elif not ws.get("reachable"):
            add(15, "Company website could not be reached", "MEDIUM", "website_check")
        elif not ws.get("has_careers_page") and not ws.get("has_contact"):
            add(5, "Website has no careers or contact page", "LOW", "website_check")

    # ----- NEW: extra signals -----
    ex = f.get("extra", {})
    if "asks_sensitive_data" in ex:
        add(40, f"Asks for sensitive data: {', '.join(ex['asks_sensitive_data'])}", "HIGH", "extra_signals")
    if "payment_request" in ex:
        add(35, f"Payment request: {', '.join(ex['payment_request'])}", "HIGH", "extra_signals")
    if "lookalike_domain" in ex:
        add(30, f"Lookalike company domain: {', '.join(ex['lookalike_domain'])}", "HIGH", "extra_signals")
    if "suspicious_tld" in ex:
        add(20, "Suspicious domain ending", "MEDIUM", "extra_signals")
    if "unrealistic_pay" in ex:
        add(15, "Unrealistically high pay claim", "MEDIUM", "extra_signals")

    return min(score, 100), reasons


def verdict_from_score(score: int) -> str:
    if score >= 60:
        return "LIKELY_SCAM"
    if score >= 30:
        return "SUSPICIOUS"
    return "LIKELY_GENUINE"


# ---------- Step C: ONE LLM call to write evidence + advice ----------
def analyze(message: str, retries: int = 3):
    findings = run_tools(message)
    score, reasons = rule_score(findings)
    verdict = verdict_from_score(score)

    prompt = (
        "You are a job-scam advisor for students in India.\n"
        "Below are verified findings from automated checks, and a risk score.\n"
        "Write the evidence list (max 6 items, only from these findings) and "
        "short advice (2-3 sentences). Do not invent facts.\n\n"
        f"Verdict: {verdict}\nRisk score: {score}/100\n"
        f"Findings: {json.dumps(findings, default=str)}\n"
        f"Signals: {json.dumps(reasons)}"
    )

    llm_out = None
    for _ in range(retries):
        try:
            llm_out = structured_llm.invoke(prompt)
            break
        except Exception:
            time.sleep(2)

    if llm_out is None:   # fallback so the app never crashes
        evidence = [Evidence(**r) for r in reasons[:6]]
        advice = ("Do not pay any money or share documents. Verify the company on its "
                  "official website and contact HR through the official email.")
    else:
        evidence, advice = llm_out.evidence, llm_out.advice

    report = ScamReport(verdict=verdict, risk_score=score, evidence=evidence, advice=advice)
    return report, findings


def analyze_rules_only(message: str):
    """No LLM call. Used for evaluation (free and fast)."""
    findings = run_tools(message)
    score, reasons = rule_score(findings)
    return verdict_from_score(score), score, reasons