"""AI Analyst chat and file upload routes."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.ai_analyst import AiAnalystRequest, AiAnalystResponse, UploadResponse
from app.services.ai_analyst_service import process_analyst_chat

router = APIRouter(prefix="/api/ai-analyst", tags=["ai-analyst"])

ALLOWED_TYPES = {
    "application/pdf", "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png", "image/jpeg", "image/jpg", "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/chat", response_model=AiAnalystResponse)
async def analyst_chat(req: AiAnalystRequest):
    history = [{"role": m.role, "content": m.content} for m in req.history]
    attachments = [a.dict() for a in req.attachments] if req.attachments else None
    result = await process_analyst_chat(
        message=req.message,
        history=history,
        model=req.model,
        attachments=attachments,
    )
    return result


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT, CSV, PNG, JPG, WEBP")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large ({len(content)} bytes). Max: {MAX_FILE_SIZE // (1024*1024)}MB")

    # Generate a basic summary based on file type
    summary = ""
    if file.content_type == "text/plain" or file.content_type == "text/csv":
        text = content.decode("utf-8", errors="replace")[:2000]
        summary = f"Text content ({len(content)} bytes): {text[:500]}"
    elif file.content_type == "application/pdf":
        summary = f"PDF document ({len(content)} bytes). Full text extraction available in future version."
    elif file.content_type and file.content_type.startswith("image/"):
        summary = f"Image file ({file.content_type}, {len(content)} bytes). Visual analysis available in future version."
    else:
        summary = f"Document ({file.content_type}, {len(content)} bytes). Content parsing available in future version."

    return {
        "filename": file.filename or "unknown",
        "contentType": file.content_type or "application/octet-stream",
        "size": len(content),
        "summary": summary,
    }
