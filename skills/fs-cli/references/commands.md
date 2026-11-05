# fs command reference

Full parameters, defaults, limits, output fields, warnings and errors of every `fs` command. SKILL.md has the
overview; read the section of the command you are using when you need an option or a field it does not show.

Contents: 1. Conventions shared by all commands · 2. Commands (select, search wiki, search paper, read, related,
meta, --version) · 3. Errors (see errors.md)

## 1. Conventions shared by all commands

**Arguments**
- Quote multi-word queries.
- Options may come before, between or after the positional words.
- Unknown or abbreviated options are an error.
- Paths are relative to the wiki root: `/`-separated, no leading `/`, no `..`, at most 5 levels deep. The root is the empty path.
- Use paths only as they appear in `fs` output; never invent them.

**Paper ids.** All of these are accepted and normalised to the bare form without a version:
- `2402.03216`, `2402.03216v2`
- old-style `cs/0601001`

**Dates.** `--before D` keeps dates strictly earlier than `D`; `--after D` keeps dates strictly later than `D`. Papers with an unknown date are dropped by either filter. A timestamp (`2025-04-12T18:43:24+00:00`) is accepted and cut to its day.

**Output.** JSON on stdout (one object per call), except page reads, which print Markdown (see `fs read`).

List answers (`select`, `search`, `read --papers`, `read --grep`, `related`) have this shape:

```
{"total": int, "returned": int, "offset": int, "has_more": bool,
 "next": str,          # only when has_more: the exact command for the next page
 "truncated": {...},   # only when cut by the size budget: {"reason": "budget", "limit": int}
 "warnings": [...],    # only when the answer is partial
 "items": [...], "as_of": str}
```

Lookup answers (`read` of given targets, `meta`) have this shape:

```
{"total": int, "warnings": [...]?, "items": [...], "as_of": str}
```

How to read them:
- **`has_more: true` means you have not seen everything.** Run `next`, or raise `--topk`, before concluding that something is absent.
- Each warning is `{"code": str, "message": str, "ids": [str]?, ...}`. The codes mean different things (some only
  report merged duplicates); [errors.md](errors.md#3-warnings) lists each one and its effect.
- **Scores** are 0-100 within one answer, where the best match is 100. Do not compare them across calls.
- **Matching**: all searches are BM25 keyword searches. Words are lower-cased and split on non-alphanumerics; stop
  words and one-letter words are dropped; words are matched as written (no stemming, no synonyms). `total` counts
  every document holding at least one query word, so it is an upper bound, not a count of relevant results.
- **Ordering** is deterministic: ties are broken by path or id. Paging with `--offset` gives exactly the same items as one larger call.
- **Paging options** on every list command: `--topk N` (default 20, 1-100) and `--offset N` (default 0).
- **Size budget**: a list answer holds up to about 800 JSON characters per requested item (`--topk` × 800, between 8,000 and 64,000). Items with long fields, such as grep lines, can hit it before `--topk`; then `truncated` is set and `next` continues where the answer stopped.

## 2. Commands

### fs select

```
fs select ["QUERY"] [--path P]... [--topk N] [--offset N]
```

Lists the children of a folder.

```
fs select "robot task planning"                     # domains ranked for the query
fs select "robot task planning" --path robotics     # topics of robotics
fs select "LSM tree compaction" --path databases-and-data-management --path systems-and-architecture
```

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `QUERY` | string, ≤1000 chars | none | Rank the children by relevance. A folder's score is the mean BM25 score of its 10 best pages. |
| `--path P` | folder path, repeatable up to 10 | root | Folder(s) to list. With several, the children of all of them are ranked together (beam search over the best branches of the previous level). |
| `--topk`, `--offset` | int | 20, 0 | Paging |

**Order**
- With QUERY: by score.
- Without QUERY, at the root, a domain or a topic: by size (number of pages).
- Without QUERY, in a subtopic or facet folder: sub-folders first, then pages in name order.

**Items**
- Folder: `{"path": str, "kind": "domain"|"topic"|"subtopic"|"facet", "name": str, "counts": {"topics"?: int, "subtopics": int} (domain, topic) | {"papers": int, "primary": int} (subtopic) | {"pages": int} (facet), "score"?: float, "parent"?: str}`
- Page (inside a subtopic or facet folder): `{"path": str, "kind": "page", "name": str, "approx_tokens": int, "score"?: float, "parent"?: str}`
- `score` is present only with QUERY. `parent` is present only when several `--path` are given.

**Errors**
- `not_found` (field `path`): no such folder.
- `invalid_argument`: more than 10 paths, bad path, `topk`/`offset` out of range.

### fs search wiki

```
fs search wiki [index|pages|frontier|bench] "QUERY" [options]
```

The kind comes before the query and defaults to `index`. An option of another kind is an `invalid_argument` error (for example `--before` on `index` or `pages`: wiki pages have no date filter).

```
fs search wiki --level subtopic "adaptive retrieval"
fs search wiki pages "confidence gated retrieval" --facet methods --path information-retrieval --grep entropy
fs search wiki frontier --path information-retrieval --status open --gap-type evaluation
fs search wiki bench MIRACL --before 2025-01-01
```

| Parameter | Kinds | Type / values | Meaning |
|---|---|---|---|
| `QUERY` | all | string, ≤1000 chars | Required, except for `frontier`. For `bench`: the benchmark or dataset name. |
| `--path P` | all | folder path | Only under this domain / topic / subtopic |
| `--level L` | index | `domain`, `topic`, `subtopic` | Only overview pages of this level. Without it: all three levels. |
| `--facet F` | pages | `problems`, `methods`, `resources`, `mechanisms`; repeatable | Only these page kinds. Without it: all four. |
| `--grep "PHRASE"` | index, pages | string, ≤1024 chars | Keep only pages whose file contains the phrase (case, `-`, `_` and spaces normalized) |
| `--strict` | index, pages | flag | `--grep` as a plain case-sensitive ripgrep regex |
| `--gap-type T` | frontier | `data`, `evaluation`, `method`, `theory`, `efficiency`, `deployment`; repeatable | Gaps of these types |
| `--status S` | frontier | `open`, `partial` | Gaps with this status |
| `--trend T` | frontier | `rising`, `steady`, `no-recent` | Approaches with this trend |
| `--before D` | frontier, bench | date | frontier: gaps first raised before D (approaches are not filtered). bench: papers before D. |
| `--topk`, `--offset` | all | int | Paging |

**index / pages**: BM25 over page text (title, keywords, body).
- Item: `{"path": str, "title": str, "score": float, "level": "domain"|"topic"|"subtopic"|"page", "facet": "Problems"|"Methods"|"Resources"|"Mechanisms"|null, "subtopic": str|null, "aggregate": bool}`
- `aggregate: true` marks an `other-<group>-NN.md` page: a collection of short entries, each about one object supported by a single paper. Such a page is not about one topic; to cite it, read the entry that matched. `aggregate: false` is a full page about one object.
- With `--grep`, the files are checked most relevant first. If that stops early, a `grep_partial` warning gives `checked` and `candidates`, and `total` counts only the checked pages.

**frontier**: gap and approach records from the subtopics' `frontier.md`.
- With QUERY: ranked by BM25.
- Without QUERY: filtered only, listed by subtopic, then kind, then name. Give at least `--path` or a filter; the full list holds ~250k records.
- Gap item: `{"subtopic", "kind": "gap", "name", "as_of", "frontier_page": str (command), "types": [str], "status": str, "supporting_papers": int, "first": {"date", "paper_id"}, "latest": {"date", "paper_id"}, "quality_warnings"?: [str]}`
- Approach item: `{"subtopic", "kind": "approach", "name", "as_of", "frontier_page", "trend": str, "papers": [paper_id] (≤10), "quality_warnings"?: [str]}`
- `as_of` is the date of the frontier analysis. It only covers papers in the wiki.

**bench**: QUERY is a benchmark or dataset name, matched exactly after normalization.
- Items, in this order:
  - `{"kind": "resource_page", "path", "subtopic"}`: the Resources pages about it;
  - `{"kind": "earliest_paper"|"using_paper", "paper_id", "title", "date", "subtopic"}`: the papers whose profile lists it, oldest first.
- `earliest_paper` is the oldest one in the wiki, **not necessarily the paper that introduced the benchmark**. This is always stated by an `origin_unverified` warning.
- An unknown name is a `not_found` error; its `hint` lists similar names.

**Errors**
- `invalid_argument`: missing QUERY, a value outside the listed choices, `topk` out of range.
- `not_found`: bad `--path`, or an unknown benchmark name.

### fs search paper

```
fs search paper "QUERY" [--path P] [--role R] [--before D] [--after D] [--topk N] [--offset N]
```

BM25 over paper title (counted twice), abstract and dataset names.

```
fs search paper "LSM tree compaction" --before 2024-10-01 --topk 20
fs search paper "adaptive retrieval" --path information-retrieval --role all --after 2023-01-01
```

| Parameter | Type / values | Default | Meaning |
|---|---|---|---|
| `QUERY` | string, ≤1000 chars | required | Search words |
| `--path P` | folder path | none | Only papers routed to subtopics under P |
| `--role R` | `primary`, `secondary`, `all` | `primary` | With `--path`: which routes count |
| `--before D`, `--after D` | date | none | First-version date bounds |
| `--topk`, `--offset` | int | 20, 0 | Paging |

**Item**: `{"paper_id": str, "title": str, "date": str|null, "score": float, "subtopic": str|null (primary), "secondary": [str] (≤5)}`

**Errors**: `invalid_argument` (missing QUERY, bad date, bad role); `not_found` (bad `--path`).

### fs read

```
fs read TARGET... [options]
```

**TARGET** (up to 10 per call) can be:
- a folder path, or a page path (`.md`);
- a node id: `page:<hex>` (wiki pages) or `wiki:<path>`;
- a paper id;
- `<paper id>/<facet>`, where facet is one of `overview`, `problem`, `method`, `evaluation`, `mechanism` (case-insensitive; plurals accepted). Most papers have
  `problem`, `method` and `evaluation`; `mechanism` exists when the paper has a mechanism or theory part; `overview`
  is rare. `fs read <id>` lists the ones that exist.
  Old-style ids work the same way (`cs/0407046`, `cs/0407046/method`).

With several targets, a target that fails becomes a `not_found` warning; with one target it is an error.

```
fs read information-retrieval/agentic-search/adaptive-retrieval --stat
fs read information-retrieval/agentic-search/adaptive-retrieval --papers --role all --before 2024-10-01 --topk 20
fs read information-retrieval/agentic-search/adaptive-retrieval/Methods/confidence-gated-retrieval.md --sections
fs read information-retrieval/agentic-search/adaptive-retrieval/Methods/confidence-gated-retrieval.md --section "Core Idea"
fs read 2202.04522 2307.16693/method --max-chars 3000
fs read information-retrieval/agentic-search --grep "confidence gated" --query "retrieval gating"
```

**What each target returns**

- **Folder**
  ```
  {"kind": "dir", "path", "level", "title",
   "children": [{"path", "kind": "topic"|"subtopic"|"facet"|"page"|"frontier", "title", "approx_tokens"?, "aggregate"?}],
   "papers"?: {"total", "primary", "secondary", "latest": date, "list_with": str},
   "stat"?: {...}}
  ```
  - `papers` is present for subtopics.
  - `--stat` adds `stat`: `{"keywords": [str], "scope": str, "counts": {...}, "pages": int}`. It is computed offline; no model is involved.
- **Page** (also a `frontier.md`): printed as Markdown between marker lines.
  - The first line is `<<< title | path | node_id=... | chars a-b of n | wiki synthesis ... >>>`.
  - The first chunk also has a `Sections: ...` line.
  - The last line is either the command for the next chunk or `<<< end of page >>>`.
  - With `--json`: `{"kind": "page", "path", "node_id", "title", "nature": "synthesis", "chars_total": int, "range": [start, end], "sections": [str]|null, "next_offset": int|null, "content": str}`
- **paper id**: `{"kind": "paper", "paper_id", "title", "date", "facets": [str], "routes": [{"subtopic", "role"}], "abstract": {"text", "nature": "original", "source"} | null}`. `facets` lists the facet pages that exist for this paper; `abstract` is the paper's own abstract (the only original text `fs` gives), `null` when unknown.
- **`<id>/<facet>`**: the paper's synthesis page, with the same output as a page. In JSON, `kind` is `paper_facet` and there are extra `paper_id` and `facet` fields.

**Page options**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `--sections` | flag | | List the page's `##`/`###` headings without the text: `{"kind": "sections", "path", "title", "chars_total", "sections": [{"heading", "offset", "chars"}]}` |
| `--section "NAME"` | string, repeatable | | Read the section whose heading equals or contains NAME (case-insensitive). If none matches, the error `hint` lists all headings. |
| `--offset N` | int | 0 | Start the chunk at character N |
| `--max-chars N` | int, 1000-50000 | 12000 | Chunk size; a value outside the range is clamped, with a `clamped` warning |
| `--json` | flag | | JSON instead of Markdown |

**Subtopic paper list: `--papers`** (TARGET must be a subtopic)

| Parameter | Type / values | Default | Meaning |
|---|---|---|---|
| `--role R` | `primary`, `secondary`, `all` | `primary` | Which members |
| `--before D`, `--after D` | date | | First-version date bounds |
| `--query WORDS` | string | | Rank the papers by BM25 relevance of title + abstract to WORDS (each item gets a `score`) |
| `--topk`, `--offset` | int | 20, 0 | Paging |

- Items: `{"paper_id", "title", "date", "role", "score"?}`, newest first (or by `score` with `--query`).
- One subtopic per call: several TARGETs are an `invalid_argument` error. A TARGET that does not exist is `not_found`; a topic, facet folder or page is `invalid_argument`, and the `hint` names its subtopic when there is one.

**Grep under a path: `--grep "PHRASE"`** (uses the first TARGET as the folder; a page, a paper id or `<id>/<facet>` is an `invalid_argument` error: use `--sections` / `--section` in one page)

| Parameter | Type | Meaning |
|---|---|---|
| `--grep "PHRASE"` | string, ≤1024 chars | Matching lines in the `.md` files under the path. Case, `-`, `_` and spaces are normalized. |
| `--strict` | flag | Plain ripgrep regex (case-sensitive) |
| `--grep-arg=OPT` | repeatable; with `--strict` | Extra ripgrep option, e.g. `--grep-arg=-w` |
| `--query "WORDS"` | string | Order the files by BM25 relevance to WORDS. Default order: path. |
| `--topk`, `--offset` | int | Paging over files |

- Items: `{"path", "matches": int, "lines": [{"line_no": int, "line": str}] (≤5)}`
- A large folder is narrowed with the page index and checked, most relevant pages first, for about 12 s; the answer is then partial with a `grep_partial` warning instead of failing. Use a narrower folder or a rarer phrase for everything.

**Errors**
- `not_found`: no such path, node id, paper, facet page or section.
- `invalid_argument`: more than 10 targets, `--papers` on a non-subtopic, `--max-chars` or `--offset` out of range, a bad grep pattern.

### fs related

```
fs related ID... [--facet F]... [--by-cluster | --by-paper] [--before D] [--after D] [--papers-per-cluster N] [--topk N] [--offset N]
```

Finds papers that the wiki groups with the given papers.

A **cluster** is the set of papers of one full page (its `## Source Papers`), or of one entry of an `other-<group>-NN.md` page. The lookup works in two steps:
1. the given papers → the pages / entries that cite them;
2. those pages / entries → all their papers.

The given papers themselves are not returned. Clusters that hold only given papers are skipped.

```
fs related 2202.04522 2307.16693
fs related 2202.04522 2307.16693 --by-paper --before 2024-10-01 --topk 20
fs related 2210.03629 --facet methods --papers-per-cluster 5
```

| Parameter | Type / values | Default | Meaning |
|---|---|---|---|
| `ID...` | 1-50 paper ids | required | The papers to start from |
| `--facet F` | `methods`, `resources`, `problems`, `mechanisms`; repeatable | `methods`, `resources` | Page kinds whose clusters count |
| `--by-cluster` | flag | default | One item per cluster |
| `--by-paper` | flag | | One merged, ranked list of papers |
| `--before D`, `--after D` | date | | Bounds on the papers returned (not on the given ones) |
| `--papers-per-cluster N` | int, 0-100 | 20 | `--by-cluster`: how many of each cluster's other papers to list in `papers` (newest first). `size` always gives the full count; with `0` you get only the clusters. |
| `--topk`, `--offset` | int | 20, 0 | Paging |

**Items**
- `--by-cluster`, ordered by most given papers first, then the smallest cluster:
  ```
  {"page": str, "facet": str, "subtopic": str, "title": str, "entry": str|null (anchor in an other-* page),
   "seeds": [paper_id] (given papers in it), "size": int (other papers),
   "papers": [{"paper_id", "title", "date"}] (newest first, ≤ --papers-per-cluster)}
  ```
- `--by-paper`, ordered by the number of shared clusters, then by smaller clusters:
  ```
  {"paper_id", "title", "date", "shared": int, "via": [{"page", "entry", "title"}] (≤3)}
  ```

**Warnings**: `invalid_id`, `not_found` (not in the wiki), `no_cluster`; when the answer is empty, `filtered_out` (related papers exist but none is within the date bounds) or `no_other_papers` (the citing pages cite no other paper).

**Errors**: `not_found` when none of the ids is in the wiki; `invalid_argument` for more than 50 ids or a bad facet.

### fs meta

```
fs meta ID...                     title and date
fs meta wiki ID...                subtopic routes
fs meta dates ID... [--before D] [--after D]  first-version dates, with cut-off / lower-bound checks and `within`
```

Up to 200 ids per call. Items keep the input order; duplicates are answered once.

```
fs meta 2202.04522 2307.16693
fs meta wiki 2202.04522
fs meta dates 2202.04522 2307.16693 --before 2024-10-01
fs meta dates 2202.04522 2307.16693 --after 2022-01-01 --before 2024-10-01
```

**Items**
- default: `{"paper_id", "title", "date"}`
- `wiki`: `{"paper_id", "primary": str|null, "secondary": [str]}`
- `dates`: `{"paper_id", "date", "before"?: bool}`. `before` is present only with `--before` and when the date is known.

**Warnings**: `not_found` (id not in the wiki; no item), `invalid_id`, `duplicates_removed`, `date_unknown`.

**Errors**: `invalid_argument` for no ids, more than 200 ids, or a bad date.

### fs --version

Returns `{"cli": str, "status": "ok", "api": str, "as_of": str, "pages": int, "papers": int, "key": str}`.
- `key` is `"ok"` when calls are accepted (checked with one small call; on the public endpoint this works without a key), `"missing or invalid FS_API_KEY"` otherwise. The health part itself needs no key.
- If the service is down: `{"cli": str, "server": "unreachable: ..."}`.

## 3. Errors

Error codes, HTTP statuses, exit codes and warnings are in [errors.md](errors.md).
