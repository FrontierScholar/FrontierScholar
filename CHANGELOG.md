# Changelog

Two things are versioned here, each with its own number:

- the `fs` command-line client, published on PyPI as `frontier-scholar` (`fs --version` prints it);
- the `fs-cli` agent skill, in `skills/fs-cli/` (its version is in the `metadata` of `SKILL.md`).

## fs 1.3.1 (2026-11-05)

- Package metadata only: one more maintainer contact. The commands are those of 1.3.0.

## fs 1.3.0 (2026-11-05) and skill fs-cli 0.1.0

First release from this repository.

- `fs`: `select`, `search wiki`, `search paper`, `read`, `related` and `meta` against the public endpoint
  `https://frontier-scholar.com`, no key needed (`FS_API_KEY` raises the limits, `FS_BASE` points elsewhere).
- Waits and retries by itself when the endpoint is busy or a rate limit is reached, and says so on stderr; a wait
  longer than 90 s (the daily allowance is used up) is reported at once.
- Package metadata: maintainers and project links; wording of the help text. The commands themselves are unchanged.
- Skill `fs-cli` 0.1.0: when to use `fs`, the layout of the wiki, a worked literature search with a date cut-off,
  common mistakes, how to read paged answers and warnings, dates and cut-offs, and the limits of calls without a key.
  It needs `fs` 1.3 or later.
