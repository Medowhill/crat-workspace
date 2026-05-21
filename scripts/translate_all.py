#!/usr/bin/env python3

import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from translate import translate_tc
from utils import print_help, should_show_help, show_progress


def _translate_tc(tc_dir: Path) -> tuple[bool, Path]:
    try:
        translate_tc(tc_dir)
    except Exception:
        return False, tc_dir
    return True, tc_dir


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
    tc_root_dir_1 = project_dir / "Test-Corpus" / "Public-Tests"
    tc_root_dir_2 = project_dir / "PUBLIC-Test-Corpus" / "Hidden-Tests"
    output_dir = project_dir / "c2rust-translated"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    tc_dirs = sorted(
        path
        for root_dir in (tc_root_dir_1, tc_root_dir_2)
        for path in root_dir.glob("*/*")
        if path.is_dir()
    )
    total_num = len(tc_dirs)
    success_num = 0
    failure_tcs: list[Path] = []
    show_progress(0, total_num)
    with ProcessPoolExecutor() as executor:
        for done_num, (success, tc_path) in enumerate(
            executor.map(_translate_tc, tc_dirs), start=1
        ):
            if success:
                success_num += 1
            else:
                failure_tcs.append(tc_path)
            show_progress(done_num, total_num)
    print()

    print(f"Success: {success_num}")
    print(f"Failure: {len(failure_tcs)}")
    if failure_tcs:
        print("Failure test cases:")
        for tc_path in failure_tcs:
            print(tc_path)


if __name__ == "__main__":
    main()
