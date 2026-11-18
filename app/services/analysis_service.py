"""Orchestration service: URL -> fetch -> LLM -> validated five-section report.

Cost-optimisation notes:
- Website HTML is aggressively cleaned before the LLM ever sees it (see
  website_extractor) — typically ~12k characters instead of hundreds of KB.
- A single LLM call produces all five sections (one prompt, one response).
- Results are cached in-memory per URL for CACHE_TTL_SECONDS so repeat
  analyses of the same site cost nothing extra.
"""
import json
import time
from typing import Any

from app.config import settings
from app.schemas import Analysis, BrandInfo, LinkAnalysisResponse
from app.services import llm_service
from app.services.competitor_service import COMPETITOR_INSTRUCTIONS
from app.services.website_extractor import WebsiteFetchError, fetch_website

# ------------------------------------------------------------------ cache --

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_get(url: str) -> dict[str, Any] | None:
    entry = _cache.get(url)
    if entry and time.time() - entry[0] < settings.cache_ttl_seconds:
        return entry[1]
    if entry:
        _cache.pop(url, None)
    return None


# ------------------------------------------------------------------ prompt --

SYSTEM_PROMPT = """You are a senior digital marketing and competitive-intelligence \
analyst. You are given the extracted text content of a single website page. \
Analyse ONLY what the content supports; do not invent facts about the business. \
When something must be inferred (e.g. additional services, competitors), label \
it using the fields the response schema provides. Respond with valid JSON only."""


def _build_user_prompt(website_url: str, context: str) -> str:
    return f"""Analyze this website: {website_url}

=== EXTRACTED WEBSITE CONTENT START ===
{context}
=== EXTRACTED WEBSITE CONTENT END ===

{COMPETITOR_INSTRUCTIONS}

Produce a single JSON object with EXACTLY this structure (respect all field
names; no extra top-level keys, no comments):

{{
  "brand": {{"name": "...", "category": "...", "summary": "..."}},
  "analysis": {{
    "competitor_analysis": {{
      "brand_overview": "...",
      "main_category": "...",
      "main_products_services": ["..."],
      "competitors": [
        {{"name": "...", "main_service": "...", "target_market": "...",
          "key_strength": "...", "weakness": "..."}}
      ],
      "competitor_strengths": ["..."],
      "competitor_weaknesses": ["..."],
      "your_competitive_advantages": ["..."],
      "opportunities": ["..."]
    }},
    "target_search_queries": [
      {{"query": "...",
        "platforms": ["Google", "Facebook", "Instagram", "LinkedIn", "X"],
        "intent": "e.g. Service Search / Business Discovery / Inspiration / B2B Search / Service Discovery",
        "business_relevance": "...",
        "target_audience": "..."}}
    ],
    "seo_improvements": {{
      "primary_keyword": "...",
      "secondary_keywords": ["..."],
      "long_tail_keywords": ["..."],
      "business_keywords": ["..."],
      "current_title": "...",
      "recommended_title": "...",
      "recommended_title_primary_keyword": "...",
      "title_structure_notes": "...",
      "current_meta_description": "...",
      "recommended_meta_description": "...",
      "meta_business_summary": "...",
      "supporting_content": [{{"type": "e.g. Service landing page | FAQ | Blog topic | Location page", "topic": "...", "why": "..."}}]
    }},
    "top_services": [
      {{"service_name": "...", "description": "...", "target_industry": "...",
        "target_customer": "...", "main_benefit": "...",
        "source": "website" or "inferred"}}
    ],
    "target_audience": {{
      "primary_audience": ["..."],
      "secondary_audience": ["..."],
      "industries": ["..."],
      "business_types": ["..."],
      "customer_profiles": ["..."],
      "location_focus": "...",
      "customer_needs": ["..."],
      "customer_challenges": ["..."],
      "customer_interests": ["..."],
      "recommended_segments": [{{"audience": "...", "business_type": "...", "requirement": "..."}}]
    }}
  }}
}}

STRICT RULES:
1. target_search_queries: EXACTLY 5 items. Base them on the site's services,
   category and audience. Never state or imply numeric search volumes or
   rankings — you have no such data.
2. top_services: EXACTLY 5 items, taken from actual website content where
   possible; use "source": "inferred" for anything not directly on the page.
3. seo_improvements: derive keywords from the actual page content. The
   recommended title should be <= 60 characters and the recommended meta
   description <= 160 characters.
4. Platforms array may contain only: Google, Facebook, Instagram, LinkedIn, X.
5. JSON only. No markdown, no commentary."""


# --------------------------------------------------------------- pipeline --

def analyze_link(url: str) -> dict[str, Any]:
    """Run the full analysis pipeline and return the response payload dict.

    Raises WebsiteFetchError or LLMError; both are handled by the endpoint.
    """
    cached = _cache_get(url)
    if cached:
        return {**cached, "meta": {**cached.get("meta", {}), "cached": True}}

    content, llm_context = fetch_website(url)
    llm = llm_service.generate_json(SYSTEM_PROMPT, _build_user_prompt(url, llm_context))

    try:
        analysis = Analysis.model_validate(llm.data.get("analysis", {}))
        brand = BrandInfo.model_validate(llm.data.get("brand", {}))
    except Exception as exc:
        raise llm_service.LLMError(f"LLM output failed schema validation: {exc}")

    payload = LinkAnalysisResponse(
        website=url,
        brand=brand,
        analysis=analysis,
        meta={
            "provider": settings.llm_provider,
            "model": settings.gemini_model
            if settings.llm_provider == "gemini"
            else settings.openai_model
            if settings.llm_provider == "openai"
            else settings.anthropic_model,
            "latency_ms": llm.latency_ms,
            "prompt_tokens": llm.usage.get("prompt_tokens", 0),
            "completion_tokens": llm.usage.get("completion_tokens", 0),
            "competitor_note": "Competitor details are AI-generated suggestions and must be verified independently.",
            "search_volume_note": "Search volumes/rankings are intentionally omitted (no reliable data source used).",
        },
    ).model_dump()

    _cache[url] = (time.time(), payload)
    return payload
