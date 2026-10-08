import json
import re
import time

import tldextract
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

import tools as t
from schemas import LLMOutput, ScamReport, Evidence, SecondOpinion, ExtractedInfo

load_dotenv()

MODEL_NAME = "openai/gpt-oss-120b"
llm = ChatGroq(model=MODEL_NAME, temperature=0)

# ---------------- LangChain chains (prompt | model) ----------------
extract_chain = ChatPromptTemplate.from_messages([
    ("system",
     "You extract facts from a job or internship message sent to a student. "
     "Report only what the text says. Do not guess. "
     "asks_for_money is true only when the sender demands payment from the candidate; "
     "it is false when the message merely warns that no fee is charged."),
    ("human", "{message}"),
]) | llm.with_structured_output(ExtractedInfo)

opinion_chain = ChatPromptTemplate.from_messages([
    ("system",
     "You are checking a job or internship message sent to a student in India. "
     "Decide whether it looks like a scam. Signs of a scam: a recruiter writing from a "
     "free email address (gmail, yahoo) while claiming to represent a large organisation, "
     "a vague or unknown company, unrealistic pay, an offer with no application or "
     "interview, a request for money, documents or ID, or an interview arranged through "
     "a chat app. Only answer suspicious if you can point to a specific sign in the text."),
    ("human", "{message}"),
]) | llm.with_structured_output(SecondOpinion)

report_chain = ChatPromptTemplate.from_messages([
    ("system",
     "You are a job-scam advisor for students in India. You receive verified findings from "
     "automated checks and a risk score. Write the evidence list (max 6 items, only from the "
     "findings) and short advice (2-3 sentences). Do not invent facts."),
    ("human", "Verdict: {verdict}\nRisk score: {score}/100\nFindings: {findings}\nSignals: {signals}"),
]) | llm.with_structured_output(LLMOutput)

chat_chain = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful job-scam advisor for students in India. Answer follow-up questions "
     "about the report below in simple language, in at most 4 sentences. Use only the report "
     "and the original message. If something is not in the report, say you cannot tell. "
     "Never tell the student to pay money or share documents.\n\nReport: {report}\n\n"
     "Original message: {message}"),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
]) | llm | StrOutputParser()


def call(chain, inputs, retries=3):
    """Run a chain with retries. Returns None if it keeps failing."""
    for _ in range(retries):
        try:
            return chain.invoke(inputs)
        except Exception:
            time.sleep(2)
    return None


def base_domain(value: str) -> str:
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

    email_domains = [e.split("@")[-1].lower() for e in emails]
    findings["extra"] = t.extra_signals(message, email_domains)

    rf = findings["red_flags"]
    if "asks_for_money" in rf:
        kept = [p for p in rf["asks_for_money"] if not t.has_negation_near(message, p)]
        if kept:
            rf["asks_for_money"] = kept
        else:
            del rf["asks_for_money"]

    return findings


# ---------- Step B: rule-based score (uses no tokens) ----------
GENERIC_WORDS = {"limited", "private", "technologies", "technology", "solutions", "group",
                 "services", "airways", "global", "india", "company", "team", "talent"}
PLATFORM_DOMAINS = ("greenhouse", "smartrecruiters", "ashbyhq", "myworkday", "lever.co",
                    "unstop", "foundit", "naukri", "linkedin", "workable", "icims")


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
            pass
        elif not ws.get("reachable"):
            add(15, "Company website could not be reached", "MEDIUM", "website_check")
        elif not ws.get("has_careers_page") and not ws.get("has_contact"):
            add(5, "Website has no careers or contact page", "LOW", "website_check")

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
        add(30, "Unrealistically high pay claim", "MEDIUM", "extra_signals")
    if "equipment_check_scam" in ex:
        add(40, f"Equipment-check scam pattern: {', '.join(ex['equipment_check_scam'])}", "HIGH", "extra_signals")
    if "paid_internship_offer" in ex:
        add(35, "Internship or training sold for a fee", "HIGH", "extra_signals")

    # ----- signals from the LLM extraction chain -----
    lx = f.get("llm_extract")
    if lx:
        if lx.get("asks_for_money") and "asks_for_money" not in rf and "payment_request" not in ex:
            add(35, "AI reading: the message asks the candidate to pay money", "HIGH", "llm_extract")
        if lx.get("asks_for_documents") and "asks_sensitive_data" not in ex:
            add(25, "AI reading: the message asks for ID or personal documents", "MEDIUM", "llm_extract")

        company = (lx.get("company_name") or "").lower()
        if company and ec and not ec["is_free_provider"]:
            dom = ec["email_domain"].replace("-", "")
            tokens = [w for w in re.findall(r"[a-z0-9]+", company)
                      if len(w) > 3 and w not in GENERIC_WORDS]
            on_platform = any(p in dom for p in PLATFORM_DOMAINS)
            if tokens and not on_platform and not any(w in dom for w in tokens):
                add(20, f"Claimed company '{lx['company_name']}' does not match sender domain {ec['email_domain']}",
                    "MEDIUM", "llm_extract")

    return min(score, 100), reasons


def verdict_from_score(score: int) -> str:
    if score >= 60:
        return "LIKELY_SCAM"
    if score >= 30:
        return "SUSPICIOUS"
    return "LIKELY_GENUINE"


# ---------- Rules + LLM assessment (shared by the app and the evaluation) ----------
def assess(message: str):
    findings = run_tools(message)

    info = call(extract_chain, {"message": message[:2000]})
    if info is not None:
        findings["llm_extract"] = info.model_dump()

    score, reasons = rule_score(findings)

    if score < 30:
        opinion = call(opinion_chain, {"message": message[:2000]})
        if opinion is not None and opinion.is_suspicious:
            score = 30
            reasons.append({"signal": f"LLM review: {opinion.reason}",
                            "severity": "MEDIUM", "source_tool": "llm_review"})
            findings["llm_review"] = opinion.reason

    return findings, score, reasons


# ---------- Full analysis for the app ----------
def analyze(message: str):
    findings, score, reasons = assess(message)
    verdict = verdict_from_score(score)

    out = call(report_chain, {
        "verdict": verdict, "score": score,
        "findings": json.dumps(findings, default=str),
        "signals": json.dumps(reasons),
    })

    if out is None:
        evidence = [Evidence(**r) for r in reasons[:6]]
        advice = ("Do not pay any money or share documents. Verify the company on its "
                  "official website and contact HR through the official email.")
    else:
        evidence, advice = out.evidence, out.advice

    report = ScamReport(verdict=verdict, risk_score=score, evidence=evidence, advice=advice)
    return report, findings


# ---------- Follow-up chat ----------
def follow_up(question: str, report, message: str, history: list):
    msgs = [HumanMessage(content=t_) if r == "user" else AIMessage(content=t_)
            for r, t_ in history]
    out = call(chat_chain, {
        "report": report.model_dump_json(),
        "message": message[:1500],
        "history": msgs,
        "question": question,
    })
    return out or "Sorry, I could not answer that right now. Please try again."


# ---------- Evaluation helpers ----------
def analyze_rules_only(message: str):
    """No LLM call. Rules only."""
    findings = run_tools(message)
    score, reasons = rule_score(findings)
    return verdict_from_score(score), score, reasons


def analyze_hybrid(message: str):
    """Rules + LLM extraction + LLM second opinion (same logic as the app)."""
    findings, score, reasons = assess(message)
    return verdict_from_score(score), score, reasons, True