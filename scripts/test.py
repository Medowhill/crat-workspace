#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

from utils import copy_translated_rust, print_help, should_show_help


def _usage() -> str:
    return f"Usage: {sys.argv[0]} <translation_dir> <tc_dir> [--verbose]"


def main() -> None:
    if should_show_help(sys.argv):
        print_help(_usage())
        sys.exit(0)

    verbose = len(sys.argv) == 4 and sys.argv[3] == "--verbose"
    if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and not verbose):
        print(_usage())
        sys.exit(1)

    translation_dir = Path(sys.argv[1])
    tc_dir = Path(sys.argv[2])

    tc_dir = tc_dir.resolve()
    tc_name = tc_dir.name
    tc_p_dir_name = tc_dir.parent.name
    tc_pp_dir_name = tc_dir.parent.parent.name
    corpus_dir = tc_dir.parent.parent.parent

    src_dir = translation_dir / "bin" / tc_pp_dir_name / tc_p_dir_name / tc_name
    dst_dir = tc_dir / "translated_rust"

    copy_translated_rust(src_dir, dst_dir)

    command = [
        "./deployment/scripts/github-actions/run_rust.sh",
        "--keep-going",
        "-m",
        f"^{tc_pp_dir_name}/{tc_p_dir_name}/{tc_name}$",
    ]
    if verbose:
        command.insert(2, "--verbose")
    subprocess.run(command, cwd=corpus_dir, stderr=subprocess.PIPE)


if __name__ == "__main__":
    main()
