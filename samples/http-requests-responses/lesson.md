# HTTP Requests and Responses

**Learning objective:** Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.

*Estimated time: 45.0 minutes*

## Why HTTP status codes matter
*(hook · 3.0 min)*

Every time a browser loads a page or an app calls an API, an HTTP exchange happens. Misreading a status code can send you debugging the wrong layer. In the next 45 minutes you will explain GET vs POST and classify responses into 2xx, 4xx, and 5xx.

## Requests, responses, and methods
*(concept · 8.0 min)*

HTTP is a request/response protocol. A client sends a request with a method, URL, headers, and optional body. The server returns a status code, headers, and optional body.

GET asks the server for a representation of a resource and should be safe (no side effects) and idempotent. POST submits data to be processed; it is neither safe nor necessarily idempotent.

## Status code categories
*(concept · 8.0 min)*

Status codes are three-digit integers grouped by the first digit:
- 2xx means success (for example 200 OK, 201 Created).
- 4xx means the client appears to have erred (for example 400 Bad Request, 401 Unauthorized, 404 Not Found).
- 5xx means the server failed to fulfill an apparently valid request (for example 500 Internal Server Error).

401 is a client error (4xx), not a server error. Confusing 4xx and 5xx leads to wrong ownership of bugs.

## Worked example: fetching vs creating
*(worked_example · 7.0 min)*

Scenario A — load a profile: the client issues GET /users/42. Expect 200 with a JSON body, or 404 if the user does not exist.

Scenario B — create a comment: the client issues POST /posts/9/comments with a JSON body. Expect 201 Created on success, 400 if the body is invalid, or 500 if the server crashes while saving.

### Live sandbox outputs (httpbin.org)
- GET: status=200 body='{\n  "args": {},\n  "headers": {\n    "Accept": "*/*",\n    "Accept-Encoding": "gzip'
- POST: status=200 body='{\n  "args": {},\n  "headers": {\n    "Accept": "*/*",\n    "Accept-Encoding": "gzip'
- STATUS_200: status=200 body=''
- STATUS_404: status=404 body=''
- STATUS_500: status=500 body=''

## Practical applications
*(practical · 5.0 min)*

1) Mobile app login: wrong password → 401; auth service down → 503/500.
2) Public CDN asset: browser uses GET; a successful cache hit still reflects a prior 2xx.
3) Payment webhook: provider POSTs an event; your handler must distinguish 4xx validation failures from 5xx so the provider knows whether to retry.

## Hands-on: classify these exchanges
*(activity · 6.0 min)*

In pairs, classify each case as GET or POST and pick the most likely status category:
a) Browser opens https://example.com/about
b) Form submits a new support ticket
c) API returns 'user not found'
d) Database connection pool exhausted during checkout
Discuss for 6 minutes, then share answers.

## Knowledge checks
*(knowledge_check · 4.0 min)*

Answer the questions below without looking at notes first.

## Summary
*(summary · 2.0 min)*

GET retrieves; POST submits for processing. 2xx = success, 4xx = client problem, 5xx = server problem. Always check the first digit before deciding who owns the fix.

## Supplementary videos
*(videos · 1.0 min)*

Watch a short HTTP overview focusing on methods and status codes. Why watch: reinforces GET/POST and category meanings with concrete UI examples. Suggested segment: start near the methods section of an HTTP crash course.

## References
*(references · 1.0 min)*

See the sources panel / references.json for MDN HTTP methods, status codes, and RFCs. Prefer MDN and RFC 9110 for authoritative wording.

## Knowledge Check Answer Key

### Q1. How do GET and POST differ in typical intent?
**Answer:** GET retrieves a representation; POST submits data to be processed.
**Explanation:** Matches the learning objective's method distinction.

### Q2. Is HTTP 401 a 4xx or 5xx code, and what does that imply?
**Answer:** 401 is 4xx (client error), usually missing/invalid credentials — not a server crash.
**Explanation:** Directly tests status category discrimination.

### Q3. Give one example each of 2xx, 4xx, and 5xx.
**Answer:** 200 OK; 404 Not Found; 500 Internal Server Error (examples may vary).
**Explanation:** Checks category mapping.
