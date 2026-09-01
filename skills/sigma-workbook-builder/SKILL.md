---
name: sigma-workbook-builder
description: >-
  THE workbook builder — use when authoring, editing, or reviewing a Sigma workbook in
  code (workbooks-as-code / the /v2/workbooks/spec API) for PRODUCTION use in your own
  environment, on your own warehouse data. Triggers: "build a Sigma workbook in code",
  "workbooks as code", "author a workbook spec", "add a page/KPI/pivot/agent to this
  workbook", "why does my spec render blank", "our numbers are wrong in the workbook",
  "programmatically update a Sigma workbook". Carries the production defaults (native
  elements over hand-built cards, theme-driven styling, live formulas instead of typed
  numbers, pivot totals/layout/sort, two-tier sourcing), the verified element shapes, and
  the traps that pass spec/verify and still render wrong. Use **report-to-workbook** when
  the input is an existing report to replicate. Prerequisite: an authenticated Sigma CLI.
---

# Building production Sigma workbooks in code

This is for workbooks people depend on: real warehouse data, numbers that have to
reconcile, and a team that maintains the thing for years.

> **On borrowed examples.** Most public Sigma workbook examples — including Sigma's own
> pre-sales demo generators — are built to a different brief: impact on a first call, on
> sample data. Their element shapes, layout, agent wiring and plugin patterns transfer
> directly; their **data strategy does not**. Read `reference/demo-vs-production.md` before
> borrowing from any of them.

## Read in this order

| file | what it gives you |
|---|---|
| `reference/production-defaults.md` | **start here** — the ten defaults + a first-pass checklist |
| `reference/element-shapes.md` | verified shapes for every element kind, controls, layout XML, formulas |
| `reference/traps.md` | what passes `spec/verify` and still renders wrong |
| `reference/demo-vs-production.md` | which lessons to take from demo-oriented examples, and which to refuse |
| `reference/visual-fidelity.md` | matching an existing report's look — extract its visual system, then let the theme cascade |
| `reference/report-to-data-model.md` | reading a report image into a table list, grain, and parameter grid |
| `reference/plugins.md` | when a visualization gap justifies a custom plugin, how to wire one in, and how to get it deployed |
| `examples/exemplar-spec.json` | the defaults applied end to end — read it to see what "done" looks like, not to clone |

## Procedure

1. **Model first.** Work `reference/report-to-data-model.md`: find the engines behind the
   sections, name each table's grain in one sentence, and calibrate against the source
   *before* building any UI — every tile inherits a scale error.
2. **Two-tier sourcing.** Data model → thin spine tables on a hidden page → every visual
   reads a spine table. Swapping environments becomes one id change.
3. **Compose with native elements.** Work down `production-defaults.md`. If you are about
   to hand-build a tile out of text elements, check what the native element already does.
4. **Hit a visualization Sigma can't do natively?** Work the decision list in
   `reference/plugins.md` — native element, then native + conditional formatting, then a
   plugin. If a plugin is genuinely warranted, `sigma-plugin-development` builds it and
   `examples/plugins/` has eighteen worked ones named by what they do.
5. **Theme once, style almost never.** If you are matching a source, extract its visual
   system first (`reference/visual-fidelity.md`) — canvas tone, border weight, radius,
   density, accent and status colours are *read off the image*, not chosen. Set them on
   the theme and write almost no per-element `style`.
6. **Verify by rendering.** Below.
7. **Ship it as code.** One command rebuilds the workbook, so a change is a reviewable
   diff. That is the point of building this way.

## Running it

Auth is the Sigma CLI and nothing else (`sigma auth login`). From the package root:

```bash
scripts/api/preflight.sh                       # confirm auth first
scripts/api/list-connections.sh                # get a connectionId
scripts/api/list-folders.sh                    # get a folderId
scripts/api/probe-schema-tables.sh <conn> <DB> <SCHEMA> <TABLE…>
scripts/api/list-table-columns.sh <inodeId>
scripts/api/publish-datamodel.sh post model.json
scripts/api/publish-workbook.sh  post workbook.json    # lints, then POSTs
python3 scripts/shot.py <workbookId> out.png <pageId>  # render — the verification step
ELEMENT=<elementId> python3 scripts/shot.py <workbookId> tile.png <pageId>
```

In Python: `sigma_spec.verify / create / update / get_spec`, `grid.envelope()` to build the
spec body, `validate-spec.py` to lint before pushing.

## The loop

```
generate → spec/verify → push → export PNG → ACTUALLY LOOK AT THE IMAGE → fix
```

`spec/verify` checks structure, not whether anything renders. A spec can pass verify, pass
the linter, round-trip cleanly through GET, and still render every tile broken. Budget a
render after every push; see `reference/traps.md`.

## Changing a workbook that already exists

Never regenerate over a workbook someone has edited in the UI — a generated spec is a full
replacement and will erase their work. Patch the live spec instead:

```python
spec = sigma_spec.get_spec(WB)      # fetch at RUNTIME, not from a saved snapshot
...                                  # mutate
ok, _ = sigma_spec.verify(spec)
sigma_spec.update(WB, spec)
```

Sigma enforces optimistic concurrency on a round-tripped spec ("The document has changed
since it was read"), so a stale snapshot is refused. Make layout edits idempotent so a
re-run is safe. See `scripts/` for the transport helpers this uses.

## Standards worth holding

- **Numbers in prose are formulas, never typed constants.** A stale hardcoded count is the
  fastest way to lose trust in the whole workbook.
- **Don't claim an order you haven't applied** — if a subtitle says "largest first", the
  pivot needs a real `sort.by`.
- **Say plainly when you are standing in sample or placeholder data.** Once, early.
- **Prefer a native element to a plugin.** A plugin is code you own, host, and secure —
  `reference/plugins.md` has the decision list and the honest cost.
- **A locally-served plugin renders only on your machine.** Say so when you build one;
  don't let someone discover it from an empty tile in a shared workbook.
