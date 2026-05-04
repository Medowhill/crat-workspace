#!/usr/bin/env python3

import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from clang.cindex import Cursor, CursorKind, Index

T = TypeVar("T")


@dataclass(frozen=True)
class Artifact:
    name: str
    artifact_type: str
    sources: list[Path]
    link_args: list[str]


def _load_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)


def _dump_json(data, path: Path) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _unique(values: list[T]) -> list[T]:
    return list(dict.fromkeys(values))


def _get_target(build_dir: Path) -> list[Artifact]:
    cmake_reply_dir = build_dir / ".cmake" / "api" / "v1" / "reply"

    index_path = next(cmake_reply_dir.glob("index-*.json"))
    index = _load_json(index_path)

    codemodel_filename = index["reply"]["codemodel-v2"]["jsonFile"]
    codemodel_path = cmake_reply_dir / codemodel_filename
    codemodel = _load_json(codemodel_path)
    source_dir = Path(codemodel["paths"]["source"])

    target_entries = codemodel["configurations"][0]["targets"]
    targets = {
        entry["id"]: _load_json(cmake_reply_dir / entry["jsonFile"])
        for entry in target_entries
    }

    cache: dict[str, list[Path]] = {}

    def resolve_sources(target_id: str) -> list[Path]:
        if target_id in cache:
            return cache[target_id]
        target = targets[target_id]
        sources = [
            source_dir / source["path"]
            for source in target.get("sources", [])
            if "path" in source and Path(source["path"]).suffix == ".c"
        ]
        for dependency in target.get("dependencies", []):
            dependency_id = dependency["id"]
            if dependency_id in targets:
                sources.extend(resolve_sources(dependency_id))
        resolved = _unique(sources)
        cache[target_id] = resolved
        return resolved

    def resolve_link_args(target_id: str) -> list[str]:
        target = targets[target_id]
        fragments = [
            fragment["fragment"]
            for fragment in target.get("link", {}).get("commandFragments", [])
            if fragment.get("role") == "libraries"
            and fragment["fragment"].startswith("-l")
        ]
        return _unique(fragments)

    artifacts: list[Artifact] = []
    for target in targets.values():
        artifact_name = str(target["name"])
        artifact_type = str(target["type"])
        if "sphincs_core" in artifact_name:
            continue
        if artifact_type not in {"EXECUTABLE", "SHARED_LIBRARY"}:
            continue
        artifacts.append(
            Artifact(
                artifact_name,
                artifact_type,
                resolve_sources(target["id"]),
                resolve_link_args(target["id"]),
            )
        )
    return artifacts


def _add_link_args_to_build_rs(build_rs: Path, link_args: list[str]) -> None:
    if not link_args:
        return
    lines = build_rs.read_text(encoding="utf-8").splitlines(keepends=True)
    insert_at = next(
        index + 1 for index, line in enumerate(lines) if line.strip() == "fn main() {"
    )
    for link_arg in reversed(link_args):
        lines.insert(insert_at, f'    println!("cargo:rustc-link-arg={link_arg}");\n')
    build_rs.write_text("".join(lines), encoding="utf-8")


def _get_exposed_fns(
    compile_commands: list[dict[str, object]], source_dir: Path
) -> list[str]:
    def preserve_option(option: str) -> bool:
        return (
            option.startswith("-D")
            or option.startswith("-I")
            or option.startswith("-std=")
            or option.startswith("-m")
        )

    def command_args(command: dict[str, object]) -> list[str]:
        arguments = command.get("arguments")
        if isinstance(arguments, list):
            values = [str(value) for value in arguments[1:]]
        else:
            values = shlex.split(str(command["command"]))[1:]
        return [value for value in values if preserve_option(value)]

    parse_args = [
        "-x",
        "c-header",
        *_unique(
            [arg for command in compile_commands for arg in command_args(command)]
        ),
    ]
    names: set[str] = set()

    def visit_header_functions(node: Cursor) -> None:
        if node.kind == CursorKind.FUNCTION_DECL and node.location.file is not None:
            decl_file = Path(node.location.file.name).resolve()
            if decl_file.is_relative_to(source_dir) and decl_file.suffix == ".h":
                names.add(node.spelling)
        for child in node.get_children():
            visit_header_functions(child)

    index = Index.create()
    for header in sorted(source_dir.rglob("*.h")):
        translation_unit = index.parse(str(header), args=parse_args)
        visit_header_functions(translation_unit.cursor)
    return sorted(names)


def translate_with_c2rust(archive: Path, output_dir: Path) -> None:
    output_dir = output_dir.resolve()

    archive_name = archive.name.removesuffix(".tar.gz")
    workspace = output_dir / archive_name
    if workspace.exists():
        shutil.rmtree(workspace)

    source_dir = workspace / "c"
    source_dir.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        tar.extractall(source_dir)

    build_dir = source_dir / "build"
    query_dir = build_dir / ".cmake" / "api" / "v1" / "query" / "codemodel-v2"
    preset_flag = (
        ["--preset", "test"] if (source_dir / "CMakePresets.json").exists() else []
    )
    query_dir.mkdir(parents=True)
    command = [
        "cmake",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=1",
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
        "-G",
        "Ninja",
        *preset_flag,
    ]
    subprocess.run(command, check=True)

    commands_file = build_dir / "compile_commands.json"
    compile_commands = _load_json(commands_file)
    exposed_fns = _get_exposed_fns(compile_commands, source_dir)

    targets = _get_target(build_dir)
    sources = set([source for target in targets for source in target.sources])
    filtered_commands = [
        command
        for command in compile_commands
        if Path(str(command["file"])).resolve() in sources
    ]
    _dump_json(filtered_commands, commands_file)

    target_name = next(
        (target.name for target in targets if target.artifact_type == "EXECUTABLE"),
        targets[0].name,
    )
    dst_dir = workspace / "translated_rust" / target_name
    dst_dir.mkdir(parents=True)
    command = [
        "c2rust-transpile",
        "-o",
        str(dst_dir),
        "-e",
        str(commands_file),
    ]
    subprocess.run(command, check=True)

    link_args = sorted(set([arg for target in targets for arg in target.link_args]))
    _add_link_args_to_build_rs(dst_dir / "build.rs", link_args)

    command = [
        "cargo",
        "build",
    ]
    env = {
        **dict(os.environ),
        "RUSTFLAGS": "-Awarnings",
    }
    subprocess.run(command, cwd=dst_dir, env=env, check=True)


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <archive> <output_dir>")
        sys.exit(1)

    archive = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    translate_with_c2rust(archive, output_dir)


if __name__ == "__main__":
    main()
