import re


def normalize_food_search_query(query: str) -> str:
    """
    Deterministic food search normalization:
    - lowercase
    - strip leading/trailing whitespace
    - collapse multiple spaces to a single space
    - remove special punctuation symbols that interfere with lookup
    """
    if not query:
        return ""

    q = query.lower().strip()
    # Replace non-alphanumeric (except standard hyphen/space) with space
    q = re.sub(r"[^\w\s\-]", " ", q)
    # Collapse multiple whitespaces
    q = re.sub(r"\s+", " ", q).strip()
    return q
