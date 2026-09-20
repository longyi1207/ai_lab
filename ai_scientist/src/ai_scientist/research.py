"""Phase-1 auto-research: fetch user URLs + light web search notes for intake.

Network is best-effort and fully skippable (`AI_SCIENTIST_NO_WEB=1` or FakeLLM mode) so
offline tests never hang. Secrets are never written into research artifacts.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

URL_RE = re.compile(r"https?://[^\s\]\)>\"']+")
USER_AGENT = "ai_scientist/0.1 (+local research; contact=none)"


@dataclass
class ResearchNote:
    source: str
    title: str = ""
    excerpt: str = ""
    error: str | None = None

    def to_markdown(self) -> str:
        if self.error:
            return f"- `{self.source}` — _error: {self.error}_"
        title = self.title or self.source
        body = self.excerpt.strip() or "_no excerpt_"
        return f"### {title}\n\nSource: {self.source}\n\n{body}\n"


@dataclass
class ResearchBundle:
    notes: list[ResearchNote] = field(default_factory=list)
    skipped: str | None = None
    queries: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        if self.skipped and not self.notes:
            return f"_research skipped: {self.skipped}_"
        parts = ["# Auto-research notes", ""]
        if self.queries:
            parts.append("Queries: " + "; ".join(self.queries))
            parts.append("")
        if self.skipped:
            parts.append(f"_note: {self.skipped}_")
            parts.append("")
        for note in self.notes:
            parts.append(note.to_markdown())
            parts.append("")
        return "\n".join(parts).strip() + "\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "skipped": self.skipped,
            "queries": self.queries,
            "notes": [
                {
                    "source": n.source,
                    "title": n.title,
                    "excerpt": n.excerpt[:2000],
                    "error": n.error,
                }
                for n in self.notes
            ],
        }


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title and not self.title:
            self.title = text[:200]
        else:
            self._chunks.append(text)

    def text(self, limit: int = 4000) -> str:
        joined = " ".join(self._chunks)
        return joined[:limit]


def web_disabled() -> bool:
    if os.environ.get("AI_SCIENTIST_NO_WEB", "").strip() in {"1", "true", "yes"}:
        return True
    if os.environ.get("AI_SCIENTIST_FAKE_LLM", "").strip() in {"1", "true", "yes"}:
        return True
    return False


def extract_urls(*texts: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for match in URL_RE.findall(text or ""):
            url = match.rstrip(".,;:)")
            if url not in seen:
                seen.add(url)
                found.append(url)
    return found[:8]


def fetch_url(url: str, *, timeout_s: float = 8.0, max_bytes: int = 200_000) -> ResearchNote:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 - intentional
            raw = resp.read(max_bytes)
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return ResearchNote(source=url, error=f"{type(exc).__name__}: {exc}")

    if "html" in ctype or raw.lstrip()[:1] == b"<":
        parser = _TextExtractor()
        try:
            parser.feed(raw.decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            return ResearchNote(source=url, error=f"html_parse: {exc}")
        return ResearchNote(source=url, title=parser.title, excerpt=parser.text())
    text = raw.decode("utf-8", errors="replace")[:4000]
    return ResearchNote(source=url, title=url, excerpt=text)


def search_duckduckgo(query: str, *, timeout_s: float = 8.0, max_results: int = 3) -> list[ResearchNote]:
    """Best-effort HTML search. Failures become empty notes, never exceptions."""
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            html = resp.read(300_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return [ResearchNote(source=url, error=f"search_failed: {type(exc).__name__}: {exc}")]

    # result links look like ...uddg=<encoded url>
    notes: list[ResearchNote] = []
    for match in re.finditer(r"uddg=([^&\"']+)", html):
        target = urllib.parse.unquote(match.group(1))
        if not target.startswith("http"):
            continue
        if any(n.source == target for n in notes):
            continue
        notes.append(fetch_url(target, timeout_s=timeout_s))
        if len(notes) >= max_results:
            break
    if not notes:
        notes.append(ResearchNote(source=url, title=f"search:{query}", excerpt=html[:1500]))
    return notes


def gather(
    brief: str,
    *,
    documents_text: str = "",
    knowledge_sources: list[str] | None = None,
    extra_urls: list[str] | None = None,
    allow_network: bool | None = None,
) -> ResearchBundle:
    """Collect research notes for Phase-1 intake.

    Always returns a bundle (possibly skipped) so the intake driver can record what it
    knew vs what it still needs to ask.
    """
    sources = knowledge_sources or ["web_default"]
    want_web = any(s.startswith("web") for s in sources) or "web" in sources
    network = (not web_disabled()) if allow_network is None else allow_network

    bundle = ResearchBundle()
    if not want_web:
        bundle.skipped = "knowledge_sources exclude web"
        return bundle
    if not network:
        bundle.skipped = "network disabled (AI_SCIENTIST_NO_WEB / FAKE_LLM)"
        # Still record URLs we *would* have fetched, so the intake log is honest.
        for url in extract_urls(brief, documents_text, *(extra_urls or [])):
            bundle.notes.append(
                ResearchNote(source=url, title=url, excerpt="_not fetched: network disabled_")
            )
        return bundle

    urls = extract_urls(brief, documents_text, *(extra_urls or []))
    for url in urls:
        bundle.notes.append(fetch_url(url))

    # One search query derived from the brief when no URLs were supplied.
    query = " ".join((brief or "").split())[:160]
    if query and not urls:
        bundle.queries.append(query)
        bundle.notes.extend(search_duckduckgo(query))

    if not bundle.notes:
        bundle.skipped = "no urls or search hits"
    return bundle
