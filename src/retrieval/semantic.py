from collections import Counter


def _char_ngrams(text: str, n: int = 3) -> Counter:
    s = text.lower()
    return Counter([s[i:i+n] for i in range(len(s) - n + 1)])


def compute_fuzzy_subword_score(query: str, content: str) -> float:
    """
    Step 3 of Retrieval: Character-level fuzzy / subword similarity (character 3-gram cosine).
    Provides robust term-variant matching (e.g. 'vibrates' vs 'vibration', 'leaking' vs 'leakage')
    without requiring external heavyweight dense embedding vectors.
    """
    q_grams = _char_ngrams(query)
    c_grams = _char_ngrams(content)
    if not q_grams or not c_grams:
        return 0.0

    intersection = sum((q_grams & c_grams).values())
    norm_q = sum(v * v for v in q_grams.values()) ** 0.5
    norm_c = sum(v * v for v in c_grams.values()) ** 0.5

    if norm_q == 0 or norm_c == 0:
        return 0.0

    cosine_sim = intersection / (norm_q * norm_c)
    return round(min(1.0, float(cosine_sim)), 4)


# Backward compatibility alias
compute_semantic_score = compute_fuzzy_subword_score
