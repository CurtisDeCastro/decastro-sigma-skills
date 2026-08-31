#!/usr/bin/env python3
"""Headless PNG render of a workbook page — the build->render->LOOK->fix loop.

  POST /v2/workbooks/{id}/export {"format":{"type":"png"},"pageId":...} -> queryId
  GET  /v2/query/{queryId}/download  (Accept: */*)                      -> bytes

A zero-byte 200 means "still rendering", not "failed".

Usage: python3 shot.py <workbookId> <outPath> [pageId]
"""
import json, pathlib, sys, time, urllib.error, urllib.request, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sigma_auth import base_url, token

POLL, MAX_WAIT = 3, 240


def req(method, path, body=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Authorization": "Bearer " + token(), "Accept": accept}
    if data:
        h["Content-Type"] = "application/json"
    return urllib.request.Request(base_url() + path, data=data, headers=h, method=method)


wb, out = sys.argv[1], sys.argv[2]
page = sys.argv[3] if len(sys.argv) > 3 else None
body = {"format": {"type": "png"}}
if page:
    body["pageId"] = page
el = os.environ.get("ELEMENT")
if el:
    body["elementId"] = el
with urllib.request.urlopen(req("POST", f"/v2/workbooks/{wb}/export", body), timeout=90) as r:
    qid = json.loads(r.read().decode())["queryId"]
print("queryId:", qid)

waited = 0
while waited < MAX_WAIT:
    try:
        with urllib.request.urlopen(req("GET", f"/v2/query/{qid}/download", accept="*/*"),
                                    timeout=90) as r:
            blob = r.read()
        if blob:
            pathlib.Path(out).write_bytes(blob)
            print(f"wrote {out} ({len(blob):,} bytes)")
            sys.exit(0)
    except urllib.error.HTTPError as e:
        if e.code not in (404, 409, 425, 500, 502, 503, 504):
            print("HTTP", e.code, e.read()[:300].decode(errors="replace")); sys.exit(1)
    time.sleep(POLL); waited += POLL
print(f"timed out after {MAX_WAIT}s"); sys.exit(1)
