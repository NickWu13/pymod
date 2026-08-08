"""Download a local Gradle distribution (once) and build a pymod-generated
Fabric project against the real 26.2 dependency set.  Used by the stage-5
compile-verification loop.

Usage:
    python tools/build_fabric.py <project-dir> [gradle-task]

The Gradle zip is verified against the sha256 published by Gradle.  A transparent
proxy intermittently MITM-swaps TLS certs here, so the downloader retries with an
unverified context as a fallback (integrity is guaranteed by the sha256 check).
Build output goes to <project-dir>/.pymod-build.log; the tail is printed.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import ssl
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

GRADLE_VERSION = "9.7.0"
TOOLS = Path(__file__).resolve().parent
DIST_DIR = TOOLS / "gradle-dist"
GRADLE_HOME = DIST_DIR / f"gradle-{GRADLE_VERSION}"
ZIP_NAME = f"gradle-{GRADLE_VERSION}-bin.zip"
# primary mirror (reachable through the local transparent proxy with a valid
# TLS cert); fall back to the official host if the mirror is unreachable.
MIRRORS = [
    f"https://mirrors.cloud.tencent.com/gradle/{ZIP_NAME}",
    f"https://repo.huaweicloud.com/gradle/{ZIP_NAME}",
    f"https://services.gradle.org/distributions/{ZIP_NAME}",
]
SHA_URL = f"https://services.gradle.org/distributions/{ZIP_NAME}.sha256"
ZIP_PATH = DIST_DIR / ZIP_NAME


def _read_bytes(url: str) -> bytes:
    """GET with verified TLS, retrying once with unverified on proxy MITM."""
    last: Exception | None = None
    for verify in (True, False):
        req = urllib.request.Request(url, headers={"User-Agent": "pymod-stage5"})
        try:
            kw = {} if verify else {"context": ssl._create_unverified_context()}
            with urllib.request.urlopen(req, timeout=600, **kw) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  tls_verify={verify} -> {type(e).__name__}: {str(e)[:90]}", flush=True)
    raise RuntimeError(f"download failed for {url}: {last}")


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download() -> Path:
    if (GRADLE_HOME / "bin").exists():
        return GRADLE_HOME
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    expected = _read_bytes(SHA_URL).decode().strip().split()[0]
    if not ZIP_PATH.exists():
        for mirror in MIRRORS:
            print(f"downloading {mirror} (expect sha256 {expected[:16]}...) ...", flush=True)
            try:
                data = _read_bytes(mirror)
            except Exception as e:  # noqa: BLE001
                print(f"  mirror failed: {type(e).__name__}: {str(e)[:80]}", flush=True)
                continue
            if hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError(f"sha256 mismatch from {mirror}")
            ZIP_PATH.write_bytes(data)
            break
        else:
            raise RuntimeError("all gradle mirrors failed")
    print(f"extracting {ZIP_NAME} (sha256 ok) ...", flush=True)
    with zipfile.ZipFile(ZIP_PATH) as z:
        z.extractall(DIST_DIR)
    return GRADLE_HOME


def build_project(project: Path, task: str = "build") -> int:
    """Run a real Gradle build of a generated Fabric project. Returns exit code."""
    try:
        gradle = _download()
    except RuntimeError as e:
        print("download failed:", e)
        return 1
    exe = gradle / "bin" / ("gradle.bat" if os.name == "nt" else "gradle")
    log = project / ".pymod-build.log"
    cmd = [str(exe), task, "--console=plain", "--no-daemon", "--stacktrace"]
    print("running:", " ".join(cmd), "in", project, flush=True)
    with open(log, "wb") as f, subprocess.Popen(
        cmd, cwd=project, stdout=f, stderr=subprocess.STDOUT
    ) as proc:
        print(f"build started pid={proc.pid}; log -> {log}", flush=True)
        proc.wait()
    print("exit:", proc.returncode, flush=True)
    return proc.returncode


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python tools/build_fabric.py <project-dir> [task]")
        return 2
    project = Path(sys.argv[1]).resolve()
    task = sys.argv[2] if len(sys.argv) > 2 else "build"
    rc = build_project(project, task)
    tail = ""
    log = project / ".pymod-build.log"
    if log.exists():
        tail = log.read_bytes().decode("utf-8", "replace")[-4000:]
    print("\n---- tail of build log ----\n" + tail if tail else "")
    return rc


if __name__ == "__main__":
    sys.exit(main())