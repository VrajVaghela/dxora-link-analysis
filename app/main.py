"""FastAPI application entry point.

Run with:  uvicorn app.main:app --host 0.0.0.0 --port 4000
Docs at:   http://localhost:4000/docs
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas import LinkAnalysisResponse
from app.services.analysis_service import analyze_link
from app.services.llm_service import LLMError
from app.services.website_extractor import WebsiteFetchError
from app.utils.validators import InvalidURLError, PrivateAddressError, validate_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("link-analysis")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Analyzes a website URL, understands its content with an LLM, and returns "
        "structured business, competitor, SEO, search-query and target-audience insights."
    ),
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a JSON error instead of a plain-text 500 for anything unexpected."""
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"success": False, "error": "Internal server error."})


class LinkAnalysisRequest(BaseModel):
    url: str = Field(..., examples=["https://example.com"])


@app.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    responses={
        200: {"description": "Structured five-section website analysis report"},
        400: {"description": "Invalid URL or blocked private/internal address (SSRF protection)"},
        422: {"description": "Inaccessible website or insufficient readable content"},
        502: {"description": "LLM provider or parsing error"},
    },
)
def link_analysis(request: LinkAnalysisRequest) -> JSONResponse:
    """Analyze a website and return the five-section structured report."""
    try:
        url = validate_url(request.url)
    except InvalidURLError as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})

    try:
        result = analyze_link(url)
        return JSONResponse(status_code=200, content=result)
    except WebsiteFetchError as exc:
        # Inaccessible websites / blocked bots / non-HTML pages.
        logger.warning("Fetch failed for %s: %s", url, exc)
        return JSONResponse(status_code=422, content={"success": False, "error": str(exc)})
    except LLMError as exc:
        logger.error("LLM failure for %s: %s", url, exc)
        return JSONResponse(status_code=502, content={"success": False, "error": f"Analysis engine failure: {exc}"})


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect root to interactive Swagger UI documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_provider": settings.llm_provider}
