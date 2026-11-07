"""Crisis-language detection and escalation guidance.

SWASTI is not an emergency service. When free-text suggests serious
distress or a safety risk, the person is shown human crisis resources
immediately. Agents never attempt to counsel or respond as a first responder.
"""
import re

CRISIS_PATTERNS = [
    r"\bsuicid", r"\bkill (my ?self|me)\b", r"\bend (my|it all|my life)\b", r"\bself[- ]?harm",
    r"\bhurt (my ?self)\b", r"\bno reason to live\b", r"\bwant to die\b", r"\bbetter off dead\b",
    r"\bcan'?t go on\b", r"\bhopeless\b",
]
_RX = re.compile("|".join(CRISIS_PATTERNS), re.IGNORECASE)

CRISIS_GUIDANCE = {
    "message": (
        "It sounds like you may be going through something very difficult. You don't have to face "
        "it alone. Please reach out to someone now. SWASTI is not an emergency service."
    ),
    "resources": [
        {"name": "Emergency services (India)", "contact": "112"},
        {"name": "Tele-MANAS — free 24x7 mental health support (MoHFW)", "contact": "14416 or 1-800-891-4416"},
        {"name": "A trusted person, or your nearest hospital emergency department", "contact": ""},
    ],
}


def detect_crisis(*texts: str | None) -> bool:
    return any(t and _RX.search(t) for t in texts)
