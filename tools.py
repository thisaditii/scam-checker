import re
from datetime import datetime

import requests
import whois
from bs4 import BeautifulSoup


# ---------- Tool 1: Extract emails, URLs, phone numbers ----------
def extract_entities(text: str) -> dict:
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    urls = re.findall(r"https?://[^\s]+|www\.[^\s]+", text)
    phones = re.findall(r"(?:\+91[\s-]?)?[6-9]\d{9}", text)
    return {"emails": emails, "urls": urls, "phones": phones}


# ---------- Tool 2: How old is the domain? ----------
def check_domain_age(domain: str) -> dict:
    try:
        w = whois.whois(domain)
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if not created:
            return {"domain": domain, "age_days": None, "note": "unknown"}
        created = created.replace(tzinfo=None)
        age_days = (datetime.now() - created).days
        return {"domain": domain, "age_days": age_days}
    except Exception as e:
        return {"domain": domain, "age_days": None, "note": f"lookup failed: {e}"}


# ---------- Tool 3: Check the sender email ----------
FREE_PROVIDERS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"}

def check_email_domain(email: str, company_site: str = "") -> dict:
    domain = email.split("@")[-1].lower()
    return {
        "email_domain": domain,
        "is_free_provider": domain in FREE_PROVIDERS,
        "matches_company_site": bool(company_site) and domain in company_site.lower(),
    }


# ---------- Tool 4: Scan for scam phrases ----------
RED_FLAGS = {
    "asks_for_money": ["registration fee", "security deposit", "refundable",
                       "training fee", "processing fee", "pay rs", "pay ₹"],
    "unprofessional_channel": ["whatsapp only", "telegram", "contact on whatsapp"],
    "too_good_to_be_true": ["no interview", "guaranteed job", "earn per day",
                            "work from home earn", "limited seats"],
    "urgency": ["urgent", "within 24 hours", "immediately", "last chance"],
}

def scan_red_flags(text: str) -> dict:
    t = text.lower()
    found = {cat: [p for p in phrases if p in t] for cat, phrases in RED_FLAGS.items()}
    return {k: v for k, v in found.items() if v}


# ---------- Tool 5: Check the company website ----------
def check_website(url: str) -> dict:
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ").lower()
        return {
            "reachable": r.status_code == 200,
            "status": r.status_code,
            "has_careers_page": "career" in text or "jobs" in text,
            "has_contact": "contact" in text,
            "title": soup.title.string.strip() if soup.title and soup.title.string else None,
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}