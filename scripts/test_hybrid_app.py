from pipeline import analyze

msg = """Hello, I'm from the Human Resources team at a large healthcare group. We came
across your profile and would like to discuss an opportunity. Please reply to
hr.recruitment.team@gmail.com"""

report, findings = analyze(msg)
print(report.verdict, report.risk_score)
for e in report.evidence:
    print(f" [{e.severity}] {e.signal} ({e.source_tool})")
print("Advice:", report.advice)