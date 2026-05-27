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
