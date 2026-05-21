#!/usr/bin/env python3

import shutil
import sys
import tarfile
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from translate import translate
from transform import transform
from utils import (
    dump_json,
    get_name_without_suffix,
    load_json,
    should_show_help,
    show_progress,
    print_help,
    run,
    ParamVal,
    Parameters,
)


def _extract_config_vars(archive_file: Path) -> dict[str, list[ParamVal]] | None:
    temp_dir = Path(
        tempfile.mkdtemp(prefix="tmp-", dir=tempfile.gettempdir())
    ).resolve()
    with tarfile.open(archive_file) as tar:
        tar.extractall(temp_dir)
    test_case_dir = temp_dir / "test_case"
    if not test_case_dir.exists():
        test_case_dir = temp_dir
    config_file = test_case_dir / "configuration.json"
    config_vars = (
        load_json(config_file)["configurable_variables"]
        if config_file.exists()
        else None
    )
    shutil.rmtree(temp_dir)
    return config_vars


def _build_parameter_sets(config_vars: dict[str, list[ParamVal]]) -> list[Parameters]:
    parameter_sets: list[Parameters] = [[]]
    for name, values in config_vars.items():
        parameter_sets = [
            [*current, (name, value)] for current in parameter_sets for value in values
        ]
    return parameter_sets


def _translate_and_transform_with_parameters(
    arg: tuple[Path, Path, Parameters],
) -> tuple[bool, Parameters, Path]:
    workspace, archive_file, parameters = arg
    tc_name = get_name_without_suffix(archive_file)
    name = "_".join([str(value) for _, value in parameters])
    final_dir = workspace / name / "bin" / tc_name
    try:
        translate(archive_file, workspace / name / "c2rust" / tc_name, parameters)
        transform(workspace / name, tc_name)
        return (True, parameters, final_dir)
    except:
        return (False, parameters, final_dir)


def _combine_logs(log_paths: list[Path], destination: Path) -> None:
    with destination.open("a", encoding="utf-8") as out:
        for path in log_paths:
            if path.exists():
                content = path.read_text(encoding="utf-8")
                out.write(content)
                if content and not content.endswith("\n"):
                    out.write("\n")
            out.write("\n")


def orchestrate(archive_file: Path) -> None:
    workspace = Path(
        # tempfile.mkdtemp(prefix="tmp-", dir=tempfile.gettempdir())
        tempfile.mkdtemp(prefix="tmp-", dir=".")
    ).resolve()

    try:
        config_vars = _extract_config_vars(archive_file)
        if config_vars:
            parameter_sets = _build_parameter_sets(config_vars)
            args = [
                (workspace, archive_file, parameters) for parameters in parameter_sets
            ]
            total_num = len(args)
            successes: list[tuple[Parameters, Path]] = []
            failures: list[Parameters] = []
            show_progress(0, total_num)
            with ProcessPoolExecutor() as executor:
                for done_num, (success, parameters, final_dir) in enumerate(
                    executor.map(_translate_and_transform_with_parameters, args),
                    start=1,
                ):
                    if success:
                        successes.append((parameters, final_dir))
                    else:
                        failures.append(parameters)
                    show_progress(done_num, total_num)
            print()

            if failures:
                print("Failure parameters:")
                for parameters in failures:
                    print(parameters)
                raise

            json_file = workspace / f"translations.json"
            dump_json(
                [
                    {
                        "dir": str(final_dir),
                        **{name: value for name, value in parameters},
                    }
                    for parameters, final_dir in successes
                ],
                json_file,
            )

            stdout_logs = [final_dir / "stdout.log" for _, final_dir in successes]
            stderr_logs = [final_dir / "stderr.log" for _, final_dir in successes]
            stdout_log = workspace / "stdout.log"
            stderr_log = workspace / "stderr.log"
            _combine_logs(stdout_logs, stdout_log)
            _combine_logs(stderr_logs, stderr_log)

            command = ["crat-merge", str(json_file), str(workspace)]
            run(command, stdout_log=stdout_log, stderr_log=stderr_log)
        else:
            pass

    finally:
        pass
        # shutil.rmtree(workspace)


def _usage() -> str:
    return f"Usage: {sys.argv[0]} <test_case_tarball>"


def main() -> None:
    if should_show_help(sys.argv):
        print_help(_usage())
        sys.exit(0)

    if len(sys.argv) != 2:
        print_help(_usage())
        sys.exit(1)

    archive_file = Path(sys.argv[1])
    orchestrate(archive_file)


if __name__ == "__main__":
    main()
