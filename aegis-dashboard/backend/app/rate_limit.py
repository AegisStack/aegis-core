"""
Shared rate limiter instance and 429 handler.

Kept in its own module (rather than defined in main.py) so route modules
can import `limiter` for the @limiter.limit(...) decorator without a
circular import back to main.py, which imports those route modules.
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

# headers_enabled=True is intentionally NOT used here: slowapi's decorator
# tries to inject rate-limit headers into the endpoint's raw return value,
# which for FastAPI routes returning a Pydantic model or dict (i.e. all of
# ours) is not yet a Response object - it crashes on every successful
# request, not just ones that hit the limit. rate_limit_exceeded_handler
# below adds the one header (Retry-After) that actually matters, on the
# 429 response it constructs itself (which is a real Response), sidestepping
# that code path entirely.
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """429 handler with a Retry-After header, without slowapi's built-in
    header injection (see the note on `limiter` above for why)."""
    response = JSONResponse({"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429)
    # All of our limits are per-minute, so 60s is always a correct (if not
    # perfectly tight) upper bound on when the window resets.
    response.headers["Retry-After"] = "60"
    return response
