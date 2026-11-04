# Errors, warnings and exit codes

How `fs` reports failure and partial success, and what to do about each case. SKILL.md links here.

## 1. Where to look

| Outcome | stdout | stderr | Exit code |
|---|---|---|---|
| Success | the answer (JSON, or Markdown for a page) | nothing | 0 |
| Partial success | the answer, with a `warnings` list | nothing | 0 |
| Failure | nothing | one JSON line: the error | 1, 2 or 3 |
| Bad command line (unknown option, missing value, value not among the choices, a command of the old CLI such as `fs paper`, a typographic dash such as `—before`) | nothing | an argparse usage message (not JSON); for old commands and dashes it names the correct form | 2 |

An error looks like this:

```
{"error": {"code": "not_found", "message": "no section 'Results'", "status": 404, "field": "section",
           "hint": "sections: Definition | Target Problems | Core Ideas | ..."}}
```

| Field | Present | Meaning |
|---|---|---|
| `code` | always | One of the codes below; branch on this, not on `message` |
| `message` | always | Human-readable description |
| `status` | when the service answered | HTTP status of the response |
| `field` | when one argument is at fault | Name of that argument (`path`, `targets`, `topk`, ...) |
| `limit` | when a bound was exceeded | The bound, e.g. `100` for `topk` |
| `hint` | when there is a next step | A command or a list to use next: section names, similar benchmark names, where to find folders |
| `retry_after` | with `rate_limited` | Seconds to wait |

## 2. Error codes

| HTTP status | `code` | Exit | When | What to do |
|---|---|---|---|---|
| 400 | `invalid_argument` | 2 | A value is malformed or out of range (`topk` 0 or > 100, a bad date, a bad path); too many items (more than 10 read targets or select paths, 50 related ids, 200 meta ids, more than one `--papers` subtopic); an option that does not apply (e.g. `--before` on `search wiki pages`, `--grep` on a page, `--papers` on a topic); an invalid grep pattern | Fix the argument named in `field`; respect `limit`; read `hint` |
| 401 | `unauthorized` | 2 | `FS_API_KEY` is not a valid key, or the service at `FS_BASE` needs a key and none is set (the public endpoint does not) | Stop and report it: the key is provided by the operator. `fs --version` shows `"key": "ok"` when calls are accepted |
| 404 | `not_found` | 2 | No such folder, page, node id, section, paper, paper facet page, benchmark name or command; for `related`, none of the ids is in the wiki | Follow `hint`; find real paths with `fs select` or `fs search`; never retry the same path unchanged |
| 429 | `rate_limited` | 3 | Without a key: the IP's minute or daily allowance, or the public daily total, is used up. With a key: more than 3,600 requests per minute, or more than 64 at the same time | The CLI has already retried 4 times with backoff. Wait `retry_after` seconds, then send fewer calls in parallel |
| 500 | `internal` | 1 | A server error | Retry once; if it repeats, report the command |
| 504 | `timeout` | 3 | The call took too long: in practice `read --grep` over a large folder (20 s limit) | Narrow the path, or use `search wiki pages --grep`, which checks the most relevant pages first |
| none | `unavailable` | 3 | The service cannot be reached (down, restarting, or the network path is broken) | The CLI has already retried. Try again later |
| other | `http_<status>` | 1 | A non-JSON error from something between the CLI and the service, e.g. `http_502` from a proxy | Try again later |

403 (`forbidden`) is reserved; the service does not return it.

The CLI retries `rate_limited`, `timeout` and `unavailable` 4 times, waiting about 0.5, 1, 2 and 4 seconds, before
it reports the error.

## 3. Warnings

A warning does not stop the answer: the command returns what it could, and lists what it could not, in
`warnings: [{"code", "message", "ids"?, ...}]`. Read the code; they do not all mean the same thing.

| `code` | Commands | Meaning | Effect on your answer |
|---|---|---|---|
| `not_found` | read (several targets), meta, related | These ids or targets do not exist in the wiki (listed in `ids`); the rest were answered | They are not in this wiki, which does not mean they do not exist: keep a paper you trust from elsewhere, and say FrontierScholar could not check it |
| `invalid_id` | meta, related | These inputs are not arXiv ids | Fix or drop them |
| `duplicates_removed` | meta | Repeated ids were answered once | Nothing is missing |
| `date_unknown` | meta | The first-version date of these papers is unknown | A date cut-off cannot be confirmed for them: leave them out or say so |
| `grep_partial` | search wiki --grep | Only the most relevant `checked` of `candidates` pages were checked; `total` counts only those | Matches may be missing: narrow `--path` or use a rarer phrase |
| `no_cluster` | related | These papers are not cited by any page of the requested `--facet` kinds | No related papers found for them; try other facets, or `fs search paper` |
| `clamped` | read | An option was outside its range and was adjusted (e.g. `max_chars` 300 → 1000) | Nothing is missing; use values in range |
| `filtered_out` | related | Related papers exist, but none is within `--before` / `--after` | Widen the dates, or report that none qualifies |
| `no_other_papers` | related | The pages citing the given papers cite no other paper | Try other `--facet` kinds, or `fs search paper` |
| `non_english_query` | select, search (public endpoint) | The query has words in another script (Chinese, ...); the indexes are English, so those words match next to nothing | Search again with English keywords |
| `origin_unverified` | search wiki bench | `earliest_paper` is the oldest paper in the wiki that lists the benchmark | Do not call it the paper that introduced the benchmark without checking |

`truncated` is not a warning but a field of list answers: the answer was cut by its size budget, by whole items.
`has_more` is then true, and `next` continues where it stopped.
