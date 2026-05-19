#!/usr/bin/env python3

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from find_unsafe import find_unsafe
from utils import print_help, should_show_help, show_progress


def _usage() -> str:
    return f"Usage: {sys.argv[0]} <translation_dir>"


def main() -> None:
    if should_show_help(sys.argv):
        print_help(_usage())
        sys.exit(0)

    if len(sys.argv) != 2:
        print(_usage())
        sys.exit(1)

    translation_dir = Path(sys.argv[1])

    input_dirs = sorted(
        path for path in translation_dir.glob("*-post/*/*/*") if path.is_dir()
    )
    total_num = len(input_dirs)
    success_num = 0
    failures: list[tuple[Path, str]] = []
    show_progress(0, total_num)
    with ProcessPoolExecutor() as executor:
        for done_num, (success, translated_dir, stderr) in enumerate(
            executor.map(find_unsafe, input_dirs),
            start=1,
        ):
            if success:
                success_num += 1
            else:
                failures.append((translated_dir, stderr))
            show_progress(done_num, total_num)
    print()

    print(f"Success: {success_num}")
    print(f"Failure: {len(failures)}")
    print("Failure dirs:")
    for translated_dir, stderr in failures:
        print(translated_dir)
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
