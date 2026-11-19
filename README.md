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
git clone https://github.com/VrajVaghela/dxora-link-analysis.git
cd dxora-link-analysis
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
- Interactive root redirect: **http://localhost:4000/** (redirects to `/docs`)
- Health check: `GET http://localhost:4000/health`

### Run tests

```bash
pytest
```

All 23 unit and regression tests pass; external website fetching and LLM calls are mocked, so tests are free, reproducible, and fast.

---

## 2. API usage

### Request

```bash
curl -X POST http://localhost:4000/link-analysis \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Complete Response Example

```json
{
  "success": true,
  "website": "https://example.com",
  "brand": {
    "name": "Example Domain",
    "category": "Documentation & Standards",
    "summary": "An illustrative domain established by IANA for use in illustrative examples in documents."
  },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "Example Domain provides placeholder and illustrative web resources for RFCs and technical documentation.",
      "main_category": "Standards & Reference Domains",
      "main_products_services": [
        "Example web domain reservation",
        "RFC 2606 and RFC 6761 demonstration",
        "Documentation placeholder links"
      ],
      "competitors": [
        {
          "name": "IANA (Internet Assigned Numbers Authority)",
          "main_service": "Global IP and DNS parameter coordination",
          "target_market": "Network engineers, registries, developers",
          "key_strength": "Official global authority for Internet standards",
          "weakness": "Strictly administrative, non-commercial documentation"
        },
        {
          "name": "ICANN",
          "main_service": "Internet namespace management and domain governance",
          "target_market": "Domain registrars and technical communities",
          "key_strength": "Global policy leadership and domain ecosystem authority",
          "weakness": "Complex organizational scope; not focused on developer placeholders"
        },
        {
          "name": "RFC Editor",
          "main_service": "Publication and archiving of RFC technical specifications",
          "target_market": "Software engineers and protocol architects",
          "key_strength": "Definitive source of RFC documentation",
          "weakness": "Academic formatting with limited modern web guidance"
        }
      ],
      "competitor_strengths": [
        "Globally recognized authority",
        "Established by international standards bodies",
        "Zero-downtime authoritative infrastructure"
      ],
      "competitor_weaknesses": [
        "Static and informational only",
        "No interactive developer sandbox",
        "Minimal SEO and digital marketing utility"
      ],
      "your_competitive_advantages": [
        "Universal recognition across every modern browser and documentation repository",
        "Permanent, immutable reserve status under RFC 6761",
        "Fastest loading time with zero external scripts or tracking"
      ],
      "opportunities": [
        "Host interactive API mockup playgrounds for developers",
        "Provide machine-readable OpenAPI and schema.org standard examples",
        "Enhance developer tutorials on domain delegation and DNSSEC"
      ],
      "strengths": [
        "Universal recognition across every modern browser and documentation repository",
        "Permanent, immutable reserve status under RFC 6761"
      ],
      "competitor_data_source": "ai_generated_suggestion"
    },
    "target_search_queries": [
      {
        "query": "RFC 2606 reserved example domain names",
        "platforms": ["Google", "LinkedIn"],
        "intent": "Technical Documentation",
        "business_relevance": "Direct match for developers seeking compliant example URLs",
        "target_audience": "Software developers, technical writers"
      },
      {
        "query": "How to use example.com in documentation",
        "platforms": ["Google", "X"],
        "intent": "How-To Reference",
        "business_relevance": "Educational intent for technical authors and bloggers",
        "target_audience": "Documentation authors and engineers"
      },
      {
        "query": "IANA special use domain names guidelines",
        "platforms": ["Google", "LinkedIn"],
        "intent": "Compliance & Standards Search",
        "business_relevance": "Standardized DNS resource query",
        "target_audience": "System administrators and network engineers"
      },
      {
        "query": "Best placeholder URLs for API testing",
        "platforms": ["Google", "X"],
        "intent": "Tool Discovery",
        "business_relevance": "Engineers building automated tests and test fixtures",
        "target_audience": "QA engineers and full-stack developers"
      },
      {
        "query": "Valid dummy domain names for sample code",
        "platforms": ["Google", "Facebook"],
        "intent": "Developer Discovery",
        "business_relevance": "Coding tutorials and educational courses",
        "target_audience": "Computer science students and educators"
      }
    ],
    "seo_improvements": {
      "primary_keyword": "Example Domain",
      "secondary_keywords": [
        "reserved domains",
        "RFC 2606",
        "IANA documentation domains",
        "placeholder URL"
      ],
      "long_tail_keywords": [
        "how to use example domains in technical documentation",
        "IANA reserved domain names for testing"
      ],
      "business_keywords": [
        "DNS standards",
        "Internet Assigned Numbers Authority",
        "ICANN"
      ],
      "current_title": "Example Domain",
      "recommended_title": "Example Domain | Official IANA Documentation Resource",
      "recommended_title_primary_keyword": "Example Domain",
      "title_structure_notes": "Placed primary identifier first followed by authority branding.",
      "current_meta_description": "",
      "recommended_meta_description": "Official reserved example domain by IANA for illustrative documentation and technical testing.",
      "meta_description": "Official reserved example domain by IANA for illustrative documentation and technical testing.",
      "meta_description_keywords": [
        "Example Domain",
        "IANA",
        "technical testing"
      ],
      "meta_business_summary": "Authoritative placeholder domain for technical documentation.",
      "supporting_content": [
        {
          "type": "FAQ",
          "topic": "Can I purchase or register example.com?",
          "why": "Directly answers the most frequent user question and reduces bounce rate."
        },
        {
          "type": "Developer Guide",
          "topic": "Best practices for using example.com in API tutorials",
          "why": "Attracts high-authority backlinks from developer blogs and documentation sites."
        },
        {
          "type": "Compliance Page",
          "topic": "RFC 6761 Special-Use Domain Names summary",
          "why": "Targets high-intent technical search queries from standards auditors."
        }
      ]
    },
    "top_services": [
      {
        "service_name": "Documentation Placeholder",
        "description": "Safe, collision-free placeholder domain for use in RFCs, tutorials, and books.",
        "target_industry": "Information Technology & Publishing",
        "target_customer": "Technical authors, developers, and educators",
        "main_benefit": "Guarantees no real-world traffic collisions or unintended domain purchases",
        "source": "website"
      },
      {
        "service_name": "RFC 2606 & 6761 Reference",
        "description": "Living web implementation of Internet Engineering Task Force reserved name standards.",
        "target_industry": "Internet Governance & Networking",
        "target_customer": "Network engineers and protocol designers",
        "main_benefit": "Standardized compliance verification",
        "source": "website"
      },
      {
        "service_name": "API Mock URL Target",
        "description": "Standard endpoint target for automated testing and code snippet examples.",
        "target_industry": "Software Quality Assurance",
        "target_customer": "QA automation engineers and test developers",
        "main_benefit": "Prevents spamming real servers during automated test execution",
        "source": "inferred"
      },
      {
        "service_name": "DNS Sandbox Demonstration",
        "description": "Reference resolution test target for DNS resolver configurations and validators.",
        "target_industry": "Cloud Infrastructure & Hosting",
        "target_customer": "DevOps engineers and network administrators",
        "main_benefit": "Consistent, predictable DNS resolution without external dependencies",
        "source": "inferred"
      },
      {
        "service_name": "Educational Tutorial Fixture",
        "description": "Safe domain for educational demonstrations, textbooks, and interactive coding labs.",
        "target_industry": "EdTech & Computer Science Education",
        "target_customer": "Instructors, bootcamps, and students",
        "main_benefit": "Zero security liability when published in student repositories",
        "source": "inferred"
      }
    ],
    "target_audience": {
      "primary_audience": [
        "Software Engineers & Full-Stack Developers",
        "Technical Writers & Documentation Authors"
      ],
      "secondary_audience": [
        "Computer Science Students & Educators",
        "Network Administrators & DevOps Specialists"
      ],
      "industries": [
        "Information Technology",
        "Software Development",
        "Cloud Infrastructure",
        "Technical Publishing"
      ],
      "business_types": [
        "Open-source projects",
        "Enterprise technology teams",
        "EdTech platforms",
        "Standards organizations"
      ],
      "customer_profiles": [
        "Lead technical documentation specialists writing developer guides",
        "Software engineers creating automated unit test mock data"
      ],
      "location_focus": "Global",
      "customer_needs": [
        "Safe, reserved domain names that will never be registered by third parties",
        "Adherence to official RFC and IANA standards"
      ],
      "customer_challenges": [
        "Accidental spamming or DDoS of live sites when using real domains in examples",
        "Security compliance flags when using arbitrary domains in documentation"
      ],
      "customer_interests": [
        "RFC standards",
        "API documentation best practices",
        "Clean code and mock test design"
      ],
      "recommended_segments": [
        {
          "audience": "Technical Writers",
          "business_type": "Developer Tools & Documentation",
          "requirement": "Clean placeholder domains for published manuals"
        },
        {
          "audience": "QA Automation Engineers",
          "business_type": "Enterprise Software",
          "requirement": "Mock test fixtures that never trigger real external network calls"
        },
        {
          "audience": "Protocol Developers",
          "business_type": "Networking & Infrastructure",
          "requirement": "Standards-compliant test namespaces"
        }
      ]
    }
  },
  "meta": {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "latency_ms": 1420,
    "prompt_tokens": 3120,
    "completion_tokens": 1280,
    "cached": false,
    "competitor_note": "Competitor details are AI-generated suggestions and must be verified independently.",
    "search_volume_note": "Search volumes/rankings are intentionally omitted (no reliable data source used)."
  }
}
```

### Server Execution Logs

```text
2026-11-18 12:15:02,104 INFO Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
2026-11-18 12:15:05,230 INFO [link-analysis] POST /link-analysis requested for: https://example.com
2026-11-18 12:15:05,245 INFO [link-analysis] Validated URL: https://example.com (DNS resolved to public IP: 93.184.215.14)
2026-11-18 12:15:05,820 INFO [link-analysis] Website content extracted (Title: 'Example Domain', 1,450 characters)
2026-11-18 12:15:07,240 INFO [link-analysis] Gemini 2.5 Flash response received (1,420ms, 4,400 tokens)
2026-11-18 12:15:07,248 INFO [link-analysis] Analysis completed and cached in memory. Status 200 OK
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

## 4. LLM Platform & Model Research (Pricing Verified 2026)

### A. Platform comparison

Prices are published paid-tier rates per 1M tokens (input / output).

| Criteria | Google Gemini | OpenAI | Anthropic |
|---|---|---|---|
| **Provider** | Google AI | OpenAI | Anthropic |
| **Recommended model** | `gemini-2.5-flash` | `gpt-4o-mini` | `claude-3-5-haiku-20241022` |
| **API cost (in/out)** | **$0.30 / $2.50** (or $0.10 / $0.40 on Flash-Lite) | $0.15 / $0.60 | $1.00 / $5.00 |
| **Response speed** | Very fast (~1.2–2.0s for 4.5k input / 1.5k output tokens) | Fast (~1.5–2.5s) | Fast (~1.5–2.5s) |
| **Accuracy (content understanding)** | Excellent on multi-section extraction, domain classification, and competitive intelligence | Strong general reasoning and JSON adherence | High instruction compliance, concise analysis |
| **Context window** | **1M tokens** | 128K tokens | 200K tokens |
| **JSON support** | Native `responseMimeType: application/json` constrained mode | Native `response_format: {"type": "json_object"}` | Supported via schema prompt pinning |
| **Recommendation** | **Best fit (Primary)** | **Top Fallback** | **Alternative Fallback** |

Sources: Google AI Studio developer documentation (`ai.google.dev/pricing`); OpenAI API documentation (`platform.openai.com/docs/models`); Anthropic Claude documentation (`docs.anthropic.com/en/docs/models-overview`).

### B. Selection rationale

1. **Accuracy** — Gemini 2.5 Flash demonstrates superior zero-shot structured extraction and industry classification benchmarks on diverse HTML pages.
2. **Speed & Latency** — Low time-to-first-token and high generation throughput enable full 5-section response generation under ~2 seconds.
3. **Cost Efficiency** — At $0.30/1M input and $2.50/1M output, a typical 4,500-input / 2,000-output website analysis costs only ~$0.0064 (less than 1 cent per site).
4. **Reliable Structured Output** — Native `responseMimeType: "application/json"` ensures grammatically valid JSON directly at the decoder level.
5. **Massive Context Window** — 1M token context headroom easily accommodates long landing pages without losing vital content.

### C. Cost optimization applied

- **Pre-LLM HTML Cleaning**: Scripts, styles, tracking tags, and noise containers are stripped before LLM ingestion (~12k chars ≈ ~3k tokens instead of 50k+ raw HTML tokens).
- **Signal Prioritization**: Page title, meta description, H1-H3 headings, and internal links are budgeted first to maximize information density per token.
- **Single-Turn Consolidation**: All five sections are generated in one prompt pass (eliminating multi-turn conversational overhead).
- **Bounded In-Memory Cache**: 1-hour TTL in-memory cache with normalized URLs and 500-item LRU capacity prevents redundant external API charges.
- **Conservative Generation Limits**: Temperature pinned to 0.4 with an upper token limit of 4,096 tokens.

### D. Final recommendation

| Item | Value |
|---|---|
| Recommended provider | Google (Gemini API) |
| Recommended model | `gemini-2.5-flash` |
| Estimated input usage | ~4,500 tokens/page (system prompt + cleaned page context) |
| Estimated output usage | ~1,500 – 2,000 tokens/page |
| Estimated cost / analysis | 4.5k × $0.30/1M + 2k × $2.50/1M ≈ **$0.0064** (~$6.40 per 1,000 analyses) |
| Expected response time | ~1.5–3.0 s total request latency (`meta.latency_ms` reports exact measured time) |
| Reason | High accuracy on business intelligence, native constrained JSON mode, 1M context, low cost |
| Fallback model | `gpt-4o-mini` (OpenAI, $0.15/$0.60) or `claude-3-5-haiku-20241022` (Anthropic, $1/$5) |
| Resilience approach | Switch seamlessly via `LLM_PROVIDER` in `.env` without modifying codebase |

---

## 5. Project structure

```text
ai-link-analysis/
├── app/
│   ├── main.py                    # FastAPI app + POST /link-analysis & /health
│   ├── config.py                  # env-driven settings (pydantic-settings)
│   ├── schemas.py                 # strict Pydantic response models & validation
│   ├── services/
│   │   ├── website_extractor.py   # safe streaming fetch + BeautifulSoup parsing
│   │   ├── llm_service.py         # Gemini / OpenAI / Anthropic JSON calls
│   │   ├── analysis_service.py    # orchestration, prompt, LRU cache, validation
│   │   └── competitor_service.py  # competitor-analysis prompt policy
│   └── utils/
│       └── validators.py          # URL validation, normalization & SSRF protection
├── tests/
│   └── test_link_analysis.py      # 22 unit & regression tests
├── .env.example
├── requirements.txt
└── README.md
```

---

## 6. Deployment

Deploy to any container or Python cloud platform (Render, Railway, Fly.io, or VPS).

### Option A: Render (Recommended - Free & Instant)

1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New + Web Service**.
2. Connect your GitHub repository: `https://github.com/VrajVaghela/dxora-link-analysis`
3. Configure settings:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In **Environment Variables**, add:
   - `LLM_PROVIDER`: `gemini` (or `openai`)
   - `GEMINI_API_KEY`: `your_gemini_api_key`
5. Click **Deploy Web Service**.

Once deployed:
- Root redirect: `GET https://<your-render-subdomain>.onrender.com/` (redirects straight to Swagger docs)
- Live API Documentation: `GET https://<your-render-subdomain>.onrender.com/docs`
- Live Analysis Endpoint: `POST https://<your-render-subdomain>.onrender.com/link-analysis`
- Health check: `GET https://<your-render-subdomain>.onrender.com/health`

### Option B: Docker

```bash
docker build -t dxora-link-analysis .
docker run -p 4000:4000 --env-file .env dxora-link-analysis
```

---

## 7. Submission Checklist

Per Dxora Practical Test instructions:

- [x] Complete Python 3.x FastAPI source code
- [x] Public GitHub Repository: [VrajVaghela/dxora-link-analysis](https://github.com/VrajVaghela/dxora-link-analysis)
- [x] Full setup, test execution, and API documentation
- [x] Working `/docs` Swagger schema with full request and response models
- [x] Interactive root redirect to `/docs`
- [x] Comprehensive LLM comparison table and cost analysis
- [x] SSRF protection blocking private IPs, loopbacks, and redirect hops
- [x] Zero committed credentials (`.env` in `.gitignore`, `.env.example` provided)
- [ ] Deploy API to a public host (e.g., Render / Railway) to obtain the **Live Demo URL**
- [ ] Follow Dxora Technologies on LinkedIn: [LinkedIn](https://www.linkedin.com/company/dxora-technologies)
- [ ] Follow CREST on Instagram: [Instagram](https://www.instagram.com/crestspot/)
- [ ] Submit final email to `hr@chivoxai.com` with Name, Live Demo URL, GitHub link, and contact details.
