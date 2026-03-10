#!/usr/bin/env python3
"""
JFR Full Report Generator
Runs all four analysis modules and produces a single Markdown report.
Usage: python3 jfr_full.py <file_path>

Accepts both .jfr binary files (auto-converted via `jfr print`) and
plain-text JFR exports.
"""

import sys
import os
from datetime import datetime

# Allow importing sibling scripts regardless of cwd
_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

from jfr_convert import ensure_text_file
from jfr_gc import analyze_gc
from jfr_cpu import analyze_cpu
from jfr_alloc import analyze_alloc
from jfr_threads import analyze_threads


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "full_analysis.txt"
    abs_path = os.path.abspath(path)

    text_path, tmp = ensure_text_file(path)
    try:
        header = [
            "# JFR Performance Analysis Report",
            "",
            f"**File**: `{abs_path}`",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ]

        sections = [
            analyze_gc(text_path),
            analyze_cpu(text_path),
            analyze_alloc(text_path),
            analyze_threads(text_path),
        ]

        print("\n".join(header))
        for section in sections:
            print(section)
            print("---\n")
    finally:
        if tmp:
            tmp.cleanup()


if __name__ == "__main__":
    main()
