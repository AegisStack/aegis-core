# Security Policy

## Supported Versions

Aegis is pre-1.0. Security fixes are made against the `main` branch and
released as soon as practical; there is no separate long-term-support
branch yet.

## Reporting a Vulnerability

Please report suspected security vulnerabilities privately, **not** via a
public GitHub issue:

- Use [GitHub Security Advisories](https://github.com/AegisStack/aegis-core/security/advisories/new)
  for this repository, or
- Email the maintainers with details and reproduction steps.

We'll acknowledge reports within a few business days and aim to ship a fix
or mitigation before any public disclosure.

## Known Design Tradeoffs

These are deliberate, accepted-risk decisions made during pre-1.0
hardening, documented here so they're a choice on record rather than an
unstated gap.

### Dashboard JWTs are stored in `localStorage`, not an httpOnly cookie

`aegis-dashboard/frontend/src/lib/api.ts`'s request interceptor and
`src/lib/websocket.ts`'s `?token=` query-param authentication both assume
a JS-readable token. Moving to httpOnly cookies would require reworking
both, adding CSRF protection (cookies auto-attach cross-site, which a
bearer token in a header does not), and solving cross-port cookie delivery
for the WebSocket handshake in local dev - a larger rework than justified
pre-1.0.

**Mitigation:** access tokens are short-lived (`access_token_expire_minutes`
in `app/config.py`) and refresh tokens are single-use (rotated on every
`/auth/refresh` call, revoked on reuse - see `app/services/auth.py`), which
bounds how long a token exfiltrated via XSS remains useful. This does not
replace addressing XSS at its source (input sanitization, CSP); it only
limits the blast radius of a token leak.

### SDK ingestion API keys: HMAC-SHA256 with a dedicated pepper, not bcrypt/argon2

`Customer.api_key_hash` (`app/models/policy.py`) is computed via
`services/auth.hash_api_key()` - HMAC-SHA256 keyed with a pepper
(`Settings.api_key_pepper`) that is separate from the JWT `secret_key`, so
a leaked JWT signing secret doesn't also make API keys forgeable.

This is deliberately not a slow/salted password-hashing scheme
(bcrypt/argon2): API keys are high-entropy random-ish strings, not
low-entropy user-chosen passwords, so the offline-brute-force resistance a
slow hash buys you doesn't apply the same way, and `verify_api_key`
(`app/api/v1/ingest.py`) runs on every SDK ingestion call, where added
latency has a real cost. The threat this closes is a database dump or
backup exposing usable keys directly; it does not defend against a leaked
pepper (`api_key_pepper` must be set to a real secret in production, like
`secret_key`) or a compromised database *plus* application server.

### Rate limiting is per-IP, not per-account or per-API-key

`app/rate_limit.py`'s `Limiter` keys on the caller's remote address
(`slowapi.util.get_remote_address`). This is a coarse first line of
defense - effective against unsophisticated brute-force/spam traffic, but
not against a distributed attempt from many IPs against one account, or
one IP legitimately serving many customers (e.g. behind a shared NAT/proxy)
hitting a shared limit. Tightening this to a per-account or per-API-key
key function is a reasonable follow-up once real traffic patterns are
known.

## Dependency Scanning

Dependabot (`.github/dependabot.yml`) watches the SDK, dashboard backend,
dashboard frontend, and GitHub Actions workflows for known-vulnerable
dependencies. CI also runs `pip-audit`/`npm audit` on every PR
(`.github/workflows/lint.yml`, `dependency-scan` job); it currently reports
findings without blocking merges while the baseline is established, and
will be tightened to blocking once that baseline is clean.
