#!/usr/bin/env python3
"""
Public-facing "URL preview" web app — the SSRF-vulnerable entry point.

This is the ONLY service exposed to the attacker (published on host port 8888).
Its /preview endpoint fetches any URL the user supplies, server-side, with no
validation of the destination. That is the SSRF (Server-Side Request Forgery)
vulnerability: the attacker makes THIS server issue HTTP requests on their
behalf, from inside the trusted network, reaching things the attacker cannot
reach directly.

Real-world analogue: the 2019 Capital One breach began with an SSRF in a
web-app firewall that was tricked into querying the AWS metadata endpoint.
"""
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

LANDING = b"""<!doctype html>
<html><head><title>LinkPeek - URL Preview Service</title></head>
<body style="font-family:system-ui;max-width:640px;margin:40px auto">
  <h1>LinkPeek</h1>
  <p>Paste a URL and we'll fetch a server-side preview for you.</p>
  <form action="/preview" method="get">
    <input name="url" size="50" placeholder="https://example.com" value="https://example.com">
    <button type="submit">Preview</button>
  </form>
  <hr>
  <p style="color:#888;font-size:13px">Internal tool. Fetches run from our
  application server. v1.3.0</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "LinkPeek/1.3.0"

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            return self._send(200, LANDING)

        if parsed.path == "/robots.txt":
            # A small "attack surface" breadcrumb, as real sites have.
            return self._send(200, "User-agent: *\nDisallow: /preview\nDisallow: /internal-notes.txt\n", "text/plain")

        if parsed.path == "/internal-notes.txt":
            return self._send(200,
                "TODO(devops): the preview fetcher can reach the internal admin API and the\n"
                "cloud metadata service. Lock down egress before GA. -- 2026-02\n", "text/plain")

        if parsed.path == "/preview":
            qs = parse_qs(parsed.query)
            url = (qs.get("url") or [""])[0]
            if not url:
                return self._send(400, "missing ?url=")
            # ---- THE VULNERABILITY ----
            # Whatever URL arrives, we fetch it server-side. No allowlist,
            # no scheme check, no block on internal/link-local addresses.
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "LinkPeek-preview/1.3"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = resp.read(65536)
                    ct = resp.headers.get("Content-Type", "application/octet-stream")
                return self._send(200, data, ct)
            except urllib.error.HTTPError as e:
                return self._send(200, f"[upstream returned HTTP {e.code}]\n{e.read(2048).decode(errors='replace')}",
                                  "text/plain")
            except Exception as e:
                return self._send(502, f"[fetch failed: {type(e).__name__}: {e}]", "text/plain")

        return self._send(404, "not found")

    def log_message(self, fmt, *args):
        print("[ssrf-app] " + (fmt % args))


if __name__ == "__main__":
    print("[ssrf-app] LinkPeek listening on 0.0.0.0:80")
    ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
