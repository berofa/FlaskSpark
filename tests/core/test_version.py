"""flaskspark.core.__version__ is the version of the installed package, i.e. the one in pyproject.toml."""
import tomllib
from pathlib import Path

import flaskspark.core


def test_the_core_version_is_the_package_version():
    pyproject = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())
    assert flaskspark.core.__version__ == pyproject["project"]["version"]
