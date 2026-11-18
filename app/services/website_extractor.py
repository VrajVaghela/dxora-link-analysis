"""Website fetching and content extraction.

Downloads a page with httpx, then uses BeautifulSoup to extract structured,
clean content (title, meta description, headings, links, visible text).
Content is cleaned and capped before being sent to the LLM (cost control).
"""
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.validators import InvalidURLError, PrivateAddressError, validate_url

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 ai-link-analysis/1.0"
)

# Boilerplate tags that add noise but no meaning.
STRIP_TAGS = [
    "script", "style", "noscript", "iframe", "svg", "form", "button",
    "footer", "aside",
]

# Class/id fragments that mark repeated boilerplate (cookies, banners, share widgets).
BOILERPLATE_HINTS = re.compile(
    r"(cookie(-banner|-consent)?|consent-modal|social-share|subscribe|newsletter|copyright|breadcrumb)",
    re.IGNORECASE,
)


class WebsiteFetchError(Exception):
    """Raised when the website cannot be fetched or parsed."""


@dataclass
class WebsiteContent:
    url: str
    final_url: str
    title: str = ""
    meta_description: str = ""
    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    text: str = ""
    language: str = ""


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def extract_content(html: str, url: str, final_url: str) -> WebsiteContent:
    soup = BeautifulSoup(html, "lxml")

    title = _clean_text(soup.title.get_text() if soup.title else "")
    meta_desc = ""
    if soup.head:
        for meta in soup.head.find_all("meta"):
            name = (meta.get("name") or meta.get("property") or "").lower()
            if name in ("description", "og:description"):
                meta_desc = _clean_text(meta.get("content", ""))
                if name == "description":
                    break

    # Extract headings and links prior to decomposing boilerplate
    headings = []
    for level in ("h1", "h2", "h3"):
        for h in soup.find_all(level):
            text = _clean_text(h.get_text())
            if text and text not in headings:
                headings.append(text)

    links = []
    base = final_url or url
    for a in soup.find_all("a", href=True):
        absolute = urljoin(base, a["href"])
        if urlparse(absolute).scheme in ("http", "https"):
            links.append(_clean_text(a.get_text()) or absolute)
    # de-duplicate, keep order
    links = list(dict.fromkeys(links))

    # Strip scripts/styles/noise tags
    for tag in soup(STRIP_TAGS):
        tag.decompose()
    # Drop boilerplate containers by class/id
    for el in soup.find_all(attrs={"class": BOILERPLATE_HINTS}):
        el.decompose()
    for el in soup.find_all(attrs={"id": BOILERPLATE_HINTS}):
        el.decompose()

    body = soup.body or soup
    text = _clean_text(body.get_text(separator=" "))

    lang = (soup.html.get("lang") if soup.html else "") or ""

    return WebsiteContent(
        url=url,
        final_url=final_url,
        title=title,
        meta_description=meta_desc,
        headings=headings,
        links=links,
        text=text,
        language=lang,
    )


def _build_llm_context(content: WebsiteContent) -> str:
    """Build a compact, structured text context for the LLM.

    Capped by settings.max_content_chars to control token cost:
    - headings and nav links carry high signal density
    - body text fills the remaining headroom dynamically
    """
    max_chars = settings.max_content_chars
    parts: list[str] = []

    def add_section(label: str, value: str, limit: int):
        clean_val = (value or "").strip()[:limit]
        if clean_val:
            parts.append(f"## {label}\n{clean_val}")

    add_section("PAGE TITLE", content.title, 300)
    add_section("META DESCRIPTION", content.meta_description, 400)
    add_section("HEADINGS", " | ".join(content.headings), 1500)
    add_section("INTERNAL LINKS / SECTIONS", " | ".join(content.links[:40]), 1200)

    # Dynamically allocate remaining headroom to body text
    current_len = sum(len(p) + 4 for p in parts)
    remaining = max(0, max_chars - current_len - 50)
    add_section("PAGE TEXT", content.text, remaining)

    return "\n\n".join(parts)[:max_chars]


def fetch_website(url: str) -> tuple[WebsiteContent, str]:
    """Fetch the page safely and return (WebsiteContent, llm_context_text).

    Protects against:
    - SSRF via redirects (validates each redirect target against private IPs)
    - OOM DoS via unbounded response streaming (enforces max_page_bytes during streaming)
    - Unreachable or non-HTML targets
    """
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en"}
    current_url = url
    max_redirects = 5
    html = ""
    final_url = current_url

    with httpx.Client(
        timeout=settings.request_timeout_seconds,
        follow_redirects=False,
    ) as client:
        for _ in range(max_redirects + 1):
            try:
                with client.stream("GET", current_url, headers=headers) as response:
                    # Check for redirects manually to validate target against SSRF
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            raise WebsiteFetchError("Website redirected without Location header.")
                        next_url = urljoin(current_url, location)
                        try:
                            current_url = validate_url(next_url)
                        except (InvalidURLError, PrivateAddressError) as exc:
                            raise WebsiteFetchError(f"Redirect blocked by SSRF policy: {exc}") from exc
                        continue

                    if response.status_code in (401, 403, 429):
                        raise WebsiteFetchError(
                            f"Website returned HTTP {response.status_code} (access restricted)."
                        )
                    if response.status_code >= 400:
                        raise WebsiteFetchError(f"Website returned HTTP {response.status_code}.")

                    content_type = response.headers.get("content-type", "")
                    if content_type and "text/html" not in content_type:
                        raise WebsiteFetchError(f"URL does not return an HTML page ({content_type}).")

                    chunks = []
                    total_bytes = 0
                    for chunk in response.iter_bytes(chunk_size=65536):
                        total_bytes += len(chunk)
                        if total_bytes > settings.max_page_bytes:
                            raise WebsiteFetchError(
                                f"Website response exceeded size limit of {settings.max_page_bytes} bytes."
                            )
                        chunks.append(chunk)

                    raw_bytes = b"".join(chunks)
                    encoding = response.encoding or "utf-8"
                    html = raw_bytes.decode(encoding, errors="replace")
                    final_url = current_url
                    break
            except httpx.TimeoutException as exc:
                raise WebsiteFetchError(f"Request to {current_url} timed out.") from exc
            except httpx.HTTPError as exc:
                raise WebsiteFetchError(f"Could not fetch {current_url}: {exc}") from exc
        else:
            raise WebsiteFetchError("Too many redirects while fetching the website.")

    content = extract_content(html, url, final_url)
    if len(content.text) < 80:
        raise WebsiteFetchError("Very little text could be extracted from this page.")
    return content, _build_llm_context(content)
