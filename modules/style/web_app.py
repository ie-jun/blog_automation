"""Module 3 FastAPI application — Style guide web UI.

Routes:
    GET  /                              → index.html
    GET  /guide                         → current style guide JSON
    POST /feedback                      → update guide via user feedback
    GET  /history                       → style change history
    POST /analyze-url                   → start URL style analysis
    GET  /analyze-url/status/{sid}      → check analysis session status
    POST /apply-style                   → apply selected sections from analysis
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import settings
from core.logger import setup_logger
from modules.style import history_manager, style_updater
from modules.style.runner import (
    run_style_module,
    run_url_analysis_module,
    run_style_merge_module,
)

logger = setup_logger("style")

# In-memory session cache: {session_id: AnalysisSession dict}
_analysis_cache: dict[str, dict] = {}

app = FastAPI(title="Blog Style Guide", version="1.0.0")

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    feedback: str


class AnalyzeUrlRequest(BaseModel):
    url: str


class ApplyStyleRequest(BaseModel):
    session_id: str
    selected_sections: list[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Serve the main web UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/guide")
async def get_guide() -> JSONResponse:
    """Return the current style guide."""
    guide = style_updater.load_current_guide()
    return JSONResponse(content=guide)


@app.post("/feedback")
async def feedback(req: FeedbackRequest) -> JSONResponse:
    """Update the style guide based on user feedback.

    Args:
        req: FeedbackRequest with feedback text.

    Returns:
        JSON with success status and diff summary.
    """
    if not req.feedback.strip():
        raise HTTPException(status_code=400, detail="feedback must not be empty")

    result = run_style_module(req.feedback)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return JSONResponse(content={
        "success": True,
        "diff_summary": result.diff_summary,
        "updated_at": result.updated_at,
    })


@app.get("/history")
async def get_history(limit: int = 20) -> JSONResponse:
    """Return recent style guide change history.

    Args:
        limit: Maximum number of entries to return.
    """
    entries = history_manager.load_history(limit=limit)
    return JSONResponse(content=entries)


@app.post("/analyze-url")
async def analyze_url(req: AnalyzeUrlRequest) -> JSONResponse:
    """Start async URL style analysis and return a session ID.

    Args:
        req: AnalyzeUrlRequest with the blog post URL.
    """
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url must not be empty")

    result = await run_url_analysis_module(
        req.url, _analysis_cache, session_ttl=settings.url_analysis_session_ttl
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return JSONResponse(content={
        "success": True,
        "session_id": result.session_id,
        "post_title": result.post_title,
        "analysis_summary": result.analysis_summary,
        "style_sections": result.style_sections,
    })


@app.get("/analyze-url/status/{session_id}")
async def analysis_status(session_id: str) -> JSONResponse:
    """Check whether an analysis session is still valid.

    Args:
        session_id: Session ID returned by /analyze-url.
    """
    session = _analysis_cache.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    now = datetime.now(timezone.utc).timestamp()
    expires_in = int(session["expires_at"] - now)
    if expires_in <= 0:
        del _analysis_cache[session_id]
        raise HTTPException(status_code=404, detail="Session expired — please re-analyze")

    return JSONResponse(content={"valid": True, "expires_in_seconds": expires_in})


@app.post("/apply-style")
async def apply_style(req: ApplyStyleRequest) -> JSONResponse:
    """Apply selected sections from a cached analysis into the style guide.

    Args:
        req: ApplyStyleRequest with session_id and selected_sections.
    """
    session = _analysis_cache.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    now = datetime.now(timezone.utc).timestamp()
    if session["expires_at"] < now:
        del _analysis_cache[req.session_id]
        raise HTTPException(status_code=404, detail="Session expired — please re-analyze")

    result = run_style_merge_module(
        extracted_style=session["extracted_style"],
        selected_sections=req.selected_sections,
        source_url=session["source_url"],
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    # Clean up session after apply
    del _analysis_cache[req.session_id]

    return JSONResponse(content={
        "success": True,
        "applied_sections": result.applied_sections,
        "diff_summary": result.diff_summary,
        "updated_at": result.updated_at,
    })
