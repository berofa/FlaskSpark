"""The components in a real browser: the docs app serves /_tests/components, headless Chromium runs its checks.

Skipped without Chromium. The page reports one result per check as JSON; every check must pass.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BROWSER = next((shutil.which(name) for name in ("chromium", "chromium-browser", "google-chrome") if shutil.which(name)), None)

pytestmark = pytest.mark.skipif(BROWSER is None, reason="no Chromium/Chrome installed")

SERVER = """
import runpy
app = runpy.run_path("docs/run.py", run_name="docs_app")["app"]  # docs/run.py changes into docs/ and builds the app
app.run(host="127.0.0.1", port=int(PORT), debug=False, use_reloader=False)
"""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def docs_url(tmp_path_factory):
    port = _free_port()
    log = tmp_path_factory.mktemp("docs") / "server.log"
    process = subprocess.Popen(
        [sys.executable, "-c", SERVER.replace("PORT", str(port))],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=log.open("wb"),  # a file, not a pipe: nobody reads it while the server runs
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(url + "/_tests/components", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("docs app did not start: " + log.read_text(errors="replace")[-2000:])
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


def _results(url: str) -> list[dict]:
    dom = subprocess.run(
        # Reduced motion: headless virtual time runs no animation frames, so scrolls must jump (the carousel checks).
        [BROWSER, "--headless=new", "--no-sandbox", "--disable-gpu", "--force-prefers-reduced-motion", "--virtual-time-budget=10000",
         "--dump-dom", url],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    ).stdout
    match = re.search(r'<pre id="results">(.*?)</pre>', dom, re.S)
    assert match, "no results on the page"
    return json.loads(html.unescape(match.group(1)))


def test_components_in_the_browser(docs_url):
    results = _results(docs_url + "/_tests/components")
    failed = [f"{r['name']}: {r['detail']}" for r in results if not r["ok"]]
    assert len(results) >= 30
    assert failed == []


def test_customizing_demos_in_the_browser(docs_url):
    """Every customizing demo of the docs changes how its component looks (the tokens reach it)."""
    results = _results(docs_url + "/_tests/customizing")
    failed = [f"{r['name']}: {r['detail']}" for r in results if not r["ok"]]
    assert len(results) >= 30
    assert failed == []
