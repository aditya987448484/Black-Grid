"""
Tests for pdf_service.generate_report_pdf()
Acceptance criteria:
  - _build_html() returns a string containing ticker, company, rating, disclaimer
  - generate_report_pdf() returns bytes with %PDF header (mocked on macOS dev env)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.schemas.schemas import (
    AnalystReport, TechnicalViewpoint, FundamentalSnapshot,
    MacroContext, InvestmentCase, RiskAndCatalyst, FinalRating,
    RecommendationType,
)


# ── Fixture ────────────────────────────────────────────────────────────────

def _make_report(ticker="TSLA", company="Tesla Inc.") -> AnalystReport:
    return AnalystReport(
        ticker=ticker,
        company_name=company,
        report_date=datetime(2026, 1, 15, 10, 0, 0),
        current_price=250.00,
        executive_summary="Strong fundamentals with positive momentum.",
        investment_highlight="AI integration driving margin expansion.",
        technical_view=TechnicalViewpoint(
            trend="Uptrend", key_levels=[230.0, 270.0], signal_strength=78.5,
            momentum="Strong", ma_alignment="Bullish",
            summary="Above all key MAs with breakout confirmed.",
        ),
        fundamental_snapshot=FundamentalSnapshot(
            eps=6.05, revenue_growth=18.5, profit_margin=14.2,
            roe=22.0, debt_to_equity=0.9,
            valuation_assessment="Fairly Valued", quality_score=82.0,
        ),
        macro_context=MacroContext(
            sector_performance="Outperforming",
            industry_tailwinds=["EV adoption", "AI integration"],
            macro_headwinds=["Rising rates", "Supply chain"],
            correlation_market=0.72, macro_outlook="Positive",
        ),
        bull_case=InvestmentCase(
            thesis="Market share gains drive re-rating.",
            key_catalysts=["FSD expansion", "Megapack orders"],
            timeline="12-18 months", probability=68.0,
        ),
        bear_case=InvestmentCase(
            thesis="Margin compression pressures multiples.",
            key_catalysts=["BYD competition", "Rate sensitivity"],
            timeline="6-12 months", probability=32.0,
        ),
        risks=[RiskAndCatalyst(description="Cybertruck ramp", severity="High",
                                mitigation="Monitor quarterly volumes")],
        catalysts=[RiskAndCatalyst(description="Q2 earnings beat", severity="High",
                                    mitigation="Strong delivery numbers")],
        final_rating=FinalRating(
            recommendation=RecommendationType.BUY, target_price=300.00,
            price_upside=20.0, conviction="High",
            rationale="Multiple expansion supported by strong fundamentals.",
        ),
        confidence_score=84.5,
    )


# ── HTML template tests (no system libs needed) ────────────────────────────

def test_build_html_contains_ticker():
    from app.services.pdf_service import _build_html
    html = _build_html(_make_report(ticker="NVDA", company="NVIDIA Corporation"))
    assert "NVDA" in html
    assert "NVIDIA Corporation" in html


def test_build_html_contains_rating():
    from app.services.pdf_service import _build_html
    html = _build_html(_make_report())
    assert "BUY" in html


def test_build_html_contains_price():
    from app.services.pdf_service import _build_html
    html = _build_html(_make_report())
    assert "250" in html


def test_build_html_contains_disclaimer():
    from app.services.pdf_service import _build_html
    html = _build_html(_make_report())
    lower = html.lower()
    assert "disclaimer" in lower or "not financial advice" in lower


def test_build_html_contains_all_sections():
    from app.services.pdf_service import _build_html
    html = _build_html(_make_report())
    for section in ["Executive Summary", "Technical Analysis",
                     "Fundamental Snapshot", "Macro Context",
                     "Investment Cases", "Risk Factors", "Near-Term Catalysts"]:
        assert section in html, f"Missing section: {section}"


def test_build_html_bull_bear_side_by_side():
    from app.services.pdf_service import _build_html
    html = _build_html(_make_report())
    assert "Bull Case" in html
    assert "Bear Case" in html


def test_build_html_is_valid_html():
    from app.services.pdf_service import _build_html
    html = _build_html(_make_report())
    assert html.strip().startswith("<!DOCTYPE html>")
    assert "</html>" in html


# ── PDF bytes tests (WeasyPrint mocked so they pass on any OS) ─────────────

def test_generate_report_pdf_returns_bytes():
    """generate_report_pdf must return bytes."""
    fake_pdf = b"%PDF-1.4 fake pdf content for testing purposes"
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.return_value = fake_pdf

    with patch.dict("sys.modules", {"weasyprint": MagicMock(HTML=MagicMock(return_value=mock_html_instance))}):
        # Re-import to pick up the mock
        import importlib
        import app.services.pdf_service as svc
        importlib.reload(svc)
        result = svc.generate_report_pdf(_make_report())

    assert isinstance(result, bytes)


def test_generate_report_pdf_is_valid_pdf():
    """%PDF magic header must be present."""
    fake_pdf = b"%PDF-1.4 fake"
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.return_value = fake_pdf

    with patch.dict("sys.modules", {"weasyprint": MagicMock(HTML=MagicMock(return_value=mock_html_instance))}):
        import importlib, app.services.pdf_service as svc
        importlib.reload(svc)
        pdf = svc.generate_report_pdf(_make_report())

    assert pdf[:4] == b"%PDF"


def test_generate_report_pdf_calls_weasyprint_with_html():
    """WeasyPrint HTML() must be called with the html string."""
    fake_pdf = b"%PDF-1.4 fake"
    mock_html_cls = MagicMock()
    mock_html_cls.return_value.write_pdf.return_value = fake_pdf

    with patch.dict("sys.modules", {"weasyprint": MagicMock(HTML=mock_html_cls)}):
        import importlib, app.services.pdf_service as svc
        importlib.reload(svc)
        svc.generate_report_pdf(_make_report())

    mock_html_cls.assert_called_once()
    _, kwargs = mock_html_cls.call_args
    assert "string" in kwargs
    assert "TSLA" in kwargs["string"]


# ── Regression tests for review fixes ──────────────────────────────────────

def test_build_html_escapes_html_special_chars():
    """C2 — HTML-special characters in LLM fields must be escaped."""
    from app.services.pdf_service import _build_html
    from app.schemas.schemas import (
        AnalystReport, TechnicalViewpoint, FundamentalSnapshot,
        MacroContext, InvestmentCase, RiskAndCatalyst, FinalRating,
        RecommendationType,
    )
    from datetime import datetime

    xss_report = AnalystReport(
        ticker="XSS",
        company_name='<script>alert("xss")</script>',
        report_date=datetime(2026, 1, 1),
        current_price=100.0,
        executive_summary='Summary with <b>bold</b> & "quotes"',
        investment_highlight="Highlight with <i>italic</i>",
        technical_view=TechnicalViewpoint(
            trend="Uptrend & More", key_levels=[90.0, 110.0],
            signal_strength=70.0, momentum="Strong > Neutral",
            ma_alignment='Bullish "strong"',
            summary="Above all <key> MAs",
        ),
        fundamental_snapshot=FundamentalSnapshot(
            eps=5.0, revenue_growth=10.0, profit_margin=20.0,
            roe=15.0, debt_to_equity=1.0,
            valuation_assessment="Fairly <Valued>", quality_score=75.0,
        ),
        macro_context=MacroContext(
            sector_performance="Out<performing>",
            industry_tailwinds=["EV & AI adoption"],
            macro_headwinds=["Rising <rates>"],
            correlation_market=0.7, macro_outlook="Positive & Stable",
        ),
        bull_case=InvestmentCase(
            thesis='Bull thesis with "quotes" & <tags>',
            key_catalysts=["<script>xss</script>"],
            timeline="12 > 18 months", probability=65.0,
        ),
        bear_case=InvestmentCase(
            thesis="Bear & bull fight",
            key_catalysts=["Risk & reward"],
            timeline="6-12 months", probability=35.0,
        ),
        risks=[RiskAndCatalyst(
            description='Risk with <b>HTML</b> & "quotes"',
            severity="High", mitigation="<mitigation & plan>"
        )],
        catalysts=[RiskAndCatalyst(
            description="Catalyst > earnings", severity="Medium"
        )],
        final_rating=FinalRating(
            recommendation=RecommendationType.BUY, target_price=120.0,
            price_upside=20.0, conviction='High "certainty"',
            rationale='Rationale with <b>bold</b> & "quotes"',
        ),
        confidence_score=80.0,
    )

    html = _build_html(xss_report)

    # Raw tags must not appear in the output
    assert "<script>" not in html
    assert "<b>" not in html, "Unescaped <b> found"
    assert "<i>" not in html, "Unescaped <i> found"
    assert "<key>" not in html
    assert "<tags>" not in html

    # Escaped forms must be present
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_build_html_handles_z_suffix_date():
    """I1 — report_date with Z suffix must not raise ValueError."""
    from app.services.pdf_service import _build_html
    # Reuse the helper from the existing fixture but with a Z-suffix date string
    report = _make_report()
    # Manually set a Z-suffix date string on the model
    object.__setattr__(report, 'report_date', '2026-06-01T00:00:00Z')
    html = _build_html(report)
    assert "2026" in html  # date rendered without error


def test_content_disposition_is_rfc_quoted():
    """I2 — Content-Disposition filename must be quoted per RFC 6266."""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app

    FAKE_PDF = b"%PDF-1.4 fake"
    client = TestClient(app)

    with patch("app.api.routes.analyst_export.generate_report_pdf", return_value=FAKE_PDF):
        resp = client.post("/api/analyst/export-pdf", json=_SAMPLE_PAYLOAD)

    cd = resp.headers.get("content-disposition", "")
    # Must contain filename="..." (quoted)
    assert 'filename="' in cd, f"filename not quoted: {cd}"


def test_oversized_payload_returns_413():
    """I7 — Payload exceeding 512 KB must be rejected with 413."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # Build a payload where one string field is larger than the limit
    big_payload = dict(_SAMPLE_PAYLOAD)
    big_payload["executive_summary"] = "x" * (600 * 1024)

    # TestClient doesn't send Content-Length automatically for large bodies;
    # we set it manually to trigger the header check in the route.
    big_body = __import__("json").dumps(big_payload).encode()
    resp = client.post(
        "/api/analyst/export-pdf",
        content=big_body,
        headers={"Content-Type": "application/json",
                 "Content-Length": str(len(big_body))},
    )
    assert resp.status_code == 413


# Shared sample payload used by regression tests above
_SAMPLE_PAYLOAD = {
    "ticker": "AAPL", "company_name": "Apple Inc.",
    "report_date": "2026-01-15T10:00:00",
    "current_price": 220.00,
    "executive_summary": "Apple is strong.",
    "investment_highlight": "Services inflection.",
    "technical_view": {
        "trend": "Uptrend", "key_levels": [210.0, 230.0],
        "signal_strength": 80.0, "momentum": "Strong",
        "ma_alignment": "Bullish", "summary": "Clear breakout.",
    },
    "fundamental_snapshot": {
        "eps": 7.5, "revenue_growth": 12.0, "profit_margin": 26.0,
        "roe": 90.0, "debt_to_equity": 1.9,
        "valuation_assessment": "Fairly Valued", "quality_score": 92.0,
    },
    "macro_context": {
        "sector_performance": "Outperforming",
        "industry_tailwinds": ["AI adoption"], "macro_headwinds": ["Rates"],
        "correlation_market": 0.85, "macro_outlook": "Positive",
    },
    "bull_case": {
        "thesis": "AI supercycle.", "key_catalysts": ["iPhone 17"],
        "timeline": "12-18 months", "probability": 70.0,
    },
    "bear_case": {
        "thesis": "China headwinds.", "key_catalysts": ["Regulation"],
        "timeline": "6-12 months", "probability": 30.0,
    },
    "risks": [{"description": "China sales", "severity": "High", "mitigation": "Diversify"}],
    "catalysts": [{"description": "Services beat", "severity": "High", "mitigation": "Watch"}],
    "final_rating": {
        "recommendation": "BUY", "target_price": 250.0, "price_upside": 13.6,
        "conviction": "High", "rationale": "Strong cash generation.",
    },
    "confidence_score": 88.0,
}
