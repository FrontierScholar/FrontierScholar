"""fs - FrontierScholar: search ~1.01M computer-science arXiv papers and read a research wiki.

The wiki is a tree of research areas, domain / topic / subtopic (e.g. information-retrieval / agentic-search /
adaptive-retrieval). Each subtopic has an overview (index.md), Problems/, Methods/, Resources/ and Mechanisms/ pages,
a paper list, and frontier.md (open gaps, approach trends). Wiki and per-paper pages are syntheses written from the
papers, not the papers' own text. Read-only: no model calls, no web access; every answer states its data snapshot
("as_of").

Usage:
  fs COMMAND [ARGS] [OPTIONS]
  fs COMMAND -h                 options, output fields and examples of one command

Commands:
  select     list the next level of the tree, ranked by a query; several folders at once (beam search)
  search     search wiki        ranked wiki pages: index (overviews), pages, frontier (gaps/trends), bench (by name)
             search paper       ranked papers (title, abstract, dataset names), with date and area filters
  read       a folder, page, paper or paper facet page; a subtopic's papers (--papers); grep under a path
  related    papers that share a Methods / Resources page with given papers
  meta       title and date, subtopic routes (wiki), or a date cut-off check (dates) for paper ids

Examples:
  fs select "retrieval augmented generation"                     which domains cover a topic
  fs search wiki --level subtopic "adaptive retrieval"            which subtopics cover it
  fs search paper "LSM tree compaction" --before 2024-10-01 --topk 50
  fs read information-retrieval/agentic-search/adaptive-retrieval --papers --role all
  fs read 2202.04522/method --section "Core Idea"
  fs related 2202.04522 2307.16693 --by-paper
  fs meta dates 2202.04522 2307.16693 --before 2024-10-01

Output:
  JSON, one object per call; a page read prints Markdown between <<< ... >>> marker lines. List answers start with
  total / returned / offset / has_more; "next" is the exact command for the next page. has_more=true means you
  have not seen everything. "warnings" (only when present) mean a partial answer. Scores are 0-100 within one answer.

Environment:
  FS_API_KEY   API key (optional: without one, the public endpoint answers with per-IP limits)
  FS_BASE      service URL (default https://frontier-scholar.com)

Exit codes:
  0 success (check "warnings")   2 bad argument / not found / invalid key   3 rate limited, timed out or unreachable
  after retries   1 other errors. Errors are one JSON line on stderr: {"error": {code, message, field, limit, hint}}.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional, Sequence

from . import __version__
from .client import Client, FsError

WIKI_KINDS = ("index", "pages", "frontier", "bench")
META_KINDS = ("wiki", "dates")
def _facet(value: str) -> str:
    """--facet Methods / method / methods -> methods (the choices are the lower-case plurals)."""
    v = value.strip().lower()
    return {"problem": "problems", "method": "methods", "resource": "resources", "mechanism": "mechanisms"}.get(v, v)


# commands of the old frontier-scholar CLI, and what to use instead
OLD_COMMANDS = {"paper": "fs read <arxiv id>   (a facet: fs read <id>/method)", "nav": "fs select [--path P]",
                "dates": "fs meta dates <ids> --before YYYY-MM-DD", "grep": "fs read <folder> --grep PHRASE",
                "locate": 'fs search wiki --level subtopic "<words>"', "bench": "fs search wiki bench NAME",
                "frontier": 'fs search wiki frontier "<words>"   or   fs read <subtopic>/frontier.md',
                "read-id": "fs read <node id>", "call": "one of: fs select / search / read / related / meta"}
DASHES = ("\u2014", "\u2013", "\u2212", "\u2012")       # em dash, en dash, minus, figure dash

OPTIONS_ANYWHERE = "Options may come before or after the positional words; quote multi-word queries."
EXIT = {"invalid_argument": 2, "not_found": 2, "unauthorized": 2, "forbidden": 2, "rate_limited": 3, "timeout": 3,
        "unavailable": 3, "http_429": 3, "http_502": 3, "http_503": 3, "http_504": 3}


def _emit(obj) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def _render_page(item: dict, command_base: str, as_of: str = "") -> str:
    start, end = item["range"]
    total = item["chars_total"]
    nature = "wiki synthesis (not the paper's original text)" if item.get("nature") == "synthesis" else item.get("nature", "")
    head = (f"<<< {item.get('title')} | {item['path']} | node_id={item.get('node_id')} | chars {start}-{end} of {total} | "
            f"{nature}" + (f" | as_of={as_of}" if as_of else "") + " >>>")
    lines = [head]
    if item.get("sections"):
        lines.append("Sections: " + " · ".join(item["sections"]))
        lines.append("")
    lines.append(item["content"].rstrip())
    if item.get("next_offset") is not None:
        lines.append(f"<<< more: {command_base} {item['path']} --offset {item['next_offset']} (or --section \"<name>\"; list: --sections) >>>")
    else:
        lines.append("<<< end of page >>>")
    return "\n".join(lines)


def cmd_read(client: Client, a) -> None:
    sections = a.section if isinstance(a.section, list) else ([a.section] if a.section else [None])
    common = dict(targets=a.targets, offset=a.offset, max_chars=a.max_chars, sections=a.sections, papers=a.papers,
                  role=a.role, before=a.before, after=a.after, stat=a.stat, grep=a.grep, strict=a.strict,
                  grep_args=a.grep_arg, query=a.query, topk=a.topk)
    if len(sections) > 1:                         # several --section: one call each, printed in order
        bodies, missing, first_error = [], [], None
        for sec in sections:
            try:
                bodies.append(client.call("read", dict(common, section=sec)))
            except FsError as exc:                # a page without that heading: say so, keep the sections it has
                if exc.code != "not_found" or exc.details.get("field") != "section":
                    raise
                first_error = first_error or exc
                missing.append({"code": "section_not_found", "section": sec, "message": exc.message,
                                "hint": exc.details.get("hint", "")})
        if not bodies:
            raise first_error
        items = [it for b in bodies for it in b.get("items") or []]
        body = dict(bodies[0], items=items, total=len(items))
        warnings = []
        for w in [w for b in bodies for w in b.get("warnings") or []] + missing:
            if w not in warnings:
                warnings.append(w)
        body["warnings"] = warnings
    else:
        body = client.call("read", dict(common, section=sections[0]))
    items = body.get("items") or []
    if items and not a.json and all(it.get("kind") in ("page", "paper_facet") for it in items):
        out = [_render_page(it, "fs read", body.get("as_of", "")) for it in items]
        if body.get("warnings"):
            out.append("<<< warnings: " + json.dumps(body["warnings"], ensure_ascii=False) + " >>>")
        sys.stdout.write("\n\n".join(out) + "\n")
        return
    _emit(body)


def cmd_search(client: Client, a) -> None:
    if a.target == "paper":
        if not a.rest:
            raise FsError("invalid_argument", 'usage: fs search paper "<query>"')
        args = dict(query=" ".join(a.rest), path=a.path, before=a.before, after=a.after, role=a.role,
                    topk=a.topk, offset=a.offset)
        _emit(client.call("search/paper", args))
        return
    rest = list(a.rest)
    kind = rest.pop(0) if rest and rest[0] in WIKI_KINDS else "index"
    query = " ".join(rest)
    args = dict(kind=kind, query=query, path=a.path, level=a.level, facet=a.facet, grep=a.grep, strict=a.strict,
                gap_type=a.gap_type, status=a.status, trend=a.trend, before=a.before,
                topk=a.topk, offset=a.offset)
    _emit(client.call("search/wiki", args))


def cmd_select(client: Client, a) -> None:
    path = a.path[0] if a.path and len(a.path) == 1 else a.path
    _emit(client.call("select", dict(query=" ".join(a.query), path=path, topk=a.topk, offset=a.offset)))


def cmd_related(client: Client, a) -> None:
    _emit(client.call("related", dict(ids=a.ids, facet=a.facet, by=a.by, before=a.before, after=a.after,
                                      papers_per_cluster=a.papers_per_cluster, topk=a.topk, offset=a.offset)))


def cmd_meta(client: Client, a) -> None:
    ids = list(a.ids)
    kind = ids.pop(0) if ids and ids[0] in META_KINDS else "default"
    if not ids:
        raise FsError("invalid_argument", "usage: fs meta [wiki|dates] <id>...")
    _emit(client.call("meta", dict(kind=kind, ids=ids, before=a.before, after=a.after)))


_FMT = dict(formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=28, width=120),
            allow_abbrev=False)
def _paging(parser) -> None:
    g = parser.add_argument_group("paging")
    g.add_argument("--topk", type=int, metavar="N", help="results per call (default 20, max 100)")
    g.add_argument("--offset", type=int, metavar="N", help="skip the first N results (default 0); see \"next\" in the answer")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fs", description=__doc__, usage=argparse.SUPPRESS, **_FMT)
    p.add_argument("--version", action="store_true", help="CLI version, API version, data snapshot and whether FS_API_KEY works, as JSON")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    # the description already lists the commands; argparse's own list would repeat it
    p.format_help = lambda: __doc__ + ("\nOptions:\n  -h, --help   this help\n"
                                       "  --version    CLI version, API version, data snapshot and whether FS_API_KEY works, as JSON\n")

    # ---------------------------------------------------------------- select
    sel = sub.add_parser("select", help="list the next level of the tree, ranked by a query (beam search over several folders)",
                         usage='fs select ["QUERY"] [--path P]... [--topk N] [--offset N]', **_FMT, description="""\
List the children of a folder: the 20 domains at the root, the topics of a domain, the subtopics of a topic, the
facet folders and pages of a subtopic.

With QUERY they are ranked by relevance (a folder scores the mean BM25 of its 10 best pages; 0-100, best = 100).
Without QUERY: by size; in a subtopic, folders first, then pages by name. Repeat --path to rank the children of
several folders together, e.g. the best 2-3 branches of the previous level (beam search); each item then names its
"parent".

Items: {path, kind: domain|topic|subtopic|facet|page, name, counts, score?, parent?, approx_tokens? (pages)}""",
                         epilog="""\
examples:
  fs select                                         the 20 domains
  fs select "robot task planning"                   domains ranked for the query
  fs select "robot task planning" --path robotics   topics of robotics
  fs select "LSM tree compaction" --path databases-and-data-management --path systems-and-architecture""")
    sel.add_argument("query", nargs="*", metavar="QUERY", help="words to rank by (optional; quote several words)")
    sel.add_argument("--path", action="append", metavar="P", help="folder to list (default: the root); repeatable, up to 10")
    _paging(sel)
    sel.set_defaults(func=cmd_select)

    # ---------------------------------------------------------------- search
    s = sub.add_parser("search", help="ranked search: wiki pages (index / pages / frontier / bench) or papers",
                       usage='fs search wiki [index|pages|frontier|bench] "QUERY" [options]\n       fs search paper "QUERY" [options]',
                       **_FMT, description="""\
fs search wiki index "Q"      overview pages (index.md) of domains, topics, subtopics (index is the default kind)
fs search wiki pages "Q"      problem / method / resource / mechanism pages
fs search wiki frontier "Q"   gap and approach records of the subtopics' frontier.md (Q optional: then filter only)
fs search wiki bench NAME     a benchmark or dataset: its Resources pages and the papers that use it (oldest first)
fs search paper "Q"           papers, by title, abstract and dataset names

Ranking is BM25; scores are 0-100 within one answer.
Items:
  index / pages: {path, title, score, level, facet, subtopic, aggregate}   (aggregate: an other-*-NN.md page that
                 collects single-paper entries)
  frontier:      {subtopic, kind: gap|approach, name, as_of, frontier_page, types, status, supporting_papers,
                 first{date, paper_id}, latest{...} | trend, papers}
  bench:         {kind: resource_page, path, subtopic} then {kind: earliest_paper|using_paper, paper_id, title, date,
                 subtopic}; earliest_paper is the oldest in the wiki, not necessarily the benchmark's origin
  paper:         {paper_id, title, date, score, subtopic (primary), secondary}""",
                       epilog="""\
examples:
  fs search wiki --level subtopic "adaptive retrieval"
  fs search wiki pages "confidence gated retrieval" --facet methods --path information-retrieval --grep entropy
  fs search wiki frontier --path information-retrieval --status open --gap-type evaluation
  fs search wiki bench MIRACL --before 2025-01-01
  fs search paper "LSM tree compaction" --path databases-and-data-management --role all --before 2024-10-01""")
    s.add_argument("target", choices=["wiki", "paper"], help="what to search")
    s.add_argument("rest", nargs="*", metavar="[KIND] QUERY", help="wiki: index (default) | pages | frontier | bench, then the query")
    g = s.add_argument_group("all kinds")
    g.add_argument("--path", metavar="P", help="only under this domain / topic / subtopic")
    g.add_argument("--before", metavar="D", help="YYYY-MM-DD, first arXiv version strictly before D (paper, frontier: gaps "
                                                  "first raised, bench: papers)")
    g = s.add_argument_group("wiki index / pages")
    g.add_argument("--level", choices=["domain", "topic", "subtopic"], help="index: only overviews of this level")
    g.add_argument("--facet", action="append", type=_facet, choices=["problems", "methods", "resources", "mechanisms"],
                   help="pages: only these page kinds (repeatable; default all four; case-insensitive)")
    g.add_argument("--grep", metavar="PHRASE", help="keep only pages containing PHRASE (case, hyphen, underscore and "
                                                    "spaces normalized); may warn grep_partial on large folders")
    g.add_argument("--strict", action="store_true", help="--grep as a plain, case-sensitive ripgrep regex")
    g = s.add_argument_group("wiki frontier")
    g.add_argument("--gap-type", action="append", choices=["data", "evaluation", "method", "theory", "efficiency", "deployment"],
                   help="gaps of these types (repeatable)")
    g.add_argument("--status", choices=["open", "partial"], help="gaps with this status")
    g.add_argument("--trend", choices=["rising", "steady", "no-recent"], help="approaches with this trend")
    g = s.add_argument_group("paper")
    g.add_argument("--after", metavar="D", help="YYYY-MM-DD, first arXiv version strictly after D")
    g.add_argument("--role", choices=["primary", "secondary", "all"], help="with --path: which subtopic routes count "
                                                                           "(default primary)")
    _paging(s)
    s.set_defaults(func=cmd_search)

    # ---------------------------------------------------------------- read
    r = sub.add_parser("read", help="read a folder, page, paper or paper facet; list a subtopic's papers; grep under a path",
                       usage="fs read TARGET... [options]", **_FMT, description="""\
TARGET (up to 10): a wiki path (folder or .md page), a node id page:<hex>, an arXiv id, or <arXiv id>/<facet>
with facet overview | problem | method | evaluation | mechanism.

  folder         {kind: dir, path, level, title, children[{path, kind, title, approx_tokens?}], papers? (subtopic)}
  page, facet    Markdown between marker lines: <<< title | path | node_id | chars a-b of n >>> ... and a last line
                 with the command for the next chunk (or <<< end of page >>>); --json gives {content, range, ...}
  arXiv id       {kind: paper, paper_id, title, date, facets (pages that exist), routes[{subtopic, role}],
                  abstract{text, nature: original}}: the paper's own arXiv abstract, the one original text
  --papers       one subtopic's papers, newest first or ranked by --query: {paper_id, title, date, role, score?}
  --grep         matching lines under the first TARGET: {path, matches, lines[{line_no, line}] (<=5)}  (paged)

With several TARGETs, one that fails becomes a not_found warning.""",
                       epilog="""\
examples:
  fs read information-retrieval/agentic-search/adaptive-retrieval --stat
  fs read information-retrieval/agentic-search/adaptive-retrieval --papers --role all --before 2024-10-01 --topk 100
  fs read information-retrieval/agentic-search/adaptive-retrieval/Methods/confidence-gated-retrieval.md --sections
  fs read information-retrieval/agentic-search/adaptive-retrieval/Methods/confidence-gated-retrieval.md --section "Core Idea"
  fs read 2202.04522 2307.16693/method --max-chars 3000
  fs read information-retrieval/agentic-search --grep "confidence gated" --query "retrieval gating"
  fs read information-retrieval/agentic-search --grep "Confidence-Gated" --strict --grep-arg=-w""")
    r.add_argument("targets", nargs="+", metavar="TARGET", help="path, node id, arXiv id or <arXiv id>/<facet>")
    g = r.add_argument_group("folder")
    g.add_argument("--stat", action="store_true", help="add keywords, scope and counts (computed offline)")
    g = r.add_argument_group("page")
    g.add_argument("--sections", action="store_true", help="list the page's headings with offset and size, not the text")
    g.add_argument("--section", action="append", metavar="NAME",
                   help="read the section whose heading equals or contains NAME (case-insensitive); repeatable; an "
                        "unknown NAME lists the headings in the error, but with several names the page's other "
                        "sections are still printed and a section_not_found warning names the missing ones")
    g.add_argument("--offset", type=int, metavar="N", help="start at character N (page); skip N results (lists)")
    g.add_argument("--max-chars", type=int, metavar="N", help="characters per chunk (default 12000, 1000-50000)")
    g.add_argument("--json", action="store_true", help="print the page as JSON instead of Markdown")
    g = r.add_argument_group("subtopic paper list")
    g.add_argument("--papers", action="store_true", help="list the subtopic's papers, newest first")
    g.add_argument("--role", choices=["primary", "secondary", "all"], help="which members (default primary)")
    g.add_argument("--before", metavar="D", help="first arXiv version strictly before YYYY-MM-DD")
    g.add_argument("--after", metavar="D", help="first arXiv version strictly after YYYY-MM-DD")
    g = r.add_argument_group("grep under a path")
    g.add_argument("--grep", metavar="PHRASE", help="matching lines in the .md files under the path (case, hyphen, "
                                                    "underscore and spaces normalized); a large folder is checked for about 12 s, then the answer says grep_partial")
    g.add_argument("--strict", action="store_true", help="plain, case-sensitive ripgrep regex")
    g.add_argument("--grep-arg", action="append", metavar="OPT", help="with --strict: extra ripgrep option, e.g. --grep-arg=-w")
    g.add_argument("--query", metavar="WORDS", help="order the matching files (--grep) or papers (--papers) by relevance to "
                                                    "WORDS (default: by path / newest first)")
    g = r.add_argument_group("paging (--papers, --grep)")
    g.add_argument("--topk", type=int, metavar="N", help="results per call (default 20, max 100)")
    r.set_defaults(func=cmd_read)

    # ---------------------------------------------------------------- related
    rel = sub.add_parser("related", help="papers that share a Methods / Resources page with given papers",
                         usage="fs related ID... [--facet F]... [--by-cluster | --by-paper] [--before D] [--after D] "
                               "[--papers-per-cluster N] [--topk N] [--offset N]", **_FMT, description="""\
Papers the wiki groups with the given ones. A cluster is the paper set of one full page (its "Source Papers") or
of one entry of an other-*-NN.md page. Step 1: the given papers -> the pages / entries that cite them; step 2:
those -> all their papers. The given papers are not returned; clusters holding only given papers are skipped.

  --by-cluster (default)  one item per cluster, most given papers first, then the smallest:
                          {page, facet, subtopic, title, entry (anchor in an other-* page, else null),
                           seeds (given papers in it), size (other papers), papers[{paper_id, title, date}]}
  --by-paper              one list of papers, by the number of shared clusters, then by smaller clusters:
                          {paper_id, title, date, shared, via[{page, entry, title}]}""",
                         epilog="""\
examples:
  fs related 2202.04522 2307.16693
  fs related 2202.04522 2307.16693 --by-paper --before 2024-10-01 --topk 50
  fs related 2210.03629 --facet methods --papers-per-cluster 5""")
    rel.add_argument("ids", nargs="+", metavar="ID", help="1-50 arXiv ids")
    rel.add_argument("--facet", action="append", type=_facet, choices=["methods", "resources", "problems", "mechanisms"],
                     help="page kinds whose clusters count (repeatable; default methods and resources)")
    by = rel.add_mutually_exclusive_group()
    by.add_argument("--by-cluster", dest="by", action="store_const", const="cluster", help="one item per cluster (default)")
    by.add_argument("--by-paper", dest="by", action="store_const", const="paper", help="one ranked list of papers")
    rel.add_argument("--before", metavar="D", help="only papers first published strictly before YYYY-MM-DD")
    rel.add_argument("--after", metavar="D", help="only papers first published strictly after YYYY-MM-DD")
    rel.add_argument("--papers-per-cluster", type=int, metavar="N", help="--by-cluster: papers listed per cluster (default 20, 0-100); "
                                                              "\"size\" always gives the full count")
    _paging(rel)
    rel.set_defaults(func=cmd_related)

    # ---------------------------------------------------------------- meta
    m = sub.add_parser("meta", help="title and date, subtopic routes (wiki) or a date cut-off check (dates) for paper ids",
                       usage="fs meta [wiki|dates] ID... [--before D] [--after D]", **_FMT, description="""\
fs meta ID...                     {paper_id, title, date}
fs meta wiki ID...                {paper_id, primary (subtopic or null), secondary[]}
fs meta dates ID... --before D --after D
                                  {paper_id, date, before / after (true/false, with that option and a known date),
                                   within (true when every given bound holds)}

Up to 200 ids, answered in input order; ids not in the wiki are listed in a not_found warning, unknown dates in
date_unknown. Dates are arXiv first-version dates.""",
                       epilog="""\
examples:
  fs meta 2202.04522 2307.16693
  fs meta wiki 2202.04522
  fs meta dates 2202.04522 2307.16693 2510.99999 --before 2024-10-01
  fs meta dates 2202.04522 2307.16693 --after 2022-01-01 --before 2024-10-01""")
    m.add_argument("ids", nargs="+", metavar="[wiki|dates] ID", help="optional kind, then 1-200 arXiv ids")
    m.add_argument("--before", metavar="D", help="dates: check a YYYY-MM-DD cut-off (first version strictly before D)")
    m.add_argument("--after", metavar="D", help="dates: check a lower bound (first version strictly after D)")
    m.set_defaults(func=cmd_meta)
    return p


def _say_waiting(error, seconds: float, attempt: int) -> None:
    """One line on stderr before a retry, so a pause is not mistaken for a hang (the JSON error line stays the last)."""
    reason = error.message or error.code
    print(f"fs: {error.code}: {reason}; waiting {seconds:.0f} s, retry {attempt} of 4", file=sys.stderr, flush=True)


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_parser()
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in OLD_COMMANDS:
        parser.error(f"'{args[0]}' is a command of the old frontier-scholar CLI; use: {OLD_COMMANDS[args[0]]}")
    if "--json" in args and args[0] != "read":           # every other answer is JSON already
        args = [x for x in args if x != "--json"]
    typo = [x for x in args if x.startswith(DASHES)]
    if typo:
        parser.error(f"{typo[0]!r} starts with a typographic dash; options take two ASCII hyphens, e.g. --before")
    # argparse stops filling a nargs="*"/"+" positional at the first option, so `fs search wiki pages --facet
    # methods "bge m3"` would leave the query unparsed. Put such leftover words back into the command's
    # positional list; only unknown *options* are an error.
    a, extra = parser.parse_known_args(args)
    words = [x for x in extra if not x.startswith("-")]
    unknown = [x for x in extra if x.startswith("-")]
    if unknown:
        parser.error("unrecognized arguments: " + " ".join(unknown))
    if words:
        slot = {"read": "targets", "search": "rest", "select": "query", "related": "ids", "meta": "ids"}.get(a.command or "")
        if slot is None:
            parser.error("unrecognized arguments: " + " ".join(words))
        setattr(a, slot, list(getattr(a, slot) or []) + words)
    client = Client(on_wait=_say_waiting)
    if a.version:
        info = {"cli": __version__}
        try:
            info.update(client.health())
        except Exception as exc:                     # the version must print even when the service is down
            info["server"] = f"unreachable: {exc}"
        else:                                        # health needs no key: check it with one small protected call
            try:
                client.call("select", {"topk": 1})
                info["key"] = "ok"
            except FsError as exc:
                info["key"] = {"unauthorized": "missing or invalid FS_API_KEY"}.get(exc.code, f"not checked: {exc.code}")
        _emit(info)
        return
    if not getattr(a, "func", None):
        parser.print_help()
        sys.exit(2)
    try:
        a.func(client, a)
    except FsError as exc:
        sys.stderr.write(json.dumps({"error": exc.as_dict()}, ensure_ascii=False) + "\n")
        sys.exit(EXIT.get(exc.code, 1))
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(0)


if __name__ == "__main__":
    main()
