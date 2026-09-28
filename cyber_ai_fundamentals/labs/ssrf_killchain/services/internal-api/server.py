#!/usr/bin/env python3
"""
Internal admin API — NOT published to the host.

It has no authentication because "only internal services can reach it" — the
classic flat-network assumption that SSRF destroys. The attacker can never
connect to this container directly from their machine; they can only reach it
by pivoting THROUGH the SSRF in the public app.

This models "Task 5: enumerate internal services · identify admin interfaces."
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

USERS = [
    {"id": 1, "user": "svc-deploy", "role": "admin", "note": "CI/CD service account"},
    {"id": 2, "user": "j.reyes",   "role": "operator", "note": "on-call"},
    {"id": 3, "user": "backup",    "role": "readonly", "note": "nightly dumps"},
]


class Handler(BaseHTTPRequestHandler):
    server_version = "internal-admin/2.1"

    def _json(self, code, obj):
        body = json.dumps(obj, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._json(200, {
                "service": "internal-admin-api",
                "version": "2.1",
                "auth": "none (internal network only)",
                "endpoints": ["/admin/users", "/admin/config"],
            })
        if path == "/admin/users":
            return self._json(200, {"users": USERS})
        if path == "/admin/config":
            return self._json(200, {
                "db_host": "db.internal:5432",
                "feature_flags": {"new_billing": True},
                "internal_flag": "LAB{ssrf_pivot_to_internal_admin_api}",
            })
        return self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print("[internal-api] " + (fmt % args))


if __name__ == "__main__":
    print("[internal-api] listening on 0.0.0.0:80 (internal only)")
    ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
