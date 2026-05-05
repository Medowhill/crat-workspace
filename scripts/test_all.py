#!/usr/bin/env python3

import shutil
import subprocess
import sys
from pathlib import Path

from utils import print_help, should_show_help


def _usage() -> str:
    return f"Usage: {sys.argv[0]} <translation_dir> [--verbose]"


def main() -> None:
    if should_show_help(sys.argv):
        print_help(_usage())
        sys.exit(0)

    if len(sys.argv) not in {2, 3}:
        print(_usage())
        sys.exit(1)
    if len(sys.argv) == 3 and sys.argv[2] != "--verbose":
        print(_usage())
        sys.exit(1)

    translation_dir = Path(sys.argv[1]) / "bin"
    verbose = len(sys.argv) == 3

    project_dir = Path(__file__).resolve().parent.parent
    tc_root_dir = project_dir / "Test-Corpus"

    src_dirs = sorted(path for path in translation_dir.glob("*/*/*") if path.is_dir())
    for src_dir in src_dirs:
        tc_dir = tc_root_dir / src_dir.relative_to(translation_dir)
        dst_dir = tc_dir / "translated_rust"

        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)

    command = [
        "./deployment/scripts/github-actions/run_rust.sh",
        "--keep-going",
    ]
    if verbose:
        command.insert(2, "--verbose")
    subprocess.run(command, cwd=project_dir / "Test-Corpus", stderr=subprocess.PIPE)


if __name__ == "__main__":
    main()
