import csv
import html
import os
import uuid
from datetime import datetime

import streamlit as st
from pypdf import PdfReader

from pipeline import analyze, follow_up

st.set_page_config(page_title="Job Scam Checker", page_icon="🛡️", layout="centered")

MAX_CHECKS = 5
MAX_FOLLOWUPS = 5
FEEDBACK_FILE = "data/feedback.csv"
USAGE_FILE = "data/usage/usage.csv"

# ---------------- Style ----------------
st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 760px;}
#MainMenu, footer {visibility: hidden;}

.hero {text-align:center; margin-bottom: 1.2rem;}
.hero h1 {font-size: 2.1rem; font-weight: 800; margin-bottom: .2rem;}
.hero p {opacity: .7; font-size: 1rem; margin-top: 0;}

.verdict {border-radius: 18px; padding: 1.4rem 1.6rem; margin: 1rem 0 .6rem 0;
          border: 1px solid rgba(128,128,128,.25);}
.verdict .label {font-size: .8rem; letter-spacing: .12em; opacity: .75; font-weight: 600;}
.verdict .title {font-size: 1.9rem; font-weight: 800; margin: .15rem 0;}
.verdict .sub {opacity: .8; font-size: .95rem;}
.v-scam {background: rgba(239,68,68,.12);  border-color: rgba(239,68,68,.45);}
.v-sus  {background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.45);}
.v-ok   {background: rgba(34,197,94,.12);  border-color: rgba(34,197,94,.45);}

.ev {display:flex; gap:.7rem; align-items:flex-start; padding:.7rem .9rem; margin-bottom:.5rem;
     border-radius:12px; border:1px solid rgba(128,128,128,.2);}
.badge {font-size:.68rem; font-weight:700; padding:.18rem .55rem; border-radius:999px;
        letter-spacing:.06em; white-space:nowrap; margin-top:.15rem;}
.b-HIGH {background: rgba(239,68,68,.18); color:#ef4444;}
.b-MEDIUM {background: rgba(245,158,11,.18); color:#f59e0b;}
.b-LOW {background: rgba(59,130,246,.18); color:#3b82f6;}
.ev .txt {font-size:.95rem; line-height:1.35;}
.ev .src {font-size:.75rem; opacity:.55; margin-top:.1rem;}

.stButton>button {border-radius: 12px; font-weight: 600;}
.stButton>button[kind="primary"] {width: 100%; padding: .65rem 0;}
</style>
""", unsafe_allow_html=True)

# ---------------- State ----------------
for key, default in [("count", 0), ("result", None), ("chat", []),
                     ("message", ""), ("feedback_given", False)]:
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------- Helpers ----------------
def log_event(event, detail=""):
    """Anonymous usage log: time, random session id, event. No IP, no message text."""
    try:
        os.makedirs("data/usage", exist_ok=True)
        is_new = not os.path.exists(USAGE_FILE)
        with open(USAGE_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(["time", "session", "event", "detail"])
            w.writerow([datetime.now().isoformat(timespec="seconds"),
                        st.session_state.sid, event, detail])
    except Exception:
        pass   # logging must never break the app


if "sid" not in st.session_state:
    st.session_state.sid = uuid.uuid4().hex[:8]
    log_event("visit")


def pdf_to_text(file) -> str:
    reader = PdfReader(file)
    return "\n".join((p.extract_text() or "") for p in reader.pages[:6])


def save_feedback(verdict, score, user_says, text):
    os.makedirs("data", exist_ok=True)
    is_new = not os.path.exists(FEEDBACK_FILE)
    with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["time", "verdict", "score", "user_says", "text"])
        w.writerow([datetime.now().isoformat(timespec="seconds"),
                    verdict, score, user_says, text])


VERDICT_UI = {
    "LIKELY_SCAM":    ("v-scam", "🚨", "Likely a scam",
                       "Strong warning signs found. Do not pay or share documents."),
    "SUSPICIOUS":     ("v-sus", "⚠️", "Suspicious",
                       "Some warning signs found. Verify before you proceed."),
    "LIKELY_GENUINE": ("v-ok", "✅", "Likely genuine",
                       "Few warning signs found. Still verify through official channels."),
}
SEV_ICON = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🔵"}
SOURCE_NAME = {
    "red_flag_scan": "📝 Scam phrases", "email_check": "📧 Sender email",
    "domain_age": "🌐 Domain age", "website_check": "🔗 Website",
    "extra_signals": "🧩 Pattern check", "llm_extract": "🤖 AI reading",
    "llm_review": "🤖 AI review",
}

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### Scam Checker")
    left = max(MAX_CHECKS - st.session_state.count, 0)
    st.metric("Checks left this session", f"{left} / {MAX_CHECKS}")
    st.markdown("---")
    st.markdown("**How it works**")
    st.markdown(
        "1. Checks sender email, domain age and website\n"
        "2. Scans for scam phrases and patterns\n"
        "3. AI reads the message for a second opinion\n"
        "4. You get a score, evidence and advice"
    )
    st.markdown("---")
    st.caption("Advisory tool, not a guarantee. Always verify the company on its official website.")

# ---------------- Header ----------------
st.markdown(
    '<div class="hero"><h1>🛡️ Job Scam Checker</h1>'
    '<p>Check an internship or job offer before you reply, pay or share documents.</p></div>',
    unsafe_allow_html=True,
)

# ---------------- Input ----------------
mode = st.radio("Input", ["✍️ Paste text", "📄 Upload PDF"], horizontal=True,
                label_visibility="collapsed")

message, uploaded = "", None
if mode == "✍️ Paste text":
    message = st.text_area("Offer message", height=180, label_visibility="collapsed",
                           placeholder="Paste the offer message or email here...")
else:
    uploaded = st.file_uploader("Offer letter (PDF)", type=["pdf"],
                                label_visibility="collapsed")

sender_email = st.text_input("📧 Sender email",
                             placeholder="hr@company.com, helps the email check")
st.caption("🔒 Your text and files are not stored unless you choose to share them in the feedback step.")

if st.button("🔎 Check this offer", type="primary"):
    text = message
    if uploaded is not None:
        try:
            text = pdf_to_text(uploaded)
        except Exception:
            text = ""
        if not text.strip():
            st.error("Could not read text from this PDF. It may be a scan or protected. "
                     "Please paste the text instead.")
            st.stop()
    if sender_email.strip():
        text = f"From: {sender_email.strip()}\n{text}"

    if not text.strip():
        st.warning("Please paste a message or upload a PDF first.")
    elif st.session_state.count >= MAX_CHECKS:
        st.error("Check limit reached for this session. Please try again later.")
    else:
        st.session_state.count += 1
        with st.spinner("Investigating..."):
            report, findings = analyze(text)
        log_event("check", report.verdict)
        st.session_state.result = (report, findings)
        st.session_state.message = text
        st.session_state.chat = []
        st.session_state.feedback_given = False
        st.rerun()

# ---------------- Result ----------------
if st.session_state.result:
    report, findings = st.session_state.result
    css, icon, title, sub = VERDICT_UI[report.verdict]

    st.markdown(
        f'<div class="verdict {css}"><div class="label">VERDICT</div>'
        f'<div class="title">{icon} {title}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )
    st.progress(report.risk_score / 100, text=f"Risk score: {report.risk_score} / 100")

    st.markdown("#### 🔎 Evidence")
    if not report.evidence:
        st.caption("No warning signs were found.")
    for e in report.evidence:
        src = SOURCE_NAME.get(e.source_tool, e.source_tool)
        st.markdown(
            f'<div class="ev"><span class="badge b-{e.severity}">{SEV_ICON[e.severity]} {e.severity}</span>'
            f'<div><div class="txt">{html.escape(e.signal)}</div>'
            f'<div class="src">{html.escape(src)}</div></div></div>',
            unsafe_allow_html=True,
        )
    if "llm_review" in findings:
        st.caption("🤖 An AI review was also used because the automated checks found few warning signs.")

    st.markdown("#### 💡 What you should do")
    with st.container(border=True):
        st.write(report.advice)

    if report.verdict == "LIKELY_SCAM":
        st.warning("🚔 If you lost money, report it at **cybercrime.gov.in** or call the **1930** helpline.")

    with st.expander("🧰 Raw tool results"):
        st.json(findings)

    # ---------- Feedback ----------
    st.markdown("#### 🙋 Was this result right?")
    if st.session_state.feedback_given:
        st.success("Thanks for your feedback! 🙌")
    else:
        share = st.checkbox("Share the message text to help improve the tool "
                            "(remove names and phone numbers first)")
        c1, c2, c3 = st.columns(3)
        choice = None
        if c1.button("👍 Correct", use_container_width=True):
            choice = "correct"
        if c2.button("👎 Wrong", use_container_width=True):
            choice = "wrong"
        if c3.button("🤷 Not sure", use_container_width=True):
            choice = "not_sure"
        if choice:
            save_feedback(report.verdict, report.risk_score, choice,
                          st.session_state.message[:3000] if share else "")
            log_event("feedback", choice)
            st.session_state.feedback_given = True
            st.rerun()

    # ---------- Follow-up chat ----------
    st.markdown("#### 💬 Ask a follow-up")
    for role, text_ in st.session_state.chat:
        with st.chat_message(role):
            st.write(text_)

    asked = sum(1 for r, _ in st.session_state.chat if r == "user")
    question = st.chat_input("e.g. Why is this suspicious? What should I reply?")
    if question:
        if asked >= MAX_FOLLOWUPS:
            st.warning("Follow-up limit reached for this check.")
        else:
            with st.spinner("Thinking..."):
                answer = follow_up(question, report, st.session_state.message,
                                   st.session_state.chat)
            log_event("followup")
            st.session_state.chat.append(("user", question))
            st.session_state.chat.append(("assistant", answer))
            st.rerun()