"""flaskspark.markdown: rendering (GitHub/GitLab flavoured, sanitised), HTML back to Markdown, the Jinja filter, and
the same results as the browser's ui-markdown/markdown.js (shared cases; the comparison runs node when it is there)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from markupsafe import Markup

from flaskspark import markdown
from flaskspark.markdown import parse_html, render, resolve_url, sanitize, slugify, to_markdown

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "webcomponents" / "fixtures" / "markdown_cases.json").read_text())
MARKDOWN_JS = ROOT / "webcomponents" / "modules" / "bootstrap" / "ui-markdown" / "markdown.js"


def _options(case):
    options = dict(case.get("options") or {})
    if options.pop("rewrite", None) == "javascript":
        options["rewrite_url"] = lambda url, kind: "javascript:alert(1)"
    return options


@pytest.mark.parametrize("case", CASES["render"], ids=[c["name"] for c in CASES["render"]])
def test_render(case):
    html = render(case["md"], **_options(case))
    assert isinstance(html, Markup)
    for part in case.get("contains", []):
        assert part in html, (part, str(html))
    for part in case.get("absent", []):
        assert part not in html, (part, str(html))


def assert_safe(html: str):
    """Only allowed tags, no event handlers, no styles but text-align, links and images only with safe schemes."""
    assert not re.search(r"<\s*(script|style|iframe|object|embed|svg|math|form|meta|base|button|textarea)", html, re.I)

    def walk(node):
        for child in node.children:
            if child.tag is None:
                continue
            assert child.tag in markdown.ALLOWED_TAGS, child.tag
            for name, value in child.attrs.items():
                assert not name.startswith("on"), name
                assert name in markdown.ALLOWED_ATTRIBUTES.get(child.tag, set()) | {"rel"}, (child.tag, name)
                if name == "style":
                    assert re.fullmatch(r"text-align:(left|right|center)", value)
                if name in ("href", "src"):
                    scheme = re.match(r"^([a-z][a-z0-9+.-]*):", value.strip(), re.I)
                    allowed = ("http", "https") if name == "src" else ("http", "https", "mailto", "tel")
                    assert not scheme or scheme.group(1).lower() in allowed, value
                if name == "class":
                    assert not {"btn", "btn-danger", "fixed-top"} & set(value.split())
            if child.tag == "input":
                assert child.attrs.get("type") == "checkbox" and "disabled" in child.attrs
            walk(child)

    walk(parse_html(html))


@pytest.mark.parametrize("case", CASES["xss"], ids=[c["name"] for c in CASES["xss"]])
def test_xss(case):
    html = render(case["md"], **_options(case))
    assert_safe(str(html))  # a text may still show "javascript:…", escaped, never as a link


def test_sanitize_forces_checkboxes_and_rel():
    html = sanitize('<input type="text" name="x" value="y"><a href="/x" rel="opener" target="_blank">x</a>')
    assert '<input type="checkbox" disabled="">' in html
    assert '<a href="/x" rel="noopener noreferrer">x</a>' == re.search(r"<a .*</a>", html).group(0)


def test_resolve_url():
    assert resolve_url("/uploads/a.png", "image", "https://h/g/p/") == "https://h/g/p/uploads/a.png"
    assert resolve_url("a.png", "image", "https://h/g/p") == "https://h/g/p/a.png"
    assert resolve_url("#x", "link", "https://h/g/p") == "#x"
    assert resolve_url("https://o/a", "link", "https://h") == "https://o/a"
    assert resolve_url("mailto:a@b.ch", "link") == "mailto:a@b.ch"
    assert resolve_url("mailto:a@b.ch", "image") is None
    assert resolve_url("data:image/png;base64,AA", "image") is None
    assert resolve_url(" java\tscript:alert(1)", "link") is None
    assert resolve_url("//cdn.example/a.png", "image") == "//cdn.example/a.png"
    assert resolve_url("\\\\evil/a", "link") is None
    proxied = resolve_url("https://o/a.png", "image", rewrite_url=lambda url, kind: f"/proxy?u={url}")
    assert proxied == "/proxy?u=https://o/a.png"
    assert resolve_url("https://o/a.png", "image", rewrite_url=lambda url, kind: None) is None


def test_render_rewrites_images_through_a_hook():
    calls = []

    def proxy(url, kind):
        calls.append((url, kind))
        return "/img?u=" + url if kind == "image" else url

    html = render("![a](https://o/a.png) [l](https://o/l)", rewrite_url=proxy)
    assert 'src="/img?u=https://o/a.png"' in html and 'href="https://o/l"' in html
    assert ("https://o/a.png", "image") in calls and ("https://o/l", "link") in calls


def test_slugify():
    assert slugify("Über uns!") == "über-uns"
    assert slugify("  a -- b  ") == "a-b"
    assert slugify("snake_case 2") == "snake_case-2"
    assert slugify("???") == "section"


@pytest.mark.parametrize("md", CASES["roundtrip"])
def test_roundtrip(md):
    assert to_markdown(render(md)) == md


@pytest.mark.parametrize("case", CASES["to_markdown"], ids=[c["name"] for c in CASES["to_markdown"]])
def test_to_markdown(case):
    assert to_markdown(case["html"], **_options(case)) == case["md"]


def test_to_markdown_renders_back_to_the_same_html():
    html = render("Mixed *a* **b** `c` [d](https://e.ch)\n\n- [x] f\n\n> [!tip]\n> g\n")
    assert render(to_markdown(html)) == html


def test_empty_input():
    assert render(None) == "" and render("") == ""
    assert to_markdown(None) == "" and to_markdown("") == ""


def test_jinja_filter(tmp_path, monkeypatch):
    from flask import Flask, render_template_string

    from flaskspark.app import FlaskSpark

    app = Flask(__name__)
    FlaskSpark._register_markdown(type("Stub", (), {"app": app})())
    with app.test_request_context():
        out = render_template_string("{{ text|markdown }}|{{ text|markdown(base_url='https://h/p') }}",
                                     text="**x** ![i](/a.png)")
    assert "<strong>x</strong>" in out and "&lt;strong&gt;" not in out
    assert 'src="https://h/p/a.png"' in out


# --- the browser's implementation gives the same HTML and Markdown --------------------------------------------------

NODE_SCRIPT = r"""
const m = await import(process.argv[1]);
await m.loadMarkdown();
const input = JSON.parse(await new Promise((resolve) => {
  let data = ""; process.stdin.on("data", (c) => (data += c)); process.stdin.on("end", () => resolve(data));
}));
const options = (o) => {
  o = o || {};
  const out = { baseUrl: o.base_url, breaks: o.breaks, alertTitles: o.alert_titles };
  if (o.rewrite === "javascript") out.rewriteUrl = () => "javascript:alert(1)";
  return out;
};
const out = {
  render: input.render.map((c) => m.render(c.md, options(c.options))),
  toMarkdown: input.toMarkdown.map((c) => m.toMarkdown(c.html, { ...options(c.options), native: false })),
  roundtrip: input.roundtrip.map((md) => m.toMarkdown(m.render(md))),
};
process.stdout.write(JSON.stringify(out));
"""


def _canonical(html: str):
    """A tree to compare HTML by (attribute order and quoting do not count)."""

    def walk(node):
        if node.tag is None:
            return node.text
        return (node.tag, tuple(sorted(node.attrs.items())), tuple(walk(c) for c in node.children))

    return walk(parse_html(html))


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_browser_gives_the_same_results():
    samples = CASES["render"] + CASES["xss"] + [{"md": md} for md in CASES["roundtrip"]]
    request = {
        "render": [{"md": c["md"], "options": c.get("options")} for c in samples],
        "toMarkdown": [{"html": c["html"], "options": c.get("options")} for c in CASES["to_markdown"]],
        "roundtrip": CASES["roundtrip"],
    }
    result = subprocess.run(["node", "--input-type=module", "-e", NODE_SCRIPT, str(MARKDOWN_JS)], cwd=ROOT,
                            input=json.dumps(request), capture_output=True, text=True, timeout=60, check=True)
    js = json.loads(result.stdout)
    for case, js_html in zip(samples, js["render"]):
        py_html = str(render(case["md"], **_options(case)))
        assert _canonical(js_html) == _canonical(py_html), (case["md"], py_html, js_html)
    for case, js_md in zip(CASES["to_markdown"], js["toMarkdown"]):
        assert js_md == to_markdown(case["html"], **_options(case)), case["name"]
    assert js["roundtrip"] == CASES["roundtrip"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_core_labels_are_the_editors():
    """flaskspark.core.markdown_labels (translated by the core's catalogue) has the editor's keys and English texts."""
    pytest.importorskip("yaml")  # flaskspark.core needs the extra "core"
    from flaskspark.core.markdown_labels import LABELS, markdown_editor_labels

    script = ('const c = await import(process.argv[1]); '
              'process.stdout.write(JSON.stringify(c.DEFAULT_LABELS));')
    editor = ROOT / "webcomponents" / "modules" / "bootstrap" / "ui-markdown-editor" / "editor-commands.js"
    result = subprocess.run(["node", "--input-type=module", "-e", script, str(editor)], capture_output=True, text=True,
                            timeout=30, check=True)
    assert LABELS == json.loads(result.stdout)
    assert markdown_editor_labels() == LABELS  # outside a request: English


def test_core_labels_in_german(tmp_path):
    pytest.importorskip("yaml")
    from flask import Flask
    from flask_babel import Babel

    from flaskspark.core.markdown_labels import markdown_editor_labels

    app = Flask(__name__)
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = str(ROOT / "flaskspark" / "core" / "locales")
    Babel(app, locale_selector=lambda: "de")
    with app.test_request_context():
        labels = markdown_editor_labels()
        titles = markdown.alert_titles()
    assert labels["heading-1"] == "Überschrift 1" and labels["paragraph"] == "Normaler Text"
    assert titles["note"] == "Hinweis" and "ß" not in "".join(labels.values())
