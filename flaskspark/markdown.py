"""Markdown for FlaskSpark apps: render it (GitHub/GitLab flavoured, sanitised) and turn HTML back into Markdown.

    from flaskspark import markdown

    html = markdown.render(text)                                 # Markup, safe to put into a template
    html = markdown.render(text, base_url="https://git.example.com/group/project")   # relative links and images
    html = markdown.render(text, rewrite_url=lambda url, kind: proxy(url) if kind == "image" else url)
    text = markdown.to_markdown(html)                            # e.g. the HTML of a rich text editor

Templates use the filter: ``{{ issue.description|markdown }}`` or ``{{ text|markdown(base_url=project_url) }}``.

What it renders (the same rules as the browser's ``webcomponents/modules/bootstrap/ui-markdown/markdown.js``, so
server and client agree; a test compares both):

- CommonMark with tables, strikethrough (``~~x~~``), autolinks (``https://…``, ``www.…``, e-mail addresses),
- task lists (``- [ ]`` / ``- [x]``), alerts (``> [!note]`` … ``[!caution]``, with an optional title after the marker),
- collapsible sections (raw ``<details><summary>``), a table of contents (``[[_TOC_]]`` or ``[TOC]`` alone in a
  paragraph; headings get ids), code blocks with their language as ``class="language-…"`` (Mermaid and PlantUML stay
  code blocks, nothing is drawn).

The result is sanitised with an allowlist (nh3): no scripts, styles, frames or event handlers; links only http(s),
mailto, tel and relative (``rel="noopener noreferrer"``), images only http(s) and relative; raw HTML is reduced to
the allowed tags.
"""

from __future__ import annotations

import re
import unicodedata
from html import escape
from html.parser import HTMLParser
from typing import Callable, Iterable

import nh3
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markupsafe import Markup

ALERT_TYPES = ("note", "tip", "important", "warning", "caution")
DEFAULT_ALERT_TITLES = {"note": "Note", "tip": "Tip", "important": "Important", "warning": "Warning",
                        "caution": "Caution"}

UrlRewriter = Callable[[str, str], "str | None"]

# --- sanitiser ---------------------------------------------------------------------------------------------------

ALLOWED_TAGS = frozenset({
    "a", "abbr", "b", "blockquote", "br", "code", "dd", "del", "details", "div", "dl", "dt", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "i", "img", "input", "ins", "kbd", "li", "mark", "nav", "ol", "p", "pre", "q", "s",
    "samp", "small", "span", "strong", "sub", "summary", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr",
    "u", "ul", "var",
})
# Removed together with their content (the other tags not allowed are unwrapped: their text stays).
DROPPED_TAGS = frozenset({
    "script", "style", "template", "iframe", "object", "embed", "svg", "math", "noscript", "textarea", "select",
    "title", "xmp", "noembed", "noframes", "head", "frameset", "frame", "applet", "audio", "video", "canvas",
})
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "abbr": {"title"},
    "img": {"src", "alt", "title", "width", "height"},
    "input": {"type", "checked", "disabled", "class"},
    "ol": {"start", "class"},
    "ul": {"class"},
    "li": {"class"},
    "p": {"class"},
    "div": {"class"},
    "nav": {"class"},
    "code": {"class"},
    "pre": {"class"},
    "th": {"style", "colspan", "rowspan"},
    "td": {"style", "colspan", "rowspan"},
    "details": {"open"},
    **{f"h{n}": {"id"} for n in range(1, 7)},
}
# The classes that stay, per tag (anything else is removed from the class attribute).
_CLASSES = {
    "ul": re.compile(r"contains-task-list"),
    "ol": re.compile(r"contains-task-list"),
    "li": re.compile(r"task-list-item"),
    "input": re.compile(r"task-list-item-checkbox"),
    "div": re.compile(r"markdown-alert(-(note|tip|important|warning|caution))?"),
    "p": re.compile(r"markdown-alert-title"),
    "nav": re.compile(r"markdown-toc"),
    "code": re.compile(r"language-[A-Za-z0-9_+#.-]+"),
    "pre": re.compile(r"language-[A-Za-z0-9_+#.-]+"),
}
LINK_SCHEMES = frozenset({"http", "https", "mailto", "tel"})
IMAGE_SCHEMES = frozenset({"http", "https"})
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
_ALIGN = re.compile(r"^\s*text-align\s*:\s*(left|right|center)\s*;?\s*$", re.I)
_URL_JUNK = re.compile(r"[\t\n\r]")


def _clean_url(url: str) -> str:
    """The URL as a browser reads it: tabs and line breaks inside are dropped, controls and spaces around trimmed."""
    return _URL_JUNK.sub("", url).strip("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14"
                                         "\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f ")


def is_relative(url: str) -> bool:
    """A relative URL (path, query or fragment), not an absolute one or a protocol-relative one (``//host``)."""
    return not _SCHEME.match(url) and not url.startswith(("//", "\\\\", "/\\", "\\/"))


def resolve_url(url: str, kind: str, base_url: str | None = None, rewrite_url: UrlRewriter | None = None) -> str | None:
    """The URL of a link (kind "link") or image (kind "image") as it is put out, None to drop it.

    A relative URL (not ``#…``) gets ``base_url`` in front (``/uploads/a.png`` with base ``https://h/g/p`` gives
    ``https://h/g/p/uploads/a.png``: the base is a prefix, like GitLab's uploads of a project), then ``rewrite_url(url,
    kind)`` may change it (e.g. a proxy for images; None or "" drops it). Allowed in the end: links http(s), mailto,
    tel and relative; images http(s) and relative."""
    url = _clean_url(url or "")
    if not url and kind == "image":
        return None
    if base_url and url and is_relative(url) and not url.startswith("#"):
        url = base_url.rstrip("/") + ("" if url.startswith(("/", "?")) else "/") + url
    if rewrite_url is not None:
        url = _clean_url(rewrite_url(url, kind) or "")
        if not url:
            return None
    match = _SCHEME.match(url)
    if match:
        allowed = IMAGE_SCHEMES if kind == "image" else LINK_SCHEMES
        return url if match.group(1).lower() in allowed else None
    if url.startswith(("//", "\\\\", "/\\", "\\/")):
        return url if url.startswith("//") else None
    return url


def _class_filter(tag: str, value: str) -> str | None:
    pattern = _CLASSES.get(tag)
    if pattern is None:
        return None
    kept = [c for c in value.split() if pattern.fullmatch(c)]
    return " ".join(dict.fromkeys(kept)) or None


def sanitize(html: str, *, base_url: str | None = None, rewrite_url: UrlRewriter | None = None) -> Markup:
    """HTML reduced to the allowlist of Markdown's output (see the module's description)."""

    def attribute_filter(tag: str, attr: str, value: str) -> str | None:
        if attr == "class":
            return _class_filter(tag, value)
        if attr == "style":
            match = _ALIGN.match(value)
            return f"text-align:{match.group(1).lower()}" if match else None
        if tag == "a" and attr == "href":
            return resolve_url(value, "link", base_url, rewrite_url)
        if tag == "img" and attr == "src":
            return resolve_url(value, "image", base_url, rewrite_url)
        if attr in ("width", "height", "start", "colspan", "rowspan"):
            return value.strip() if re.fullmatch(r"[0-9]+", value.strip()) else None
        if attr == "id":
            return value if re.fullmatch(r"[\w-]+", value) else None
        return value

    cleaned = nh3.clean(
        html or "",
        tags=set(ALLOWED_TAGS),
        clean_content_tags=set(DROPPED_TAGS),
        attributes={tag: set(names) for tag, names in ALLOWED_ATTRIBUTES.items()},
        attribute_filter=attribute_filter,
        strip_comments=True,
        link_rel="noopener noreferrer",
        set_tag_attribute_values={"input": {"type": "checkbox", "disabled": ""}},
        url_schemes=set(LINK_SCHEMES),
    )
    return Markup(cleaned)


# --- rendering -----------------------------------------------------------------------------------------------------

_TASK = re.compile(r"^\[([ xX])\](?=\s|$)[ \t]?")
_ALERT = re.compile(r"^\[!(note|tip|important|warning|caution)\][ \t]*([^\n]*)(?:\n|$)", re.I)
_TOC = re.compile(r"^(\[\[_TOC_\]\]|\[TOC\])$")


def slugify(text: str) -> str:
    """The id of a heading (like GitLab): lower case, letters, digits, «_» and «-» only, spaces become «-»."""
    kept = "".join(c for c in text.lower()
                   if unicodedata.category(c)[0] in "LN" or c in "_-" or c.isspace())
    slug = re.sub(r"-{2,}", "-", re.sub(r"\s+", "-", kept.strip())).strip("-")
    return slug or "section"


def _plain(inline) -> str:
    """The text of an inline token (what a heading shows)."""
    out = []
    for child in inline.children or []:
        if child.type in ("text", "code_inline", "text_special"):
            out.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            out.append(" ")
        elif child.type == "image":
            out.append(_plain(child))
    return "".join(out)


def _closing(tokens, start: int) -> int:
    """The index of the token that closes the one at `start` (same nesting)."""
    level = 0
    for i in range(start, len(tokens)):
        level += tokens[i].nesting
        if level == 0:
            return i
    return len(tokens) - 1


def _make_md(breaks: bool, alert_titles: dict) -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "breaks": breaks})
    md.enable(["table", "strikethrough", "linkify"])

    def blocks(state):
        """Task lists and alerts, on the raw text of the blocks (before the inline parsing)."""
        tokens = state.tokens
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type == "list_item_open" and i + 2 < len(tokens) and tokens[i + 2].type == "inline":
                inline = tokens[i + 2]
                match = _TASK.match(inline.content)
                if match:
                    checked = " checked" if match.group(1) in "xX" else ""
                    inline.content = (f'<input type="checkbox" class="task-list-item-checkbox" disabled{checked}> '
                                      + inline.content[match.end():])
                    token.attrJoin("class", "task-list-item")
                    for j in range(i - 1, -1, -1):  # the list the item belongs to
                        if tokens[j].type in ("bullet_list_open", "ordered_list_open") and tokens[j].level == token.level - 1:
                            if "contains-task-list" not in (tokens[j].attrGet("class") or ""):
                                tokens[j].attrJoin("class", "contains-task-list")
                            break
            elif (token.type == "blockquote_open" and i + 2 < len(tokens) and tokens[i + 1].type == "paragraph_open"
                  and tokens[i + 2].type == "inline"):
                inline = tokens[i + 2]
                match = _ALERT.match(inline.content)
                if match:
                    kind = match.group(1).lower()
                    title = match.group(2).strip() or alert_titles.get(kind) or DEFAULT_ALERT_TITLES[kind]
                    end = _closing(tokens, i)
                    for t in (token, tokens[end]):
                        t.tag = "div"
                    token.attrSet("class", f"markdown-alert markdown-alert-{kind}")
                    heading = Token("html_block", "", 0)
                    heading.content = f'<p class="markdown-alert-title">{escape(title, quote=False)}</p>\n'
                    inline.content = inline.content[match.end():]
                    if not inline.content.strip():  # the marker was the whole paragraph
                        del tokens[i + 1:i + 4]
                    tokens.insert(i + 1, heading)
            i += 1

    def headings(state):
        """Ids of the headings and the table of contents."""
        tokens = state.tokens
        seen: dict[str, int] = {}
        entries = []
        for i, token in enumerate(tokens):
            if token.type == "heading_open" and i + 1 < len(tokens):
                text = _plain(tokens[i + 1])
                slug = slugify(text)
                if slug in seen:
                    seen[slug] += 1
                    slug = f"{slug}-{seen[slug]}"
                else:
                    seen[slug] = 0
                token.attrSet("id", slug)
                entries.append((int(token.tag[1]), slug, text))
        i = 0
        while i < len(tokens):
            if (tokens[i].type == "paragraph_open" and i + 2 < len(tokens) and tokens[i + 1].type == "inline"
                    and _TOC.match(tokens[i + 1].content.strip())):
                toc = Token("html_block", "", 0)
                toc.content = toc_html(entries)
                tokens[i:i + 3] = [toc]
            i += 1

    md.core.ruler.before("inline", "flaskspark_blocks", blocks)
    md.core.ruler.push("flaskspark_headings", headings)
    return md


def toc_html(entries: Iterable[tuple[int, str, str]]) -> str:
    """The table of contents: nested lists of links to the headings (level, id, text)."""
    entries = list(entries)
    if not entries:
        return '<nav class="markdown-toc"></nav>\n'
    out = ['<nav class="markdown-toc">']
    stack: list[int] = []
    for level, slug, text in entries:
        if not stack:
            out.append("<ul>")
            stack.append(level)
        elif level > stack[-1]:
            out.append("<ul>")
            stack.append(level)
        else:
            out.append("</li>")
            while len(stack) > 1 and level < stack[-1]:
                stack.pop()
                out.append("</ul></li>")
        out.append(f'<li><a href="#{escape(slug)}">{escape(text, quote=False)}</a>')
    out.append("</li>")
    while len(stack) > 1:
        stack.pop()
        out.append("</ul></li>")
    out.append("</ul></nav>\n")
    return "".join(out)


_MD_CACHE: dict[tuple, MarkdownIt] = {}


def render(text: str | None, *, base_url: str | None = None, rewrite_url: UrlRewriter | None = None,
           breaks: bool = False, alert_titles: dict | None = None) -> Markup:
    """Markdown as sanitised HTML (Markup). base_url / rewrite_url: see resolve_url(). breaks: a single line break is
    a <br> (as in comments on GitHub); default CommonMark's (a space). alert_titles: the default titles of the alerts
    by type (e.g. {"note": "Hinweis"}), English otherwise."""
    titles = {**DEFAULT_ALERT_TITLES, **(alert_titles or {})}
    key = (breaks, tuple(sorted(titles.items())))
    md = _MD_CACHE.get(key)
    if md is None:
        md = _MD_CACHE[key] = _make_md(breaks, titles)
    return sanitize(md.render(text or ""), base_url=base_url, rewrite_url=rewrite_url)


# --- HTML to Markdown ----------------------------------------------------------------------------------------------

VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"})
BLOCKS = frozenset({
    "address", "article", "aside", "blockquote", "details", "dd", "div", "dl", "dt", "fieldset", "figcaption",
    "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p",
    "pre", "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
})
# A start tag that closes an open element of these (p before a block, li before li, cells and rows).
_CLOSES = {"li": {"li"}, "dt": {"dt", "dd"}, "dd": {"dt", "dd"}, "tr": {"tr", "td", "th"}, "td": {"td", "th"},
           "th": {"td", "th"}, "thead": {"tbody", "tr", "td", "th"}, "tbody": {"thead", "tr", "td", "th"},
           "tfoot": {"tbody", "tr", "td", "th"}}
_SKIP_CONTENT = frozenset({"script", "style", "template", "head", "title", "noscript", "textarea", "select"})


class Node:
    """An element (tag, attrs, children) or a text (tag None, text)."""

    __slots__ = ("tag", "attrs", "children", "text", "parent")

    def __init__(self, tag=None, attrs=None, text=""):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: list[Node] = []
        self.text = text
        self.parent = None

    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    def text_content(self) -> str:
        return self.text if self.tag is None else "".join(c.text_content() for c in self.children)


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]
        self.skip = 0

    def _close(self, tags):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag in tags:
                del self.stack[i:]
                return
            if self.stack[i].tag in ("ul", "ol", "table", "blockquote", "div", "details"):
                return

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_CONTENT:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in BLOCKS and self.stack[-1].tag == "p":
            self.stack.pop()
        if tag in _CLOSES:
            self._close(_CLOSES[tag])
        node = Node(tag, {k: (v if v is not None else "") for k, v in attrs})
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and not self.skip and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if self.skip:
            if tag in _SKIP_CONTENT:
                self.skip -= 1
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.skip:
            return
        node = Node(None, text=data)
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)


def parse_html(html: str) -> Node:
    """A small, lenient HTML tree (enough for Markdown's and editors' HTML)."""
    builder = _TreeBuilder()
    builder.feed(html or "")
    builder.close()
    return builder.root


_WS = re.compile(r"[ \t\r\n\f]+")


def _escape_text(text: str) -> str:
    """Characters of a text that Markdown would read as markup, escaped."""
    out = []
    n = len(text)
    for i, c in enumerate(text):
        prev = text[i - 1] if i else ""
        nxt = text[i + 1] if i + 1 < n else ""
        if c in "\\`*[]":
            out.append("\\" + c)
        elif c == "_":
            out.append("_" if prev.isalnum() and nxt.isalnum() else "\\_")
        elif c == "~":
            out.append("\\~" if "~" in (prev, nxt) else "~")
        elif c == "<":
            out.append("\\<" if re.match(r"[A-Za-z/!?]", nxt) else "<")
        elif c == "&":
            out.append("\\&" if re.match(r"#?\w+;", text[i + 1:]) else "&")
        else:
            out.append(c)
    return "".join(out)


_LINE_START = re.compile(r"^(#{1,6}(?=\s|$)|>|[-+](?=\s|$)|\d+(?=[.)](\s|$))|=+\s*$|-+\s*$)")


def _escape_line_starts(text: str) -> str:
    """Lines of a paragraph that would start a block (heading, quote, list, setext line), escaped."""
    lines = []
    for line in text.split("\n"):
        match = _LINE_START.match(line)
        if match:
            if match.group(0)[0].isdigit():
                end = len(match.group(0))
                line = line[:end] + "\\" + line[end:]
            else:
                line = "\\" + line
        lines.append(line)
    return "\n".join(lines)


def _fence(content: str, char: str = "`") -> str:
    longest = max((len(m) for m in re.findall(re.escape(char) + "+", content)), default=0)
    return char * max(3, longest + 1)


def _code_span(content: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", content)), default=0)
    ticks = "`" * (longest + 1)
    pad = " " if content.startswith(("`", " ")) or content.endswith(("`", " ")) or not content.strip() else ""
    return f"{ticks}{pad}{content}{pad}{ticks}"


def _destination(url: str) -> str:
    if re.search(r"[\s<>]", url) or url.count("(") != url.count(")"):
        return "<" + url.replace("<", "%3C").replace(">", "%3E").replace(" ", "%20") + ">"
    return url


def _title(title: str | None) -> str:
    return f' "{title.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"' if title else ""


def _wrap(inner: str, mark: str) -> str:
    """Emphasis around inner text, the spaces at its ends outside of the marks (Markdown needs them inside)."""
    stripped = inner.strip(" ")
    if not stripped:
        return inner
    lead = inner[:len(inner) - len(inner.lstrip(" "))]
    trail = inner[len(inner.rstrip(" ")):]
    return f"{lead}{mark}{stripped}{mark}{trail}"


class _Converter:
    def __init__(self, alert_titles: dict):
        self.alert_titles = alert_titles

    # inline --------------------------------------------------------------------------------------------------------

    def inline(self, node: Node, table: bool = False) -> str:
        if node.tag is None:
            return _escape_text(_WS.sub(" ", node.text.replace("\u00a0", " ")))
        tag = node.tag
        inner = lambda: "".join(self.inline(c, table) for c in node.children)  # noqa: E731
        if tag in ("strong", "b"):
            return _wrap(inner(), "**")
        if tag in ("em", "i"):
            return _wrap(inner(), "*")
        if tag in ("s", "del", "strike"):
            return _wrap(inner(), "~~")
        if tag == "code":
            return _code_span(_WS.sub(" ", node.text_content().replace("\u00a0", " ")))
        if tag == "br":
            return "<br>" if table else "\\\n"
        if tag == "input":
            return ""
        if tag == "img":
            src = node.attrs.get("data-md-src") or node.attrs.get("src") or ""  # an editor keeps the original
            if not src:
                return ""
            if node.attrs.get("width") or node.attrs.get("height"):
                given = {**node.attrs, "src": src}
                attrs = "".join(f' {k}="{escape(given[k])}"' for k in ("src", "alt", "title", "width", "height")
                                if given.get(k))
                return f"<img{attrs}>"
            alt = (node.attrs.get("alt") or "").replace("[", "\\[").replace("]", "\\]")
            return f"![{alt}]({_destination(src)}{_title(node.attrs.get('title'))})"
        if tag == "a":
            href = (node.attrs.get("data-md-href") or node.attrs.get("href") or "").strip()
            text = inner()
            plain = node.text_content().strip()
            if not href:
                return text
            if all(c.tag is None for c in node.children) and plain and (
                    href in (plain, "mailto:" + plain, "http://" + plain)) and not node.attrs.get("title") \
                    and re.match(r"(https?|mailto):", href, re.I):
                return f"<{href}>" if re.search(r"[*_~\[\]\\`<>\s]", plain) else plain
            return f"[{text}]({_destination(href)}{_title(node.attrs.get('title'))})"
        if tag in ("u", "ins", "sub", "sup", "kbd", "mark", "small", "abbr", "q", "samp", "var"):
            attr = f' title="{escape(node.attrs["title"])}"' if tag == "abbr" and node.attrs.get("title") else ""
            return f"<{tag}{attr}>{inner()}</{tag}>"
        return inner()

    # blocks --------------------------------------------------------------------------------------------------------

    def blocks(self, node: Node) -> list[str]:
        """The Markdown blocks of a container's children."""
        out: list[tuple[str, str]] = []  # (kind, text)
        buffer: list[Node] = []

        def flush():
            if buffer:
                text = self.paragraph(buffer)
                if text:
                    out.append(("p", text))
                buffer.clear()

        for child in node.children:
            if child.tag is not None and (child.tag in BLOCKS) and child.tag not in ("li", "summary"):
                flush()
                kind = child.tag
                text = self.block(child)
                if text:
                    if out and kind in ("ul", "ol") and out[-1][0] == kind:
                        out.append(("comment", "<!-- -->"))  # two lists in a row stay two lists
                    out.append((kind, text))
            elif child.tag in ("li", "summary"):
                flush()
                blocks = self.blocks(child)
                out.extend(("p", b) for b in blocks)
            else:
                buffer.append(child)
        flush()
        return [text for _, text in out]

    def paragraph(self, nodes: list[Node], table: bool = False) -> str:
        text = "".join(self.inline(n, table) for n in nodes)
        lines = [line.strip(" ") for line in text.split("\n")]
        text = "\n".join(lines).strip("\n")
        while text.endswith("\\"):  # a line break at the end (editors put one into an empty block)
            text = text[:-1].rstrip("\n ")
        return _escape_line_starts(text)

    def block(self, node: Node) -> str:
        tag = node.tag
        if tag == "p" or tag in ("dt", "dd", "figcaption", "address"):
            return self.paragraph(node.children) if not self._has_blocks(node) else "\n\n".join(self.blocks(node))
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = self.paragraph(node.children).replace("\\\n", " ").replace("\n", " ")
            if text.startswith("\\#"):
                text = text[1:]
            if text.endswith("#"):
                text = text[:-1] + "\\#"
            return f"{'#' * int(tag[1])} {text}".rstrip() if text else ""
        if tag == "hr":
            return "---"
        if tag == "pre":
            code = node.children[0] if (len(node.children) == 1 and node.children[0].tag == "code") else None
            source = node if code is None else code
            classes = source.classes() + node.classes()
            lang = next((c[9:] for c in classes if c.startswith("language-")), "")
            content = source.text_content().replace("\u00a0", " ")
            if content.endswith("\n"):
                content = content[:-1]
            fence = _fence(content)
            return f"{fence}{lang}\n{content}\n{fence}"
        if tag == "blockquote":
            return self.quote("\n\n".join(self.blocks(node)))
        if tag in ("ul", "ol"):
            return self.list(node)
        if tag == "table":
            return self.table(node)
        if tag == "nav" and "markdown-toc" in node.classes():
            return "[[_TOC_]]"
        if tag == "div" and "markdown-alert" in node.classes():
            return self.alert(node)
        if tag == "details":
            return self.details(node)
        return "\n\n".join(self.blocks(node))

    @staticmethod
    def _has_blocks(node: Node) -> bool:
        return any(c.tag in BLOCKS for c in node.children)

    @staticmethod
    def quote(text: str) -> str:
        return "\n".join(f"> {line}" if line else ">" for line in text.split("\n")) if text else ">"

    def alert(self, node: Node) -> str:
        kind = next((c[15:] for c in node.classes() if c.startswith("markdown-alert-") and c[15:] in ALERT_TYPES),
                    "note")
        children = list(node.children)
        title = ""
        for i, child in enumerate(children):
            if child.tag is None and not child.text.strip():
                continue
            if child.tag == "p" and "markdown-alert-title" in child.classes():
                text = _WS.sub(" ", child.text_content()).strip()
                defaults = {kind, DEFAULT_ALERT_TITLES[kind].lower(), (self.alert_titles.get(kind) or "").lower()}
                title = "" if text.lower() in defaults else text
                del children[i]
            break
        body = Node("div")
        body.children = children
        content = "\n\n".join(self.blocks(body))
        head = f"[!{kind.upper()}]" + (f" {title}" if title else "")
        return self.quote(head + ("\n" + content if content else ""))

    def details(self, node: Node) -> str:
        summary = next((c for c in node.children if c.tag == "summary"), None)
        body = Node("div")
        body.children = [c for c in node.children if c is not summary]
        content = "\n\n".join(self.blocks(body))
        is_open = "open" in node.attrs and "data-md-closed" not in node.attrs
        head = "<details open>" if is_open else "<details>"
        title = escape(_WS.sub(" ", summary.text_content()).strip(), quote=False) if summary else ""
        parts = [head + (f"\n<summary>{title}</summary>" if summary is not None else "")]
        if content:
            parts.append(content)
        parts.append("</details>")
        return "\n\n".join(parts)

    def list(self, node: Node) -> str:
        ordered = node.tag == "ol"
        start = (node.attrs.get("start") or "").strip()
        number = int(start) if re.fullmatch(r"[0-9]+", start) else 1
        items = [c for c in node.children if c.tag == "li"]
        loose = any(any(g.tag == "p" for g in li.children) for li in items)
        task_list = "data-task" in node.attrs
        out = []
        for li in items:
            marker = f"{number}. " if ordered else "- "
            number += 1
            box = next((c for c in li.children if c.tag == "input" and (c.attrs.get("type") or "") == "checkbox"),
                       None)
            if box is None:  # the box may sit in the item's first paragraph
                first = next((c for c in li.children if c.tag is not None), None)
                if first is not None and first.tag == "p":
                    box = next((c for c in first.children if c.tag == "input"), None)
            check = ""
            if box is not None:
                check = "[x] " if "checked" in box.attrs else "[ ] "
            elif task_list or "data-checked" in li.attrs:
                check = "[x] " if li.attrs.get("data-checked") == "true" else "[ ] "
            text = ("\n\n" if loose else "\n").join(self.blocks(li))
            lines = (check + text).split("\n")
            indent = " " * len(marker)
            body = "\n".join([marker + lines[0]] + [indent + line if line else "" for line in lines[1:]])
            out.append(body.rstrip())
        return ("\n\n" if loose else "\n").join(out)

    def table(self, node: Node) -> str:
        rows: list[tuple[Node, bool]] = []

        def collect(parent: Node, head: bool):
            for child in parent.children:
                if child.tag == "tr":
                    rows.append((child, head))
                elif child.tag in ("thead", "tbody", "tfoot"):
                    collect(child, child.tag == "thead")

        collect(node, False)
        if not rows:
            return ""
        cells = [[c for c in row.children if c.tag in ("td", "th")] for row, _ in rows]
        width = max(len(r) for r in cells) or 1
        header = cells[0]
        aligns = []
        for i in range(width):
            cell = header[i] if i < len(header) else None
            style = (cell.attrs.get("style") or "") if cell is not None else ""
            match = re.search(r"text-align\s*:\s*(left|right|center)", style, re.I)
            align = (match.group(1).lower() if match else (cell.attrs.get("align") or "").lower() if cell else "")
            aligns.append({"left": ":---", "right": "---:", "center": ":---:"}.get(align, "---"))

        def line(row: list[Node]) -> str:
            texts = []
            for i in range(width):
                if i < len(row):
                    text = self.paragraph(row[i].children, table=True) if not self._has_blocks(row[i]) else \
                        "<br>".join(self._cell_blocks(row[i]))
                    text = re.sub(r"(\s*<br>)+$", "", text)  # an editor's empty cell or trailing break
                    texts.append(text.replace("|", "\\|").replace("\n", " "))
                else:
                    texts.append("")
            return "| " + " | ".join(texts) + " |"

        return "\n".join([line(header), "| " + " | ".join(aligns) + " |"] + [line(r) for r in cells[1:]])

    def _cell_blocks(self, cell: Node) -> list[str]:
        return [b.replace("\n", " ") for b in self.blocks(cell)]


def to_markdown(html: str | None, *, alert_titles: dict | None = None) -> str:
    """HTML (Markdown's output, an editor's) as Markdown: headings, paragraphs, emphasis, strikethrough, code, links,
    images, lists, task lists (``<input type="checkbox">`` or ``<ul data-task>`` with ``<li data-checked>``), quotes,
    alerts, collapsible sections, tables and the table of contents. Other tags give their text. alert_titles: as for
    render(), so a default title is not written as a custom one."""
    converter = _Converter({**DEFAULT_ALERT_TITLES, **(alert_titles or {})})
    text = "\n\n".join(b for b in converter.blocks(parse_html(html or "")) if b)
    return text.strip("\n") + "\n" if text.strip() else ""


def alert_titles() -> dict:
    """The default titles of the alerts in the page's language (Flask-Babel's catalogues; English outside a
    request or without a translation)."""
    try:
        from flask_babel import gettext

        return {kind: gettext(title) for kind, title in DEFAULT_ALERT_TITLES.items()}
    except Exception:  # no app or request context, no Babel
        return dict(DEFAULT_ALERT_TITLES)


def template_filter(text: str | None, **options) -> Markup:
    """The Jinja filter ``markdown``: render() with the alert titles in the page's language.

        {{ issue.description|markdown }}
        {{ note.text|markdown(base_url=project_url, breaks=true) }}
    """
    options.setdefault("alert_titles", alert_titles())
    return render(text, **options)


__all__ = ["ALERT_TYPES", "DEFAULT_ALERT_TITLES", "alert_titles", "render", "resolve_url", "sanitize", "slugify",
           "template_filter", "to_markdown"]
