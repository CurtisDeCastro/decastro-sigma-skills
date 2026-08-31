#!/usr/bin/env python3
"""Generic `sigma api …` caller for this repo's Python — one place, not four.

    from sigma_api import api, paginate

    api("connections", "list", params={"limit": 200})
    paginate("files", "list", params={"typeFilters": "folder"})

Why the CLI rather than urllib: it owns credentials, refresh, base URL and headers, and
raw HTTP additionally trips a Cloudflare challenge on large image-heavy bodies (verified
2026-08-11). Set SIGMA_PROFILE to target a non-default profile.

`scripts/sigma_spec.py` builds the workbook-spec calls on top of this; anything needing a
body too large for argv still falls back to HTTP there.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


class SigmaApiError(RuntimeError):
    """A non-zero CLI exit. `.code` is the API's numeric code when it gave one."""

    def __init__(self, message: str, code: int | None = None, raw: str = ""):
        super().__init__(message)
        self.code = code
        self.raw = raw


def _leading_json(text: str) -> tuple[bool, object]:
    """(parsed_ok, first JSON value in `text`).

    The CLI prints a JSON error object AND a trailing `error[api]: …` line, so a plain
    json.loads() over the whole output fails on exactly the errors you want to read.

    Returns a flag rather than just the value because a literal `null` is a real,
    meaningful response here — `query download get` returns it while a job is still
    running — and must not be confused with "could not parse".
    """
    text = text.lstrip()
    if not text:
        return False, None
    try:
        value, _ = json.JSONDecoder().raw_decode(text)
        return True, value
    except ValueError:
        return False, None


def run(args: list[str], body: str | None = None) -> tuple[int, str]:
    """Run `sigma <args>` (plus `--json <body>`). Returns (rc, stdout+stderr)."""
    profile = os.environ.get("SIGMA_PROFILE")
    cmd = ["sigma"] + (["-p", profile] if profile else []) + args
    if body is not None:
        cmd += ["--json", body]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("sigma CLI not on PATH. Install it, then run `sigma auth login`.")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def api(*path: str, params: dict | None = None, body: dict | None = None):
    """Call `sigma api <path…>` and return the parsed JSON. Raises SigmaApiError."""
    args = ["api", *path]
    if params:
        args += ["--params", json.dumps(params)]
    args += ["-f", "json"]
    rc, out = run(args, json.dumps(body) if body is not None else None)
    ok, parsed = _leading_json(out)
    if rc != 0:
        msg = parsed.get("message") if isinstance(parsed, dict) else None
        code = parsed.get("code") if isinstance(parsed, dict) else None
        raise SigmaApiError(msg or out.strip()[:400] or "sigma api call failed",
                            code=code, raw=out)
    if not ok:
        raise SigmaApiError(f"could not parse CLI output: {out[:300]}", raw=out)
    return parsed


def paginate(*path: str, params: dict | None = None, key: str = "entries",
             limit: int = 1000) -> list:
    """Follow `nextPage` and return every entry across pages."""
    out: list = []
    page = None
    while True:
        p = dict(params or {})
        p["limit"] = limit
        if page:
            p["page"] = page
        d = api(*path, params=p)
        out.extend(d.get(key) or [])
        page = d.get("nextPage")
        if not page:
            return out
