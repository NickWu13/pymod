"""Optional integration test: compile a generated Fabric project against the
real 26.2 dependency set.

This is gated behind ``PYMOD_RUN_FABRIC_BUILD=1`` because the first invocation
downloads Gradle + the 26.2 dependency set and takes minutes. Run it locally
with:

    PYMOD_RUN_FABRIC_BUILD=1 python -m pytest tests/test_fabric_build.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

from helpers import EXAMPLES, parse_build  # noqa: E402

_NEEDS_BUILD = os.environ.get("PYMOD_RUN_FABRIC_BUILD") == "1"
pytestmark = pytest.mark.skipif(
    not _NEEDS_BUILD,
    reason="set PYMOD_RUN_FABRIC_BUILD=1 to compile against real deps",
)


def test_fabric_project_builds_end_to_end(tmp_path):
    import build_fabric
    from pymod.target.fabric import FabricTarget

    spec = parse_build((EXAMPLES / "fabric_demo.py").read_text(encoding="utf-8"))
    FabricTarget(spec, tmp_path, game_version="26.2").generate()

    rc = build_fabric.build_project(tmp_path, "build")
    assert rc == 0, f"gradle build failed; see {tmp_path / '.pymod-build.log'}"

    jars = list((tmp_path / "build/libs").glob("*.jar"))
    assert jars, "no jar produced"
    jar = max(jars, key=lambda p: p.stat().st_size)  # the remapped mod jar
    import zipfile

    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
    assert "fabric.mod.json" in names
    assert "net/pymod/fdemo/FdemoMod.class" in names
    assert "data/fdemo/tags/blocks/magic.json" in names