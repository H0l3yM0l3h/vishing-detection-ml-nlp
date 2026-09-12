"""
intel_extract.py — pull actionable identifiers out of a call transcript.
========================================================================
Why this exists
---------------
Until now the system had two capabilities that never spoke to each other:

  1. the scanner, which classifies the *language* of a call, and
  2. the Threat Intel page, where a user could manually type a phone number
     or bank account and query the PenipuMY scam database.

A vishing call almost always contains a concrete identifier — the number to
call back, the account to transfer money into, the link to "verify" on. Those
identifiers are the part of the call the scammer cannot fake away: the money
has to arrive somewhere real.

Extracting them and checking them against a scam database adds an independent,
factual line of evidence to a verdict that was previously based entirely on
how the sentence was phrased. A transcript can be worded innocently; a bank
account with fourteen fraud reports against it cannot be worded away.

Design notes (FYP Ch.4)
-----------------------
Precision matters far more than recall here. A false "this account is a known
scam account" is much worse than missing one, so:

  * Bank accounts require a nearby context word ("account", "akaun",
    "transfer", a bank name). A bare 10-digit run in a transcript is more
    likely an OTP, a reference number or an amount.
  * OTP-like short codes are explicitly excluded — they are what the scammer
    is trying to *steal*, not where the money goes.
  * Malaysian mobile and landline formats are handled specifically, since the
    deployment target is Malaysia and PenipuMY is a Malaysian database.
"""

from __future__ import annotations

import re

# ── Malaysian phone numbers ────────────────────────────────────────────────
# Mobile:   01X-XXX XXXX  (01X followed by 7 or 8 digits)
# Landline: 0X-XXXX XXXX  (03 KL, 04 Penang, 05 Perak, 06, 07, 08X, 09)
# Also accepts +60 / 60 international prefixes and common separators.
_PHONE_RE = re.compile(
    r"""
    (?<![\w.])                      # not mid-word / mid-decimal
    (?:
        (?:\+?60[\s.-]?)            # +60 / 60 country code
      | 0                           # or a leading national 0
    )
    (?:
        1\d[\s.-]?\d{3,4}[\s.-]?\d{4}     # mobile: 1X XXX(X) XXXX
      | [3-9][\s.-]?\d{3,4}[\s.-]?\d{4}   # landline: X XXX(X) XXXX
    )
    (?![\w])
    """,
    re.VERBOSE,
)

# ── Bank accounts ──────────────────────────────────────────────────────────
# Malaysian account numbers run roughly 10-16 digits. Requiring a context word
# nearby is what keeps this from matching every long number in a transcript.
_ACCOUNT_RE = re.compile(r"(?<![\w.])(\d[\d\s-]{8,20}\d)(?![\w])")

_ACCOUNT_CONTEXT = re.compile(
    r"\b("
    r"account|acct|a/c|akaun|no\.?\s*akaun|"
    r"transfer|transfered|transferred|remit|deposit|bank[\s-]?in|banking|"
    r"maybank|cimb|public\s*bank|rhb|hong\s*leong|ambank|bank\s*islam|"
    r"bsn|ocbc|uob|hsbc|affin|alliance|agrobank|muamalat|rakyat|"
    r"duitnow|ibg|instant\s*transfer"
    r")\b",
    re.IGNORECASE,
)

# ── URLs ───────────────────────────────────────────────────────────────────
_URL_RE = re.compile(
    r"\b(?:https?://|www\.)[^\s<>\"')]+"
    r"|\b[a-z0-9][a-z0-9-]{1,61}\.(?:com|net|org|my|co|io|xyz|top|info|link|site)"
    r"(?:/[^\s<>\"')]*)?\b",
    re.IGNORECASE,
)

# Codes the caller is trying to extract FROM the victim. These are never a
# destination for money and must not be reported as identifiers.
_OTP_CONTEXT = re.compile(
    r"\b(otp|tac|one[\s-]?time|verification\s*code|pin|password|cvv|kod)\b",
    re.IGNORECASE,
)

_CONTEXT_WINDOW = 45


def _context_of(text: str, start: int, end: int, window: int = _CONTEXT_WINDOW) -> str:
    """Return the surrounding text, used for both filtering and display."""
    return text[max(0, start - window): min(len(text), end + window)].strip()


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _normalise_phone(raw: str) -> str:
    """Reduce a phone number to its national form for consistent lookup."""
    d = _digits(raw)
    if d.startswith("60"):
        d = "0" + d[2:]
    if not d.startswith("0"):
        d = "0" + d
    return d


def extract_phones(text: str) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for m in _PHONE_RE.finditer(text or ""):
        normalized = _normalise_phone(m.group(0))
        # Malaysian numbers are 9-11 digits in national form.
        if not (9 <= len(normalized) <= 12) or normalized in seen:
            continue
        seen.add(normalized)
        out.append({
            "value": m.group(0).strip(),
            "normalized": normalized,
            "context": _context_of(text, m.start(), m.end()),
        })
    return out


def extract_accounts(text: str) -> list[dict]:
    """Bank accounts, but only where the surrounding words support it."""
    seen: set[str] = set()
    out: list[dict] = []
    phone_digits = {p["normalized"] for p in extract_phones(text)}

    for m in _ACCOUNT_RE.finditer(text or ""):
        digits = _digits(m.group(1))
        if not (10 <= len(digits) <= 16) or digits in seen:
            continue

        context = _context_of(text, m.start(), m.end())
        if not _ACCOUNT_CONTEXT.search(context):
            continue          # a long number with no banking context nearby
        if _OTP_CONTEXT.search(context):
            continue          # an OTP/TAC the caller wants, not a destination
        if digits in phone_digits or _normalise_phone(digits) in phone_digits:
            continue          # already reported as a phone number

        seen.add(digits)
        out.append({
            "value": m.group(1).strip(),
            "normalized": digits,
            "context": context,
        })
    return out


def extract_urls(text: str) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for m in _URL_RE.finditer(text or ""):
        raw = m.group(0).rstrip(".,;:)")
        key = raw.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "value": raw,
            "normalized": key,
            "context": _context_of(text, m.start(), m.end()),
        })
    return out


def extract_identifiers(text: str) -> dict:
    """All actionable identifiers found in a transcript.

    Returns ``{"phones": [...], "accounts": [...], "urls": [...]}``.
    Each entry carries the raw match, a normalised form for lookup, and the
    surrounding phrase so a user can see *why* it was picked up.
    """
    return {
        "phones": extract_phones(text),
        "accounts": extract_accounts(text),
        "urls": extract_urls(text),
    }


def has_identifiers(extracted: dict) -> bool:
    return any(extracted.get(k) for k in ("phones", "accounts", "urls"))
