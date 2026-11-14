"""CSS variables of the components: documented completely and themeable on the host."""
from __future__ import annotations

import json
import re

import pytest

from webcomponents.tokens import PACKAGE_ROOT, UNSET, component_tokens, declared_tokens, undocumented

MODULE = PACKAGE_ROOT / "modules" / "bootstrap"
SUBMODULES = sorted(
    path.parent.name
    for path in MODULE.glob("*/submodule.json")
    if "tokens" in json.loads(path.read_text(encoding="utf-8"))
)
SHADOW_STYLES = (MODULE / "shadow-styles.js").read_text(encoding="utf-8")
CONSTANTS = dict(re.findall(r'const (\w+) = "([^"]+)";', SHADOW_STYLES))
HOISTS = {
    (selector, prefix, CONSTANTS.get(host, host.strip('"')))
    for selector, prefix, host in re.findall(r'\{ selector: "([^"]+)", prefix: "([^"]+)", host: ("[^"]+"|\w+) \}', SHADOW_STYLES)
}


def _host_elements(host: str) -> set[str]:
    """The elements a hoist targets: "ui-badge" or ":is(ui-input, ui-select)"."""
    return {re.sub(r"\[.*?\]", "", name).strip() for name in re.sub(r"^:is\((.*)\)$", r"\1", host).split(",")}


CSS = """
@layer components {
  .demo {
    --bs-demo-gap: 1rem;
    --bs-demo-bg: var(--bs-bg-2);
    --bs-other: red;
    display: flex;
  }
  .demo-sm, .demo { --bs-demo-gap: 2rem; }
  .demo.active { --bs-demo-bg: blue; }
}
"""


def test_declared_tokens_reads_the_rule_with_that_first_selector():
    assert declared_tokens(".demo", "--bs-demo-", CSS) == {"--bs-demo-gap": "1rem", "--bs-demo-bg": "var(--bs-bg-2)"}


def test_declared_tokens_of_a_missing_rule():
    assert declared_tokens(".nothing", "--bs-nothing-", CSS) == {}


def test_own_tokens_come_from_the_component_stylesheet(tmp_path):
    from webcomponents.tokens import spec_tokens

    (tmp_path / "ui-demo.css").write_text("/* A comment. */\n:host {\n  --ui-demo-gap: 1rem;\n  --ui-demo-bg: var(--bs-bg-2);\n  display: block;\n}\n")
    spec = {"sources": [{"selector": ":host", "prefix": "--ui-demo-", "file": "ui-demo.css"}], "descriptions": {"--ui-demo-gap": "Gap."}}
    tokens = spec_tokens(spec, base=tmp_path)
    assert [(t.name, t.default, t.description) for t in tokens] == [("--ui-demo-gap", "1rem", "Gap."), ("--ui-demo-bg", "var(--bs-bg-2)", "")]


def test_some_components_document_tokens():
    assert {"ui-alert", "ui-badge", "ui-button", "ui-card", "ui-list-group"} <= set(SUBMODULES)


@pytest.mark.parametrize("submodule", SUBMODULES)
def test_every_token_is_described(submodule):
    missing, stale = undocumented("bootstrap", submodule)
    assert missing == [], f"tokens without a description in {submodule}/submodule.json"
    assert stale == [], f"descriptions without a token in {submodule}/submodule.json"


@pytest.mark.parametrize("submodule", SUBMODULES)
def test_declared_tokens_have_defaults(submodule):
    tokens = component_tokens("bootstrap", submodule)
    assert tokens, submodule
    optional = set(json.loads((MODULE / submodule / "submodule.json").read_text())["tokens"].get("optional", []))
    for token in tokens:
        assert (token.default == UNSET) == (token.name in optional), token


@pytest.mark.parametrize("submodule", SUBMODULES)
def test_documented_tokens_are_themeable_on_the_host(submodule):
    """The docs promise `ui-x { --bs-x-…: … }` works: every source rule must be hoisted to the host."""
    manifest = json.loads((MODULE / submodule / "submodule.json").read_text())
    if manifest["tokens"].get("light"):
        pytest.skip("light-DOM component: the tokens are set on Bootstrap's own element")
    hosted = {(selector, prefix) for selector, prefix, host in HOISTS if _host_elements(host) & set(manifest["elements"])}
    for source in manifest["tokens"]["sources"]:
        if source.get("file"):
            continue  # the component's own tokens, declared on :host
        assert (source["selector"], source["prefix"]) in hosted, source


def _docs_page_specs():
    """Token specs of docs pages for markup without an element of its own (nav, navbar).

    The pages package is loaded on its own (as "docs_pages"): importing app.pages would start the docs app.
    """
    import importlib
    import importlib.util
    import sys

    pages = PACKAGE_ROOT.parent / "docs" / "app" / "pages"
    if "docs_pages" not in sys.modules:
        spec = importlib.util.spec_from_file_location("docs_pages", pages / "__init__.py", submodule_search_locations=[str(pages)])
        module = importlib.util.module_from_spec(spec)
        sys.modules["docs_pages"] = module
        spec.loader.exec_module(module)
    specs = []
    for path in sorted(pages.glob("*.py")):
        if path.stem in {"__init__", "common", "custom"}:
            continue
        page = importlib.import_module(f"docs_pages.{path.stem}").PAGE
        token_spec = (page.get("tokens") or {}).get("spec")
        if token_spec:
            specs.append(pytest.param(token_spec, id=path.stem))
    return specs


@pytest.mark.parametrize("spec", _docs_page_specs())
def test_docs_page_token_specs_are_complete(spec):
    from webcomponents.tokens import spec_tokens

    names = {token.name for token in spec_tokens(spec)}
    assert names, "no tokens found"
    assert names == set(spec["descriptions"])


def _docs_pages():
    """The PAGE dicts of the docs app (loaded like _docs_page_specs)."""
    import importlib

    _docs_page_specs()  # registers the "docs_pages" package
    pages = PACKAGE_ROOT.parent / "docs" / "app" / "pages"
    return [
        pytest.param(importlib.import_module(f"docs_pages.{path.stem}").PAGE, id=path.stem)
        for path in sorted(pages.glob("*.py"))
        if path.stem not in {"__init__", "common", "custom"}
    ]


@pytest.mark.parametrize("page", _docs_pages())
def test_docs_pages_show_the_tokens_of_their_component(page):
    """A component with documented tokens gets the "CSS variables" table on its page."""
    from webcomponents.tokens import load_manifest

    if not page.get("submodule"):
        return
    manifest = load_manifest(page.get("module", "bootstrap"), page["submodule"])
    if manifest.get("tokens"):
        assert page.get("tokens", {}).get("host"), f"{page['submodule']}: PAGE needs a tokens entry"


def test_calendar_tokens_are_documented():
    missing, stale = undocumented("calendar", "ui-calendar")
    assert (missing, stale) == ([], [])
    assert component_tokens("calendar", "ui-calendar")


def test_ui_tokens_css_is_generated_from_bootstrap():
    """ui-tokens.css follows the vendored Bootstrap (regenerate: python -m webcomponents.tokens > …/ui-tokens.css)."""
    from webcomponents.tokens import root_tokens_css

    generated = (MODULE / "ui-tokens.css").read_text(encoding="utf-8")
    assert generated == root_tokens_css()
    assert "--bs-primary-bg" in generated and "[data-bs-theme=dark]" in generated and "@layer reboot" not in generated
