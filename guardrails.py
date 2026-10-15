import re
import unicodedata

# Phrases that try to give instructions to the checker itself.
INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    r"disregard (all |any )?(the )?(previous|prior|above|earlier)",
    r"(mark|label|classify|rate|report|treat) (this|it|the message) as (safe|genuine|legit|legitimate|not (a )?scam)",
    r"do not (flag|mark|report|treat) (this|it)",
    r"(reveal|show|print) (your |the )?(system )?prompt",
    r"new instructions\s*:",
    r"jailbreak",
]
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize(text: str) -> str:
    """Remove hidden/control characters and our own delimiter tags."""
    text = unicodedata.normalize("NFKC", text)           # fullwidth and compatibility lookalikes
    text = "".join(
        ch for ch in text
        if ch in "\n\t" or unicodedata.category(ch) not in ("Cc", "Cf")   # control + zero-width/bidi
    )
    text = re.sub(r"</?\s*message\s*>", " ", text, flags=re.IGNORECASE)    # stop tag break-out
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def detect_injection(text: str) -> list:
    """Return the patterns that matched (empty list = none)."""
    return [p.pattern for p in _INJECTION_RE if p.search(text)]