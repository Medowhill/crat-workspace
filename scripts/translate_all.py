#!/usr/bin/env python3

import sys
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from translate_with_c2rust import translate_with_c2rust


def translate_archive(args: tuple[Path, Path]) -> tuple[bool, Path]:
    archive_path, output_dir = args
    pdir_name = archive_path.parent.name
    ppdir_name = archive_path.parent.parent.name
    try:
        translate_with_c2rust(archive_path, output_dir / ppdir_name / pdir_name)
    except Exception:
        return False, archive_path
    return True, archive_path


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <bundles_dir> <output_dir>")
        sys.exit(1)

    bundles_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    archive_paths = sorted(bundles_dir.glob("*/*/*.tar.gz"))
    success_num = 0
    failure_tarballs: list[Path] = []
    with ProcessPoolExecutor() as executor:
        for success, archive_path in executor.map(
            translate_archive, ((path, output_dir) for path in archive_paths)
        ):
            if success:
                success_num += 1
            else:
                failure_tarballs.append(archive_path)

    print(f"Success: {success_num}")
    print(f"Failure: {len(failure_tarballs)}")
    print("Failure tarballs:")
    for archive_path in failure_tarballs:
        print(archive_path)


if __name__ == "__main__":
    main()
