"""Company search service — fast indexed search with fuzzy, alias, and exchange-aware matching."""

from __future__ import annotations

from app.services.market_universe import get_universe, get_company_info_from_universe


def _stem(word: str) -> str:
    """Lightweight suffix stripper so 'LABS' matches 'LAB', 'NETWORKS' matches 'NETWORK', etc."""
    w = word.upper()
    # Order matters: strip longest suffixes first
    for suffix in ("OLOGIES", "OLOGY", "MENTS", "MENT", "RIES", "INGS", "TION", "SION",
                   "NESS", "ICAL", "ICAL", "IES", "ORS", "ERS", "ALS",
                   "LY", "ED", "ES", "S"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,       # insert
                prev_row[j + 1] + 1,   # delete
                prev_row[j] + cost,    # replace
            ))
        prev_row = curr_row
    return prev_row[-1]


async def search_companies(query: str, limit: int = 15) -> list[dict]:
    """Search the universe by symbol or name with fuzzy, word-order-independent matching."""
    if not query or len(query) < 1:
        return []

    q = query.strip()
    q_upper = q.upper()

    # Fast path: exact symbol match (O(1) via dict)
    exact = get_company_info_from_universe(q_upper)
    if exact:
        return [_to_result(exact, 1.0)]

    universe = await get_universe()
    q_words = set(q_upper.split())

    scored: list[tuple[float, dict]] = []
    for company in universe:
        sym = company["symbol"]
        name = (company.get("name") or "").upper()

        score = _score_match(sym, name, q_upper, q_words)
        if score > 0:
            scored.append((score, company))

    scored.sort(key=lambda x: (-x[0], len(x[1]["symbol"]), x[1]["symbol"]))
    return [_to_result(c, s) for s, c in scored[:limit]]


def _score_match(sym: str, name: str, q_upper: str, q_words: set[str]) -> float:
    """Score a company against a search query. Returns 0 for no match."""
    # Exact symbol
    if sym == q_upper:
        return 1.0

    # Symbol prefix
    if sym.startswith(q_upper):
        return 0.9 - len(sym) * 0.005

    # Exact substring in name
    if q_upper in name:
        if name.startswith(q_upper):
            return 0.7
        idx = name.index(q_upper)
        return max(0.2, 0.65 - idx * 0.004)

    # Word-based matching: all query words found somewhere in name
    # Handles "charles schwab" matching "SCHWAB (CHARLES) CORP"
    # Also matches stems: "LABS" matches "LAB", "NETWORKS" matches "NETWORK"
    if len(q_words) > 1:
        name_words = set(_tokenize(name))
        name_stems = {_stem(w) for w in name_words}
        q_stems = {_stem(w) for w in q_words}
        # Exact word match
        if q_words.issubset(name_words):
            return 0.6
        # Stem match (e.g. "ROCKET LABS" matches "ROCKET LAB")
        if q_stems.issubset(name_stems):
            return 0.58
        # Partial word match: at least 2/3 of query words found (exact or stem)
        overlap_exact = len(q_words & name_words)
        overlap_stem = len(q_stems & name_stems)
        overlap = max(overlap_exact, overlap_stem)
        if overlap >= max(2, len(q_words) * 0.6):
            return 0.3 + overlap * 0.05

    # Single word in name (exact or stem)
    if len(q_words) == 1:
        word = next(iter(q_words))
        name_words = set(_tokenize(name))
        if word in name_words:
            return 0.45
        # Stem match for single word
        word_stem = _stem(word)
        if any(_stem(nw) == word_stem for nw in name_words):
            return 0.42

    # Symbol contains query
    if q_upper in sym:
        return 0.4

    # ── Fuzzy matching (Levenshtein) ────────────────────────────────────
    # Fuzzy symbol match: allow 1 edit for short symbols, 2 for longer
    if len(q_upper) >= 2 and len(q_upper) <= 6:
        max_dist = 1 if len(q_upper) <= 3 else 2
        dist = _levenshtein(q_upper, sym)
        if dist <= max_dist:
            return max(0.15, 0.5 - dist * 0.15)

    # Fuzzy name word match: find close matches in name words
    if len(q_upper) >= 3:
        name_words = set(_tokenize(name))
        for nw in name_words:
            if len(nw) < 3:
                continue
            max_dist = 1 if len(q_upper) <= 5 else 2
            dist = _levenshtein(q_upper, nw)
            if dist <= max_dist:
                return max(0.1, 0.35 - dist * 0.1)

    # Multi-word fuzzy: each query word matches some name word within edit distance
    if len(q_words) > 1:
        name_words = set(_tokenize(name))
        fuzzy_matches = 0
        for qw in q_words:
            if len(qw) < 2:
                continue
            for nw in name_words:
                max_d = 1 if len(qw) <= 4 else 2
                if _levenshtein(qw, nw) <= max_d:
                    fuzzy_matches += 1
                    break
        if fuzzy_matches >= len(q_words) * 0.7 and fuzzy_matches >= 2:
            return 0.25

    # Partial symbol match for international tickers (e.g. query "NVDA" vs symbol "NVDA.L")
    if sym.startswith(q_upper + "."):
        return 0.35

    return 0.0


def _tokenize(text: str) -> list[str]:
    """Split a company name into searchable words, stripping parentheses and suffixes."""
    import re
    # Remove parentheses content but keep the words
    cleaned = text.replace("(", " ").replace(")", " ").replace(",", " ").replace(".", " ")
    words = re.findall(r'[A-Z0-9]+', cleaned.upper())
    # Filter out common suffixes that add noise
    noise = {"INC", "CORP", "CO", "LTD", "PLC", "NV", "SA", "AG", "THE", "SPN", "ADR", "SHS", "REG", "HOLDINGS", "GROUP", "INTERNATIONAL", "TECHNOLOGIES", "TECHNOLOGY", "SYSTEMS", "SOLUTIONS"}
    return [w for w in words if w not in noise and len(w) > 1]


def _to_result(company: dict, score: float) -> dict:
    return {
        "symbol": company["symbol"],
        "name": company.get("name", company["symbol"]),
        "exchange": company.get("exchange"),
        "sector": company.get("sector"),
        "assetType": company.get("assetType"),
        "matchScore": round(score, 3),
    }
