#!/usr/bin/env python3
"""
JFR Full Report Generator
Runs all four analysis modules and produces a single Markdown report.
Usage: python3 jfr_full.py <file_path>
"""

import sys
import os
from datetime import datetime

# Allow importing sibling scripts regardless of cwd
_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

from jfr_gc import analyze_gc
from jfr_cpu import analyze_cpu
from jfr_alloc import analyze_alloc
from jfr_threads import analyze_threads


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "full_analysis.txt"
    abs_path = os.path.abspath(path)

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
        analyze_gc(path),
        analyze_cpu(path),
        analyze_alloc(path),
        analyze_threads(path),
    ]

    print("\n".join(header))
    for section in sections:
        print(section)
        print("---\n")


if __name__ == "__main__":
    main()
