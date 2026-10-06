import re
from datetime import datetime

import requests
import whois
from bs4 import BeautifulSoup

def extract_entities(text: str) -> dict:
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    urls = re.findall(r"https?://[^\s]+|www\.[^\s]+", text)
    phones = re.findall(r"(?:\+91[\s-]?)?[6-9]\d{9}", text)
    return {"emails": emails, "urls": urls, "phones": phones}


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

FREE_PROVIDERS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"}

def check_email_domain(email: str, company_site: str = "") -> dict:
    domain = email.split("@")[-1].lower()
    return {
        "email_domain": domain,
        "is_free_provider": domain in FREE_PROVIDERS,
        "matches_company_site": bool(company_site) and domain in company_site.lower(),
    }


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


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def check_website(url: str) -> dict:
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=8, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ").lower()
        blocked = r.status_code in (401, 403, 429)
        return {
            "reachable": r.status_code == 200,
            "status": r.status_code,
            "has_careers_page": None if blocked else ("career" in text or "jobs" in text),
            "has_contact": None if blocked else ("contact" in text),
            "title": soup.title.string.strip() if soup.title and soup.title.string else None,
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}