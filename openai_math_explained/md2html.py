"""Minimal Markdown → HTML for the 精讲 chapters (no third-party deps).

Supports exactly what the chapters use: ATX headings, paragraphs, block quotes,
nested bullet / numbered lists, pipe tables, fenced code, horizontal rules,
`{{FIG_…}}` figure placeholder lines (passed through for the build to fill),
and inline **bold**, *italic*, `code`, [text](url) and bare URLs.
"""
import html
import re

_INLINE_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_BARE_URL = re.compile(r"(?<![\"'>=])(https?://[^\s<>()（）,，。;；]+[^\s<>()（）,，。;；.])")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITAL = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])")
_ESCAPED = re.compile(r"\\([\\`*_\[\]()#+\-.!|{}])")


def inline(text):
    """Escape and render inline markup. Code spans are protected from other rules."""
    stash = []

    def keep(s):
        stash.append(s)
        return f"\x00{len(stash) - 1}\x00"

    text = _INLINE_CODE.sub(lambda m: keep(f"<code>{html.escape(m.group(1), quote=False)}</code>"), text)
    text = _ESCAPED.sub(lambda m: keep(html.escape(m.group(1), quote=False)), text)  # \* \_ etc. → literal
    text = _LINK.sub(lambda m: keep(f'<a href="{html.escape(m.group(2))}">{_emphasis(html.escape(m.group(1), quote=False))}</a>'), text)
    text = _BARE_URL.sub(lambda m: keep(f'<a href="{html.escape(m.group(1))}">{html.escape(m.group(1), quote=False)}</a>'), text)
    text = _emphasis(html.escape(text, quote=False))
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)


def _emphasis(text):
    """**bold** and *italic* on already-escaped text."""
    return _ITAL.sub(r"<em>\1</em>", _BOLD.sub(r"<strong>\1</strong>", text))


_LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")


def _render_list(lines):
    """lines: raw lines of one list block (items plus continuation lines)."""
    items = []  # (indent, ordered, text)
    for ln in lines:
        m = _LIST_ITEM.match(ln)
        if m:
            items.append([len(m.group(1).expandtabs(4)), not m.group(2)[0] in "-*+", m.group(3)])
        elif items:
            items[-1][2] += " " + ln.strip()
    out, stack = [], []  # stack of (indent, tag)
    for indent, ordered, text in items:
        tag = "ol" if ordered else "ul"
        while stack and indent < stack[-1][0]:
            out.append(f"</li></{stack.pop()[1]}>")
        if not stack or indent > stack[-1][0]:
            out.append(f"<{tag}>")
            stack.append((indent, tag))
        else:
            out.append("</li>")
        out.append(f"<li>{inline(text)}")
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


def _render_table(lines):
    # split on unescaped pipes; `\|` inside a cell is a literal pipe
    rows = [[c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))]
            for ln in lines]
    head, body = rows[0], [r for r in rows[2:]]
    h = "".join(f"<th>{inline(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def blocks(md, heading_offset=1):
    """Render block-level markdown. `#` maps to h(1+offset), `##` to h(2+offset), …"""
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
        elif s.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            code = "\n".join(lines[i + 1:j])
            out.append(f"<pre><code>{html.escape(code, quote=False)}</code></pre>")
            i = j + 1
        elif re.match(r"^#{1,6}\s", s):
            level = len(s) - len(s.lstrip("#"))
            out.append(f"<h{min(level + heading_offset, 6)}>{inline(s[level:].strip())}</h{min(level + heading_offset, 6)}>")
            i += 1
        elif re.fullmatch(r"-{3,}|\*{3,}", s):
            i += 1  # section breaks are carried by headings in the deck
        elif re.fullmatch(r"\{\{FIG_[A-Z0-9_]+\}\}", s):
            out.append(s)  # figure placeholder: the build script substitutes the SVG
            i += 1
        elif s.startswith(">"):
            j = i
            inner = []
            while j < len(lines) and lines[j].strip().startswith(">"):
                inner.append(re.sub(r"^\s*>\s?", "", lines[j]))
                j += 1
            out.append(f"<blockquote>{blocks(chr(10).join(inner), heading_offset)}</blockquote>")
            i = j
        elif s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            out.append(_render_table(lines[i:j]))
            i = j
        elif _LIST_ITEM.match(ln):
            j = i
            while j < len(lines) and lines[j].strip() and (
                    _LIST_ITEM.match(lines[j]) or lines[j].startswith((" ", "\t"))):
                j += 1
            out.append(_render_list(lines[i:j]))
            i = j
        else:
            j = i
            para = []
            while j < len(lines) and lines[j].strip() and not re.match(
                    r"^(#{1,6}\s|>|```|\|)", lines[j].strip()) and not _LIST_ITEM.match(lines[j]):
                para.append(lines[j].strip())
                j += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
            i = j
    return "\n".join(out)
