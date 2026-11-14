"""Run the documentation app.

FlaskSpark (0.1.x) resolves the application package relative to the current
working directory (``app_base_dir = cwd/<app_module>``), so this runner
changes into docs/ once, permanently, before the app is constructed. The
previous version restored the old cwd after import, which left request-time
path resolution (FlaskSpark falls back to cwd there as well) pointing at a
different directory than at construction time.

The clean long-term fix is an explicit app-root parameter in FlaskSpark.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = ROOT / "docs"

sys.path.insert(0, str(ROOT))       # webcomponents (also installed editable in the venv)
sys.path.insert(0, str(DOCS_ROOT))  # the docs "app" package

os.chdir(DOCS_ROOT)

from app import app  # noqa: E402


if __name__ == "__main__":
    app.run(
        host=app.config["APP_BIND_HOST"],
        port=app.config["APP_PORT"],
        debug=app.config["DEBUG"],
    )
