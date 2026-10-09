from agent import investigate

scam = """Congratulations! You are selected for Data Entry Internship.
No interview needed. Pay registration fee Rs 1500 (refundable) within 24 hours.
Contact on WhatsApp only: 9876543210. Email: hr.jobsindia@gmail.com"""

genuine = """Hi, we are pleased to invite you for an interview for the Software
Intern role at Infosys. Please reply to confirm a slot. Details at
https://www.infosys.com/careers. Regards, Talent Team, careers@infosys.com"""

for name, msg in [("SCAM SAMPLE", scam), ("GENUINE SAMPLE", genuine)]:
    print("=" * 60)
    print(name)
    text, calls = investigate(msg)
    print("\nTools used:")
    for c in calls:
        print(" -", c["tool"], "->", c["output"][:120])
    print("\nAgent summary:\n", text)