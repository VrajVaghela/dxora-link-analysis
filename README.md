# AI-Powered Website Link Analysis API

A FastAPI service that analyzes a website URL, understands its content with an LLM, and returns a
structured report covering **competitor analysis, target search queries, SEO improvements, top
services and target audience**.

## Planning method

This project was planned using the **goldfish method**: instead of holding the whole spec in memory,
it was split into short independent iterations (validation → extraction → LLM layer → schema →
endpoint → tests → research), with the spec re-read and the previous iteration re-verified at the
start of each step.

---

## 1. Quick start

```bash
# 1. Clone and install
python -m venv .venv
.venv/Scripts/activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Configure your LLM API key
copy .env.example .env            # Linux/macOS: cp .env.example .env
# then edit .env and set GEMINI_API_KEY=... (or an OpenAI / Anthropic key)

# 3. Run
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

- API documentation (Swagger): **http://localhost:4000/docs**
- Health check: `GET http://localhost:4000/health`

### Run tests

```bash
pytest tests/ -q
```

All 19 tests pass; external website fetching and LLM calls are mocked, so tests are free and fast.

---

## 2. API usage

### Request

```http
POST http://localhost:4000/link-analysis
Content-Type: application/json

{ "url": "https://example.com" }
```

### Response (abridged)

```json
{
  "success": true,
  "website": "https://example.com",
  "brand": { "name": "...", "category": "...", "summary": "..." },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "...",
      "main_category": "...",
      "main_products_services": ["..."],
      "competitors": [
        { "name": "...", "main_service": "...", "target_market": "...",
          "key_strength": "...", "weakness": "..." }
      ],
      "competitor_strengths": ["..."],
      "competitor_weaknesses": ["..."],
      "your_competitive_advantages": ["..."],
      "opportunities": ["..."],
      "competitor_data_source": "ai_generated_suggestion"
    },
    "target_search_queries": [
      { "query": "...", "platforms": ["Google", "LinkedIn"],
        "intent": "Service Discovery", "business_relevance": "...", "target_audience": "..." }
    ],
    "seo_improvements": {
      "primary_keyword": "...", "secondary_keywords": ["..."],
      "long_tail_keywords": ["..."], "business_keywords": ["..."],
      "current_title": "...", "recommended_title": "...",
      "recommended_title_primary_keyword": "...", "title_structure_notes": "...",
      "current_meta_description": "...", "recommended_meta_description": "...",
      "meta_business_summary": "...", "supporting_content": [{"type": "FAQ", "topic": "...", "why": "..."}]
    },
    "top_services": [
      { "service_name": "...", "description": "...", "target_industry": "...",
        "target_customer": "...", "main_benefit": "...", "source": "website" }
    ],
    "target_audience": {
      "primary_audience": ["..."], "secondary_audience": ["..."],
      "industries": ["..."], "business_types": ["..."], "customer_profiles": ["..."],
      "location_focus": "...", "customer_needs": ["..."], "customer_challenges": ["..."],
      "customer_interests": ["..."],
      "recommended_segments": [{"audience": "...", "business_type": "...", "requirement": "..."}]
    }
  },
  "meta": {
    "provider": "gemini", "model": "gemini-3.5-flash-lite",
    "latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0,
    "cached": false,
    "competitor_note": "Competitor details are AI-generated suggestions and must be verified independently.",
    "search_volume_note": "Search volumes/rankings are intentionally omitted (no reliable data source used)."
  }
}
```

### Error handling

| Case | HTTP | Body |
|---|---|---|
| Malformed / private / non-HTTP URL (SSRF-blocked) | 400 | `{"success": false, "error": "..."}` |
| Site unreachable, blocked (401/403/429), not HTML | 422 | `{"success": false, "error": "..."}` |
| LLM/provider failure after retries | 502 | `{"success": false, "error": "..."}` |

---

## 3. How it works

1. **Validate** the URL (`app/utils/validators.py`) — scheme check, credentials check, DNS
   resolution, and SSRF protection: every resolved address must be globally routable (blocks
   `localhost`, RFC1918 ranges, `169.254.169.254` metadata endpoints, `::1`, link-local…).
2. **Fetch** the page with `httpx` (`app/services/website_extractor.py`) — timeouts, redirect and
   size caps, User-Agent header, 401/403/429 handled explicitly.
3. **Extract & clean** — BeautifulSoup strips scripts/styles/nav/footer/boilerplate and produces
   title, meta description, headings, internal-link labels and body text.
4. **Build a compact LLM context** — capped at ~12,000 characters (default) to control cost.
5. **One LLM call** (`app/services/llm_service.py`) generates all five sections in **strict JSON
   mode** (Gemini `responseMimeType`, OpenAI `response_format`, Anthropic prompt-pinned JSON),
   with retry on transient failures.
6. **Validate** the output against strict Pydantic schemas (`app/schemas.py`) — exactly 5 search
   queries, exactly 5 services, enum-checked platforms, `"source": "website" | "inferred"` labelling.
7. **Return** structured JSON; results are cached in memory per URL for 1 hour (cost control).

### Honesty guarantees (per task requirements)

- Competitor details come from the LLM's industry knowledge and are always marked
  `competitor_data_source: "ai_generated_suggestion"`.
- **No search volumes or rankings are ever invented** — none are returned anywhere.
- Inferred services are labelled `"source": "inferred"`.

---

## 4. LLM Platform & Model Research (pricing verified 17 Nov 2026)

### A. Platform comparison

Prices are the providers' published paid-tier rates per 1M tokens.

| Criteria | Google Gemini | OpenAI | Anthropic |
|---|---|---|---|
| **Provider** | Google AI | OpenAI | Anthropic |
| **Recommended model** | `gemini-3.5-flash-lite` | `gpt-6.1-terra` | `claude-haiku-4-5` |
| **API cost (in/out)** | **$0.30 / $2.50** | $1.00 / $5.00 | $1.00 / $5.00 |
| **Response speed** | Fastest of the three (Lite-class model, ~sub-2s typical for this prompt size — *estimated, not benchmarked*) | Fast (mid-class) | Fast (Haiku-class) |
| **Accuracy (content understanding)** | Strong for this task class; Gemini model card (Jul 2026) shows Flash-Lite outperforming Haiku 4.5 on knowledge-work benchmarks (GDPVal Elo 1140 vs 907) | Comparable or better on coding/agentic benchmarks, more than needed here | Good, but the same DeepMind card shows Haiku 4.5 trailing both competitors on the cited knowledge-work benchmarks |
| **Context window** | **1M tokens** | 272K+ (2× long-context pricing past 272K) | 200K |
| **JSON support** | Native `responseMimeType: application/json` constrained JSON mode | Native `response_format: json_object` | Prompt-pinned JSON (no hard mode) |
| **Recommendation** | **Best fit** | Solid fallback | Solid fallback |

Sources: Google DeepMind model card for Gemini 3.5 Flash-Lite and Google AI Studio pricing page;
OpenAI pricing page (`developers.openai.com/api/docs/pricing`); Anthropic docs
(`platform.claude.com/docs/en/models/haiku-4-5/overview`).

### B. Selection rationale

1. **Accuracy** — Flash-Lite benchmarks (GDPVal, SWE-Bench Pro) place it at parity with GPT-5.4-mini
   and ahead of Claude Haiku 4.5 for knowledge-work tasks, which is what content analysis is.
   *(Vendor-published benchmark, not independently measured for this task.)*
2. **Speed** — Flash-Lite is Google's lowest-latency current tier; latency is dominated by output
   length, which is capped at 4,096 tokens here.
3. **Cost** — cheapest per-output-token of the three candidates ($2.50 vs $5.00).
4. **Reliable JSON** — native constrained JSON mode; combined with strict Pydantic validation,
   malformed output cannot reach the client.
5. **Large context** — 1M tokens comfortably handles big pages even untruncated.

### C. Cost optimization applied

- HTML is stripped of scripts/styles/boilerplate **before** the LLM sees it (~12k chars ≈ ~3k
  tokens instead of 50k+ tokens of raw HTML).
- Headings and link labels are prioritized over raw text — highest information per token.
- Single LLM call for all five sections (no multi-round agent loops).
- In-memory result cache (1h TTL) — repeat analyses of the same URL are free.
- Temperature 0.4 and a 4,096-token output cap.

### D. Final recommendation

| Item | Value |
|---|---|
| Recommended provider | Google (Gemini API) |
| Recommended model | `gemini-3.5-flash-lite` |
| Estimated input usage | ~4,500 tokens/page (analysis prompt ≈ 1.5k + website context ≈ 3k) |
| Estimated output usage | ~2,000 tokens/page |
| Estimated cost / analysis | 4.5k × $0.30/1M + 2k × $2.50/1M ≈ **$0.0064** (~$6.4 per 1,000 analyses) |
| Expected response time | ~2–4 s total request latency (estimated; `meta.latency_ms` in the response reports the measured LLM time) |
| Reason | Lowest published cost of current fast-tier models, native JSON mode, 1M context, adequate benchmarked knowledge-work accuracy |
| Fallback model | `gpt-6.1-terra` (OpenAI, $1/$5) or `claude-haiku-4-5` ($1/$5) — both switchable via `.env` with no code change |
| Balance approach | Keep Flash-Lite for standard analyses; escalate to a larger model only for pages where schema validation fails repeatedly; use caching and content capping to control volume cost |

---

## 5. Project structure

```text
ai-link-analysis/
├── app/
│   ├── main.py                    # FastAPI app + POST /link-analysis
│   ├── config.py                  # env-driven settings (pydantic-settings)
│   ├── schemas.py                 # strict Pydantic response models
│   ├── services/
│   │   ├── website_extractor.py   # fetch + BeautifulSoup extraction + cleaning
│   │   ├── llm_service.py         # Gemini / OpenAI / Anthropic JSON-mode calls
│   │   ├── analysis_service.py    # orchestration, prompt, caching, validation
│   │   └── competitor_service.py  # competitor-analysis prompt policy
│   └── utils/
│       └── validators.py          # URL validation + SSRF protection
├── tests/
│   └── test_link_analysis.py      # 19 tests (fetch & LLM mocked)
├── .env.example
├── requirements.txt
└── README.md
```

---

## 6. Deployment

Deploy anywhere Python runs; a minimal production recipe:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 4000   # behind nginx / a PaaS proxy in production
```

Options: Render / Railway / Fly.io (free tiers), or a VPS with `systemd` + Caddy. Set the same
`.env` variables in the platform's environment settings and expose `POST /link-analysis` and
`GET /docs` over HTTPS.
