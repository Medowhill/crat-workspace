You are an expert in Rust.

# Project-Specific Instructions

* Crat is a tool to improve C2Rust's translation through several passes. Your
  goal is to improve Crat. Its source code is under `crat`.
* `scripts` contains scripts to run Crat on multiple input C programs.
* Never run `scripts/translate.py` and `scripts/translate_all.py`. They run
  C2Rust to translate C code bundled in each tarball, but this is needed only
  once after bundles are updated, which the user will handle.
* Never access anything inside `aws-translate`.
* Never access anything inside `bundles`.

# General Rules

## Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.
