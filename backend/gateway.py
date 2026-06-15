"""API gateway (:8000) — the single origin the frontend talks to.

It owns CORS and reverse-proxies each path prefix to the service that handles
it. The browser never talks to :8001-:8004 directly, so we configure CORS in
exactly one place and services stay internal.

  /auth/*                         -> auth-service      (:8001)
  /jobs/*, /applications/*        -> jobs-service      (:8002)
  /interview/*                    -> interview-service (:8004)

screening-service (:8003) is intentionally NOT proxied — only jobs-service
calls it, server-to-server, during the apply flow.
"""
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from common.config import AUTH_URL, INTERVIEW_URL, JOBS_URL

# Longest-prefix match wins, so order matters less, but keep it readable.
ROUTES = {
    "/auth": AUTH_URL,
    "/jobs": JOBS_URL,
    "/applications": JOBS_URL,
    "/interview": INTERVIEW_URL,
}

# Hop-by-hop headers must not be forwarded (RFC 7230 §6.1).
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}

app = FastAPI(title="api-gateway")
# Allow the Vite dev server on any localhost port — Vite hops to 5174+ when 5173
# is taken, so pinning a single origin breaks CORS. Tighten this for production.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = httpx.AsyncClient(timeout=180)


def _upstream_for(path: str) -> str | None:
    for prefix, base in ROUTES.items():
        if path == prefix or path.startswith(prefix + "/"):
            return base
    return None


@app.get("/")
def health():
    return {"status": "ok", "service": "gateway"}


@app.api_route("/{full_path:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(full_path: str, request: Request):
    path = "/" + full_path
    base = _upstream_for(path)
    if base is None:
        return Response('{"detail":"Not found"}', status_code=404,
                        media_type="application/json")

    url = base + path
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in _HOP_BY_HOP}

    try:
        upstream = await _client.request(
            request.method, url,
            params=request.query_params,
            headers=headers,
            content=body,
        )
    except httpx.RequestError as exc:
        return Response(f'{{"detail":"Upstream unavailable: {exc}"}}',
                        status_code=502, media_type="application/json")

    resp_headers = {k: v for k, v in upstream.headers.items()
                    if k.lower() not in _HOP_BY_HOP}
    return Response(content=upstream.content, status_code=upstream.status_code,
                    headers=resp_headers,
                    media_type=upstream.headers.get("content-type"))
