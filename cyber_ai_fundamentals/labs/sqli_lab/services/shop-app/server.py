#!/usr/bin/env python3
"""
"BookNook" - a deliberately SQL-injectable product-search web app.

The vulnerability is in ONE line: the /search endpoint builds its SQL query by
string-concatenating the user's `q` parameter straight into the statement,
instead of using a parameterized query. That is classic SQL injection.

Backend is SQLite (in-process, pure stdlib - no external DB to run). It's seeded
with a public `products` table and a NON-public `users` table holding password
hashes. The whole point of the lab: an attacker who can only search for books
can, through the injection, read the `users` table they were never meant to see.

Real-world analogue: SQL injection has topped the OWASP/CWE danger lists for two
decades; the 2017 Equifax-era and countless breaches began exactly here.
"""
import html
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DB = sqlite3.connect(":memory:", check_same_thread=False)


def seed():
    c = DB.cursor()
    c.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, author TEXT, price REAL)")
    c.executemany("INSERT INTO products (name, author, price) VALUES (?,?,?)", [
        ("The Pragmatic Programmer", "Hunt & Thomas", 39.99),
        ("Clean Code", "Robert Martin", 34.50),
        ("The Web Application Hacker's Handbook", "Stuttard & Pinto", 50.00),
        ("Designing Data-Intensive Applications", "Martin Kleppmann", 44.99),
        ("Practical Malware Analysis", "Sikorski & Honig", 59.95),
    ])
    # The prize: a table the search UI never exposes on purpose.
    c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password_md5 TEXT, role TEXT)")
    c.executemany("INSERT INTO users (username, password_md5, role) VALUES (?,?,?)", [
        # md5 of common passwords - dumpable + crackable, like a real breach.
        ("admin",   "5f4dcc3b5aa765d61d8327deb882cf99", "admin"),      # password
        ("jsmith",  "e10adc3949ba59abbe56e057f20f883e", "editor"),     # 123456
        ("svc_sync", "827ccb0eea8a706c4c34a16891f84e7b", "service"),   # 12345
        ("guest",   "d8578edf8458ce06fbc5bb76a58c5ca4", "readonly"),   # qwerty
    ])
    DB.commit()


LANDING = b"""<!doctype html>
<html><head><title>BookNook - search</title></head>
<body style="font-family:system-ui;max-width:640px;margin:40px auto">
  <h1>BookNook</h1>
  <p>Search our catalogue.</p>
  <form action="/search" method="get">
    <input name="q" size="40" placeholder="e.g. clean" value="clean">
    <button type="submit">Search</button>
  </form>
  <p style="color:#888;font-size:13px">Demo store. v0.9</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "BookNook/0.9"

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

        if parsed.path == "/search":
            q = (parse_qs(parsed.query).get("q") or [""])[0]
            # ---- THE VULNERABILITY ----
            # User input concatenated directly into SQL. Never do this.
            sql = ("SELECT id, name, author, price FROM products "
                   "WHERE name LIKE '%" + q + "%' OR author LIKE '%" + q + "%'")
            try:
                rows = DB.cursor().execute(sql).fetchall()
            except Exception as e:
                # Verbose DB errors are themselves a finding (error-based SQLi).
                return self._send(200, f"<p>query error: {html.escape(str(e))}</p>")
            if not rows:
                return self._send(200, "<p>No books matched.</p>")
            items = "".join(
                f"<li>#{r[0]} <b>{html.escape(str(r[1]))}</b> by {html.escape(str(r[2]))} — ${r[3]}</li>"
                for r in rows
            )
            return self._send(200, f"<ul>{items}</ul>")

        return self._send(404, "not found")

    def log_message(self, fmt, *args):
        print("[shop-app] " + (fmt % args))


if __name__ == "__main__":
    seed()
    print("[shop-app] BookNook listening on 0.0.0.0:80 (SQLite backend, seeded)")
    ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
