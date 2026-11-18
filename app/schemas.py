"""Pydantic response schemas for the /link-analysis endpoint."""
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- Brand ----

class BrandInfo(BaseModel):
    name: str
    category: str
    summary: str


# ------------------------------------------------- Section 1: competitors --

class CompetitorDetail(BaseModel):
    name: str
    main_service: str
    target_market: str
    key_strength: str
    weakness: str


class CompetitorAnalysis(BaseModel):
    brand_overview: str
    main_category: str
    main_products_services: list[str]
    competitors: list[CompetitorDetail] = Field(
        description="Minimum 3 competitors where reliable information is available"
    )
    competitor_strengths: list[str]
    competitor_weaknesses: list[str]
    your_competitive_advantages: list[str]
    opportunities: list[str]
    competitor_data_source: Literal["ai_generated_suggestion"] = (
        "ai_generated_suggestion"
    )  # competitor intel is LLM-generated; never presented as verified fact


# --------------------------------------- Section 2: search queries ---------

class SearchQuery(BaseModel):
    query: str
    platforms: list[Literal["Google", "Facebook", "Instagram", "LinkedIn", "X"]]
    intent: str
    business_relevance: str
    target_audience: str


# --------------------------------------- Section 3: SEO --------------------

class SeoImprovements(BaseModel):
    primary_keyword: str
    secondary_keywords: list[str]
    long_tail_keywords: list[str]
    business_keywords: list[str]
    current_title: str
    recommended_title: str
    recommended_title_primary_keyword: str
    title_structure_notes: str
    current_meta_description: str
    recommended_meta_description: str
    meta_business_summary: str
    supporting_content: list[dict[str, str]] = Field(
        description='List of {"type": ..., "topic": ..., "why": ...} suggestions'
    )


# --------------------------------------- Section 4: top services -----------

class ServiceItem(BaseModel):
    service_name: str
    description: str
    target_industry: str
    target_customer: str
    main_benefit: str
    source: Literal["website", "inferred"]  # inferred items must be labelled


# --------------------------------------- Section 5: audience ---------------

class AudienceItem(BaseModel):
    audience: str
    business_type: str
    requirement: str


class TargetAudience(BaseModel):
    primary_audience: list[str]
    secondary_audience: list[str]
    industries: list[str]
    business_types: list[str]
    customer_profiles: list[str]
    location_focus: str
    customer_needs: list[str]
    customer_challenges: list[str]
    customer_interests: list[str]
    recommended_segments: list[AudienceItem]


# ----------------------------------------------------------- Full response --

class Analysis(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SeoImprovements
    top_services: list[ServiceItem] = Field(min_length=5, max_length=5)
    target_audience: TargetAudience


class LinkAnalysisResponse(BaseModel):
    success: bool = True
    website: str
    brand: BrandInfo
    analysis: Analysis
    meta: dict = Field(
        description="LLM provider/model, latency and token usage for transparency"
    )
