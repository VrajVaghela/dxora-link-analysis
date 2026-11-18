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

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 ai-link-analysis/1.0"
)

# Boilerplate tags that add noise but no meaning.
STRIP_TAGS = [
    "script", "style", "noscript", "iframe", "svg", "form", "button",
    "nav", "footer", "header", "aside",
]

# Class/id fragments that usually mark repeated boilerplate (headers, menus...).
BOILERPLATE_HINTS = re.compile(
    r"(nav|menu|header|footer|sidebar|cookie|banner|promo|social|subscribe|"
    r"newsletter|copyright|breadcrumb|widget)",
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

    for tag in soup(STRIP_TAGS):  # remove scripts/styles/nav/footer etc.
        tag.decompose()
    # Drop common boilerplate containers by class/id.
    for el in soup.find_all(attrs={"class": BOILERPLATE_HINTS}):
        el.decompose()
    for el in soup.find_all(attrs={"id": BOILERPLATE_HINTS}):
        el.decompose()

    title = _clean_text(soup.title.get_text() if soup.title else "")
    meta_desc = ""
    if soup.head:
        for meta in soup.head.find_all("meta"):
            name = (meta.get("name") or meta.get("property") or "").lower()
            if name in ("description", "og:description"):
                meta_desc = _clean_text(meta.get("content", ""))
                if name == "description":
                    break

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
    - body text is truncated last
    """
    headroom = settings.max_content_chars
    parts: list[str] = []

    def add(label: str, value: str, limit: int) -> int:
        value = (value or "")[:limit]
        if value:
            parts.append(f"## {label}\n{value}")
        return headroom - len(value) - 40

    def budget(value: str, limit: int) -> int:
        return min(limit, max(headroom, 0))

    add("PAGE TITLE", content.title, budget(content.title, 300))
    headroom -= 350
    add("META DESCRIPTION", content.meta_description, budget(content.meta_description, 400))
    headroom -= 450
    add("HEADINGS", " | ".join(content.headings), budget(" | ".join(content.headings), 1500))
    headroom -= 1600
    # Internal links often reveal services/about pages -> services structure.
    link_labels = " | ".join(content.links[:40])
    add("INTERNAL LINKS / SECTIONS", link_labels, budget(link_labels, 1200))
    headroom -= 1300
    add("PAGE TEXT", content.text, budget(content.text, settings.max_content_chars))

    return "\n\n".join(parts)[: settings.max_content_chars]


def fetch_website(url: str) -> tuple[WebsiteContent, str]:
    """Fetch the page and return (WebsiteContent, llm_context_text).

    Raises WebsiteFetchError on network/HTTP problems, redirects,
    or non-HTML responses.
    """
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en"}
    try:
        with httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            response = client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise WebsiteFetchError(f"Request to {url} timed out.") from exc
    except httpx.HTTPError as exc:
        raise WebsiteFetchError(f"Could not fetch {url}: {exc}") from exc

    if response.status_code in (401, 403, 429):
        raise WebsiteFetchError(
            f"Website returned HTTP {response.status_code} (access restricted)."
        )
    if response.status_code >= 400:
        raise WebsiteFetchError(f"Website returned HTTP {response.status_code}.")
    if response.status_code in (301, 302, 307, 308):
        raise WebsiteFetchError("Too many redirects while fetching the website.")

    content_type = response.headers.get("content-type", "")
    if content_type and "text/html" not in content_type:
        raise WebsiteFetchError(f"URL does not return an HTML page ({content_type}).")

    html = response.text[: settings.max_page_bytes]
    content = extract_content(html, url, str(response.url))
    if len(content.text) < 80:
        raise WebsiteFetchError(
            "Very little text could be extracted from this page."
        )
    return content, _build_llm_context(content)
