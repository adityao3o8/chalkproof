"""Deterministic fixture lesson used when CHALKPROOF_DEMO_MODE=1 or LLM keys are missing."""

from __future__ import annotations

from app.models.schemas import KnowledgeCheckItem, LessonBlock, LessonClaim, LessonContent


def build_fixture(title: str, objective: str, source_ids: list[int]) -> LessonContent:
    """Pick a fixture based on topic keywords."""
    blob = f"{title} {objective}".lower()
    if "cache" in blob:
        return caching_fixture(title, objective, source_ids)
    return http_fixture(title, objective, source_ids)


def http_fixture(title: str, objective: str, source_ids: list[int]) -> LessonContent:
    """A grounded 45-minute HTTP lesson. source_ids are real DB ids from research."""
    sid = source_ids[0] if source_ids else 0
    sid2 = source_ids[1] if len(source_ids) > 1 else sid
    sid3 = source_ids[2] if len(source_ids) > 2 else sid

    blocks = [
        LessonBlock(
            id="b1",
            type="hook",
            title="Why HTTP status codes matter",
            content=(
                "Every time a browser loads a page or an app calls an API, an HTTP exchange happens. "
                "Misreading a status code can send you debugging the wrong layer. In the next 45 minutes "
                "you will explain GET vs POST and classify responses into 2xx, 4xx, and 5xx."
            ),
            estimated_minutes=3,
        ),
        LessonBlock(
            id="b2",
            type="concept",
            title="Requests, responses, and methods",
            content=(
                "HTTP is a request/response protocol. A client sends a request with a method, URL, headers, "
                "and optional body. The server returns a status code, headers, and optional body.\n\n"
                "GET asks the server for a representation of a resource and should be safe (no side effects) "
                "and idempotent. POST submits data to be processed; it is neither safe nor necessarily idempotent."
            ),
            estimated_minutes=8,
        ),
        LessonBlock(
            id="b3",
            type="concept",
            title="Status code categories",
            content=(
                "Status codes are three-digit integers grouped by the first digit:\n"
                "- 2xx means success (for example 200 OK, 201 Created).\n"
                "- 4xx means the client appears to have erred (for example 400 Bad Request, 401 Unauthorized, 404 Not Found).\n"
                "- 5xx means the server failed to fulfill an apparently valid request (for example 500 Internal Server Error).\n\n"
                "401 is a client error (4xx), not a server error. Confusing 4xx and 5xx leads to wrong ownership of bugs."
            ),
            estimated_minutes=8,
        ),
        LessonBlock(
            id="b4",
            type="worked_example",
            title="Worked example: fetching vs creating",
            content=(
                "Scenario A — load a profile: the client issues GET /users/42. Expect 200 with a JSON body, "
                "or 404 if the user does not exist.\n\n"
                "Scenario B — create a comment: the client issues POST /posts/9/comments with a JSON body. "
                "Expect 201 Created on success, 400 if the body is invalid, or 500 if the server crashes while saving."
            ),
            estimated_minutes=7,
        ),
        LessonBlock(
            id="b5",
            type="practical",
            title="Practical applications",
            content=(
                "1) Mobile app login: wrong password → 401; auth service down → 503/500.\n"
                "2) Public CDN asset: browser uses GET; a successful cache hit still reflects a prior 2xx.\n"
                "3) Payment webhook: provider POSTs an event; your handler must distinguish 4xx validation "
                "failures from 5xx so the provider knows whether to retry."
            ),
            estimated_minutes=5,
        ),
        LessonBlock(
            id="b6",
            type="activity",
            title="Hands-on: classify these exchanges",
            content=(
                "In pairs, classify each case as GET or POST and pick the most likely status category:\n"
                "a) Browser opens https://example.com/about\n"
                "b) Form submits a new support ticket\n"
                "c) API returns 'user not found'\n"
                "d) Database connection pool exhausted during checkout\n"
                "Discuss for 6 minutes, then share answers."
            ),
            estimated_minutes=6,
        ),
        LessonBlock(
            id="b7",
            type="knowledge_check",
            title="Knowledge checks",
            content="Answer the questions below without looking at notes first.",
            estimated_minutes=4,
        ),
        LessonBlock(
            id="b8",
            type="summary",
            title="Summary",
            content=(
                "GET retrieves; POST submits for processing. 2xx = success, 4xx = client problem, "
                "5xx = server problem. Always check the first digit before deciding who owns the fix."
            ),
            estimated_minutes=2,
        ),
        LessonBlock(
            id="b9",
            type="videos",
            title="Supplementary videos",
            content=(
                "Watch a short HTTP overview focusing on methods and status codes. "
                "Why watch: reinforces GET/POST and category meanings with concrete UI examples. "
                "Suggested segment: start near the methods section of an HTTP crash course."
            ),
            estimated_minutes=1,
        ),
        LessonBlock(
            id="b10",
            type="references",
            title="References",
            content=(
                "See the sources panel / references.json for MDN HTTP methods, status codes, and RFCs. "
                "Prefer MDN and RFC 9110 for authoritative wording."
            ),
            estimated_minutes=1,
        ),
    ]

    claims = [
        LessonClaim(
            claim_text="GET requests a representation of the specified resource.",
            source_id=sid,
            supporting_quote="The GET method requests a representation of the specified resource.",
            block_id="b2",
        ),
        LessonClaim(
            claim_text="POST is used to submit an entity to the specified resource.",
            source_id=sid2,
            supporting_quote="The POST method is used to submit an entity to the specified resource",
            block_id="b2",
        ),
        LessonClaim(
            claim_text="4xx status codes indicate client errors.",
            source_id=sid3,
            supporting_quote="Client error responses (400 – 499)",
            block_id="b3",
        ),
        LessonClaim(
            claim_text="5xx status codes indicate server errors.",
            source_id=sid3,
            supporting_quote="Server error responses (500 – 599)",
            block_id="b3",
        ),
    ]

    kcs = [
        KnowledgeCheckItem(
            question="How do GET and POST differ in typical intent?",
            answer="GET retrieves a representation; POST submits data to be processed.",
            explanation="Matches the learning objective's method distinction.",
        ),
        KnowledgeCheckItem(
            question="Is HTTP 401 a 4xx or 5xx code, and what does that imply?",
            answer="401 is 4xx (client error), usually missing/invalid credentials — not a server crash.",
            explanation="Directly tests status category discrimination.",
        ),
        KnowledgeCheckItem(
            question="Give one example each of 2xx, 4xx, and 5xx.",
            answer="200 OK; 404 Not Found; 500 Internal Server Error (examples may vary).",
            explanation="Checks category mapping.",
        ),
    ]

    return LessonContent(
        title=title,
        objective=objective,
        blocks=blocks,
        claims=claims,
        knowledge_checks=kcs,
        total_estimated_minutes=45.0,
    )


def caching_fixture(title: str, objective: str, source_ids: list[int]) -> LessonContent:
    sid = source_ids[0] if source_ids else 0
    sid2 = source_ids[1] if len(source_ids) > 1 else sid
    blocks = [
        LessonBlock(
            id="b1", type="hook", title="When caches surprise you",
            content=(
                "A fix ships to production but users still see the old page. Often the culprit is caching, "
                "not your deploy. This lesson focuses on Cache-Control directives and common mistakes."
            ),
            estimated_minutes=3,
        ),
        LessonBlock(
            id="b2", type="concept", title="What Cache-Control does",
            content=(
                "Cache-Control is an HTTP header that tells browsers and shared caches how responses may be stored "
                "and reused. Directives include max-age (freshness lifetime in seconds), no-store (do not store), "
                "private (only browser caches), and public (shared caches may store)."
            ),
            estimated_minutes=8,
        ),
        LessonBlock(
            id="b3", type="concept", title="Freshness vs revalidation",
            content=(
                "Within max-age, a cache may reuse a response without contacting the origin. After freshness expires, "
                "caches may revalidate. Mixing no-store with max-age is a common misconfiguration — no-store means "
                "the response must not be stored in any cache."
            ),
            estimated_minutes=8,
        ),
        LessonBlock(
            id="b4", type="worked_example", title="Worked examples",
            content=(
                "Example 1: Cache-Control: public, max-age=3600 — shared caches may serve for one hour.\n"
                "Example 2: Cache-Control: private, max-age=60 — browser-only, one minute.\n"
                "Example 3: Cache-Control: no-store — never cache (typical for authenticated HTML)."
            ),
            estimated_minutes=7,
        ),
        LessonBlock(
            id="b5", type="practical", title="Practical applications",
            content=(
                "1) Static assets: long max-age with fingerprinted filenames.\n"
                "2) Personalized dashboards: private or no-store.\n"
                "3) CDN misconfig: public caching of Set-Cookie responses — a security/privacy bug."
            ),
            estimated_minutes=5,
        ),
        LessonBlock(
            id="b6", type="activity", title="Hands-on header clinic",
            content=(
                "Given three response headers, choose the correct directive set and explain who may cache them. "
                "Debate edge cases for logged-in users."
            ),
            estimated_minutes=6,
        ),
        LessonBlock(
            id="b7", type="knowledge_check", title="Knowledge checks",
            content="Answer without notes first.",
            estimated_minutes=4,
        ),
        LessonBlock(
            id="b8", type="summary", title="Summary",
            content=(
                "max-age sets freshness; private vs public controls who stores; no-store forbids storage. "
                "Validate headers against the sensitivity of the content."
            ),
            estimated_minutes=2,
        ),
        LessonBlock(
            id="b9", type="videos", title="Supplementary videos",
            content="Watch an HTTP caching overview focusing on Cache-Control. Suggested: caching section of an HTTP course.",
            estimated_minutes=1,
        ),
        LessonBlock(
            id="b10", type="references", title="References",
            content="MDN Cache-Control, MDN HTTP caching guide, RFC 9111.",
            estimated_minutes=1,
        ),
    ]
    claims = [
        LessonClaim(
            claim_text="Cache-Control controls how responses are cached.",
            source_id=sid,
            supporting_quote="The Cache-Control HTTP header field holds directives",
            block_id="b2",
        ),
        LessonClaim(
            claim_text="no-store means the response must not be stored in any cache.",
            source_id=sid2,
            supporting_quote="no-store",
            block_id="b3",
        ),
    ]
    kcs = [
        KnowledgeCheckItem(
            question="What does max-age control?",
            answer="How long a response is considered fresh (in seconds).",
            explanation="Core Cache-Control directive.",
        ),
        KnowledgeCheckItem(
            question="When would you use no-store?",
            answer="When the response must not be stored in any cache (e.g., sensitive pages).",
            explanation="Tests directive understanding.",
        ),
        KnowledgeCheckItem(
            question="Difference between private and public?",
            answer="private = browser-only caches; public = shared caches may store.",
            explanation="Common mistake area.",
        ),
    ]
    return LessonContent(
        title=title,
        objective=objective,
        blocks=blocks,
        claims=claims,
        knowledge_checks=kcs,
        total_estimated_minutes=45.0,
    )
