# Security Policy

## Scope

This repository is an **independent, community-maintained** library of agent skills for
Sigma Computing. It is not an official Sigma Computing product and is not supported by
Sigma Computing.

## Reporting a Vulnerability

Report issues in **this repository's own code** by opening a
[GitHub security advisory](https://github.com/CurtisDeCastro/decastro-sigma-skills/security/advisories/new).
Please do not open a public issue for a security report.

For vulnerabilities in the **Sigma Computing product itself** — not this repository —
use Sigma's Vulnerability Disclosure Program: https://www.sigmacomputing.com/product/vdp

## Credentials

These skills authenticate exclusively through the `sigma` CLI. Do not commit tokens,
client secrets, or `.env` files. Nothing here should ever read a credential from source.
