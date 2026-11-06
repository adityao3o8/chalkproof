# HTTP Caching and Cache-Control Headers

**Learning objective:** Explain how Cache-Control directives (max-age, no-store, private, public) affect browser and shared caches, and identify common caching mistakes.

*Estimated time: 46.0 minutes*

## When caches surprise you
*(hook · 3.0 min)*

A fix ships to production but users still see the old page. Often the culprit is caching, not your deploy. This lesson focuses on Cache-Control directives and common mistakes.

## What Cache-Control does
*(concept · 9.0 min)*

Cache-Control is an HTTP header that tells browsers and shared caches how responses may be stored and reused. Directives include max-age (freshness lifetime in seconds), no-store (do not store), private (only browser caches), and public (shared caches may store).

## Freshness vs revalidation
*(concept · 8.0 min)*

Within max-age, a cache may reuse a response without contacting the origin. After freshness expires, caches may revalidate. Mixing no-store with max-age is a common misconfiguration — no-store means the response must not be stored in any cache.

## Worked examples
*(worked_example · 7.0 min)*

Example 1: Cache-Control: public, max-age=3600 — shared caches may serve for one hour.
Example 2: Cache-Control: private, max-age=60 — browser-only, one minute.
Example 3: Cache-Control: no-store — never cache (typical for authenticated HTML).

### Live sandbox outputs (httpbin.org)
- GET: status=200 body='{\n  "args": {},\n  "headers": {\n    "Accept": "*/*",\n    "Accept-Encoding": "gzip'
- POST: status=200 body='{\n  "args": {},\n  "headers": {\n    "Accept": "*/*",\n    "Accept-Encoding": "gzip'
- STATUS_200: status=200 body=''
- STATUS_404: status=404 body=''
- STATUS_500: status=500 body=''

## Practical applications
*(practical · 5.0 min)*

1) Static assets: long max-age with fingerprinted filenames.
2) Personalized dashboards: private or no-store.
3) CDN misconfig: public caching of Set-Cookie responses — a security/privacy bug.

## Hands-on header clinic
*(activity · 6.0 min)*

Given three response headers, choose the correct directive set and explain who may cache them. Debate edge cases for logged-in users.

## Knowledge checks
*(knowledge_check · 4.0 min)*

Answer without notes first.

## Summary
*(summary · 2.0 min)*

max-age sets freshness; private vs public controls who stores; no-store forbids storage. Validate headers against the sensitivity of the content.

## Supplementary videos
*(videos · 1.0 min)*

Watch an HTTP caching overview focusing on Cache-Control. Suggested: caching section of an HTTP course.

## References
*(references · 1.0 min)*

MDN Cache-Control, MDN HTTP caching guide, RFC 9111.

## Knowledge Check Answer Key

### Q1. What does max-age control?
**Answer:** How long a response is considered fresh (in seconds).
**Explanation:** Core Cache-Control directive.

### Q2. When would you use no-store?
**Answer:** When the response must not be stored in any cache (e.g., sensitive pages).
**Explanation:** Tests directive understanding.

### Q3. Difference between private and public?
**Answer:** private = browser-only caches; public = shared caches may store.
**Explanation:** Common mistake area.
