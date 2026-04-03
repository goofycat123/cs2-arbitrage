"""Optional access gate: one shared password + signed session cookie (no secret in browser JS)."""

import hashlib
import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response


def access_lock_enabled() -> bool:
    return bool(os.getenv("APP_ACCESS_PASSWORD", "").strip())


def session_signing_secret() -> str:
    explicit = os.getenv("SESSION_SECRET", "").strip()
    if explicit:
        return explicit
    pw = os.getenv("APP_ACCESS_PASSWORD", "").strip()
    if pw:
        return hashlib.sha256(f"cs2-arb-session:{pw}".encode()).hexdigest()
    return hashlib.sha256(b"dev-cs2-arb-insecure").hexdigest()


def verify_access_password(candidate: str, stored: str) -> bool:
    """Constant-time compare via fixed-length digests."""
    if not stored:
        return False
    a = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    b = hashlib.sha256(stored.encode("utf-8")).hexdigest()
    return hmac.compare_digest(a, b)


class AccessGateMiddleware(BaseHTTPMiddleware):
    """Require session['access'] when APP_ACCESS_PASSWORD is set."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not access_lock_enabled():
            return await call_next(request)

        path = request.url.path

        if path in ("/login", "/health", "/logout"):
            return await call_next(request)
        if path.startswith("/login"):
            return await call_next(request)

        session = request.scope.get("session")
        if session is None:
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return RedirectResponse(url="/login", status_code=302)

        if session.get("access") is True:
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return RedirectResponse(url="/login", status_code=302)


LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign in</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#070a11;color:#d8e0ef;font-family:system-ui,sans-serif;padding:20px}
.card{width:100%;max-width:360px;background:#0f1726;border:1px solid #1f2a3f;border-radius:12px;padding:28px}
h1{font-size:18px;margin-bottom:6px}
p{font-size:13px;color:#7d8aa6;margin-bottom:20px}
label{display:block;font-size:11px;color:#7d8aa6;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
input{width:100%;padding:11px 12px;border-radius:8px;border:1px solid #2a3a55;background:#0a101c;color:#e8eef8;font-size:15px}
input:focus{outline:none;border-color:#49c2ff}
button{margin-top:18px;width:100%;padding:12px;border:none;border-radius:8px;background:linear-gradient(135deg,#238636,#2ea043);color:#fff;font-weight:600;font-size:14px;cursor:pointer}
button:hover{filter:brightness(1.08)}
.err{margin-top:12px;font-size:13px;color:#ff7373;display:none}
</style>
</head>
<body>
<div class="card">
  <h1>CS2 tools</h1>
  <p>Enter the shared password you were given.</p>
  <form method="post" action="/login">
    <label for="password">Password</label>
    <input type="password" id="password" name="password" required autocomplete="current-password" autofocus>
    <button type="submit">Continue</button>
  </form>
  <p class="err" id="e"></p>
</div>
<script>
if (new URLSearchParams(location.search).get('e') === '1') {
  document.getElementById('e').style.display = 'block';
  document.getElementById('e').textContent = 'Wrong password. Try again.';
}
</script>
</body>
</html>"""
