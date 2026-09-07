"""Local diagnostic property signals. These never filter Articles."""

import re
import unicodedata


def sanitize_full_text(text: str) -> str:
    """Make parser text storage-safe without deleting scientific content."""
    text = str(text or "").replace("\x00", "")
    return re.sub("[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f]", "", text).strip()


def match_property_signal(text: str, property_keywords: dict):
    """Return the first deterministic property signal as ``(class, excerpt)``."""
    candidate_patterns = property_keywords.get("candidate_patterns", [])
    if candidate_patterns:
        normalized = unicodedata.normalize("NFKC", text).replace("\x00", " ")
        normalized = re.sub("\\s+", " ", normalized)
        for item in candidate_patterns:
            signal_class = item.get("class", "candidate_pattern")
            pattern = item.get("pattern", "")
            if not pattern:
                continue
            match = re.search(pattern, normalized)
            if match:
                start = max(0, match.start() - 60)
                end = min(len(normalized), match.end() + 60)
                return (signal_class, normalized[start:end])
        return None
    for group_name in ("exact_keywords", "substring_keywords"):
        for keyword in property_keywords.get(group_name, []):
            if keyword in text:
                return (group_name, keyword)
    for pattern in property_keywords.get("regex_keywords", []):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return ("regex_keywords", match.group(0))
    known_groups = {
        "candidate_patterns",
        "exact_keywords",
        "substring_keywords",
        "regex_keywords",
    }
    for group_name, keywords in property_keywords.items():
        if group_name in known_groups or not isinstance(keywords, (list, tuple)):
            continue
        for keyword in keywords:
            if keyword and keyword in text:
                return (group_name, keyword)
    return None


def matches_property_keywords(text: str, property_keywords: dict) -> bool:
    """Return whether text contains a configured property candidate signal."""
    return match_property_signal(text, property_keywords) is not None
