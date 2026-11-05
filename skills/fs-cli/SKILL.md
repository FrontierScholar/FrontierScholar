---
name: fs-cli
description: Search ~1.01M computer-science papers and a curated research wiki with the `fs` command (FrontierScholar CLI). Use it whenever a task needs CS literature, even if FrontierScholar is not mentioned. This covers finding papers on a topic or before a date cut-off, building a related-work or reading list, finding papers similar to given ones, checking a paper's abstract, method, evaluation or first-version date, finding which papers use a benchmark or dataset, and finding the open problems and rising approaches of a research area. Prefer it over memory for paper ids, titles and dates.
license: Apache-2.0
compatibility: The `fs` command (`pip install frontier-scholar`, Python 3.8+, no other dependencies). It needs network access to https://frontier-scholar.com; no account or API key is needed for anonymous use.
metadata:
  version: "0.2.0"
  skill-author: FrontierScholar
  last-reviewed: "2026-11-05"
---

# FrontierScholar CLI

FrontierScholar indexes about 1.01M computer-science papers, with first versions up to 2026-10-09, and organises
them into a research wiki of about 21k areas: 20 domains, their topics, and the subtopics under those. Each subtopic has:
- an overview;
- pages for its research problems, method families, datasets/benchmarks/tools and theories;
- a list of its papers;
- a frontier page of open gaps and approach trends, mostly as of 2026-09 or 2026-10.

Most papers also have their own summary pages: problem, method and evaluation, plus mechanism when the paper has a
mechanism or theory part. `fs read <id>` lists which exist and gives the paper's **original abstract**.

`fs` is a read-only command-line client for all of this. Every answer comes from one fixed data snapshot (`fs --version`
prints its id). Answers are lookups and BM25 keyword
rankings over that snapshot: nothing is generated, and nothing comes from the web. That is why it is the reliable
source for paper ids and dates.

The wiki and paper pages are **summaries written from the papers, not the papers' own text**. Use them to understand
and to find evidence, then cite the paper ids they name. The only original text `fs` gives is a paper's abstract
(`fs read <id>`, field `abstract`, `"nature": "original"`). When a task asks for verbatim quotes, quote the abstract.
Do not quote summary sentences as if the paper said them.

## Setup

Check with `fs --version`. If `fs` is missing, install it with `pip install frontier-scholar` (Python 3.8+).

| Setting | Meaning |
|---|---|
| `FS_BASE` (optional) | Service URL; default `https://frontier-scholar.com`, the public endpoint |
| `FS_API_KEY` (optional) | An API key from the FrontierScholar team; never print it. Without one, the public endpoint answers with per-IP limits |

`fs --version` prints the CLI and API versions and the data snapshot, and `"key": "ok"` when calls are accepted. If it
says `"key": "missing or invalid FS_API_KEY"`, stop and report it: every other command will fail with `unauthorized`.

**Without a key** each call is smaller: `--topk` up to 20 and `--offset` up to 500, `fs read` up to 5 targets and
`--max-chars` up to 12,000, `fs related` up to 10 ids, `fs meta` up to 50 ids, and no `--grep`. A larger value is an
`invalid_argument` error naming the limit: lower it and follow `next` for more. Each IP also has a minute and a daily
allowance. When it is reached, `fs` waits and retries by itself (a line `fs: rate_limited: …; waiting N s` on stderr);
when the daily allowance is used up it stops at once with `rate_limited` and `retry_after`. Run calls one after
another rather than many in parallel.

## When to use

| Task | Start with | Then |
|---|---|---|
| Papers on a topic, a related-work or reading list, papers before a date | `fs search paper "…" --before D` (several phrasings) | `fs meta wiki <ids>` for where good hits live, then `fs read <subtopic> --papers --role all --before D` for each |
| Papers similar to given ones | `fs related <ids> --by-paper` | `fs read <id>` to check each candidate |
| What one paper does, in its own words | `fs read <id>` (abstract) | `fs read <id>/method`, `fs read <id>/evaluation` |
| How a method works, its strengths and limits | `fs search wiki pages "…" --facet methods` | `fs read <page> --sections`, then `--section NAME` |
| Which papers use a benchmark or dataset | `fs search wiki bench NAME` | the Resources page it lists, and the papers' `evaluation` pages |
| Open problems and rising approaches of an area | `fs search wiki frontier "…" --status open` | `fs read <subtopic>/frontier.md` |
| Where a topic sits in the tree | `fs select "…"` | `fs select "…" --path <best> --path <second>` (beam search) |
| Checking ids, titles and dates you will cite | `fs meta dates <ids> --before D` | |

## What is in it

```
<domain>/                                  20 domains, e.g. databases-and-data-management/
├── index.md                               domain overview
└── <topic>/                               e.g. storage-engines/
    ├── index.md                           topic overview
    └── <subtopic>/                        e.g. lsm-tree-storage-engines/
        ├── index.md                       subtopic overview
        ├── frontier.md                    open gaps and approach trends
        ├── Problems/                      research problems
        │   ├── index.md                   list of the folder's pages and entries
        │   ├── <cluster>.md               one page per problem; its papers under "## Source Papers", newer ones
        │   │                              under "## Additional Papers"
        │   └── other-problems-NN.md       short entries for problems supported by a single paper
        ├── Methods/                       method families (same layout: index.md, <cluster>.md, other-methods-NN.md)
        ├── Resources/                     datasets, benchmarks, tools (same layout)
        ├── Mechanisms/                    theories and mechanisms (same layout; not in every subtopic)
        └── (papers)                       listed with: fs read <subtopic> --papers

sources/<aa>/<bb>/<paper id>/            one folder per paper: Problem.md, Method.md, Evaluation.md, and
                                           Mechanism_Theory.md if the paper has a mechanism or theory part;
                                           read with fs read <id>/<facet>
```

- Each paper belongs to one **primary** subtopic and possibly several **secondary** ones. `fs read <id>` and
  `fs meta wiki <id>` give them.
- A `<cluster>.md` page groups the papers on one problem, method or resource; `fs related` uses these groups.
- **`## Additional Papers`** at the end of a page lists papers added after the page was written: they belong to it but
  are not yet summarised in its sections. They are often the newest work on the topic, so do not skip them because
  the text does not mention them; read them with `fs read <id>`.
- A subtopic overview ends with **`## Coverage and Frontier`**: how many papers it has, their date range, and the
  date of its frontier page.
- Dates are **first-version** dates (`YYYY-MM-DD`).

## Quick start

A literature search with a cut-off date. Keep the date on every step that returns papers:

```bash
fs --version                                        # versions, data snapshot, "key": "ok"
fs search paper "LSM tree compaction" --before 2024-10-01 --topk 20
fs search paper "log-structured merge key-value store write amplification" --before 2024-10-01 --topk 20
fs meta wiki 2202.04522 2307.16693                  # which subtopics the good hits live in
fs read databases-and-data-management/storage-engines/lsm-tree-storage-engines --papers --role all --before 2024-10-01 --topk 20
fs related 2202.04522 2307.16693 --by-paper --before 2024-10-01      # papers the wiki groups with these
fs read 2202.04522                                  # title, date, subtopics, original abstract, facet pages
fs read 2202.04522/method --sections                # then: --section "Core Idea"
fs meta dates 2202.04522 2307.16693 --before 2024-10-01              # finally: every id you will cite
```

## Commands

- `fs select ["QUERY"] [--path P]...`: list the next level of the tree, ranked by QUERY. Repeat `--path` to rank the
  children of several folders together (beam search). `[--topk N --offset N]`
- `fs search wiki [index|pages|frontier|bench] "QUERY"`: ranked wiki pages.
  - `index`: area overviews. `[--level domain|topic|subtopic --grep PHRASE --strict]`
  - `pages`: problem/method/resource/mechanism pages. `[--facet F --grep PHRASE --strict]`
  - `frontier`: gap and trend records. `[--gap-type T --status S --trend T --before D]`
  - `bench`: a benchmark or dataset by name. `[--before D]`
  - All kinds: `[--path P --topk N --offset N]`. An option of another kind is an error.
- `fs search paper "QUERY"`: ranked papers by title, abstract and dataset names.
  `[--path P --role primary|secondary|all --before D --after D --topk N --offset N]`
- `fs read TARGET...`: read a folder, a page, a paper (`<id>`: abstract and routes) or a paper's page (`<id>/<facet>`).
  - Page options: `[--sections --section NAME (repeatable) --offset N --max-chars N --json]`; folder option: `[--stat]`.
  - `--papers [--role R --before D --after D --query WORDS]`: one subtopic's papers, newest first, or ranked by WORDS.
  - `--grep PHRASE [--strict --grep-arg OPT --query WORDS]`: matching lines in the files under a folder.
- `fs related ID...`: papers that share a `<cluster>.md` page (or an `other-*` entry) with the given papers.
  `[--facet F --by-cluster | --by-paper --before D --after D --papers-per-cluster N --topk N --offset N]`
- `fs meta [wiki|dates] ID...`: for each id, the title and date (default), the subtopic routes (`wiki`), or the
  first-version date and a cut-off / lower-bound check (`dates`). `[--before D --after D]`

`fs COMMAND -h` shows each command's options, output fields and examples. Every parameter, default, limit and output
field is in [references/commands.md](references/commands.md).

## Limits and common mistakes

| Instead of | Do | Why |
|---|---|---|
| `fs paper <id>`, `fs nav`, `fs dates`, `fs grep` (old CLI) | `fs read <id>`, `fs select`, `fs meta dates`, `fs read <folder> --grep` | They do not exist in `fs`; the error names the replacement |
| `fs read <topic or page> --papers`, or several paths with `--papers` | One subtopic per call: `fs read <subtopic> --papers --role all` | `--papers` lists a single subtopic; the error names the subtopic of a page |
| A path copied from a page's text or front matter | A path from `fs` output, e.g. `fs read <id>` → `routes` | Paths inside page text can be stale; `fs` output paths always exist |
| `fs read <page or id> --grep X` | `fs read <page> --sections`, then `--section NAME` | `--grep` searches the files under a folder |
| `--max-chars 300` | `--max-chars` between 1,000 and 50,000 (default 12,000) | Values outside are clamped, with a `clamped` warning |
| `\| head`, `\| sed`, `2>/dev/null` on `fs` output | `--topk`, `--section`, `--max-chars`; read stderr | Truncation breaks the JSON and drops `next` and `warnings`; stderr holds the error and its `hint` |
| `—before`, `–topk` (typographic dashes) | `--before`, `--topk` | They are rejected; a pasted dash would otherwise drop the filter |

Facet names are case-insensitive, singular or plural: `--facet Methods`, `<id>/Evaluation`. `--before` also accepts a
timestamp (`2025-04-12T18:43:24+00:00`); only the day counts.

## How to find papers well

- **Keep what you have already seen.** Papers an agent met in its own `fs` output are often dropped later. Keep a
  candidate list of every paper that may fit. Drop a paper only when its title or abstract clearly fails a condition of
  the question. When unsure, keep it and rank it lower.
- **Relevant papers are spread over many subtopics.** A topic's papers often sit in many subtopics, not
  one. To see where your good hits live, run `fs meta wiki <ids>`. Then list each of those subtopics with
  `--papers --role all`. Use `--query WORDS` to rank a long list, or follow `next`: newest papers come first, so older
  ones are on later pages.
- **Ask in the papers' words, briefly, several times.** Searches are BM25 keyword searches: they match words, not
  meaning. Short queries in the field's terms work better than the question's long sentence. Repeat with synonyms,
  other word forms and spelled-out acronyms (`LLM`, `large language model`).
- **Use the neighbours.** `fs related <good ids> --by-paper` surfaces papers the wiki groups with your best hits.
- **Write scratch files in the working directory**, not `/tmp`: a stray `/tmp/types.py` breaks Python.

## Reading the output

- **Format.** `fs read` of a page (including `<id>/<facet>` and `frontier.md`) prints Markdown between `<<< … >>>`
  marker lines. The first line gives the page's size, the next line lists its sections,
  and the last line gives the command for the next chunk. `--json` gives the same page as JSON. Everything else (folders,
  papers, lists, `meta`, `--version`) is one JSON object per call.
- **Lists are paged.** List answers start with `total`, `returned`, `offset`, `has_more`.
  - When `has_more` is true there are more results than you have seen.
  - `next` holds the exact command for the next page. Run it, or raise `--topk` (max 100; 20 without a key), before you conclude a
    paper or page is not there.
- **`total` counts every match, not every relevant result.** Any document holding one of the query words matches, so
  `search paper` totals run into the hundreds of thousands. Relevance falls off down the ranking: page on while
  results stay on topic, not to the end.
- **Warnings: read the code.** `warnings` appears only when there is something to know about the answer. Its meaning
  depends on the code:
  - `grep_partial`: matches may be missing (a large folder is checked for about 12 seconds, most relevant pages first);
  - `section_not_found`: a `--section` name the page does not have (the page's other requested sections were printed);
  - `not_found` / `date_unknown`: some ids were not answered or not dated;
  - `filtered_out`: related papers exist, but none is within your dates;
  - `clamped`: an option was out of range and was adjusted;
  - `duplicates_removed`: only a note.

  [references/errors.md](references/errors.md#3-warnings) lists every code and what to do about it.
- **`not_found` for a paper means "not in this wiki", not "does not exist".** Do not drop a paper only because `fs`
  does not know it. If it comes from somewhere else you trust, keep it and say it was not checked in FrontierScholar.
- **Scores are relative.** Scores run from 0 to 100 within one answer; compare them only inside that answer.

## Dates and cut-offs

- **Filters are strict and work by day.** `--before D` keeps first-version dates earlier than D, `--after D` later than
  D. Papers with an unknown date are dropped.
- **Wiki pages cannot be filtered by date.** They summarise all papers in the snapshot, including papers after your
  cut-off. Use them to find leads; take the papers you cite from date-filtered commands.
- **`search wiki frontier --before`** keeps gaps first raised before D. It does not filter approaches, and it does not
  give the state of the field at that date.
- **Check the final list.** Before answering, run `fs meta dates <every id you cite> --before D` (`--after D` for a lower bound too; each item then has `within`), up to 200 ids per
  call, and drop ids whose `before` is not `true`, including those reported in `date_unknown`.

## Errors

Errors are one JSON line on stderr: `{"error": {"code", "message", "status", "field", "limit", "hint"}}`. Exit code 2
means fix the request (`invalid_argument`, `not_found`, `unauthorized`), 3 means the service is busy or unreachable
after retries, 1 is anything else. `hint` is usually the command to run next. Every code, HTTP status and warning, with
what to do, is in [references/errors.md](references/errors.md).

## Tips

- **Take ids and paths only from `fs` output.** Ids recalled from memory are often a different paper, and invented
  paths return `not_found`.
- **Search more than one area.** A topic is often split across domains. Search without `--path` first, then narrow.
- **Say what the answer rests on.** Name the data snapshot (`fs --version`). Mark claims that come from wiki summaries rather
  than the papers, especially exact numbers, SOTA claims and benchmark origins. Mention warnings that limit the answer.
- **Quote multi-word queries.** Options may come before or after the positional words.
