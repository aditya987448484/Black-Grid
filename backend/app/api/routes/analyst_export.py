"""
POST /api/analyst/export-pdf         — structured AnalystReport → branded PDF
POST /api/analyst/export-markdown-pdf — raw markdown text → branded PDF
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re as _re
import html as _html_lib
from datetime import datetime
from functools import partial

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.schemas.schemas import AnalystReport
from app.services.pdf_service import generate_report_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyst", tags=["analyst-export"])

# Maximum accepted request body size (512 KB / 1 MB).
_MAX_PAYLOAD_BYTES = 512 * 1024
_MAX_MARKDOWN_BYTES = 1_048_576  # 1 MB


@router.post(
    "/export-pdf",
    summary="Export analyst report as PDF",
    response_description="Branded PDF research report download",
)
async def export_analyst_pdf(request: Request, report: AnalystReport) -> StreamingResponse:
    """
    Generate a branded BlackGrid research PDF from a full AnalystReport payload.

    **Returns:** `application/pdf` binary stream with
    `Content-Disposition: attachment; filename="{TICKER}_BlackGrid_Research.pdf"`.
    """
    # I7 — reject oversized bodies before doing any work
    content_length = int(request.headers.get("content-length", 0))
    if content_length > _MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Payload too large (max {_MAX_PAYLOAD_BYTES // 1024} KB).",
        )

    try:
        # C3 — WeasyPrint is synchronous and CPU-bound.
        # Run it in the default ThreadPoolExecutor so the event loop stays
        # responsive to other requests during rendering (typically 2–8 s).
        loop = asyncio.get_event_loop()
        pdf_bytes: bytes = await loop.run_in_executor(
            None, partial(generate_report_pdf, report)
        )
    except RuntimeError as exc:
        # WeasyPrint / system library missing
        logger.error("PDF generation failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error generating PDF for %s", report.ticker)
        raise HTTPException(status_code=500, detail="PDF generation failed") from exc

    # I2 — filename must be RFC 6266 quoted
    filename = f"{report.ticker.upper()}_BlackGrid_Research.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Markdown → PDF helpers
# ---------------------------------------------------------------------------

def _md_to_html_body(md: str) -> str:
    """Convert markdown to HTML body content for the PDF."""
    lines = md.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.strip().startswith("```"):
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(_html_lib.escape(lines[i]))
                i += 1
            out.append(
                f'<pre style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;'
                f'padding:12px;font-size:8pt;color:#93c5fd;overflow-x:auto;margin:8px 0">'
                f'{"<br>".join(code_lines)}</pre>'
            )
            i += 1
            continue

        # H2 headers (## )
        if line.startswith("## "):
            heading = _html_lib.escape(line[3:].strip())
            out.append(
                f'<div style="margin-top:24px;margin-bottom:10px;padding-bottom:6px;'
                f'border-bottom:2px solid #c9a84c">'
                f'<span style="font-size:12pt;font-weight:700;color:#f8fafc;'
                f'letter-spacing:-0.3px">{heading}</span></div>'
            )
            i += 1
            continue

        # H3 headers (### )
        if line.startswith("### "):
            heading = _html_lib.escape(line[4:].strip())
            out.append(
                f'<div style="margin-top:16px;margin-bottom:6px">'
                f'<span style="font-size:10pt;font-weight:600;color:#e2e8f0">{heading}</span></div>'
            )
            i += 1
            continue

        # H1 headers (# )
        if line.startswith("# "):
            heading = _html_lib.escape(line[2:].strip())
            out.append(
                f'<div style="margin-top:20px;margin-bottom:8px">'
                f'<span style="font-size:14pt;font-weight:700;color:#f8fafc">{heading}</span></div>'
            )
            i += 1
            continue

        # Bullet points
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            bullet_content = _html_lib.escape(line.strip()[2:])
            bullet_content = _re.sub(
                r'\*\*(.+?)\*\*',
                r'<strong style="color:#f1f5f9">\1</strong>',
                bullet_content,
            )
            bullet_content = _re.sub(
                r'`([^`]+)`',
                r'<code style="background:rgba(255,255,255,0.08);border-radius:3px;'
                r'padding:1px 4px;font-family:monospace;font-size:0.88em;color:#93c5fd">\1</code>',
                bullet_content,
            )
            out.append(
                f'<div style="padding:3px 0 3px 16px;color:#cbd5e1;font-size:9pt;'
                f'line-height:1.55">• {bullet_content}</div>'
            )
            i += 1
            continue

        # Empty lines
        if line.strip() == "":
            out.append('<div style="height:6px"></div>')
            i += 1
            continue

        # Normal paragraph
        para = _html_lib.escape(line.strip())
        para = _re.sub(
            r'\*\*(.+?)\*\*',
            r'<strong style="color:#f1f5f9">\1</strong>',
            para,
        )
        para = _re.sub(
            r'`([^`]+)`',
            r'<code style="background:rgba(255,255,255,0.08);border-radius:3px;'
            r'padding:1px 4px;font-family:monospace;font-size:0.88em;color:#93c5fd">\1</code>',
            para,
        )
        if para:
            out.append(
                f'<p style="color:#cbd5e1;font-size:9.5pt;line-height:1.65;margin:2px 0">{para}</p>'
            )
        i += 1

    return "\n".join(out)


def _build_markdown_pdf_html(
    ticker: str, title: str, content_md: str, generated_at: str
) -> str:
    """Build full HTML document for markdown-based PDF export."""
    safe_ticker = _html_lib.escape(ticker.upper())
    safe_title  = _html_lib.escape(title)
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        date_str = dt.strftime("%B %d, %Y")
        year = dt.year
    except Exception:
        dt = datetime.utcnow()
        date_str = dt.strftime("%B %d, %Y")
        year = dt.year

    body_html = _md_to_html_body(content_md)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    color: #e2e8f0;
    background: #080b10;
  }}
  .header {{
    background: #0f172a;
    border-bottom: 3px solid #c9a84c;
    padding: 28px 36px 22px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .logo {{ font-size:18pt; font-weight:700; color:#f8fafc; }}
  .logo span {{ color:#c9a84c; }}
  .ticker-badge {{
    font-size: 28pt; font-weight: 800; color: #c9a84c;
    border: 2px solid rgba(201,168,76,0.27);
    border-radius: 8px; padding: 8px 20px;
    background: rgba(201,168,76,0.08);
  }}
  .subtitle {{ font-size:9pt; color:#64748b; margin-top:4px; }}
  .body {{ padding: 24px 36px; }}
  .footer {{
    background: #0f172a; border-top: 1px solid #1e293b;
    padding: 14px 36px; margin-top: 28px;
    font-size: 7pt; color: #475569; line-height: 1.5;
  }}
  @page {{ size: A4; margin: 0; }}
  @media print {{ body {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }} }}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">Black<span>Grid</span></div>
    <div style="font-size:13pt;font-weight:600;color:#f8fafc;margin-top:5px">{safe_title}</div>
    <div class="subtitle">
      Generated {date_str} · BlackGrid AI Research Platform · Institutional Grade Analysis
    </div>
  </div>
  <div class="ticker-badge">{safe_ticker}</div>
</div>
<div class="body">{body_html}</div>
<div class="footer">
  <strong>Disclaimer — Not Financial Advice</strong><br/>
  This report was generated by BlackGrid AI Research on {date_str}. Content is produced
  algorithmically and is for informational purposes only. It does not constitute investment
  advice or an offer to buy or sell any security. Consult a qualified financial professional
  before making investment decisions. &copy; {year} BlackGrid Research.
</div>
</body>
</html>"""


def _render_pdf(html_str: str) -> bytes:
    """Render HTML string to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML as WeasyHTML  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint not installed. Run: pip install weasyprint"
        ) from exc
    return WeasyHTML(string=html_str).write_pdf()


# ---------------------------------------------------------------------------
# New route: markdown → PDF
# ---------------------------------------------------------------------------

@router.post(
    "/export-markdown-pdf",
    summary="Export raw markdown analysis as PDF",
    response_description="Branded PDF from plain markdown text",
)
async def export_markdown_pdf(request: Request) -> StreamingResponse:
    """
    Accept raw markdown text and generate a clean branded PDF.
    Used by the AI Analyst chat page to export DeepSeek analysis that has
    not been parsed into a structured AnalystReport.

    Body (JSON):
        ticker       — ticker symbol (default "Research")
        title        — document title
        content      — markdown body text
        generated_at — ISO-8601 timestamp string
    """
    body = await request.body()
    if len(body) > _MAX_MARKDOWN_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large (max 1 MB).")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body.") from exc

    ticker       = str(data.get("ticker", "Research"))
    title        = str(data.get("title", f"{ticker} — Institutional Analysis"))
    content_md   = str(data.get("content", ""))
    generated_at = str(data.get("generated_at", datetime.utcnow().isoformat()))

    html = _build_markdown_pdf_html(ticker, title, content_md, generated_at)

    try:
        loop = asyncio.get_event_loop()
        pdf_bytes: bytes = await loop.run_in_executor(None, lambda: _render_pdf(html))
    except RuntimeError as exc:
        logger.error("Markdown PDF failed (WeasyPrint): %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Markdown PDF generation failed for %s", ticker)
        raise HTTPException(status_code=500, detail="PDF generation failed") from exc

    filename = f"{ticker.upper()}_BlackGrid_Research.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
