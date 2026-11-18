"""Tests for the /link-analysis API.

External effects (website fetching and LLM calls) are mocked, so the suite
runs fast and costs nothing. SSRF / URL validation tests run against real
validation logic.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import analysis_service
from app.services.website_extractor import WebsiteContent, WebsiteFetchError

client = TestClient(app)

VALID_LLM_JSON = {
    "brand": {"name": "Test Co", "category": "Technology Services", "summary": "A tech company."},
    "analysis": {
        "competitor_analysis": {
            "brand_overview": "Overview",
            "main_category": "Technology Services",
            "main_products_services": ["Web development"],
            "competitors": [
                {"name": "Rival A", "main_service": "Web development", "target_market": "SMB",
                 "key_strength": "Brand", "weakness": "Slow support"}
            ],
            "competitor_strengths": ["Strong brand"],
            "competitor_weaknesses": ["Slow support"],
            "your_competitive_advantages": ["Pricing"],
            "opportunities": ["SEO"],
        },
        "target_search_queries": [
            {"query": f"technology services {i}", "platforms": ["Google"],
             "intent": "Service Discovery", "business_relevance": "High",
             "target_audience": "SMBs"}
            for i in range(1, 6)
        ],
        "seo_improvements": {
            "primary_keyword": "technology services",
            "secondary_keywords": ["web development"],
            "long_tail_keywords": ["affordable technology services for startups"],
            "business_keywords": ["software"],
            "current_title": "Home",
            "recommended_title": "Technology Services for Growing Businesses | Test Co",
            "recommended_title_primary_keyword": "technology services",
            "title_structure_notes": "Keyword first, brand last.",
            "current_meta_description": "",
            "recommended_meta_description": "Test Co provides technology services.",
            "meta_business_summary": "Tech services provider.",
            "supporting_content": [{"type": "FAQ", "topic": "Pricing", "why": "Common question"}],
        },
        "top_services": [
            {"service_name": f"Service {i}", "description": "desc", "target_industry": "Tech",
             "target_customer": "SMB", "main_benefit": "Value", "source": "website"}
            for i in range(1, 6)
        ],
        "target_audience": {
            "primary_audience": ["Small businesses"],
            "secondary_audience": ["Startups"],
            "industries": ["Technology"],
            "business_types": ["Services"],
            "customer_profiles": ["Owner/operators"],
            "location_focus": "Global",
            "customer_needs": ["Online presence"],
            "customer_challenges": ["Limited budget"],
            "customer_interests": ["Growth"],
            "recommended_segments": [{"audience": "SMBs", "business_type": "Services", "requirement": "Websites"}],
        },
    },
}

FAKE_CONTENT = WebsiteContent(
    url="https://example.com",
    final_url="https://example.com",
    title="Test Co — Technology Services",
    meta_description="We provide technology services.",
    headings=["Services", "About Us", "Contact"],
    links=["Services", "About"],
    text="Test Co provides technology services including web development for small businesses. " * 5,
)


def _mock_pipeline(llm_json=VALID_LLM_JSON):
    return (
        patch("app.services.analysis_service.fetch_website", return_value=(FAKE_CONTENT, "context text")),
        patch("app.services.llm_service.generate_json",
              return_value=type("R", (), {"data": llm_json, "latency_ms": 800, "usage": {"prompt_tokens": 3000, "completion_tokens": 1500}})()),
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    analysis_service._cache.clear()
    yield


class TestValidation:
    @pytest.mark.parametrize("bad_url", [
        "", "not-a-url", "ftp://example.com", "file:///etc/passwd",
        "http://localhost:4000", "http://127.0.0.1", "http://10.0.0.5",
        "http://192.168.1.1", "http://169.254.169.254/latest/meta-data",
        "http://[::1]/", "http://user:pass@example.com",
        "https://172.20.1.1",
    ])
    def test_rejects_invalid_and_private_urls(self, bad_url):
        response = client.post("/link-analysis", json={"url": bad_url})
        assert response.status_code == 400
        assert response.json()["success"] is False

    def test_accepts_valid_public_url_shape(self):
        # Valid public URL passes SSRF validation and runs the full mocked pipeline.
        fetch_patch, llm_patch = _mock_pipeline()
        with fetch_patch, llm_patch:
            response = client.post("/link-analysis", json={"url": "https://example.com"})
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestEndpoint:
    def test_happy_path_returns_five_sections(self):
        fetch_patch, llm_patch = _mock_pipeline()
        with fetch_patch, llm_patch:
            response = client.post("/link-analysis", json={"url": "https://example.com"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["website"] == "https://example.com"
        assert body["brand"]["name"] == "Test Co"
        analysis = body["analysis"]
        for section in ("competitor_analysis", "target_search_queries",
                        "seo_improvements", "top_services", "target_audience"):
            assert section in analysis
        assert len(analysis["target_search_queries"]) == 5
        assert len(analysis["top_services"]) == 5
        assert body["analysis"]["competitor_analysis"]["competitor_data_source"] == "ai_generated_suggestion"
        assert body["meta"]["prompt_tokens"] > 0

    def test_second_call_is_cached(self):
        fetch_patch, llm_patch = _mock_pipeline()
        with fetch_patch, llm_patch:
            client.post("/link-analysis", json={"url": "https://example.com"})
            response = client.post("/link-analysis", json={"url": "https://example.com"})
        assert response.json()["meta"]["cached"] is True

    def test_inaccessible_website_returns_422(self):
        with patch("app.services.analysis_service.fetch_website",
                   side_effect=WebsiteFetchError("Website returned HTTP 403 (access restricted).")):
            response = client.post("/link-analysis", json={"url": "https://example.com"})
        assert response.status_code == 422
        assert response.json() == {"success": False, "error": "Website returned HTTP 403 (access restricted)."}

    def test_llm_failure_returns_502(self):
        from app.services.llm_service import LLMError
        fetch_patch, _ = _mock_pipeline()
        with fetch_patch, patch("app.services.llm_service.generate_json",
                                side_effect=LLMError("LLM returned invalid JSON.")):
            response = client.post("/link-analysis", json={"url": "https://example.com"})
        assert response.status_code == 502
        assert response.json()["success"] is False

    def test_llm_bad_structure_rejected(self):
        bad = {"brand": {"name": "x"}, "analysis": {"competitor_analysis": {"brand_overview": "x"}}}
        fetch_patch, _ = _mock_pipeline()
        with fetch_patch, patch("app.services.llm_service.generate_json") as mock_llm:
            mock_llm.return_value.data = bad
            mock_llm.return_value.latency_ms = 100
            mock_llm.return_value.usage = {}
            response = client.post("/link-analysis", json={"url": "https://example.com"})
        assert response.status_code == 502


class TestHealth:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
