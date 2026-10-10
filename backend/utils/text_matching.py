"""Text normalization and fuzzy matching helpers (no dependency on main.py).

Copied verbatim from main.py so services can use them without a circular
import; main.py still has its own copy until it is refactored to import these.
"""
import unicodedata


def normalize_text(text):
    """Remove accents and convert to lowercase for better matching"""
    if not text:
        return ''
    # Normalize unicode characters and remove accents
    normalized = unicodedata.normalize('NFD', text)
    ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return ascii_text.lower().strip()


def calculate_similarity(s1, s2):
    """Calculate similarity ratio between two strings (0-1)"""
    s1, s2 = s1.lower(), s2.lower()
    if s1 == s2:
        return 1.0

    # Check if one contains the other
    if s1 in s2 or s2 in s1:
        return 0.9

    # Calculate character-based similarity
    set1, set2 = set(s1), set(s2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    jaccard = intersection / union if union > 0 else 0

    # Also check for common substrings (minimum 3 chars)
    common_substr_score = 0
    for i in range(len(s1) - 2):
        substr = s1[i:i+3]
        if substr in s2:
            common_substr_score += 1

    # Normalize substring score
    max_substrs = max(len(s1) - 2, 1)
    substr_ratio = min(common_substr_score / max_substrs, 1.0)

    # Combined score
    return (jaccard * 0.4) + (substr_ratio * 0.6)
