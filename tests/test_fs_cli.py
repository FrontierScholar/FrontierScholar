"""fs CLI argument parsing: options may come before, between or after positional words."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from frontier_scholar import cli  # noqa: E402


def parse(argv):
    seen = {}

    def capture(client, a):
        seen.update(vars(a))

    for name in ("cmd_read", "cmd_search", "cmd_select", "cmd_related", "cmd_meta"):
        setattr(cli, name, capture)
    import argparse
    parser = cli.build_parser()
    for action in parser._subparsers._group_actions[0].choices.values():
        action.set_defaults(func=capture)
    orig = cli.build_parser
    cli.build_parser = lambda: parser
    try:
        cli.main(argv)
    finally:
        cli.build_parser = orig
    return seen


def test_options_between_positionals():
    a = parse(["search", "wiki", "pages", "--facet", "methods", "bge m3 embedding"])
    assert a["rest"] == ["pages", "bge m3 embedding"] and a["facet"] == ["methods"]
    b = parse(["search", "wiki", "--facet", "methods", "pages", "bge", "m3"])
    assert b["rest"] == ["pages", "bge", "m3"]
    c = parse(["select", "--path", "information-retrieval", "adaptive", "retrieval"])
    assert c["query"] == ["adaptive", "retrieval"] and c["path"] == ["information-retrieval"]
    beam = parse(["select", "robot planning", "--path", "robotics", "--path", "artificial-intelligence"])
    assert beam["path"] == ["robotics", "artificial-intelligence"]
    r = parse(["related", "2405.14333", "--by-paper", "2402.08957", "--facet", "methods"])
    assert r["ids"] == ["2405.14333", "2402.08957"] and r["by"] == "paper" and r["facet"] == ["methods"]
    d = parse(["meta", "--before", "2024-10-01", "dates", "2405.14333", "2402.08957"])
    assert d["ids"] == ["dates", "2405.14333", "2402.08957"]
    e = parse(["read", "--papers", "information-retrieval/agentic-search/adaptive-retrieval", "--topk", "5"])
    assert e["targets"] == ["information-retrieval/agentic-search/adaptive-retrieval"] and e["papers"] and e["topk"] == 5


def test_no_abbreviations_and_no_unimplemented_flags():
    import pytest
    for argv in (["search", "wiki", "pages", "--fac", "methods", "x"], ["search", "paper", "x", "--type", "d"],
                 ["meta", "2402.03216", "--fields", "a"], ["search", "wiki", "bench", "MIRACL", "--results"]):
        with pytest.raises(SystemExit):
            parse(argv)


def test_client_retries_proxy_errors_and_reports_the_wait(monkeypatch):
    import io
    import urllib.error
    from frontier_scholar import client as client_mod

    answers = [(503, b"<html>503</html>", {}), (429, b'{"error": {"code": "rate_limited", "message": "slow", "retry_after": 1}}', {}),
               (200, b'{"total": 0, "items": []}', {})]
    seen = []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(req, timeout=None):
        status, body, headers = answers.pop(0)
        if status != 200:
            raise urllib.error.HTTPError(req.full_url, status, "x", headers, io.BytesIO(body))
        return Resp(body)

    monkeypatch.setattr(client_mod.time, "sleep", lambda s: None)
    c = client_mod.Client(base_url="https://example.invalid", on_wait=lambda e, s, n: seen.append((e.code, n)))
    c._open = fake_open
    assert c.call("select", {"query": "x"}) == {"total": 0, "items": []}
    assert seen == [("http_503", 1), ("rate_limited", 2)]


def test_client_does_not_sleep_through_a_daily_limit(monkeypatch):
    import io
    import urllib.error
    from frontier_scholar import client as client_mod

    def fake_open(req, timeout=None):
        body = b'{"error": {"code": "rate_limited", "message": "at most 1000 requests per day", "retry_after": 30000}}'
        raise urllib.error.HTTPError(req.full_url, 429, "x", {}, io.BytesIO(body))

    monkeypatch.setattr(client_mod.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("slept")))
    c = client_mod.Client(base_url="https://example.invalid")
    c._open = fake_open
    try:
        c.call("select", {"query": "x"})
    except client_mod.FsError as e:
        assert e.code == "rate_limited" and e.details["retry_after"] == 30000
    else:
        raise AssertionError("no error")
