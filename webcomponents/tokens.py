"""CSS variables (tokens) of a component, for its documentation.

The defaults come from the vendored Bootstrap CSS, the descriptions from the submodule manifest, so the
documentation follows a Bootstrap update without copying values by hand::

    "tokens": {
        "sources": [{"selector": ".badge", "prefix": "--bs-badge-"}],
        "optional": ["--bs-breadcrumb-padding-x"],
        "descriptions": {"--bs-badge-gap": "Space between icon and text."}
    }

``sources`` name the rules that declare the defaults (the first selector of the rule's selector list);
a source with ``"file"`` reads the component's own stylesheet instead of Bootstrap's (for components without a
Bootstrap counterpart, whose ``--ui-x-*`` tokens are declared on ``:host``).
``optional`` tokens are read by Bootstrap with a fallback but declared nowhere (default: unset).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
BOOTSTRAP_CSS = PACKAGE_ROOT / "vendor" / "bootstrap6" / "css" / "bootstrap.css"
UNSET = "unset"

# A style rule without nested blocks: "selector list { declarations }".
_RULE = re.compile(r"(?m)^[ \t]*([^@{}\s][^{}]*?)\s*\{([^{}]*)\}")
_DECLARATION = re.compile(r"(--[\w-]+)\s*:\s*([^;]*);")
_COMMENT = re.compile(r"/\*.*?\*/", re.S)


@dataclass(frozen=True)
class Token:
    name: str
    default: str
    description: str


@lru_cache(maxsize=4)
def _css(path: Path = BOOTSTRAP_CSS) -> str:
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=16)
def _without_comments(css: str) -> str:
    return _COMMENT.sub("", css)


def declared_tokens(selector: str, prefix: str, css: str | None = None) -> dict[str, str]:
    """Tokens starting with ``prefix`` declared in rules whose first selector is ``selector``, in order."""
    css = _without_comments(_css() if css is None else css)
    tokens: dict[str, str] = {}
    for match in _RULE.finditer(css):
        first = match.group(1).split(",")[0].strip()
        if first != selector:
            continue
        for name, value in _DECLARATION.findall(match.group(2)):
            if name.startswith(prefix):
                tokens.setdefault(name, " ".join(value.split()))
    return tokens


def load_manifest(module: str, submodule: str) -> dict:
    path = PACKAGE_ROOT / "modules" / module / submodule / "submodule.json"
    return json.loads(path.read_text(encoding="utf-8"))


def component_tokens(module: str, submodule: str, css: str | None = None) -> list[Token]:
    """Documented tokens of a submodule: declared ones with their default, then the optional ones."""
    base = PACKAGE_ROOT / "modules" / module / submodule
    return spec_tokens(load_manifest(module, submodule).get("tokens") or {}, css, base)


def spec_tokens(spec: dict, css: str | None = None, base: Path | None = None) -> list[Token]:
    """Tokens of a spec like a manifest's "tokens" (also for Bootstrap markup without an element, e.g. .navbar)."""
    descriptions: dict[str, str] = spec.get("descriptions", {})
    declared: dict[str, str] = {}
    for source in spec.get("sources", []):
        source_css = css
        if source.get("file"):
            if base is None:
                raise ValueError(f"source {source} needs the submodule directory")
            source_css = _css(base / source["file"])
        for name, value in declared_tokens(source["selector"], source["prefix"], source_css).items():
            declared.setdefault(name, value)
    tokens = [Token(name, value, descriptions.get(name, "")) for name, value in declared.items()]
    tokens += [Token(name, UNSET, descriptions.get(name, "")) for name in spec.get("optional", []) if name not in declared]
    return tokens


def undocumented(module: str, submodule: str) -> tuple[list[str], list[str]]:
    """(tokens without a description, descriptions without a token) of a submodule."""
    spec = load_manifest(module, submodule).get("tokens") or {}
    names = {token.name for token in component_tokens(module, submodule)}
    descriptions = set(spec.get("descriptions", {}))
    return sorted(names - descriptions), sorted(descriptions - names)


ROOT_TOKENS_HEADER = """/*
 * Bootstrap 6 design tokens for the host document (generated from vendor/bootstrap6/css/bootstrap.css by
 * webcomponents.tokens.root_tokens_css; do not edit). The shadow components inherit Bootstrap's tokens from the
 * page: pages that load Bootstrap 6 already have them, pages without it load this file.
 */
"""


def root_tokens_css(css: str | None = None) -> str:
    """The token part of Bootstrap's CSS: the layer order and every rule before the first styling layer (reboot)."""
    css = _css() if css is None else css
    body = css[: css.index("@layer reboot {")].rstrip() + "\n"
    charset = ""
    if body.startswith("@charset"):  # must stay the very first statement
        charset, body = body.split("\n", 1)
        charset += "\n"
    return charset + ROOT_TOKENS_HEADER + body


if __name__ == "__main__":  # python -m webcomponents.tokens > webcomponents/modules/bootstrap/ui-tokens.css
    print(root_tokens_css(), end="")
