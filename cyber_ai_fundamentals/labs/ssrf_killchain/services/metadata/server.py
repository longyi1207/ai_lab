#!/usr/bin/env python3
"""
Fake cloud metadata service (mimics the AWS Instance Metadata Service, IMDSv1).

In a real cloud VM this lives at the link-local address 169.254.169.254 and
hands out, among other things, the TEMPORARY IAM CREDENTIALS of the role
attached to the instance. Any code running on the box (or anything that can be
tricked into making a request from the box, i.e. an SSRF) can read it.

This is exactly the endpoint the 2019 Capital One SSRF was steered at.
We serve a realistic-looking (but entirely fake) credential blob so the lab
can demonstrate "Task 5: discover metadata endpoints" end to end without
touching anything real.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROLE = "linkpeek-app-ec2-role"

FAKE_CREDS = {
    "Code": "Success",
    "LastUpdated": "2026-09-28T22:00:00Z",
    "Type": "AWS-HMAC",
    "AccessKeyId": "AKIAFAKELABEXAMPLE01",
    "SecretAccessKey": "wJalrXUtnFEMI/FAKE/LAB/EXAMPLEKEYDONOTUSE",
    "Token": "FQoGZXIvYXdzEXAMPLEFAKESESSIONTOKENxxxxxxxxxxxxxxxxxxxxxxxxxxxx==",
    "Expiration": "2026-09-29T04:00:00Z",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "EC2ws"  # what real IMDS reports

    def _text(self, code, body):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        # IMDS is a nested directory of plain-text listings.
        if path in ("/", "/latest/meta-data/", "/latest/meta-data"):
            return self._text(200, "ami-id\nhostname\niam/\ninstance-id\n")
        if path.rstrip("/") == "/latest/meta-data/iam":
            return self._text(200, "security-credentials/\n")
        if path.rstrip("/") == "/latest/meta-data/iam/security-credentials":
            # Listing the role name is step 1; fetching it returns the keys.
            return self._text(200, ROLE + "\n")
        if path == f"/latest/meta-data/iam/security-credentials/{ROLE}":
            return self._text(200, json.dumps(FAKE_CREDS, indent=2))
        if path == "/latest/meta-data/instance-id":
            return self._text(200, "i-0fakelab0example99")
        if path == "/latest/meta-data/hostname":
            return self._text(200, "ip-10-0-3-14.ec2.internal")
        return self._text(404, "not found")

    def log_message(self, fmt, *args):
        print("[metadata] " + (fmt % args))


if __name__ == "__main__":
    print("[metadata] fake IMDS listening on 0.0.0.0:80")
    ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
