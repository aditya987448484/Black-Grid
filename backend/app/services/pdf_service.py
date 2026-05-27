"""
PDF Export Service — BlackGrid Research
Converts an AnalystReport into a branded, print-quality PDF using WeasyPrint.

Public API
----------
    generate_report_pdf(report: AnalystReport) -> bytes
        Build HTML from the report and render it to PDF bytes.

    _build_html(report: AnalystReport) -> str
        Return the raw HTML string (useful for testing / debugging).
"""

from __future__ import annotations

import logging
from datetime import datetime
from html import escape
from typing import Optional

from app.schemas.schemas import (
    AnalystReport,
    RiskAndCatalyst,
    RecommendationType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _rating_colour(rec: RecommendationType) -> str:
    return {
        RecommendationType.BUY:  "#22c55e",   # emerald-500
        RecommendationType.HOLD: "#f59e0b",   # amber-500
        RecommendationType.SELL: "#ef4444",   # red-500
    }.get(rec, "#94a3b8")


def _severity_colour(s: str) -> str:
    return {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}.get(s, "#94a3b8")


def _fmt_price(v: Optional[float]) -> str:
    return f"${v:,.2f}" if v is not None else "N/A"


def _fmt_pct(v: Optional[float], suffix: str = "%") -> str:
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}{suffix}"


def _fmt_num(v: Optional[float], decimals: int = 2) -> str:
    return f"{v:.{decimals}f}" if v is not None else "N/A"


def _risk_rows(items: list[RiskAndCatalyst]) -> str:
    rows = []
    for item in items:
        colour = _severity_colour(item.severity)
        mit = escape(item.mitigation or "—")
        rows.append(
            f"<tr>"
            f"<td>{escape(item.description)}</td>"
            f"<td style='color:{colour};font-weight:600;text-align:center'>{escape(item.severity)}</td>"
            f"<td>{mit}</td>"
            f"</tr>"
        )
    return "\n".join(rows) if rows else "<tr><td colspan='3'>None identified</td></tr>"


# ---------------------------------------------------------------------------
# HTML template builder
# ---------------------------------------------------------------------------

def _build_html(report: AnalystReport) -> str:                    # noqa: PLR0914
    """Return self-contained HTML for the analyst report PDF."""

    r = report
    rating = r.final_rating
    tech = r.technical_view
    fund = r.fundamental_snapshot
    macro = r.macro_context
    bull = r.bull_case
    bear = r.bear_case
    rating_col = _rating_colour(rating.recommendation)

    # Format date — strip Z suffix before parsing (fromisoformat rejects it on Py<3.11)
    report_date = r.report_date
    if isinstance(report_date, str):
        report_date = datetime.fromisoformat(report_date.replace("Z", "+00:00"))
    date_str = report_date.strftime("%B %d, %Y")

    # Bull / bear probability bars
    bull_bar = f"<div style='height:6px;background:{_rating_colour(RecommendationType.BUY)};width:{bull.probability:.0f}%;border-radius:3px'></div>"
    bear_bar = f"<div style='height:6px;background:{_rating_colour(RecommendationType.SELL)};width:{bear.probability:.0f}%;border-radius:3px'></div>"

    # Catalyst list items — escape all LLM-originated strings
    bull_items = "".join(f"<li>{escape(c)}</li>" for c in bull.key_catalysts)
    bear_items = "".join(f"<li>{escape(c)}</li>" for c in bear.key_catalysts)
    tailwinds  = "".join(f"<li>{escape(t)}</li>" for t in macro.industry_tailwinds)
    headwinds  = "".join(f"<li>{escape(h)}</li>" for h in macro.macro_headwinds)

    risk_rows     = _risk_rows(r.risks)
    catalyst_rows = _risk_rows(r.catalysts)

    # Pre-escape all LLM-originated free-text fields once here.
    # Everything below this point is safe to embed in HTML.
    company_name       = escape(r.company_name)
    ticker_upper       = escape(r.ticker.upper())
    executive_summary  = escape(r.executive_summary)
    investment_hl      = escape(r.investment_highlight)
    rating_rationale   = escape(rating.rationale)
    rating_conviction  = escape(rating.conviction)
    tech_trend         = escape(tech.trend)
    tech_momentum      = escape(tech.momentum)
    tech_ma            = escape(tech.ma_alignment)
    tech_summary       = escape(tech.summary)
    fund_valuation     = escape(fund.valuation_assessment)
    macro_sector       = escape(macro.sector_performance)
    macro_outlook      = escape(macro.macro_outlook)
    bull_thesis        = escape(bull.thesis)
    bull_timeline      = escape(bull.timeline)
    bear_thesis        = escape(bear.thesis)
    bear_timeline      = escape(bear.timeline)
    rating_value       = escape(rating.recommendation.value)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', Arial, sans-serif;
    font-size: 9.5pt;
    color: #e2e8f0;
    background: #0a0a0a;
    padding: 0;
  }}

  /* ── Header ── */
  .header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-bottom: 3px solid {rating_col};
    padding: 28px 36px 22px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .logo {{ font-size: 20pt; font-weight: 700; color: #f8fafc; letter-spacing: -0.5px; }}
  .logo span {{ color: {rating_col}; }}
  .company {{ font-size: 14pt; font-weight: 600; color: #f8fafc; margin-top: 6px; }}
  .sub {{ font-size: 9pt; color: #94a3b8; margin-top: 3px; }}
  .rating-box {{
    text-align: right;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 20px;
  }}
  .rating-label {{ font-size: 7pt; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }}
  .rating-value {{ font-size: 22pt; font-weight: 700; color: {rating_col}; line-height: 1.1; }}
  .target-price {{ font-size: 9pt; color: #94a3b8; margin-top: 4px; }}

  /* ── Body ── */
  .body {{ padding: 24px 36px; }}

  /* ── Section ── */
  .section {{ margin-bottom: 20px; }}
  .section-title {{
    font-size: 7pt; font-weight: 600; text-transform: uppercase;
    letter-spacing: 1.5px; color: #64748b;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 6px; margin-bottom: 10px;
  }}
  .prose {{ color: #cbd5e1; line-height: 1.6; }}

  /* ── Metric grid ── */
  .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }}
  .metric-card {{
    background: #111827; border: 1px solid #1e293b;
    border-radius: 6px; padding: 10px 12px;
  }}
  .metric-label {{ font-size: 7pt; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; }}
  .metric-value {{ font-size: 13pt; font-weight: 600; color: #f8fafc; margin-top: 3px; }}
  .metric-sub {{ font-size: 7.5pt; color: #94a3b8; margin-top: 2px; }}

  /* ── Two-column layout ── */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  .case-box {{
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 6px; padding: 14px;
  }}
  .case-title {{ font-weight: 600; font-size: 10pt; margin-bottom: 6px; }}
  .case-bull {{ color: #22c55e; }}
  .case-bear {{ color: #ef4444; }}
  .case-thesis {{ color: #94a3b8; font-size: 8.5pt; line-height: 1.5; margin-bottom: 8px; }}
  .case-list {{ color: #cbd5e1; font-size: 8.5pt; padding-left: 16px; }}
  .case-list li {{ margin-bottom: 3px; }}
  .prob-label {{ font-size: 7pt; color: #64748b; margin-top: 8px; margin-bottom: 3px; }}

  /* ── Macro pills ── */
  .pill-list {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .pill {{
    background: #1e293b; border: 1px solid #334155;
    border-radius: 20px; padding: 3px 10px;
    font-size: 8pt; color: #94a3b8;
  }}

  /* ── Table ── */
  table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
  th {{
    background: #1e293b; color: #64748b;
    font-size: 7pt; text-transform: uppercase; letter-spacing: 0.8px;
    padding: 6px 10px; text-align: left;
    border-bottom: 1px solid #334155;
  }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #1e293b; color: #cbd5e1; }}
  tr:hover td {{ background: #0f172a; }}

  /* ── Confidence bar ── */
  .conf-bar-bg {{
    background: #1e293b; border-radius: 4px; height: 8px; margin-top: 4px;
  }}
  .conf-bar-fill {{
    height: 8px; border-radius: 4px;
    background: linear-gradient(90deg, {rating_col} 0%, {rating_col}99 100%);
    width: {r.confidence_score:.0f}%;
  }}

  /* ── Footer / disclaimer ── */
  .footer {{
    background: #0f172a; border-top: 1px solid #1e293b;
    padding: 14px 36px; margin-top: 28px;
    font-size: 7pt; color: #475569; line-height: 1.5;
  }}
  .footer strong {{ color: #64748b; }}

  @page {{
    size: A4;
    margin: 0;
  }}
  @media print {{
    body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<!-- ═══ HEADER ═══════════════════════════════════════════════════════════ -->
<div class="header">
  <div>
    <div class="logo">Black<span>Grid</span></div>
    <div class="company">{company_name}</div>
    <div class="sub">
      {ticker_upper} &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp;
      Current Price: {_fmt_price(r.current_price)} &nbsp;·&nbsp;
      Confidence: {r.confidence_score:.0f}%
    </div>
  </div>
  <div class="rating-box">
    <div class="rating-label">Recommendation</div>
    <div class="rating-value">{rating_value}</div>
    <div class="target-price">
      Target: {_fmt_price(rating.target_price)}&nbsp;
      ({_fmt_pct(rating.price_upside)})
    </div>
    <div style="font-size:7.5pt;color:#64748b;margin-top:2px">
      Conviction: <strong style="color:#94a3b8">{rating_conviction}</strong>
    </div>
  </div>
</div>

<!-- ═══ BODY ══════════════════════════════════════════════════════════════ -->
<div class="body">

  <!-- 1. Executive Summary -->
  <div class="section">
    <div class="section-title">Executive Summary</div>
    <p class="prose">{executive_summary}</p>
    <p class="prose" style="margin-top:8px;font-weight:500;color:#f8fafc">
      ⚡ {investment_hl}
    </p>
  </div>

  <!-- 2. Final Rating Rationale -->
  <div class="section">
    <div class="section-title">Rating Rationale</div>
    <p class="prose">{rating_rationale}</p>
    <div style="margin-top:8px">
      <div style="font-size:7.5pt;color:#64748b">
        Overall Confidence Score — {r.confidence_score:.0f} / 100
      </div>
      <div class="conf-bar-bg">
        <div class="conf-bar-fill"></div>
      </div>
    </div>
  </div>

  <!-- 3. Fundamental Snapshot -->
  <div class="section">
    <div class="section-title">Fundamental Snapshot</div>
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">EPS (Diluted)</div>
        <div class="metric-value">{_fmt_price(fund.eps)}</div>
        <div class="metric-sub">Earnings per share</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Revenue Growth</div>
        <div class="metric-value">{_fmt_pct(fund.revenue_growth)}</div>
        <div class="metric-sub">Year-over-year</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Profit Margin</div>
        <div class="metric-value">{_fmt_pct(fund.profit_margin)}</div>
        <div class="metric-sub">Net margin</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">ROE</div>
        <div class="metric-value">{_fmt_pct(fund.roe)}</div>
        <div class="metric-sub">Return on equity</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Debt / Equity</div>
        <div class="metric-value">{_fmt_num(fund.debt_to_equity)}</div>
        <div class="metric-sub">Leverage ratio</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Quality Score</div>
        <div class="metric-value">{_fmt_num(fund.quality_score, 0)}</div>
        <div class="metric-sub">0–100 composite</div>
      </div>
      <div class="metric-card" style="grid-column:span 2">
        <div class="metric-label">Valuation</div>
        <div class="metric-value" style="font-size:11pt">{fund_valuation}</div>
      </div>
    </div>
  </div>

  <!-- 4. Technical View -->
  <div class="section">
    <div class="section-title">Technical Analysis</div>
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">Trend</div>
        <div class="metric-value" style="font-size:11pt">{tech_trend}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Signal Strength</div>
        <div class="metric-value">{_fmt_num(tech.signal_strength, 0)}</div>
        <div class="metric-sub">0–100</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Momentum</div>
        <div class="metric-value" style="font-size:11pt">{tech_momentum}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">MA Alignment</div>
        <div class="metric-value" style="font-size:10pt">{tech_ma}</div>
      </div>
    </div>
    <p class="prose" style="margin-top:10px">{tech_summary}</p>
    <p style="margin-top:6px;font-size:8pt;color:#64748b">
      Key levels: {" · ".join(_fmt_price(lv) for lv in tech.key_levels)}
    </p>
  </div>

  <!-- 5. Macro Context -->
  <div class="section">
    <div class="section-title">Macro Context</div>
    <div class="two-col">
      <div>
        <div style="font-size:8pt;color:#22c55e;font-weight:600;margin-bottom:5px">Tailwinds</div>
        <ul class="case-list" style="color:#94a3b8">{tailwinds}</ul>
      </div>
      <div>
        <div style="font-size:8pt;color:#ef4444;font-weight:600;margin-bottom:5px">Headwinds</div>
        <ul class="case-list" style="color:#94a3b8">{headwinds}</ul>
      </div>
    </div>
    <div style="margin-top:10px;font-size:8.5pt;color:#94a3b8">
      Sector Performance: <strong style="color:#f8fafc">{macro_sector}</strong>
      &nbsp;·&nbsp; Macro Outlook: <strong style="color:#f8fafc">{macro_outlook}</strong>
      &nbsp;·&nbsp; Market Correlation: <strong style="color:#f8fafc">{macro.correlation_market:.2f}</strong>
    </div>
  </div>

  <!-- 6+7. Bull & Bear Cases -->
  <div class="section">
    <div class="section-title">Investment Cases</div>
    <div class="two-col">
      <div class="case-box">
        <div class="case-title case-bull">▲ Bull Case ({bull.probability:.0f}%)</div>
        <p class="case-thesis">{bull_thesis}</p>
        <ul class="case-list">{bull_items}</ul>
        <div class="prob-label">Probability</div>
        {bull_bar}
        <div style="font-size:7pt;color:#64748b;margin-top:3px">Timeline: {bull_timeline}</div>
      </div>
      <div class="case-box">
        <div class="case-title case-bear">▼ Bear Case ({bear.probability:.0f}%)</div>
        <p class="case-thesis">{bear_thesis}</p>
        <ul class="case-list">{bear_items}</ul>
        <div class="prob-label">Probability</div>
        {bear_bar}
        <div style="font-size:7pt;color:#64748b;margin-top:3px">Timeline: {bear_timeline}</div>
      </div>
    </div>
  </div>

  <!-- 8. Risk Factors -->
  <div class="section">
    <div class="section-title">Risk Factors</div>
    <table>
      <thead>
        <tr>
          <th>Risk</th><th>Severity</th><th>Mitigation</th>
        </tr>
      </thead>
      <tbody>{risk_rows}</tbody>
    </table>
  </div>

  <!-- 9. Near-Term Catalysts -->
  <div class="section">
    <div class="section-title">Near-Term Catalysts</div>
    <table>
      <thead>
        <tr>
          <th>Catalyst</th><th>Impact</th><th>Notes</th>
        </tr>
      </thead>
      <tbody>{catalyst_rows}</tbody>
    </table>
  </div>

</div><!-- /body -->

<!-- ═══ FOOTER / DISCLAIMER ══════════════════════════════════════════════ -->
<div class="footer">
  <strong>Disclaimer — Not Financial Advice</strong><br/>
  This report was generated by BlackGrid, an AI-powered financial research platform,
  on {date_str}. The content is produced algorithmically using publicly available market
  data, SEC EDGAR filings, and FRED macroeconomic indicators, and is intended for
  informational purposes only. It does not constitute investment advice, a solicitation,
  or an offer to buy or sell any security. Past performance is not indicative of future
  results. All investments involve risk, including the possible loss of principal.
  Consult a qualified financial professional before making any investment decision.
  &copy; {report_date.year} BlackGrid Research.
</div>

</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def generate_report_pdf(report: AnalystReport) -> bytes:
    """
    Render an AnalystReport to PDF bytes using WeasyPrint.

    Args:
        report: Fully populated AnalystReport instance.

    Returns:
        Raw PDF bytes suitable for streaming to the client.
    """
    try:
        from weasyprint import HTML as WeasyHTML   # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is not installed. "
            "Run `pip install weasyprint` to enable PDF export."
        ) from exc

    html_str = _build_html(report)
    logger.info("Generating PDF for %s (%s)", report.ticker, report.company_name)
    pdf_bytes: bytes = WeasyHTML(string=html_str).write_pdf()
    logger.info("PDF generated: %d bytes for %s", len(pdf_bytes), report.ticker)
    return pdf_bytes
