#!/usr/bin/env python3

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from transform import build_crat, transform
from utils import print_help, should_show_help, show_progress


def transform_dir(args: tuple[Path, Path, str, bool]) -> tuple[bool, Path]:
    translation_dir, tc_dir, plugin, run_dependencies = args
    try:
        transform(
            translation_dir,
            tc_dir,
            plugin,
            build=False,
            run_dependencies=run_dependencies,
        )
    except Exception:
        return False, tc_dir
    return True, tc_dir


def _usage() -> str:
    return f"Usage: {sys.argv[0]} <translation_dir> <plugin> [--run-dependencies]"


def main() -> None:
    if should_show_help(sys.argv):
        print_help(_usage())
        sys.exit(0)

    if len(sys.argv) not in {3, 4}:
        print(_usage())
        sys.exit(1)
    if len(sys.argv) == 4 and sys.argv[3] != "--run-dependencies":
        print(_usage())
        sys.exit(1)

    translation_dir = Path(sys.argv[1])
    plugin = sys.argv[2]
    run_dependencies = len(sys.argv) == 4

    project_dir = Path(__file__).resolve().parent.parent
    tc_root_dir = project_dir / "Test-Corpus" / "Public-Tests"

    build_crat()

    input_dirs = sorted(path for path in tc_root_dir.glob("*/*") if path.is_dir())
    total_num = len(input_dirs)
    success_num = 0
    failure_tcs: list[Path] = []
    show_progress(0, total_num)
    with ProcessPoolExecutor() as executor:
        for done_num, (success, transformed_dir) in enumerate(
            executor.map(
                transform_dir,
                (
                    (translation_dir, path, plugin, run_dependencies)
                    for path in input_dirs
                ),
            ),
            start=1,
        ):
            if success:
                success_num += 1
            else:
                failure_tcs.append(transformed_dir)
            show_progress(done_num, total_num)
    print()

    print(f"Success: {success_num}")
    print(f"Failure: {len(failure_tcs)}")
    print("Failure test cases:")
    for transformed_dir in failure_tcs:
        print(transformed_dir)


if __name__ == "__main__":
    main()
