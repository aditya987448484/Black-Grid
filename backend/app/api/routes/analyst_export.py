"""
POST /api/analyst/export-pdf
Accepts a full AnalystReport payload and returns a branded PDF download.
"""

from __future__ import annotations

import io
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.schemas import AnalystReport
from app.services.pdf_service import generate_report_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyst", tags=["analyst-export"])


@router.post(
    "/export-pdf",
    summary="Export analyst report as PDF",
    response_description="Branded PDF research report download",
)
async def export_analyst_pdf(report: AnalystReport) -> StreamingResponse:
    """
    Generate a branded BlackGrid research PDF from a full AnalystReport payload.

    **Returns:** `application/pdf` binary stream with
    `Content-Disposition: attachment; filename="{TICKER}_BlackGrid_Research.pdf"`.
    """
    try:
        pdf_bytes = generate_report_pdf(report)
    except RuntimeError as exc:
        # WeasyPrint / system library missing
        logger.error("PDF generation failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error generating PDF for %s", report.ticker)
        raise HTTPException(status_code=500, detail="PDF generation failed") from exc

    filename = f"{report.ticker.upper()}_BlackGrid_Research.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
