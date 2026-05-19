#!/usr/bin/env python3

import os
import re
import subprocess
import sys
from pathlib import Path

from utils import copy_translated_rust, print_help, should_show_help

SUMMARY_FIELDS = [
    ("Test Cases Discovered", "- Test Cases Discovered:      "),
    ("Test Cases Skipped", "- Test Cases Skipped:         "),
    ("Test Cases Tested", "- Test Cases Tested:          "),
    ("Test Cases Failed", "- Test Cases Failed:          "),
    ("Test Vectors Passed", "- Test Vectors Passed:        "),
    ("Test Vectors Skipped", "- Test Vectors Skipped:       "),
    ("Test Vectors Failed", "- Test Vectors Failed:        "),
]
SUMMARY_LABELS = {label for label, _ in SUMMARY_FIELDS}
SUMMARY_LINE_RE = re.compile(r"^-\s*(.+?):\s*(\d+)$")
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _usage() -> str:
    return f"Usage: {sys.argv[0]} <translation_dir> [--verbose]"


def _empty_summary() -> dict[str, int]:
    return {label: 0 for label, _ in SUMMARY_FIELDS}


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def _stream_and_extract_summary(command: list[str], corpus_dir: Path) -> dict[str, int]:
    summary = _empty_summary()
    in_summary = False
    current_summary: dict[str, int] = {}
    buffered_lines: list[str] = []
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    def flush_buffered_lines() -> None:
        for buffered_line in buffered_lines:
            print(buffered_line, end="", flush=True)
        buffered_lines.clear()

    with subprocess.Popen(
        command,
        cwd=corpus_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env=env,
    ) as proc:
        if proc.stdout is None:
            return summary

        for line in proc.stdout:
            clean_line = _strip_ansi(line).strip()
            if not in_summary:
                if not clean_line:
                    buffered_lines.append(line)
                    continue
                if clean_line == "Summary:":
                    in_summary = True
                    current_summary = {}
                    buffered_lines.append(line)
                    continue
                flush_buffered_lines()
                print(line, end="", flush=True)
                continue

            buffered_lines.append(line)
            match = SUMMARY_LINE_RE.fullmatch(clean_line)
            if match is None:
                in_summary = False
                current_summary = {}
                flush_buffered_lines()
                continue

            label = match.group(1)
            if label not in SUMMARY_LABELS:
                in_summary = False
                current_summary = {}
                flush_buffered_lines()
                continue

            current_summary[label] = int(match.group(2))
            if len(current_summary) == len(SUMMARY_FIELDS):
                summary.update(current_summary)
                in_summary = False
                buffered_lines.clear()

        if buffered_lines:
            flush_buffered_lines()

        proc.wait()

    return summary


def _add_summary(dst: dict[str, int], src: dict[str, int]) -> None:
    for label, _ in SUMMARY_FIELDS:
        dst[label] += src[label]


def _print_summary(summary: dict[str, int]) -> None:
    print("\nSummary:")
    for label, prefix in SUMMARY_FIELDS:
        print(f"{prefix}{summary[label]}")


def _copy_and_test(
    corpus_dir: Path, tc_root_dir: Path, translation_dir: Path, verbose: bool
) -> dict[str, int]:
    tc_dirs = sorted(path for path in tc_root_dir.glob("*/*") if path.is_dir())
    for tc_dir in tc_dirs:
        src_dir = translation_dir / tc_dir.relative_to(corpus_dir)
        dst_dir = tc_dir / "translated_rust"
        copy_translated_rust(src_dir, dst_dir)

    command = [
        "./deployment/scripts/github-actions/run_rust.sh",
        "--keep-going",
    ]
    if verbose:
        command.insert(2, "--verbose")
    return _stream_and_extract_summary(command, corpus_dir)


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
    corpus_dir_1 = project_dir / "Test-Corpus"
    tc_root_dir_1 = corpus_dir_1 / "Public-Tests"
    corpus_dir_2 = project_dir / "PUBLIC-Test-Corpus"
    tc_root_dir_2 = corpus_dir_2 / "Hidden-Tests"

    summary = _empty_summary()
    _add_summary(
        summary, _copy_and_test(corpus_dir_1, tc_root_dir_1, translation_dir, verbose)
    )
    _add_summary(
        summary, _copy_and_test(corpus_dir_2, tc_root_dir_2, translation_dir, verbose)
    )
    _print_summary(summary)


if __name__ == "__main__":
    main()
