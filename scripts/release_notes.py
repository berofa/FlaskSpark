"""The release notes of a version: its section of CHANGELOG.md (Keep a Changelog), without the heading.

    python scripts/release_notes.py 1.0.0      (a leading "v" is ignored, e.g. the tag v1.0.0)

Used by the publish workflow for the GitHub release of a tag.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def section(text: str, version: str) -> str:
    """The section «## [<version>] …» of `text` up to the next «## » heading, stripped."""
    version = version.removeprefix("v")
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n", re.MULTILINE)
    found = heading.search(text)
    if found is None:
        raise LookupError(f"CHANGELOG.md has no section for version {version}")
    following = re.compile(r"^## ", re.MULTILINE).search(text, found.end())
    return text[found.end():following.start() if following else len(text)].strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: release_notes.py <version>", file=sys.stderr)
        return 2
    try:
        print(section(CHANGELOG.read_text(encoding="utf-8"), argv[1]))
    except LookupError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
