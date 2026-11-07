"""Research pipeline: web + books + YouTube with extraction and reliability tiers."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
import trafilatura
from sqlmodel import Session, select

from app.config import get_settings
from app.models.models import Source
from app.services.llm import LLMError, json_completion
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Domains treated as high-reliability (official docs / standards)
HIGH_TIER_DOMAINS = {
    "developer.mozilla.org",
    "mdn.io",
    "rfc-editor.org",
    "www.rfc-editor.org",
    "datatracker.ietf.org",
    "tools.ietf.org",
    "w3.org",
    "www.w3.org",
    "httpwg.org",
    "docs.python.org",
    "nodejs.org",
    "learn.microsoft.com",
    "cloud.google.com",
    "docs.aws.amazon.com",
    "kubernetes.io",
    "ietf.org",
    "whatwg.org",
}

MEDIUM_TIER_HINTS = (
    "stackoverflow.com",
    "github.com",
    "medium.com",
    "dev.to",
    "freecodecamp.org",
    "css-tricks.com",
    "smashingmagazine.com",
    "digitalocean.com",
    "realpython.com",
    "geeksforgeeks.org",
)


class VideoRelevance(BaseModel):
    relevant: bool
    reason: str = ""
    start_timestamp: str = "0:00"
    end_timestamp: str = "10:00"


def assign_reliability(url: str, title: str = "") -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    full = urlparse(url).netloc.lower()
    if host in HIGH_TIER_DOMAINS or full in HIGH_TIER_DOMAINS:
        return "high"
    # RFC / MDN path heuristics
    if "rfc" in host or "/rfc" in url.lower() or "mdn" in host:
        return "high"
    if "wikipedia.org" in full or "khanacademy.org" in full:
        return "medium"
    if any(h in full for h in MEDIUM_TIER_HINTS):
        return "medium"
    if any(k in title.lower() for k in ("official", "documentation", "specification", "standard")):
        return "high"
    return "low"


async def _search_tavily(query: str, max_results: int = 8) -> list[dict[str, Any]]:
    settings = get_settings()
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    # Tavily client is sync
    result = client.search(query, max_results=max_results, search_depth="advanced")
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in result.get("results", [])
    ]


async def _search_ddg(query: str, max_results: int = 8) -> list[dict[str, Any]]:
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in results
    ]


USER_AGENT = (
    "ChalkproofLessonBot/1.0 (local educational tool; +https://localhost; "
    "contact: chalkproof@localhost)"
)

# Curated high-quality docs used when live search APIs are unavailable
CURATED_DOCS: list[dict[str, str]] = [
    {"title": "MDN: HTTP overview", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP", "keywords": "http request response"},
    {"title": "MDN: HTTP request methods", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods", "keywords": "http get post method"},
    {"title": "MDN: HTTP response status codes", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status", "keywords": "http status 2xx 4xx 5xx"},
    {"title": "MDN: GET", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET", "keywords": "get method"},
    {"title": "MDN: POST", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/POST", "keywords": "post method"},
    {"title": "MDN: Cache-Control", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cache-Control", "keywords": "cache-control caching cache"},
    {"title": "MDN: HTTP caching", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching", "keywords": "http caching cache"},
    {"title": "RFC 9110 HTTP Semantics", "url": "https://www.rfc-editor.org/rfc/rfc9110.html", "keywords": "http semantics status method"},
    {"title": "RFC 9111 HTTP Caching", "url": "https://www.rfc-editor.org/rfc/rfc9111.html", "keywords": "http caching cache-control"},
    {"title": "MDN: DNS", "url": "https://developer.mozilla.org/en-US/docs/Glossary/DNS", "keywords": "dns resolution domain"},
    # General / maths fallbacks
    {"title": "Wikipedia: Mathematics", "url": "https://en.wikipedia.org/wiki/Mathematics", "keywords": "math maths mathematics algebra arithmetic theorem school teach"},
    {"title": "Wikipedia: Arithmetic", "url": "https://en.wikipedia.org/wiki/Arithmetic", "keywords": "math maths arithmetic numbers addition subtraction"},
    {"title": "Wikipedia: Algebra", "url": "https://en.wikipedia.org/wiki/Algebra", "keywords": "math maths algebra equation variable"},
    {"title": "Wikipedia: Geometry", "url": "https://en.wikipedia.org/wiki/Geometry", "keywords": "math maths geometry shape angle triangle theorem"},
    {"title": "Wikipedia: Pythagorean theorem", "url": "https://en.wikipedia.org/wiki/Pythagorean_theorem", "keywords": "pythagoras pythagorean phytoghoras phytagoras theorem right triangle hypotenuse a2 b2 c2"},
    {"title": "Khan Academy: Pythagorean theorem", "url": "https://www.khanacademy.org/math/geometry/hs-geo-trig/hs-geo-pythagorean-theorem/a/pythagorean-theorem", "keywords": "pythagoras pythagorean phytoghoras theorem hypotenuse"},
    {"title": "Khan Academy: Math", "url": "https://www.khanacademy.org/math", "keywords": "math maths learn mathematics school teach"},
]

# Common misspellings / aliases → Wikipedia page titles (seeded when search APIs fail)
TOPIC_WIKI_SEEDS: list[tuple[tuple[str, ...], list[str]]] = [
    (
        ("pythag", "phytoghor", "phytagor", "a2+b2", "hypotenuse"),
        ["Pythagorean_theorem", "Right_triangle", "Geometry"],
    ),
    (
        ("fraction", "decimal"),
        ["Fraction", "Decimal", "Rational_number"],
    ),
    (
        ("photosynthesis",),
        ["Photosynthesis", "Chloroplast"],
    ),
    (
        ("dns", "domain name"),
        ["Domain_Name_System"],
    ),
    (
        ("http", "get", "post", "status code"),
        [],  # handled by curated HTTP docs
    ),
    (
        ("math", "maths", "algebra", "geometry", "arithmetic", "school"),
        ["Mathematics", "Arithmetic", "Algebra", "Geometry"],
    ),
]


def _is_web_tech_topic(query: str) -> bool:
    q = query.lower()
    tech = ("http", "https", "api", "dns", "cache", "html", "css", "javascript", "tcp", "rest", "header", "status code")
    return any(t in q for t in tech)


async def _search_wikipedia(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Wikipedia search via REST + opensearch fallback."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    out: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        # Prefer REST search (often less blocked than action API for bots)
        try:
            resp = await client.get(
                "https://en.wikipedia.org/w/rest.php/v1/search/title",
                params={"q": query, "limit": max_results},
            )
            if resp.status_code == 200:
                for item in resp.json().get("pages", [])[:max_results]:
                    title = item.get("title") or item.get("key") or ""
                    if not title:
                        continue
                    slug = title.replace(" ", "_")
                    out.append(
                        {
                            "title": title,
                            "url": f"https://en.wikipedia.org/wiki/{slug}",
                            "snippet": item.get("description") or item.get("excerpt") or "",
                        }
                    )
        except Exception as e:
            logger.warning("Wikipedia REST search failed: %s", e)

        if out:
            return out

        resp = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": max_results,
                "namespace": 0,
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        titles = data[1] if len(data) > 1 else []
        descs = data[2] if len(data) > 2 else []
        urls = data[3] if len(data) > 3 else []
        for i, title in enumerate(titles):
            out.append(
                {
                    "title": title,
                    "url": urls[i] if i < len(urls) else "",
                    "snippet": descs[i] if i < len(descs) else "",
                }
            )
    return out


async def _wikipedia_summary(title: str) -> str:
    """Fetch plain-text summary for a Wikipedia page title."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    slug = title.replace(" ", "_")
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        resp = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}")
        if resp.status_code != 200:
            return ""
        data = resp.json()
        extract = data.get("extract") or ""
        desc = data.get("description") or ""
        return f"{desc}\n\n{extract}".strip()[:8000]


def _curated_matches(query: str, max_results: int = 6) -> list[dict[str, Any]]:
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in CURATED_DOCS:
        score = sum(1 for kw in doc["keywords"].split() if kw in q)
        # Also score partial token matches (handles "Phytoghoras" ≈ pythagoras keywords)
        for kw in doc["keywords"].split():
            if len(kw) >= 5 and (kw[:5] in q or any(kw[:5] in token for token in q.split())):
                score += 1
        if score:
            scored.append((score, {"title": doc["title"], "url": doc["url"], "snippet": ""}))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:max_results]]


def _wiki_seed_results(query: str) -> list[dict[str, Any]]:
    """Deterministic Wikipedia URLs from topic aliases — last-resort research seeds."""
    q = query.lower()
    titles: list[str] = []
    for needles, pages in TOPIC_WIKI_SEEDS:
        if any(n in q for n in needles):
            titles.extend(pages)
    # Always try the raw title words as a wiki slug candidate
    rough = re.sub(r"[^a-zA-Z0-9]+", "_", query.split(":")[0].strip()).strip("_")
    if rough and len(rough) > 2:
        titles.append(rough)
    # Correct common Pythagorean misspelling explicitly
    if "phytoghor" in q or "phytagor" in q or "pythag" in q:
        titles = ["Pythagorean_theorem", "Right_triangle", "Geometry"] + titles

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for t in titles:
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(
            {
                "title": t.replace("_", " "),
                "url": f"https://en.wikipedia.org/wiki/{t}",
                "snippet": "",
            }
        )
    return out[:6]


async def web_search(query: str, max_results: int = 8) -> list[dict[str, Any]]:
    settings = get_settings()
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    if settings.tavily_api_key:
        try:
            results = await _search_tavily(query, max_results)
        except Exception as e:
            errors.append(f"tavily: {e}")
            logger.warning("Tavily search failed: %s", e)

    if not results:
        try:
            results = await _search_ddg(query, max_results)
        except Exception as e:
            errors.append(f"ddg: {e}")
            logger.warning("DuckDuckGo search failed: %s", e)

    if not results:
        try:
            results = await _search_wikipedia(query, max_results)
        except Exception as e:
            errors.append(f"wikipedia: {e}")
            logger.warning("Wikipedia search failed: %s", e)

    # Always merge curated official docs that match the topic
    curated = _curated_matches(query, max_results=max_results)
    seen = {r["url"] for r in results}
    for c in curated:
        if c["url"] not in seen:
            results.append(c)
            seen.add(c["url"])

    # Alias / misspelling seeds (e.g. Phytoghoras → Pythagorean theorem)
    for seed in _wiki_seed_results(query):
        if seed["url"] not in seen:
            results.append(seed)
            seen.add(seed["url"])

    if not results:
        raise RuntimeError(f"Web search failed ({'; '.join(errors) or 'no providers'})")
    return results[: max(max_results + 2, len(results))]


async def fetch_page_text(url: str, timeout: float = 20.0) -> str:
    # Wikipedia: use REST summary (more reliable than scraping HTML)
    if "wikipedia.org/wiki/" in url:
        title = url.rstrip("/").split("/wiki/")[-1]
        text = await _wikipedia_summary(title)
        if text:
            return text
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            downloaded = trafilatura.extract(
                resp.text,
                include_comments=False,
                include_tables=True,
                url=url,
            )
            return (downloaded or "")[:15000]
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return ""


async def search_books(query: str, limit: int = 2) -> list[dict[str, Any]]:
    books: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://openlibrary.org/search.json",
                params={"q": query, "limit": limit},
            )
            resp.raise_for_status()
            docs = resp.json().get("docs", [])[:limit]
            for d in docs:
                key = d.get("key", "")
                books.append(
                    {
                        "title": d.get("title", "Untitled"),
                        "url": f"https://openlibrary.org{key}" if key else "",
                        "authors": ", ".join(d.get("author_name", [])[:3]),
                        "snippet": f"Open Library: {d.get('title')} by {', '.join(d.get('author_name', [])[:2])}",
                        "first_publish_year": d.get("first_publish_year"),
                    }
                )
    except Exception as e:
        logger.warning("Open Library search failed: %s", e)

    settings = get_settings()
    if len(books) < limit:
        try:
            params: dict[str, Any] = {"q": query, "maxResults": limit}
            if settings.google_books_api_key:
                params["key"] = settings.google_books_api_key
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params=params,
                )
                resp.raise_for_status()
                for item in resp.json().get("items", [])[: limit - len(books)]:
                    info = item.get("volumeInfo", {})
                    books.append(
                        {
                            "title": info.get("title", "Untitled"),
                            "url": info.get("infoLink", item.get("selfLink", "")),
                            "authors": ", ".join(info.get("authors", [])[:3]),
                            "snippet": (info.get("description") or "")[:500],
                            "first_publish_year": (info.get("publishedDate") or "")[:4],
                        }
                    )
        except Exception as e:
            logger.warning("Google Books search failed: %s", e)
    return books[:limit]


def _extract_video_id(url: str) -> Optional[str]:
    m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


async def search_youtube(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    settings = get_settings()
    videos: list[dict[str, Any]] = []
    if settings.youtube_api_key:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "maxResults": max_results,
                        "key": settings.youtube_api_key,
                        "relevanceLanguage": "en",
                    },
                )
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    vid = item["id"]["videoId"]
                    sn = item["snippet"]
                    videos.append(
                        {
                            "title": sn.get("title", ""),
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "video_id": vid,
                            "snippet": sn.get("description", ""),
                        }
                    )
                return videos
        except Exception as e:
            logger.warning("YouTube API search failed: %s", e)

    # Fallback: educational videos when YouTube API / DDG are unavailable
    fallback_videos = [
        {
            "title": "HTTP Crash Course & Exploration",
            "url": "https://www.youtube.com/watch?v=iYM2zFP3Zn0",
            "video_id": "iYM2zFP3Zn0",
            "snippet": "HTTP methods, status codes, headers",
            "keywords": "http get post status request response cache",
        },
        {
            "title": "DNS as Fast As Possible",
            "url": "https://www.youtube.com/watch?v=42kmeGxU9zA",
            "video_id": "42kmeGxU9zA",
            "snippet": "DNS resolution explained",
            "keywords": "dns resolution domain",
        },
        {
            "title": "Introduction to Mathematics",
            "url": "https://www.youtube.com/watch?v=V6DOm4X9N5E",
            "video_id": "V6DOm4X9N5E",
            "snippet": "Overview of mathematics topics for beginners",
            "keywords": "math maths mathematics algebra arithmetic school teach",
        },
        {
            "title": "Pythagorean Theorem",
            "url": "https://www.youtube.com/watch?v=AA6Rfg_y1t0",
            "video_id": "AA6Rfg_y1t0",
            "snippet": "Visual proof and explanation of a²+b²=c²",
            "keywords": "pythagoras pythagorean phytoghoras theorem hypotenuse",
        },
    ]
    q = query.lower()
    for v in fallback_videos:
        if any(k in q for k in v["keywords"].split()):
            videos.append(v)
    return videos[:max_results]


def fetch_transcript(video_id: str) -> tuple[str, bool]:
    """Return (transcript_text, available)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        # API shape varies by version — try both
        try:
            segments = YouTubeTranscriptApi.get_transcript(video_id)
        except AttributeError:
            api = YouTubeTranscriptApi()
            segments = api.fetch(video_id)
            segments = [{"text": s.text, "start": s.start, "duration": s.duration} for s in segments]

        parts = []
        for seg in segments:
            start = int(seg.get("start", 0))
            mm, ss = divmod(start, 60)
            parts.append(f"[{mm}:{ss:02d}] {seg.get('text', '')}")
        text = "\n".join(parts)
        return text[:20000], True
    except Exception as e:
        logger.warning("Transcript unavailable for %s: %s", video_id, e)
        return "", False


async def check_video_relevance(objective: str, title: str, transcript: str) -> VideoRelevance:
    settings = get_settings()
    if settings.chalkproof_demo_mode or not settings.has_llm_keys:
        # Keyword heuristic when LLM unavailable
        blob = f"{title}\n{transcript[:2000]}".lower()
        keys = [w for w in objective.lower().replace(",", " ").split() if len(w) > 3]
        hits = sum(1 for k in keys if k in blob)
        relevant = hits >= max(1, len(keys) // 3) or "http" in blob
        return VideoRelevance(
            relevant=relevant,
            reason=f"Demo heuristic ({hits} keyword hits)",
            start_timestamp="0:00",
            end_timestamp="12:00",
        )

    system = (
        "You assess whether a YouTube video transcript is relevant to a learning objective. "
        "Return JSON: {relevant: bool, reason: str, start_timestamp: str, end_timestamp: str}. "
        "Timestamps like '2:30'. Only mark relevant=true if the transcript genuinely covers the objective."
    )
    user = (
        f"Learning objective: {objective}\nVideo title: {title}\n\n"
        f"Transcript (may be truncated):\n{transcript[:8000]}"
    )
    try:
        return await json_completion("qc", system, user, VideoRelevance)
    except LLMError as e:
        logger.warning("Video relevance LLM failed: %s — keeping video as unverified relevant", e)
        return VideoRelevance(
            relevant=True,
            reason="LLM relevance check failed; kept tentatively",
            start_timestamp="0:00",
            end_timestamp="15:00",
        )


async def run_research(session: Session, project_id: int, title: str, objective: str) -> dict[str, Any]:
    """
    Gather 6-10 sources. Persists Source rows. Returns summary notes.
    Graceful degradation: individual fetch failures are noted, not fatal.
    """
    notes: list[str] = []
    # Clear prior sources on retry
    for old in session.exec(select(Source).where(Source.project_id == project_id)).all():
        session.delete(old)
    session.commit()

    query = f"{title}: {objective}"
    web_results: list[dict[str, Any]] = []
    try:
        if _is_web_tech_topic(query):
            web_results = await web_search(
                f"{query} site:developer.mozilla.org OR site:rfc-editor.org OR documentation",
                5,
            )
        more = await web_search(query, 6)
        seen = {r["url"] for r in web_results}
        for r in more:
            if r["url"] not in seen:
                web_results.append(r)
                seen.add(r["url"])
    except Exception as e:
        notes.append(f"Web search partially failed: {e}")
        # Absolute fallback: wiki seeds alone
        for seed in _wiki_seed_results(query):
            if seed["url"] not in {r["url"] for r in web_results}:
                web_results.append(seed)

    # If search returned URLs but nothing yet, still force wiki seeds
    if not web_results:
        web_results = _wiki_seed_results(query) or _curated_matches(query, 6)
        if web_results:
            notes.append("Used offline topic seeds because live search returned nothing.")

    saved = 0
    for r in web_results:
        if saved >= 6:
            break
        text = await fetch_page_text(r["url"])
        if not text and r.get("snippet"):
            text = r["snippet"]
            notes.append(f"Used snippet only for {r['url']} (full fetch failed)")
        if not text:
            notes.append(f"Skipped empty page: {r['url']}")
            continue
        tier = assign_reliability(r["url"], r.get("title", ""))
        src = Source(
            project_id=project_id,
            type="web",
            url=r["url"],
            title=r.get("title", "")[:300],
            fetched_text=text,
            reliability_tier=tier,
        )
        session.add(src)
        saved += 1

    # Books — keep query short; avoid forcing networking for non-tech topics
    try:
        short = " ".join(title.split()[:6])
        if _is_web_tech_topic(query):
            book_query = f"{short} computer networking"
        elif any(x in query.lower() for x in ("pythag", "phytoghor", "theorem", "geometry")):
            book_query = "Pythagorean theorem geometry textbook"
        else:
            book_query = f"{short} textbook introduction"
        books = await search_books(book_query, limit=2)
        for b in books:
            text = b.get("snippet") or f"{b['title']} by {b.get('authors', '')}"
            session.add(
                Source(
                    project_id=project_id,
                    type="book",
                    url=b.get("url", ""),
                    title=b.get("title", "")[:300],
                    fetched_text=text,
                    reliability_tier="medium",
                    metadata_json={"authors": b.get("authors"), "year": b.get("first_publish_year")},
                )
            )
            saved += 1
    except Exception as e:
        notes.append(f"Book search failed: {e}")

    # Videos
    try:
        videos = await search_youtube(f"{title} {objective} tutorial", max_results=4)
        kept = 0
        for v in videos:
            if kept >= 3:
                break
            transcript, ok = fetch_transcript(v["video_id"])
            if not ok:
                session.add(
                    Source(
                        project_id=project_id,
                        type="video",
                        url=v["url"],
                        title=v.get("title", "")[:300],
                        fetched_text=v.get("snippet", "") or "(transcript unavailable)",
                        reliability_tier="low",
                        relevant_segment=None,
                        video_verified=False,
                        metadata_json={"unverified": True, "reason": "transcript unavailable"},
                    )
                )
                notes.append(f"Video unverified (no transcript): {v['title']}")
                kept += 1
                continue

            relevance = await check_video_relevance(objective, v.get("title", ""), transcript)
            if not relevance.relevant:
                notes.append(f"Dropped irrelevant video: {v['title']} ({relevance.reason})")
                continue
            segment = f"{relevance.start_timestamp}-{relevance.end_timestamp}"
            session.add(
                Source(
                    project_id=project_id,
                    type="video",
                    url=v["url"],
                    title=v.get("title", "")[:300],
                    fetched_text=transcript,
                    reliability_tier="medium",
                    relevant_segment=segment,
                    video_verified=True,
                    metadata_json={"relevance_reason": relevance.reason},
                )
            )
            kept += 1
            saved += 1
    except Exception as e:
        notes.append(f"Video research failed: {e}")

    session.commit()
    sources = session.exec(select(Source).where(Source.project_id == project_id)).all()
    if len(sources) < 2:
        raise RuntimeError(
            f"Too few sources gathered ({len(sources)}). Check network/API keys and retry."
        )
    if len(sources) < 6:
        notes.append(
            f"Only {len(sources)} sources collected (target 6–10); continuing with graceful degradation."
        )

    summary = (
        f"Collected {len(sources)} sources "
        f"({sum(1 for s in sources if s.type=='web')} web, "
        f"{sum(1 for s in sources if s.type=='book')} books, "
        f"{sum(1 for s in sources if s.type=='video')} videos). "
        + (" Notes: " + "; ".join(notes) if notes else "")
    )
    return {"count": len(sources), "notes": notes, "summary": summary}
