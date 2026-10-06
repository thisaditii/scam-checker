from tools import *

scam_msg = """Congratulations! You are selected for Data Entry Internship.
No interview needed. Pay registration fee Rs 1500 (refundable) within 24 hours.
Contact on WhatsApp only: 9876543210. Email: hr.jobsindia@gmail.com"""

print("1. Entities:", extract_entities(scam_msg))
print("2. Red flags:", scan_red_flags(scam_msg))
print("3. Email check:", check_email_domain("hr.jobsindia@gmail.com"))
print("4. Domain age (google.com):", check_domain_age("google.com"))
print("5. Website (python.org):", check_website("python.org"))