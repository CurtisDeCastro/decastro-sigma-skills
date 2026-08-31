#!/usr/bin/env python3
"""Shared Sigma auth for the Python scripts in this repo — sourced from the
`sigma` CLI, the single source of truth for credentials.

    from sigma_auth import base_url, token

`base_url()` parses the "API host:" line of `sigma auth status`; `token()` calls
`sigma auth token`. Both cache for the process lifetime, and both defer to an
exported SIGMA_BASE_URL / SIGMA_API_TOKEN when present. Set SIGMA_PROFILE to
target a non-default CLI profile.

Exits 2 with actionable guidance when the CLI is missing or not logged in.
Never prints the token.
"""
from __future__ import annotations

import functools
import os
import subprocess
import sys


def cli(*args: str, merge_stderr: bool = False) -> str:
    """Run the sigma CLI against the selected profile and return its output.

    `sigma auth status` prints to STDERR, `sigma auth token` to STDOUT — pass
    merge_stderr=True for the former.
    """
    profile = os.environ.get("SIGMA_PROFILE")
    cmd = ["sigma"] + (["-p", profile] if profile else []) + list(args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        sys.stderr.write(
            "sigma auth: the `sigma` CLI is not on PATH. "
            "Install it, then run `sigma auth login`.\n"
        )
        sys.exit(2)
    if p.returncode != 0:
        sys.stderr.write(
            f"sigma auth: `{' '.join(cmd)}` failed:\n{p.stderr or p.stdout}"
            "  Run `sigma auth login`.\n"
        )
        sys.exit(2)
    return p.stdout + p.stderr if merge_stderr else p.stdout


@functools.lru_cache(maxsize=1)
def base_url() -> str:
    env = os.environ.get("SIGMA_BASE_URL")
    if env:
        return env.rstrip("/")
    for line in cli("auth", "status", merge_stderr=True).splitlines():
        if line.startswith("API host:"):
            host = line.split(":", 1)[1].strip()
            if host:
                if not host.startswith(("http://", "https://")):
                    host = "https://" + host
                return host.rstrip("/")
    sys.stderr.write("sigma auth: could not read the API host from `sigma auth status`.\n")
    sys.exit(2)


@functools.lru_cache(maxsize=1)
def token() -> str:
    env = os.environ.get("SIGMA_API_TOKEN")
    if env:
        return env
    tok = cli("auth", "token").strip()
    if not tok:
        sys.stderr.write("sigma auth: `sigma auth token` returned nothing — run `sigma auth login`.\n")
        sys.exit(2)
    return tok
