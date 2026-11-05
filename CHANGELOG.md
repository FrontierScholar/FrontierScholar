# Changelog

The `fs` command-line client (PyPI: `frontier-scholar`) and the `fs-cli` agent skill share one version number; the
skill's is also in the `metadata` of `skills/fs-cli/SKILL.md`.

## 0.2.0 (2026-11-05)

First public release.

- `fs`: `select`, `search wiki`, `search paper`, `read`, `related` and `meta` against the public endpoint
  `https://frontier-scholar.com`, no key needed (`FS_API_KEY` raises the limits, `FS_BASE` points elsewhere).
- Waits and retries by itself when the endpoint is busy or a rate limit is reached, and says so on stderr; a wait
  longer than 90 s (the daily allowance is used up) is reported at once.
- `fs-cli` skill: when to use `fs`, the layout of the wiki, a worked literature search with a date cut-off, common
  mistakes, how to read paged answers and warnings, dates and cut-offs, and the limits of calls without a key.
