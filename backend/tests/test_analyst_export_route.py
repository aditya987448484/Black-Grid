"""
Tests for POST /api/analyst/export-pdf
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

FAKE_PDF = b"%PDF-1.4 fake pdf bytes for BlackGrid route testing"

SAMPLE_PAYLOAD = {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "report_date": "2026-01-15T10:00:00",
    "current_price": 220.00,
    "executive_summary": "Apple is firing on all cylinders.",
    "investment_highlight": "Services revenue inflection.",
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
        "industry_tailwinds": ["AI adoption"],
        "macro_headwinds": ["Rate pressure"],
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
        "conviction": "High", "rationale": "Strong fundamentals.",
    },
    "confidence_score": 88.0,
}


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


# Patch generate_report_pdf at the route level so it never calls WeasyPrint
PDF_PATCH = "app.api.routes.analyst_export.generate_report_pdf"


def test_export_pdf_status_200(client):
    with patch(PDF_PATCH, return_value=FAKE_PDF):
        resp = client.post("/api/analyst/export-pdf", json=SAMPLE_PAYLOAD)
    assert resp.status_code == 200, resp.text


def test_export_pdf_content_type(client):
    with patch(PDF_PATCH, return_value=FAKE_PDF):
        resp = client.post("/api/analyst/export-pdf", json=SAMPLE_PAYLOAD)
    assert "application/pdf" in resp.headers.get("content-type", "")


def test_export_pdf_content_disposition(client):
    with patch(PDF_PATCH, return_value=FAKE_PDF):
        resp = client.post("/api/analyst/export-pdf", json=SAMPLE_PAYLOAD)
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "AAPL" in cd
    assert ".pdf" in cd


def test_export_pdf_body_is_pdf_bytes(client):
    with patch(PDF_PATCH, return_value=FAKE_PDF):
        resp = client.post("/api/analyst/export-pdf", json=SAMPLE_PAYLOAD)
    assert resp.content[:4] == b"%PDF"


def test_export_pdf_filename_contains_ticker(client):
    with patch(PDF_PATCH, return_value=FAKE_PDF):
        resp = client.post("/api/analyst/export-pdf", json=SAMPLE_PAYLOAD)
    cd = resp.headers.get("content-disposition", "")
    assert "AAPL_BlackGrid_Research.pdf" in cd


def test_export_pdf_missing_ticker_422(client):
    bad = {k: v for k, v in SAMPLE_PAYLOAD.items() if k != "ticker"}
    with patch(PDF_PATCH, return_value=FAKE_PDF):
        resp = client.post("/api/analyst/export-pdf", json=bad)
    assert resp.status_code == 422
