#!/usr/bin/env python3

import sys
from collections import Counter, defaultdict
from pathlib import Path

from utils import print_help, should_show_help

groups = ["B01", "B02", "P00", "P01"]
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
features = [
    "transmute",
    "union",
    "deref",
    "offset",
    "alloc",
    "std",
    "lib",
    "static",
    "fnptr",
]


def normalize_feature(name: str) -> str:
    if name == "DerefOfRawPointer":
        return "deref"
    if name == "UseOfMutableStatic":
        return "static"
    if name == "AccessToUnionField":
        return "union"
    if name == "CallToUnsafeFunction(None)":
        return "fnptr"
    if name == "transmute":
        return "transmute"
    if name in {"offset", "offset_from"}:
        return "offset"
    if name in {"calloc", "free", "malloc", "realloc"}:
        return "alloc"
    if name in {
        "as_mut",
        "as_ref",
        "from_ptr",
        "from_raw_parts",
        "from_raw_parts_mut",
    }:
        return "std"
    return "lib"


def group_name(path: Path) -> str | None:
    name = path.name
    for group in groups:
        if name.startswith(group):
            return group
    return None


def short_header(name: str) -> str:
    return name[:7] if len(name) > 7 else name


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
    counts: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for unsafe_path in sorted(translation_dir.glob("*-post/*/*/*/unsafe.txt")):
        rel_parts = unsafe_path.relative_to(translation_dir).parts
        plugin = rel_parts[0].removesuffix("-post")
        group = group_name(Path(rel_parts[2]))
        if plugin not in plugins or group is None:
            continue

        counts[(group, plugin)].update(
            normalize_feature(name)
            for name in unsafe_path.read_text(encoding="utf-8").splitlines()
            if name
        )

    for i, group in enumerate(groups):
        if i != 0:
            print()
        print(group)
        print("\t".join(["plugin", *(short_header(feature) for feature in features)]))
        for plugin in plugins:
            row = counts[(group, plugin)]
            print(
                "\t".join(
                    [short_header(plugin), *(str(row[feature]) for feature in features)]
                )
            )


if __name__ == "__main__":
    main()
