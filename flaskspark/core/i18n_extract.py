"""A Babel extractor for browser scripts that understands template literals (pybabel extract).

Babel's own JavaScript extractor loses calls inside template literals, e.g. in `${…}` within an attribute's quotes
(`<b title="${t("Save")}">`) or nested template expressions. This one tokenizes the script itself (strings, template
literals with their expressions at any depth, comments, regular expressions) and finds every call of a keyword
(`t`, `nt`, `N_`, … whatever `-k` names) anywhere:

- a string literal, a template literal without `${}` or strings joined with `+` as an argument are messages;
- `t(cond ? "Yes" : "No")`, `t(label || "Untitled")`: every string the first argument may result in is a message;
- `nt("{n} file", "{n} files", n)` gives the singular and the plural (keyword spec `nt:1,2`);
- a comment with a tag (`-c TRANSLATORS:`) on the line of the call or the one before goes along.

babel.cfg of an application (FlaskSpark also registers it as the entry point `flaskspark_js`; the section
[extractors] names it without relying on the entry point):

    [extractors]
    flaskspark_js = flaskspark.core.i18n_extract:extract_js

    [flaskspark_js: **/static/**.js]

    pybabel extract -F babel.cfg -k _ -k gettext -k N_ -k t -k nt:1,2 -o messages.pot src/myapp
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A '/' after one of these starts a regular expression (else it divides).
_REGEX_AFTER_PUNCT = set("(,=:[!&|?{};+-*%<>~^") | {"=>", "&&", "||", "??", "==", "===", "!=", "!==", "<=", ">=", "+=",
                                                   "-=", "*=", "/=", "%=", "**", "...", "?."}
_REGEX_AFTER_WORD = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do",
                     "else", "yield", "await"}
_PUNCTUATORS = sorted(["===", "!==", "**=", "...", "<<=", ">>=", ">>>", "=>", "==", "!=", "<=", ">=", "&&", "||", "??",
                       "?.", "++", "--", "+=", "-=", "*=", "/=", "%=", "**", "<<", ">>", "&=", "|=", "^="],
                      key=len, reverse=True)
_NAME = re.compile(r"[A-Za-z_$\u0080-￿][\w$\u0080-￿]*")
_NUMBER = re.compile(r"(?:0[xXbBoO][\da-fA-F_]+|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?)n?")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
# What may stand around a string in the first argument for it to be a possible result (`a ? "x" : "y"`, `a || "x"`).
_RESULT_BEFORE = {None, "?", ":", "||", "??", "("}
_RESULT_AFTER = {None, ":", "||", "??", ")"}


@dataclass
class Token:
    kind: str  # name, string, template, number, regex, punct
    value: str
    line: int
    parts: list[list[Token]] = field(default_factory=list)  # a template's expressions, tokenized


@dataclass
class _Source:
    text: str
    pos: int = 0
    line: int = 1
    comments: list[tuple[int, int, str]] = field(default_factory=list)  # (first line, last line, text)

    def advance(self, to: int) -> None:
        self.line += self.text.count("\n", self.pos, to)
        self.pos = to


def _unescape(raw: str) -> str:
    out, i = [], 0
    while i < len(raw):
        ch = raw[i]
        if ch != "\\" or i + 1 >= len(raw):
            out.append(ch)
            i += 1
            continue
        nxt = raw[i + 1]
        if nxt in _ESCAPES and not (nxt == "0" and i + 2 < len(raw) and raw[i + 2].isdigit()):
            out.append(_ESCAPES[nxt])
            i += 2
        elif nxt == "x" and re.fullmatch(r"[\da-fA-F]{2}", raw[i + 2:i + 4]):
            out.append(chr(int(raw[i + 2:i + 4], 16)))
            i += 4
        elif nxt == "u" and raw[i + 2:i + 3] == "{":
            end = raw.find("}", i + 3)
            out.append(chr(int(raw[i + 3:end], 16)) if end > 0 else "u")
            i = end + 1 if end > 0 else i + 2
        elif nxt == "u" and re.fullmatch(r"[\da-fA-F]{4}", raw[i + 2:i + 6]):
            out.append(chr(int(raw[i + 2:i + 6], 16)))
            i += 6
        elif nxt == "\r":
            i += 3 if raw[i + 2:i + 3] == "\n" else 2  # a line continuation
        elif nxt in "\n  ":
            i += 2
        else:
            out.append(nxt)
            i += 2
    return "".join(out)


def _regex_allowed(previous: Token | None) -> bool:
    if previous is None:
        return True
    if previous.kind == "punct":
        return previous.value in _REGEX_AFTER_PUNCT and previous.value not in (")", "]")
    return previous.kind == "name" and previous.value in _REGEX_AFTER_WORD


def _tokenize(src: _Source, until_brace: bool = False) -> list[Token]:
    """The tokens from src.pos on; with until_brace up to the `}` that closes a template's `${` (consumed)."""
    tokens: list[Token] = []
    depth = 0
    text = src.text
    while src.pos < len(text):
        ch = text[src.pos]
        if ch in " \t\r\n\f\v ﻿  ":
            src.advance(src.pos + 1)
            continue
        if text.startswith("//", src.pos):
            end = text.find("\n", src.pos)
            end = len(text) if end < 0 else end
            src.comments.append((src.line, src.line, text[src.pos + 2:end].strip()))
            src.advance(end)
            continue
        if text.startswith("/*", src.pos):
            end = text.find("*/", src.pos + 2)
            end = len(text) if end < 0 else end + 2
            first = src.line
            body = text[src.pos + 2:end - 2]
            src.advance(end)
            src.comments.append((first, src.line, " ".join(line.strip(" *") for line in body.splitlines()).strip()))
            continue
        line = src.line
        if ch in "'\"":
            i = src.pos + 1
            while i < len(text) and text[i] != ch and text[i] != "\n":
                i += 2 if text[i] == "\\" else 1
            tokens.append(Token("string", _unescape(text[src.pos + 1:i]), line))
            src.advance(min(i + 1, len(text)))
            continue
        if ch == "`":
            tokens.append(_template(src))
            continue
        if ch == "/" and _regex_allowed(tokens[-1] if tokens else None):
            i, in_class = src.pos + 1, False
            while i < len(text) and text[i] != "\n":
                c = text[i]
                if c == "\\":
                    i += 2
                    continue
                if c == "[":
                    in_class = True
                elif c == "]":
                    in_class = False
                elif c == "/" and not in_class:
                    break
                i += 1
            i += 1
            while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                i += 1
            tokens.append(Token("regex", text[src.pos:i], line))
            src.advance(i)
            continue
        found = _NAME.match(text, src.pos)
        if found:
            tokens.append(Token("name", found.group(), line))
            src.advance(found.end())
            continue
        found = _NUMBER.match(text, src.pos) if ch.isdigit() or (ch == "." and text[src.pos + 1:src.pos + 2].isdigit()) else None
        if found:
            tokens.append(Token("number", found.group(), line))
            src.advance(found.end())
            continue
        if until_brace:
            if ch == "{":
                depth += 1
            elif ch == "}":
                if depth == 0:
                    src.advance(src.pos + 1)
                    return tokens
                depth -= 1
        punct = next((p for p in _PUNCTUATORS if text.startswith(p, src.pos)), ch)
        tokens.append(Token("punct", punct, line))
        src.advance(src.pos + len(punct))
    return tokens


def _template(src: _Source) -> Token:
    """A template literal from its backtick: its text (when it has no `${}`) and its expressions' tokens."""
    text, line = src.text, src.line
    i = src.pos + 1
    chunks: list[str] = []
    start = i
    parts: list[list[Token]] = []
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "`":
            break
        if c == "$" and text[i + 1:i + 2] == "{":
            chunks.append(text[start:i])
            src.advance(i + 2)
            parts.append(_tokenize(src, until_brace=True))
            i = start = src.pos
            continue
        i += 1
    chunks.append(text[start:i])
    src.advance(min(i + 1, len(text)))
    return Token("template", "" if parts else _unescape(chunks[0]).replace("\r\n", "\n"), line, parts)


def _constant(tokens: list[Token]) -> str | None:
    """The text of an argument that is a constant: a string, a template without `${}`, strings joined with +."""
    if not tokens or len(tokens) % 2 == 0:
        return None
    out = []
    for index, token in enumerate(tokens):
        if index % 2:
            if token.kind != "punct" or token.value != "+":
                return None
        elif token.kind == "string" or (token.kind == "template" and not token.parts):
            out.append(token.value)
        else:
            return None
    return "".join(out)


def _results(tokens: list[Token]) -> list[str]:
    """The strings the first argument may result in: `a ? "x" : "y"`, `a || "x"` (top level only)."""
    found, depth = [], 0
    for index, token in enumerate(tokens):
        if token.kind == "punct" and token.value in "([{":
            depth += 1
        elif token.kind == "punct" and token.value in ")]}":
            depth -= 1
        if depth or not (token.kind == "string" or (token.kind == "template" and not token.parts)):
            continue
        before = tokens[index - 1].value if index and tokens[index - 1].kind == "punct" else (None if not index else "")
        after = tokens[index + 1].value if index + 1 < len(tokens) and tokens[index + 1].kind == "punct" else (
            None if index + 1 == len(tokens) else "")
        if before in _RESULT_BEFORE and after in _RESULT_AFTER:
            found.append(token.value)
    return found


def _arguments(tokens: list[Token], start: int) -> list[list[Token]] | None:
    """The arguments of the call whose `(` is tokens[start], split at top-level commas (None if not closed)."""
    args: list[list[Token]] = [[]]
    depth = 0
    for token in tokens[start + 1:]:
        if token.kind == "punct" and token.value in "([{":
            depth += 1
        elif token.kind == "punct" and token.value in ")]}":
            if depth == 0:
                return [] if args == [[]] else args
            depth -= 1
        elif token.kind == "punct" and token.value == "," and depth == 0:
            args.append([])
            continue
        args[-1].append(token)
    return None


def _calls(tokens: list[Token], keywords, found: list) -> None:
    for index, token in enumerate(tokens):
        if token.kind == "template":
            for part in token.parts:
                _calls(part, keywords, found)
            continue
        if token.kind != "name" or token.value not in keywords:
            continue
        if index + 1 >= len(tokens) or tokens[index + 1].kind != "punct" or tokens[index + 1].value != "(":
            continue
        if index and tokens[index - 1].kind == "name" and tokens[index - 1].value == "function":
            continue  # its definition
        args = _arguments(tokens, index + 1)
        if not args:
            continue
        messages = [_constant(arg) for arg in args]
        if messages[0] is not None:
            found.append((token.line, token.value, messages))
            continue
        for text in _results(args[0]):  # t(cond ? "x" : "y"): each one
            found.append((token.line, token.value, [text, *messages[1:]]))


def extract_js(fileobj, keywords, comment_tags, options):
    """Babel's extractor interface: (line, function, messages, comments) per call of a keyword."""
    encoding = (options or {}).get("encoding", "utf-8")
    src = _Source(fileobj.read().decode(encoding))
    tokens = _tokenize(src)
    found: list = []
    _calls(tokens, set(keywords), found)
    tags = tuple(comment_tags or ())
    for line, funcname, messages in sorted(found, key=lambda f: f[0]):
        comments = []
        if tags:
            for first, last, text in src.comments:
                if last in (line, line - 1) and first <= line and text.startswith(tags):
                    comments.append(text)
        yield line, funcname, messages if len(messages) > 1 else messages[0], comments


__all__ = ["extract_js"]
