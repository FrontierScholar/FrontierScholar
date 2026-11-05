<p align="center"><img src="https://raw.githubusercontent.com/FrontierScholar/FrontierScholar/main/assets/logo.png" alt="FrontierScholar" width="120"></p>

# FrontierScholar · 知沿学术

A research wiki of about 1.01M computer-science papers, built for coding agents. Papers are organised into
domains, topics and subtopics; each subtopic has pages on its research problems, method families, datasets and
benchmarks, and a frontier page of open gaps and rising approaches. Every claim points back to the papers it comes from.

This repository has the `fs` command-line client and the `fs-cli` agent skill.
Website and API documentation: <https://frontier-scholar.com>.

## Install

```bash
pip install frontier-scholar      # Python 3.8+, no dependencies
fs --version                      # CLI and API versions, data snapshot
```

`fs` talks to the public endpoint `https://frontier-scholar.com` and needs no key (see [Limits](#limits)).

## Agent skill

`skills/fs-cli/` tells a coding agent (Claude Code, Codex, Cursor, Gemini CLI, pi, ...) when and how to use `fs`:

```bash
npx skills add FrontierScholar/FrontierScholar
# or
gh skill install FrontierScholar/FrontierScholar
```

or copy `skills/fs-cli/` into your agent's skills folder. Then ask in plain language, e.g. *"Use fs: what are the open
problems of adaptive retrieval, and which approaches are rising?"*

## Commands

| Command | What it does |
|---|---|
| `fs select "QUERY"` | The next level of the tree (domains, topics, subtopics), ranked by a query |
| `fs search paper "QUERY"` | Papers ranked by title, abstract and dataset names; `--before` / `--after` dates |
| `fs search wiki [index\|pages\|frontier\|bench] "QUERY"` | Subtopic overviews, problem / method / resource pages, frontier gaps and trends, benchmarks |
| `fs read TARGET...` | A paper (original abstract, date, subtopics), a paper's pages, wiki pages, folders, a subtopic's papers |
| `fs related ID...` | Papers the wiki groups with the given ones |
| `fs meta [wiki\|dates] ID...` | Titles and dates, subtopics, first-version date checks |

```bash
fs select "adaptive retrieval" --topk 3
fs search paper "adaptive retrieval" --before 2025-01-01
fs search wiki frontier "adaptive retrieval" --status open
fs read 2601.04618
fs meta dates 2601.04618 2604.15621 --before 2026-06-01
```

Answers are JSON (wiki pages print as Markdown). They are lookups and keyword (BM25) rankings over one fixed data
snapshot: nothing is generated. Wiki pages are summaries written from the papers; the only original text is a paper's
abstract. `fs COMMAND -h` lists every option and output field.

From Python:

```python
from frontier_scholar import Client

r = Client().call("search/paper", {"query": "adaptive retrieval", "topk": 5})
for p in r["items"]:
    print(p["paper_id"], p["date"], p["title"])
```

The HTTP API is `POST https://frontier-scholar.com/api/v1/fs/<command>` with the arguments as JSON; see the
[documentation](https://frontier-scholar.com/docs/).

## Limits

Without a key, each IP gets 30 requests a minute and 300 a day, and calls are smaller (`--topk` up to 20, `read` up to
5 targets, `meta` up to 50 ids, no `--grep`); `curl https://frontier-scholar.com/api/v1/fs/quota` shows what is left.
With a key from the FrontierScholar team, set `FS_API_KEY` (in the environment, never in code); calls then use that
account's limits. When a limit is reached, `fs` waits and retries by itself. Queries should be in English: the index
is English text. `FS_BASE` points `fs` at another service.

## Layout

```
src/frontier_scholar/   the fs CLI and its client (standard library only)
skills/fs-cli/          the agent skill: SKILL.md, references/ (commands, errors)
tests/                  CLI tests
CHANGELOG.md            release notes of the CLI and the skill
```

## Contact

Questions, bug reports, and requests for a higher quota:
[philipgaq@mail.ustc.edu.cn](mailto:philipgaq@mail.ustc.edu.cn),
[chenjianlv@mail.ustc.edu.cn](mailto:chenjianlv@mail.ustc.edu.cn),
[liandefu@ustc.edu.cn](mailto:liandefu@ustc.edu.cn).

## Acknowledgements

We thank the [DeepXiv](https://github.com/DeepXiv/deepxiv_sdk) team for DeepXiv-SDK, their open-source agentic data
interface for scientific literature.

## License

Apache-2.0, see `LICENSE`.
