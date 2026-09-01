# Sigma agent skills

Multi-provider agent skills for [Sigma Computing](https://sigmacomputing.com). The same skill content runs in Claude Code, Cursor, OpenAI Codex, and Snowflake Cortex Code.

**Not an official Sigma Computing product.** An independent library maintained by @CurtisDeCastro. `sigma-api`, `sigma-data-models` and `sigma-embed` are derived from Sigma's official repo (Apache-2.0); everything else is original.

## Installation

### Claude Code

```
/plugin marketplace add https://github.com/CurtisDeCastro/decastro-sigma-skills.git
/plugin install decastro-sigma-skills@decastro-sigma-skills
```

### Cursor

Configure `.cursor-plugin/plugin.json` from this repo as a Cursor plugin source.

### OpenAI Codex

Codex auto-loads this `AGENTS.md` and the `skills/` directory from the repo root.

### Snowflake Cortex Code

Inside a Cortex Code session:

```
/skill add https://github.com/CurtisDeCastro/decastro-sigma-skills.git
```

To update to the latest version:

```
/skill sync
```

## Skills

Agents activate these automatically based on the user's request.

- **sigma-workbook-builder** — **Start here for workbooks.** Build production Sigma workbooks in code: production defaults (native elements over hand-built cards, theme-driven styling, live formulas instead of typed numbers, two-tier sourcing), verified element/layout/formula shapes, and the traps that pass `spec/verify` and still render wrong.
- **report-to-workbook** — Rebuild an existing report (screenshot, PDF, HTML, or the script that emits one) as a live Sigma workbook on your own data.
- **sigma-workbook-styling** — Visual craft: the `style` object, theme tokens, repeated containers, images and icons, composition.
- **sigma-plugin-development** — Build a custom Sigma plugin with the `@sigmacomputing/plugin` SDK (derived from Neil Oliver's plugin skills). `examples/plugins/` has eighteen worked plugins named by function.
- **sigma-plugin-patterns** — Architectural recipes for plugins (config, state, interaction).
- **sigma-api** — Authenticate against the Sigma REST API. Prerequisite for the others. *(vendored from upstream)*
- **sigma-cli** — Drive Sigma from the `sigma` CLI. *(vendored from upstream)*
- **sigma-data-models** — Create, retrieve, or modify a Sigma data model spec via the REST API. *(vendored from upstream)*
- **sigma-embed** — Server-side embed URLs (JWT signing) and per-customer workbook variants via version tags.

## Tooling

`scripts/` carries the CLI-authed transport plus `shot.py`, which renders a page or element
to PNG. Rendering is not optional: `spec/verify` checks structure, not whether anything
renders — a spec can pass verify and still render every tile broken.

See [`README.md`](./README.md) for full details.
