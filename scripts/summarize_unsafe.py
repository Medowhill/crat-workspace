#!/usr/bin/env python3

import sys
from collections import Counter
from pathlib import Path

from utils import print_help, should_show_help


def _usage() -> str:
    return f"Usage: {sys.argv[0]}"


def main() -> None:
    if should_show_help(sys.argv):
        print_help(_usage())
        sys.exit(0)

    if len(sys.argv) != 1:
        print(_usage())
        sys.exit(1)

    project_dir = Path(__file__).resolve().parent.parent
    tc_root_dir = project_dir / "Test-Corpus"

    counts: Counter[str] = Counter()
    for unsafe_path in sorted(tc_root_dir.glob("*/*/*/translated_rust/unsafe.txt")):
        counts.update(
            name
            for name in unsafe_path.read_text(encoding="utf-8").splitlines()
            if name
        )

    print(f"total: {sum(counts.values())}")
    for name, count in counts.most_common():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
