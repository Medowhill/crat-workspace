import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

HELP_ARGS = {"-h", "--help"}


def show_progress(done: int, total: int) -> None:
    print(f"\r{done}/{total}", end="", flush=True)


def should_show_help(argv: list[str]) -> bool:
    return any(arg in HELP_ARGS for arg in argv[1:]) or (
        len(argv) > 1 and argv[1] == "help"
    )


def print_help(usage: str, *details: str) -> None:
    print(usage)
    for detail in details:
        print(detail)


def load_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)


def dump_json(data, path: Path) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def load_toml(path: Path):
    import toml

    with open(path, "r") as f:
        return toml.load(f)


def dump_toml(data, path: Path) -> None:
    import toml

    with open(path, "w") as f:
        toml.dump(data, f)


def unique(values: list[T]) -> list[T]:
    return list(dict.fromkeys(values))


def run(command: list[str], **kwargs) -> None:
    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            **kwargs,
        )
    except subprocess.CalledProcessError as err:
        print(f"Command failed with exit code {err.returncode}: {shlex.join(command)}")
        if err.stdout:
            print("stdout:")
            print(err.stdout, end="" if err.stdout.endswith("\n") else "\n")
        if err.stderr:
            print("stderr:", file=sys.stderr)
            print(
                err.stderr,
                end="" if err.stderr.endswith("\n") else "\n",
                file=sys.stderr,
            )
        raise
