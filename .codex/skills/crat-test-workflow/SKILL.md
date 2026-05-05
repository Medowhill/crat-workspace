---
name: crat-test-workflow
description: Use when validating Crat pass fixes with Test-Corpus test cases and vectors, especially when running scripts/transform.py, scripts/transform_all.py, scripts/test.py, or scripts/test_all.py against a new transformed output directory, comparing against the existing transformed baseline, checking dependency passes, or running full regression transformations.
---

# Crat Test Workflow

## Ground Rules

- Work from the repository root.
- Never run `scripts/translate.py` or `scripts/translate_all.py`; translations are prepared separately.
- Treat `transformed/` as the baseline for the current/original Crat behavior. Write fix attempts to a new directory such as `transformed-pointer-fix` or `transformed-foo-fix`.
- Keep test outputs under a separate translation directory so comparisons against `transformed/` remain meaningful.
- Use `-h` or `--help` on the transform/test scripts when confirming current CLI usage.

## Test-Corpus Shape

Use test case paths under `Test-Corpus/<visibility>/<bundle>/<case>`, usually `Test-Corpus/Public-Tests/...`.

Each test case has:

- `test_case/`: the C project that was translated.
- `test_vectors/`: JSON vectors with expected behavior.
- `runner/`: present for library tests, where the Rust runner calls the translated library through FFI.

Executable vectors use fields such as `argv`, `stdin`, `stdout`, `stderr`, `rc`, and optional `has_ub`. Library vectors use `lib_state_in` and `lib_state_out` in addition to optional stdout/stderr/stdin fields. Vectors with `has_ub` are skipped by the automated runner.

## Pass Pipeline

Use these pass names with the transform scripts:

```text
expand -> extern -> preprocess -> outparam -> punning -> pointer -> io -> libc -> static -> simpl -> interface -> unsafe -> unexpand -> split -> bin
```

`--run-dependencies` runs the requested pass plus all earlier passes needed to reach it. Without `--run-dependencies`, the script expects the previous pass output to already exist in the same translation directory.

## Targeted Fix Workflow

When a specific pass mishandles a specific test case:

1. Identify the test case directory:

   ```bash
   TC=Test-Corpus/Public-Tests/<bundle>/<case>
   OUT=transformed-<pass>-fix
   PASS=<pass>
   ```

2. After fixing the pass, run the target pass with dependencies into the new output directory:

   ```bash
   python3 scripts/transform.py "$OUT" "$TC" "$PASS" --run-dependencies
   ```

3. Compare the new output against the old behavior in `transformed/`:

   ```bash
   diff -ru "transformed/$PASS/Public-Tests/<bundle>/<case>" "$OUT/$PASS/Public-Tests/<bundle>/<case>"
   ```

   Adjust the paths for the exact pass and test case. Prefer comparing the pass output where the bug is visible, not only the final `bin` output.

4. If fixing the same pass again, reuse the same output directory and omit `--run-dependencies` once earlier pass outputs already exist:

   ```bash
   python3 scripts/transform.py "$OUT" "$TC" "$PASS"
   ```

## Running Vectors

`scripts/test.py` tests a single case from the `bin` output:

```bash
python3 scripts/test.py <translation_dir> <tc_dir> [--verbose]
```

To produce `bin` for one case, run:

```bash
python3 scripts/transform.py "$OUT" "$TC" bin --run-dependencies
python3 scripts/test.py "$OUT" "$TC" --verbose
```

You may also run vectors against `transformed/` to learn whether the baseline already fails:

```bash
python3 scripts/test.py transformed "$TC" --verbose
```

`test.py` copies `<translation_dir>/bin/<visibility>/<bundle>/<case>` into `<tc_dir>/translated_rust`, then invokes the Test-Corpus Rust runner for that case.

## Regression Workflow

After the targeted case works:

1. Transform all public test cases through the fixed pass:

   ```bash
   python3 scripts/transform_all.py "$OUT" "$PASS" --run-dependencies
   ```

2. Transform all public test cases through `bin` to ensure later passes still work:

   ```bash
   python3 scripts/transform_all.py "$OUT" bin --run-dependencies
   ```

3. Run all test vectors:

   ```bash
   python3 scripts/test_all.py "$OUT"
   ```

   Add `--verbose` only when the extra output is needed:

   ```bash
   python3 scripts/test_all.py "$OUT" --verbose
   ```

4. If there are known existing failures, compare against the baseline:

   ```bash
   python3 scripts/test_all.py transformed
   ```

Use baseline results to distinguish new regressions from failures that predate the fix.
