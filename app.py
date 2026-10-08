import streamlit as st
from pipeline import analyze, follow_up

st.set_page_config(page_title="Job Scam Checker", page_icon="🛡️")
st.title("🛡️ Fake Job / Internship Scam Checker")
st.caption("Paste an offer message. The tool checks the email, domain age, website and scam phrases, then an AI reads the message.")

MAX_CHECKS = 5
MAX_FOLLOWUPS = 5
for key, default in [("count", 0), ("result", None), ("chat", []), ("message", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

message = st.text_area("Paste the job / internship message here", height=220)

if st.button("Check this offer"):
    if not message.strip():
        st.warning("Please paste a message first.")
    elif st.session_state.count >= MAX_CHECKS:
        st.error("Check limit reached for this session. Please try again later.")
    else:
        st.session_state.count += 1
        with st.spinner("Investigating..."):
            report, findings = analyze(message)
        st.session_state.result = (report, findings)
        st.session_state.message = message
        st.session_state.chat = []

if st.session_state.result:
    report, findings = st.session_state.result

    colors = {"LIKELY_SCAM": "red", "SUSPICIOUS": "orange", "LIKELY_GENUINE": "green"}
    st.markdown(f"## :{colors[report.verdict]}[{report.verdict.replace('_', ' ')}]")
    st.progress(report.risk_score / 100, text=f"Risk score: {report.risk_score}/100")

    st.subheader("Evidence")
    for e in report.evidence:
        st.write(f"**{e.severity}**: {e.signal}  \n*source: {e.source_tool}*")

    if "llm_review" in findings:
        st.caption("An AI review was also used because the automated checks found few warning signs.")

    st.subheader("What you should do")
    st.info(report.advice)

    with st.expander("Raw tool results"):
        st.json(findings)

    st.subheader("Ask a follow-up question")
    for role, text in st.session_state.chat:
        with st.chat_message(role):
            st.write(text)

    asked = sum(1 for r, _ in st.session_state.chat if r == "user")
    question = st.chat_input("e.g. Why is this suspicious? What should I reply?")
    if question:
        if asked >= MAX_FOLLOWUPS:
            st.warning("Follow-up limit reached for this check.")
        else:
            with st.spinner("Thinking..."):
                answer = follow_up(question, report, st.session_state.message,
                                   st.session_state.chat)
            st.session_state.chat.append(("user", question))
            st.session_state.chat.append(("assistant", answer))
            st.rerun()

st.caption("This tool gives advice, not a guarantee. Always verify the company on its official website.")