# Changelog

The `fs` command-line client (PyPI: `frontier-scholar`) and the `fs-cli` agent skill are released separately; the skill's
version is in the `metadata` of `skills/fs-cli/SKILL.md`.

## CLI 1.2.4 and skill fs-cli 2.4.5 (2026-11-05)

- Wording only: the help text, the package description, the README and the skill call identifiers "paper ids" and say
  "first version" for dates; examples use `--topk 20`, which works with and without a key.

## Skill fs-cli 2.4.4 (2026-11-04)

- `license`, `compatibility` and `metadata` (version, author, last review) in the front matter of `SKILL.md`.
- "How to find papers well" reworded; the changelog moved here from the skill folder.

## CLI 1.2.3 (2026-11-02)

- Waits and retries by itself when the public endpoint is busy or rate limits are reached (`429`, `502`, `503`,
  `Retry-After`), and prints a line on stderr while it waits. A wait longer than 90 s (the daily allowance is used up)
  is reported at once instead of being slept through.

## Skill fs-cli 2.4.3 (2026-11-02)

- Without a key `fs` waits and retries by itself; prefer sequential calls.
- The `non_english_query` warning: the indexes are English, use English keywords.

## CLI 1.2.2 (2026-11-02)

- Uses the public endpoint `https://frontier-scholar.com` by default; `FS_API_KEY` is optional.

## Skill fs-cli 2.4.2 (2026-11-02)

- Setup for the public endpoint, the limits of calls without a key, quick start with `--topk 20`.

## Earlier

Skill `fs-cli` 2.4.0 and 2.4.1 (October 2026): the commands `select`, `search wiki`, `search paper`, `read`, `related`
and `meta`, the wiki layout, a worked literature search with a date cut-off, common mistakes, paged answers and warnings,
dates and cut-offs; bug fixes in 2.4.1 (`read --grep` returns a partial answer instead of timing out, `meta dates --after`,
clearer hints).
