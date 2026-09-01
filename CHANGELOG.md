# Changelog

All notable changes to this project will be documented in this file.

## v0.5.0 — 2026-09-01

Upstream syncing, first tagged releases, and the report-to-data-model step that the
builder was missing.

### Added

- **`bin/sync-upstream.sh`** — vendored sync for the skills that come from Sigma's official repo. Reports drift by default, `--apply` takes upstream's version. Replaces `git merge upstream/main`, which conflicts on `README.md`, `CHANGELOG.md` and all four manifests every time because those have deliberately diverged. Vendored skills carry a `.upstream` marker naming the source commit.
- **`sigma-cli`** — vendored from upstream, which had added it after this repo forked.
- **`sigma-workbook-builder/reference/report-to-data-model.md`** — reading a report image into a table list: find the engines behind the sections (a nine-section report is usually two or three computations), name each grain in one sentence, take the parameter grid off the matrix axes, emit both decimal and integer-percent forms, and calibrate magnitudes before building any UI.

### Changed

- The exemplar spec is now positioned as **an illustration of the defaults, not a template to clone** — the point of the skill is that the principles in `production-defaults.md` are applied on the first pass, not that one cached spec is reproduced.
- `README.md` documents the vendoring model and the SAML caveat (the GitHub API for `sigmacomputing` is gated; plain `git fetch` is not).

### Fixed

- `README.md` claimed "Releases are tagged `vX.Y.Z`" when no tags existed. `v0.3.0`, `v0.4.0` and `v0.5.0` are now tagged.

## v0.4.0 — 2026-08-31

Plugin capability: the workbook builder can now recognise a visualization gap, decide
whether it justifies a custom plugin, build one, and walk the user through deploying it.

### Added

- **`sigma-workbook-builder/reference/plugins.md`** — the native-element-first decision list (native → native + conditional formatting → cosmetic-only? → plugin), how to wire a `plugin` element into a spec and its two gotchas (`plugin.style` takes a 6-digit hex only; PNG export never idles for a continuously animating plugin), the localhost-by-default hosting stance, and a deployment walkthrough covering host choice, the governance question to ask first, registration, the **set-once `pluginId`** (the Plugins API has no update endpoint), and MCP servers that can automate deploys.
- **`examples/plugins/`** — eighteen working plugins, renamed by function (`channel-sankey`, `capital-flow-chord`, `demand-clock`, `order-book-depth-ladder`, `project-gantt`, …) with a catalogue README. Serves as both a check-before-you-build library and the authoring pattern to copy.
- Plugin step added to the builder's procedure, and honesty rules noting that a locally-served plugin renders only on the machine serving it.

### Changed

- **`sigma-plugin-development`** and **`sigma-plugin-patterns`** now credit Neil Oliver's `neil-oliver/sigma-plugin-skills` as their source, in the skills themselves and in `NOTICE`.
- Plugin examples were genericised: company names, live deployment URLs, and hosting site IDs removed.

## v0.3.0 — 2026-08-31

Workbooks-as-code: a production workbook builder, report replication, styling, plugin
skills, and the CLI transport + render tooling to run them. Repository identity corrected.

### Added

- **`sigma-workbook-builder`** — the production workbook authoring skill. `reference/production-defaults.md` (ten defaults + a first-pass checklist: native elements over hand-built cards, `name`/`description` over caption text, page-header panels, theme-driven styling, live formulas instead of typed numbers, pivot totals/layout/sort, two-tier sourcing, patching the live spec), `reference/element-shapes.md` (verified shapes for every element kind, controls, layout XML, formulas), `reference/traps.md` (what passes `spec/verify` and still renders wrong), `reference/demo-vs-production.md` (which lessons transfer from demo-oriented examples and which do not), and `examples/exemplar-spec.json` — a complete production-shaped workbook that verifies as a create payload.
- **`report-to-workbook`** — rebuild an existing report from a screenshot, PDF, or HTML into a live workbook on your own data.
- **`sigma-workbook-styling`** — visual craft: `style` object, theme tokens, repeated containers, images/icons, composition.
- **`sigma-plugin-development`**, **`sigma-plugin-patterns`** — custom plugin SDK reference and architectural recipes.
- **`scripts/`** — CLI-authed transport (`sigma_spec`, `sigma_api`, `sigma_auth`, `compose/grid.py`), warehouse discovery and publish helpers under `api/`, `validate-spec.py`, and **`shot.py`** for PNG rendering of a page or single element.

### Fixed

- **Installation never worked.** Every install path — README, `AGENTS.md`, and all four plugin manifests — pointed at `sigmacomputing/sigma-agent-skills`, so following the instructions installed Sigma's official skills rather than this repository's.
- **Repository identity.** Manifests declared `name: sigma-computing`, `author: Sigma Computing`, and the official repo as `repository`. `CODEOWNERS` assigned review to `@sigmacomputing/docs`, and `SECURITY.md` routed vulnerability reports for this code to Sigma's product VDP. All corrected, with `NOTICE` added to attribute the three skills derived from Sigma's Apache-2.0 repo.

## v0.2.0 — 2026-05-28

New `sigma-embed` skill for generating Sigma embed URLs and managing per-customer workbook variants via version tags.

### Added

- **`sigma-embed`** — Generate server-side embed URLs (JWT signing via built-in `node:crypto`, no npm deps) and manage per-customer workbook variants. Covers embed vs. admin credential separation, tagged workbook URL construction (`/tag/{name}` path segment), per-customer spec composition via a `CUSTOMER_CONFIG` pattern, automated tag provisioning with auto dry-run when credentials are absent, and escalation guidance to data model tags for more complex cases. Includes `scripts/generate-embed-url.js` for quick verification and three reference files: `reference/customer-config.md`, `reference/tag-sync.md`, and `reference/escalation.md`.

## v0.1.3 — 2026-05-21

`sigma-api` base-URL allowlist resynced with the current published hosts.

### Changed

- **`sigma-api`** — `scripts/get-token.sh` allowlist now matches the 12-row Base URL table in `SKILL.md`: adds AWS US East / AU Sydney, Azure US/Europe/Canada/UK, and GCP Saudi Arabia, and corrects stale AWS Canada/Europe/UK and Azure US hostnames. Tightened the `SKILL.md` copy pointing users at **Administration → Developer Access** for their base URL.

## v0.1.2 — 2026-05-01

`sigma-api` region/base-URL list synced with the Sigma help docs.

### Changed

- **`sigma-api`** — Replaced the 6-row Base URL table with the full 12-row list from [Supported regions, data platforms, and features](https://help.sigmacomputing.com/docs/region-warehouse-and-feature-support) and linked that page as the source of truth. Adds US East, AU Sydney, three new Azure regions (Europe, Canada, UK), and GCP Saudi Arabia. Corrects stale AWS Canada/Europe/UK and Azure US hostnames.

## v0.1.1 — 2026-04-30

Security hardening for `sigma-api/scripts/get-token.sh` and minor copy edits.

### Changed

- **`sigma-api`** — `scripts/get-token.sh` now pins `$SIGMA_BASE_URL` to the published Sigma cloud hosts, strips the newline `base64` inserts at 76 columns, validates the returned token against the RFC 6750 bearer-token alphabet, and quotes the token via `printf %q` before emitting the `export` line. Together these prevent a hostile or spoofed token endpoint from injecting shell metacharacters into the caller's `eval`.
- **`sigma-data-models`** — Reworded the Requirements line in `SKILL.md` to describe API-credential permissions in terms of Sigma capabilities (create/edit data models, "Can edit" on the folder), and to point users at their Sigma admin on 403.

## v0.1.0 — 2026-04-30

Initial public release of `sigma-agent-skills`.

### Added

- **`sigma-api`** — Authenticate against the Sigma REST API. OAuth client-credentials flow, per-cloud base URLs (AWS US/Canada/Europe/UK, GCP, Azure), bearer token exchange via `scripts/get-token.sh`, and HTTP status-code reference.
- **`sigma-data-models`** — Create, retrieve, and modify Sigma data model specs (sources, columns, metrics, relationships, filters, controls, folder groupings, column-level security) via the REST API.
- Multi-provider packaging: Claude Code plugin (`.claude-plugin/`), Cursor plugin (`.cursor-plugin/`), Snowflake Cortex Code provider metadata (`.cortex-plugin/`), and `AGENTS.md` for OpenAI Codex / Cortex Code session context.
- Cortex Code auto-discovery via `.cortex/skills/` symlinks.
