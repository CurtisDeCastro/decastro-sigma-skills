# Demo workbooks vs production workbooks

Most publicly available Sigma workbook examples — including Sigma's own pre-sales demo
generators — are built to a different brief than yours. The craft in them is real. The
data strategy is not transferable.

| | demo workbook | production workbook |
|---|---|---|
| optimises for | impact in the first ten minutes of a first call | correct numbers, maintained for years |
| data | sample data reshaped into the prospect's world | your warehouse, reconcilable to a system of record |
| magnitudes | tuned so headlines "land believably" | whatever the data says; a 100× error is a bug upstream |
| lifecycle | frozen generator, forked per prospect | one artifact, versioned and evolved |
| novelty | bespoke plugins as a wow moment | native elements first; a plugin is code you now own |

## What transfers

- **Element and layout shapes** — container nesting, the 24-column grid, tabbed
  containers, hidden utility pages, overlays.
- **The build envelope** — one module producing a spec, `spec/verify` before push,
  `create` vs `update`-in-place, ids tracked so a re-run updates rather than duplicates.
- **Agent wiring** — `agents[]`, `greeting`, `dataSources`, action tools.
- **Input-table and scenario patterns** — cross-join → linked input table → computed
  columns is a genuinely reusable data-app shape.
- **Plugin authoring** — `configureEditorPanel` bindings, `ResizeObserver` on the stage
  element, a `synth()` fallback, no infinite animation loop.

## What does not

- **Reshaping sample data into an invented domain.** Demo builds hash a retail POS table
  into sectors, tickers, or loan books so a demo can run with no customer data. If you
  find yourself writing `MOD(ABS(HASH(...)), 6)` to manufacture a dimension, stop — in
  production the dimension exists upstream or the model is wrong.
- **Tuned magnitudes.** Demo builds scale a base constant until the headline number looks
  plausible. In production, a number that is off by 100× is a defect to fix in the model,
  not a constant to nudge.
- **"Wow" as the ordering principle.** Gradient KPI bands, animated tickers, and bespoke
  plugins exist to be memorable on a first call. Ask first whether a native element does
  the job — it themes, resizes, and survives upgrades.
- **Fork-per-customer.** A frozen generator cloned per prospect is a demo workflow. Your
  workbook is one artifact you version.
- **Localhost plugin hosting and `visibleAsSource` sprawl.** Fine on a laptop; neither
  survives contact with real users.

## The tell

If a build's comments explain *why a number was chosen*, you are reading demo logic. In
production, no one chooses the number.
