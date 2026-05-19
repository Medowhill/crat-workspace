#!/usr/bin/env python3

import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from transform import _crat_dir, _crat_env, build_crat
from utils import print_help, should_show_help, show_progress

plugins = [
    "extern",
    "preprocess",
    "outparam",
    "punning",
    "enum",
    "pointer",
    "io",
    "libc",
    "static",
]

post_passes = "simpl,interface,unsafe,unexpand"
post_flags = [
    "--unsafe-remove-unused",
    "--unsafe-remove-no-mangle",
    "--unsafe-replace-pub",
    "--unsafe-remove-extern-c",
    "--unexpand-use-print",
]


def _crat_bin() -> Path:
    crat = _crat_dir()
    profile = "debug" if "DEBUG" in os.environ else "release"
    return crat / "target" / profile / "crat"


def make_post_dir(args: tuple[Path, Path, Path, dict[str, str]]) -> tuple[bool, Path]:
    input_dir, output_dir, crat_bin, env = args
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            str(crat_bin),
            "-o",
            str(output_dir),
            "--config",
            str(input_dir / "config.toml"),
            "--pass",
            post_passes,
        ]
        command.extend(post_flags)
        command.append(str(input_dir))
        subprocess.run(command, env=env, check=True)
    except Exception:
        return False, input_dir
    return True, input_dir


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
    crat = _crat_dir()

    build_crat()

    crat_bin = _crat_bin()
    env = _crat_env(crat)
    input_dirs: list[tuple[Path, Path, Path, dict[str, str]]] = []
    for plugin in plugins:
        input_root_dir = translation_dir / plugin
        output_root_dir = translation_dir / f"{plugin}-post"
        output_root_dir.mkdir(parents=True, exist_ok=True)
        for input_dir in sorted(
            path for path in input_root_dir.glob("*/*/*") if path.is_dir()
        ):
            rel_dir = input_dir.relative_to(input_root_dir)
            output_dir = output_root_dir / rel_dir.parent
            input_dirs.append((input_dir, output_dir, crat_bin, env))

    total_num = len(input_dirs)
    success_num = 0
    failure_tcs: list[Path] = []
    show_progress(0, total_num)
    with ProcessPoolExecutor() as executor:
        for done_num, (success, input_dir) in enumerate(
            executor.map(make_post_dir, input_dirs),
            start=1,
        ):
            if success:
                success_num += 1
            else:
                failure_tcs.append(input_dir)
            show_progress(done_num, total_num)
    print()

    print(f"Success: {success_num}")
    print(f"Failure: {len(failure_tcs)}")
    print("Failure test cases:")
    for input_dir in failure_tcs:
        print(input_dir)


if __name__ == "__main__":
    main()
