#!/usr/bin/env python3
"""Workbook-spec transport for the Python generators — via the `sigma` CLI.

    from sigma_spec import verify, create, update, get_spec

Every generator in this repo used to hand-roll a urllib POST with a bearer token.
This routes the same calls through `sigma api workbooks spec …` instead, which is
the plugin's rule: the CLI owns credentials, refresh, base URL and headers.

Two concrete reasons beyond consistency:

1. **Cloudflare.** The raw-HTTP path gets an HTML "Just a moment..." challenge
   (HTTP 403) on specs carrying large base64 SVG data-URIs — i.e. most branded
   builds. Verified 2026-08-11: a spec that could not be verified over curl
   came back with a clean structured error list through the CLI.
2. **Readable errors.** The CLI returns parseable JSON where the raw endpoint
   emits a multi-MB union-type cascade on a shape mismatch (a 150 KB spec
   produced 10 MB).

**Fallback.** `--json` passes the body as one argv entry, so a spec near ARG_MAX
(1 MB on macOS) cannot go that way; over ARG_LIMIT we fall back to urllib using
`sigma auth token` — still CLI-owned credentials, just a different pipe. Note the
Cloudflare challenge applies to that path, so a very large image-heavy spec may be
unverifiable; create/assert still work.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sigma_auth import base_url, token  # noqa: E402
from sigma_api import run as _cli  # noqa: E402

# Body size above which --json can't be used. Headroom for the rest of argv + env.
ARG_LIMIT = int(os.environ.get("ARG_LIMIT", 800_000))


def _http(path: str, spec: dict | None = None, method: str = "POST") -> tuple[int, str]:
    """urllib fallback for bodies too large for argv. Same credentials."""
    data = json.dumps(spec).encode() if spec is not None else None
    req = urllib.request.Request(
        base_url() + path, data=data, method=method,
        headers={"Authorization": "Bearer " + token(),
                 "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        return 0, urllib.request.urlopen(req, timeout=120).read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _submit(op: str, spec: dict, workbook_id: str | None = None) -> tuple[int, str]:
    body = json.dumps(spec)
    if len(body) <= ARG_LIMIT:
        args = ["api", "workbooks", "spec", op]
        if workbook_id:
            args += ["--params", json.dumps({"workbookId": workbook_id})]
        return _cli(args, body)
    sys.stderr.write(
        f"sigma_spec: spec is {len(body)} bytes (> ARG_LIMIT {ARG_LIMIT}) — falling back "
        "to direct HTTP with `sigma auth token`; --json can't carry a body this large.\n")
    paths = {"verify": "/v2/workbooks/spec/verify", "create": "/v2/workbooks/spec"}
    if op == "update":
        return _http(f"/v2/workbooks/{workbook_id}/spec", spec, "PUT")
    return _http(paths[op], spec)


def verify(spec: dict) -> tuple[bool, str]:
    """POST spec/verify — same validation as create, persists nothing.

    Returns (valid, message). A False with a huge message is inconclusive rather than
    a rejection: union-type dumps and WAF challenges both fire on working specs.
    """
    _, out = _submit("verify", spec)
    try:
        d = json.loads(out)
        if d.get("valid"):
            return True, "valid"
        errs = [e.get("summary", e) for e in d.get("errors", [])][:12]
        if errs:
            # Known false negative: it can't evaluate Cortex/Genie tool paths.
            if any("invocable inodes are not supported" in str(e) for e in errs):
                return True, "warehouse-agent tool flagged — KNOWN FALSE NEGATIVE"
            return False, "; ".join(str(e) for e in errs)
    except json.JSONDecodeError:
        pass
    return False, f"INCONCLUSIVE ({len(out)} bytes, not a clean error list): {out[:300]}"


def create(spec: dict) -> tuple[bool, str | None, str]:
    """Create a workbook. Returns (ok, workbookId, raw)."""
    rc, out = _submit("create", spec)
    wid = None
    try:
        wid = json.loads(out).get("workbookId")
    except json.JSONDecodeError:
        for line in out.splitlines():          # YAML-ish fallback
            if "workbookId" in line:
                wid = line.split()[-1].strip('"')
                break
    return (rc == 0 and bool(wid)), wid, out


def update(workbook_id: str, spec: dict) -> tuple[bool, str]:
    """FULL replacement — anything omitted from `spec` is dropped."""
    rc, out = _submit("update", spec, workbook_id)
    return rc == 0, out


def get_spec(workbook_id: str) -> dict:
    """GET the code representation back. The GET-back is the source of truth —
    unknown keys submit fine and then vanish."""
    rc, out = _cli(["api", "workbooks", "spec", "get",
                    "--params", json.dumps({"workbookId": workbook_id})])
    if rc != 0:
        raise RuntimeError(f"spec get failed: {out[:300]}")
    d = json.loads(out)
    d = d.get("spec", d)
    if isinstance(d, str):
        d = json.loads(d)
    return d


def workbook_url(workbook_id: str) -> str | None:
    rc, out = _cli(["api", "workbooks", "get",
                    "--params", json.dumps({"workbookId": workbook_id})])
    if rc != 0:
        return None
    try:
        return json.loads(out).get("url")
    except json.JSONDecodeError:
        return None
