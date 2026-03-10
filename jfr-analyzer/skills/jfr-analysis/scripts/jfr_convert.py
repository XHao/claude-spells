#!/usr/bin/env python3
"""
JFR binary-to-text converter.

If the input file ends with .jfr, runs `jfr print` and returns a path to a
temporary text file. Otherwise returns the original path unchanged.

Usage (as library):
    from jfr_convert import ensure_text_file
    text_path, tmp = ensure_text_file(path)
    try:
        # ... analyse text_path ...
    finally:
        if tmp:
            tmp.cleanup()
"""

import os
import shutil
import subprocess
import sys
import tempfile


def ensure_text_file(path: str) -> tuple[str, "tempfile.TemporaryDirectory | None"]:
    """Return (text_path, tmp_dir_or_None).

    If *path* is already a text export, returns (path, None).
    If *path* ends with .jfr, converts it via `jfr print` into a temp file
    and returns (temp_text_path, TemporaryDirectory).  The caller must call
    tmp.cleanup() when done.

    Raises SystemExit on conversion failure.
    """
    if not path.endswith(".jfr"):
        return path, None

    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        print(f"Error: file not found: {abs_path}", file=sys.stderr)
        sys.exit(1)

    jfr_cmd = shutil.which("jfr")
    if jfr_cmd is None:
        print(
            "Error: `jfr` command not found in PATH.\n"
            "Install JDK 17+ and ensure $JAVA_HOME/bin is on PATH, or convert manually:\n"
            f"  jfr print {abs_path} > output.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    tmp = tempfile.TemporaryDirectory(prefix="jfr_analysis_")
    out_path = os.path.join(tmp.name, "recording.txt")

    print(f"Converting {abs_path} → text (this may take a moment)…", file=sys.stderr)
    try:
        with open(out_path, "w") as out_f:
            result = subprocess.run(
                [jfr_cmd, "print", abs_path],
                stdout=out_f,
                stderr=subprocess.PIPE,
                text=True,
            )
    except Exception as e:
        tmp.cleanup()
        print(f"Error running `jfr print`: {e}", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        tmp.cleanup()
        print(
            f"Error: `jfr print` exited with code {result.returncode}:\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Conversion complete → {out_path}", file=sys.stderr)
    return out_path, tmp
