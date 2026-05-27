"""
POST /api/analyst/export-pdf
Accepts a full AnalystReport payload and returns a branded PDF download.
"""

from __future__ import annotations

import asyncio
import io
import logging
from functools import partial

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.schemas.schemas import AnalystReport
from app.services.pdf_service import generate_report_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyst", tags=["analyst-export"])

# Maximum accepted request body size (512 KB).
# Prevents DoS via oversized LLM-string payloads that would force
# WeasyPrint to render a gigantic HTML document.
_MAX_PAYLOAD_BYTES = 512 * 1024


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
