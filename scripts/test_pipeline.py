from pipeline import analyze

scam = """Congratulations! You are selected for Data Entry Internship.
No interview needed. Pay registration fee Rs 1500 (refundable) within 24 hours.
Contact on WhatsApp only: 9876543210. Email: hr.jobsindia@gmail.com"""

genuine = """Hi, we are pleased to invite you for an interview for the Software
Intern role at Infosys. Please reply to confirm a slot. Details at
https://www.infosys.com/careers. Regards, Talent Team, careers@infosys.com"""

for name, msg in [("SCAM", scam), ("GENUINE", genuine)]:
    report, findings = analyze(msg)
    print("=" * 50)
    print(name, "->", report.verdict, report.risk_score)
    for e in report.evidence:
        print(f" [{e.severity}] {e.signal}  ({e.source_tool})")
    print("Advice:", report.advice)