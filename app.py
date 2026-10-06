import streamlit as st
from pipeline import analyze

st.set_page_config(page_title="Job Scam Checker", page_icon="🛡️")
st.title("🛡️ Fake Job / Internship Scam Checker")
st.caption("Paste an offer message. The tool checks the email, domain age, website and scam phrases.")

MAX_CHECKS = 5   # protects your daily token limit
if "count" not in st.session_state:
    st.session_state.count = 0

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

        colors = {"LIKELY_SCAM": "red", "SUSPICIOUS": "orange", "LIKELY_GENUINE": "green"}
        st.markdown(f"## :{colors[report.verdict]}[{report.verdict.replace('_', ' ')}]")
        st.progress(report.risk_score / 100, text=f"Risk score: {report.risk_score}/100")

        st.subheader("Evidence")
        for e in report.evidence:
            st.write(f"**{e.severity}**: {e.signal}  \n*source: {e.source_tool}*")

        st.subheader("What you should do")
        st.info(report.advice)

        with st.expander("Raw tool results"):
            st.json(findings)

st.caption("This tool gives advice, not a guarantee. Always verify the company on its official website.")