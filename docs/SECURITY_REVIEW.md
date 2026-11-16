# Security review

Review date: 16 November 2026. Scope: this repository and its reachable local Git history, configuration exclusions, source-level data handling and newly captured screenshots. This is a focused engineering review, not a penetration test or compliance certification.

## Observed checks

- Scanned all 24 historical Git blobs reachable from the cloned refs for Google API-key, GitHub-token, AWS access-ID and private-key patterns: no matches. Pattern matching cannot prove the absence of every possible secret.
- No tracked `.env`, `.sqlite3`, `.sqlite` or `.db` files were found in those historical objects. No private database was included in this change.
- `.env.example` contains only an empty API-key value and documented optional placeholders. Expanded ignore rules exclude `.env.*` except the example, SQLite files and sidecars, Python caches, test caches, node modules and build output. Representative paths were checked with `git check-ignore`.
- All nine PNGs were visually inspected. Authentication fields are blank; other visible records belong to bundled fictional profiles or a fictional local account. No passwords, API keys or real health records appear.
- Screenshot capture used a separate database outside the checkout. No existing local databases were deleted or changed.

## Source-level findings and limits

Private routes derive account ownership from a validated cookie session. Passwords use Argon2id; only session-token digests are stored. Cookies are HttpOnly and SameSite=Strict, with Secure enabled for HTTPS or explicit configuration. Origin/Fetch Metadata checks protect unsafe API requests and API responses disable caching. Existing tests exercise these controls.

Important deployment limits remain: SQLite is unencrypted, login limits are per process, proxy trust must be configured by the operator, and the application has no documented account deletion or backup lifecycle. Notes/questions can contain identifying information despite omitted profile fields in cloud context. Consent does not erase earlier model transmissions. No dependency vulnerability scanner, external penetration test or full secret-detection service was run. The application should be demonstrated with synthetic data.
