# Verification evidence

Review date: 16 November 2026. Application source inspected and tested: `d5c6cc7` (the original application source is unchanged on the documentation branch).

Environment: Linux, Python 3.12.14, Node.js 24.22.1, npm 11.9.0. Dependencies installed from the existing `requirements.txt` and `package-lock.json`; the tested Python resolution is recorded in `requirements.lock.txt`. `pip check` reported no broken requirements. A second clean virtual environment installed `requirements.lock.txt` successfully and passed all 15 tests in 2.80 seconds.

| Check | Observed result |
| --- | --- |
| `python -m pytest -q` | 15 passed in 4.43 seconds |
| `npx tsc --noEmit` | Passed, exit 0 |
| `npm run build` | Passed, exit 0; Vite bundle-size warning |
| Browser smoke check | Registration, demo navigation, metric selection, chart tooltip, check-in confirmation/save and missing-key AI errors succeeded |

The build produced a 640.49 kB JavaScript chunk (191.37 kB gzip) and warned about the default 500 kB threshold. This is a build artifact size, not a runtime performance benchmark. No production optimization was attempted in this documentation-focused change.

## Existing automated test scope

`tests/test_app.py` covers seeded demo scenarios and alert directions; missing-key behavior with continued monitoring; schema-configured mocked Gemini responses for analysis/chat/report; filtering citations to retrieved IDs; and sanitized quota/access/model errors with one SDK attempt.

`tests/test_auth.py` covers registration, duplicate email, login/logout, password hashing, session-token digest storage, anonymous access rejection, read-only demo behavior, account isolation, baseline/profile updates, AI consent and private AI history, cross-origin rejection, session expiry, rate limiting, HTTPS Secure cookies, password validation redaction, preservation of legacy tables and check-in numeric/text constraints.

The 15 count includes parametrized cases. No line/branch coverage percentage was measured. TypeScript checking verifies static types; the production build verifies compilation and bundling. Neither replaces browser workflow testing.

## Browser capture and boundaries

Playwright with installed Chromium exercised the actual compiled application served by FastAPI at loopback port 8765 using an isolated synthetic SQLite file outside the checkout. No API responses were mocked for screenshots. Nine PNGs were captured and visually inspected; login and registration fields are empty, crew records are bundled fictional scenarios, and the check-in account is fictional.

There was no Gemini key. All three AI modes were requested and returned the expected missing-key response. Successful live model output, downloaded report content, live quota behavior, NASA page availability, full offline behavior, accessibility and cross-browser behavior were not verified. The automated tests use mocked Gemini responses and are not a live model evaluation. CI has been prepared but has not run on GitHub in this task.
