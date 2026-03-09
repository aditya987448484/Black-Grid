"""Company search service — fast indexed search with word-based matching."""

from __future__ import annotations

from app.services.market_universe import get_universe, get_company_info_from_universe


async def search_companies(query: str, limit: int = 15) -> list[dict]:
    """Search the universe by symbol or name with word-order-independent matching."""
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
    if len(q_words) > 1:
        name_words = set(_tokenize(name))
        if q_words.issubset(name_words):
            return 0.6
        # Partial word match: at least 2/3 of query words found
        overlap = len(q_words & name_words)
        if overlap >= max(2, len(q_words) * 0.6):
            return 0.3 + overlap * 0.05

    # Single word in name
    if len(q_words) == 1:
        word = next(iter(q_words))
        name_words = set(_tokenize(name))
        if word in name_words:
            return 0.45

    # Symbol contains query
    if q_upper in sym:
        return 0.4

    return 0.0


def _tokenize(text: str) -> list[str]:
    """Split a company name into searchable words, stripping parentheses and suffixes."""
    import re
    # Remove parentheses content but keep the words
    cleaned = text.replace("(", " ").replace(")", " ").replace(",", " ").replace(".", " ")
    words = re.findall(r'[A-Z0-9]+', cleaned.upper())
    # Filter out common suffixes that add noise
    noise = {"INC", "CORP", "CO", "LTD", "PLC", "NV", "SA", "AG", "CLASS", "A", "B", "THE", "OF", "AND", "SPN", "ADR", "SHS", "NY", "REG"}
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
