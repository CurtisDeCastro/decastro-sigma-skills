# Sigma agent skills

Field-tested agent skills for building **production Sigma workbooks in code** — on your own
warehouse data, via the workbooks-as-code API. The same content runs in **Claude Code**,
**Cursor**, **OpenAI Codex**, and **Snowflake Cortex Code**.

> **Not an official Sigma Computing product.** This is an independent library maintained by
> [@CurtisDeCastro](https://github.com/CurtisDeCastro). Sigma's official skills live at
> [`sigmacomputing/sigma-agent-skills`](https://github.com/sigmacomputing/sigma-agent-skills);
> `sigma-api`, `sigma-data-models`, and `sigma-embed` here are derived from that repo
> (Apache-2.0) and may lag it. Everything else is original.

Releases are tagged `vX.Y.Z` — see [`CHANGELOG.md`](./CHANGELOG.md).

## Installation

### Claude Code

```bash
/plugin marketplace add https://github.com/CurtisDeCastro/decastro-sigma-skills.git
/plugin install decastro-sigma-skills@decastro-sigma-skills
```

### Cursor

Configure `.cursor-plugin/plugin.json` from this repo as a Cursor plugin source.

### OpenAI Codex

Codex auto-loads `AGENTS.md` from the repo root.

### Snowflake Cortex Code

```
/skill add https://github.com/CurtisDeCastro/decastro-sigma-skills.git
```

## Skills

| Skill | Description |
|-------|-------------|
| **sigma-workbook-builder** | **Start here for workbooks.** Build production workbooks in code: production defaults (native elements over hand-built cards, theme-driven styling, live formulas instead of typed numbers, two-tier sourcing), verified element shapes, and the traps that pass `spec/verify` and still render wrong. |
| **report-to-workbook** | Rebuild an existing report — a screenshot, PDF, HTML page, or a script that emits one — as a live Sigma workbook on your data. |
| **sigma-workbook-styling** | Visual craft: the `style` object, theme tokens, repeated containers, images and icons, composition. |
| **sigma-plugin-development** | Build a custom Sigma plugin with the `@sigmacomputing/plugin` SDK. Derived from Neil Oliver's plugin skills. |
| **sigma-plugin-patterns** | Architectural recipes for plugins (config, state, interaction). |
| **sigma-api** | Authenticate against the Sigma REST API. Prerequisite for the others. *(vendored from upstream)* |
| **sigma-cli** | Drive Sigma from the `sigma` CLI. *(vendored from upstream)* |
| **sigma-data-models** | Create, retrieve, or modify a Sigma data model spec via the REST API. *(vendored from upstream)* |
| **sigma-embed** | Server-side embed URLs (JWT signing) and per-customer workbook variants via version tags. |

## Examples

`examples/plugins/` — eighteen working plugins named by what they do (`channel-sankey`,
`capital-flow-chord`, `demand-clock`, `project-gantt`, …). Check the catalogue before
building something new; use them as the authoring pattern when you do. They run from
localhost by default — see
[`reference/plugins.md`](./skills/sigma-workbook-builder/reference/plugins.md) for the
native-element-first decision list and the deployment walkthrough.

## Prerequisites

1. **The Sigma CLI**, authenticated — the only auth mechanism. No `.env`, no client secret,
   no token file. `SIGMA_PROFILE=<name>` targets a non-default org.
   ```bash
   sigma auth login && sigma auth status
   ```
2. **Workbooks-as-Code enabled on your org.** There is no admin screen for it — verify by
   calling the endpoint. `200` = enabled; `404` with `errorcause: UnmatchedHandler` = not:
   ```bash
   sigma api workbooks spec get --params '{"workbookId":"<any-workbook-id>"}'
   ```
3. **Python 3.9+**, standard library only.

## Tooling (`scripts/`)

| script | purpose |
|---|---|
| `api/preflight.sh` | confirm CLI auth |
| `api/list-connections.sh` · `api/list-folders.sh` | discovery |
| `api/probe-schema-tables.sh` · `api/list-table-columns.sh` · `api/lookup-path.sh` | warehouse schema |
| `api/publish-datamodel.sh` · `api/publish-workbook.sh` | POST/PUT a spec (lints first) |
| `api/query-element.sh` | fetch the data behind a published element |
| `shot.py` | **render a page or element to PNG** — the verification step |
| `validate-spec.py` | static lint before you push |

Python helpers: `sigma_spec.verify / create / update / get_spec`, `compose/grid.py::envelope()`.

## The loop

```
generate → spec/verify → push → export PNG → LOOK AT THE IMAGE → fix
```

`spec/verify` checks structure, not whether anything renders. A spec can pass verify, pass
the linter, round-trip cleanly through GET, and still render every tile broken — see
`skills/sigma-workbook-builder/reference/traps.md`.

```bash
python3 scripts/shot.py <workbookId> out.png <pageId>
ELEMENT=<elementId> python3 scripts/shot.py <workbookId> tile.png <pageId>
```

PNG export renders only the **active** tab, so scope to an element id to inspect another.

## Staying current with Sigma's official skills

`sigma-api`, `sigma-cli` and `sigma-data-models` are **vendored** from
[`sigmacomputing/sigma-agent-skills`](https://github.com/sigmacomputing/sigma-agent-skills)
and carry a `.upstream` marker naming the commit they came from. Everything else is
original and is never touched by a sync.

```bash
bin/sync-upstream.sh            # report drift, change nothing
bin/sync-upstream.sh --apply    # take upstream's version of the vendored skills
```

This repo began as a fork, but it is deliberately **not** maintained by merging: the README,
CHANGELOG and four manifests have diverged on purpose, so `git merge upstream/main`
conflicts on all of them every time. Vendoring copies only the skill directories.

> The GitHub *API* for `sigmacomputing` is SAML-gated, so `gh` calls against upstream may
> 403. Plain `git fetch` works, which is what the sync script uses.

## License

Apache-2.0. See [`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE).
