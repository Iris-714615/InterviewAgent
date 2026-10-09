# [OPEN] Chat network error debugging

## Symptom
The deployed interview page still shows `出错了: network error` when starting or using an interview.

## Hypotheses
1. `/api/v1/status` works but `/api/v1/chat/stream` proxy or SSE handling fails.
2. A frontend request still bypasses same-origin `/api` and uses an incorrect base URL.
3. Nginx forwards the chat request with an incorrect path or headers.
4. The backend chat endpoint returns an error that the frontend reduces to `network error`.

## Evidence
Runtime evidence will be collected before business logic changes.

## Status
Instrumentation/evidence collection phase.
