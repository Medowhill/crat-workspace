---
name: crat-test-workflow
description: Use when validating Crat pass fixes with Test-Corpus/Public-Tests or PUBLIC-Test-Corpus/Hidden-Tests cases and vectors, especially when running scripts/transform.py, scripts/transform_all.py, scripts/test.py, or scripts/test_all.py against a new transformed output directory, comparing against the existing transformed baseline, checking unsafe feature occurrence counts, checking dependency passes, or running full regression transformations.
---

# Crat Test Workflow

## Ground Rules

- Work from the repository root.
- Never run `scripts/translate.py` or `scripts/translate_all.py`; translations are prepared separately.
- Run every invocation of `scripts/transform.py`, `scripts/transform_all.py`, `scripts/test.py`, and `scripts/test_all.py` **outside the sandbox** by setting `sandbox_permissions` to `require_escalated` in `exec_command`. Do this proactively instead of trying these scripts in the sandbox first.
- Treat `transformed/` as the baseline for the current/original Crat behavior. Write fix attempts to a new directory such as `transformed-pointer-fix` or `transformed-foo-fix`.
- Keep test outputs under a separate translation directory so comparisons against `transformed/` remain meaningful.
- Use `-h` or `--help` on the transform/test scripts when confirming current CLI usage.
- `VERBOSE=1` makes the scripts print command stdout/stderr even on success. It is usually unnecessary, but useful with Crat stderr diagnostics such as `VERBOSE=1 CRAT_POINTER_DECISION_DIAGNOSTICS=raw ./scripts/transform.py ...`.
- `scripts/find_unsafe.py` and `scripts/summarize_unsafe.py` inspect the current `Test-Corpus/Public-Tests/*/*/translated_rust` and `PUBLIC-Test-Corpus/Hidden-Tests/*/*/translated_rust` trees, so run them immediately after the `scripts/test_all.py` invocation whose output should be measured.

## Corpus Shape

Use public test case paths under `Test-Corpus/Public-Tests/<bundle>/<case>`.
Use hidden test case paths under `PUBLIC-Test-Corpus/Hidden-Tests/<bundle>/<case>`.

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

   For hidden cases, use `TC=PUBLIC-Test-Corpus/Hidden-Tests/<bundle>/<case>`.

2. After fixing the pass, run the target pass with dependencies into the new output directory:

   ```bash
   python3 scripts/transform.py "$OUT" "$TC" "$PASS" --run-dependencies
   ```

3. Compare the new output against the old behavior in `transformed/`:

   ```bash
   diff -ru "transformed/$PASS/Public-Tests/<bundle>/<case>" "$OUT/$PASS/Public-Tests/<bundle>/<case>"
   ```

   Adjust the paths for the exact pass, visibility (`Public-Tests` or `Hidden-Tests`), and test case. Prefer comparing the pass output where the bug is visible, not only the final `bin` output.

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

`test.py` copies `<translation_dir>/bin/<visibility>/<bundle>/<case>` into `<tc_dir>/translated_rust`, then invokes that corpus's Rust runner for the case.

Do not run `deployment/scripts/github-actions/run_rust.sh` directly from either corpus root to recover hidden stderr or exit-code details. `scripts/test.py` and `scripts/test_all.py` intentionally suppress that runner stderr and exit code because the hidden details are not useful for Crat validation. Use these scripts instead: they report failed vectors and summaries, and `--verbose` shows expected-versus-actual differences.

## Regression Workflow

After the targeted case works:

1. Transform all public and hidden test cases through the fixed pass:

   ```bash
   python3 scripts/transform_all.py "$OUT" "$PASS" --run-dependencies
   ```

2. Transform all public and hidden test cases through `bin` to ensure later passes still work:

   ```bash
   python3 scripts/transform_all.py "$OUT" bin --run-dependencies
   ```

3. Run all test vectors:

   ```bash
   python3 scripts/test_all.py "$OUT"
   ```

4. Count unsafe feature occurrences in the tested translation:

   ```bash
   python3 scripts/find_unsafe.py
   python3 scripts/summarize_unsafe.py
   ```

   `find_unsafe.py` writes one `unsafe.txt` under each current `translated_rust` directory. `summarize_unsafe.py` prints the total occurrence count and per-feature counts from those files. Record this summary before running another `test_all.py`, because the next test run replaces the `translated_rust` trees being inspected.

5. If there are known existing failures or unsafe counts need a baseline, compare against the baseline:

   ```bash
   python3 scripts/test_all.py transformed
   python3 scripts/find_unsafe.py
   python3 scripts/summarize_unsafe.py
   ```

Use baseline results to distinguish new regressions from failures that predate the fix. Treat an increase in total unsafe occurrences or any per-feature unsafe occurrence count as a regression unless the change is expected and explained.
