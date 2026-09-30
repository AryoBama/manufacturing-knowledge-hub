import re
from typing import List, Optional
from collections import Counter


def tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 1]


def compute_lexical_score(
    query: str,
    content: str,
    target_tag: Optional[str] = None
) -> float:
    """
    Step 2 of Retrieval: Lexical keyword search with exact engineering terminology boost
    """
    q_tokens = tokenize(query)
    if not q_tokens:
        return 0.0

    c_tokens = Counter(tokenize(content))
    c_lower = content.lower()

    # Exact token overlap
    matches = sum(1 for token in q_tokens if token in c_tokens)
    base_score = matches / len(q_tokens)

    # Exact tag boost (+0.3)
    if target_tag and target_tag.lower() in c_lower:
        base_score += 0.3

    # Engineering parameter boosts (e.g. setpoint, rpm, mm/s, trip)
    param_keywords = ["trip", "setpoint", "vibration", "alarm", "bearing", "permissive", "flow", "pressure"]
    for kw in param_keywords:
        if kw in query.lower() and kw in c_lower:
            base_score += 0.05

    return round(min(1.0, base_score), 4)
