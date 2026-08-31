# Traps that pass `spec/verify`

`spec/verify` checks structure. It does not check that anything renders. On one build a
spec passed verify, passed the linter, and round-tripped cleanly through GET — and
rendered **every tile** as "Reference to errored column." Only the PNG caught it.

Each item below was found by looking at a render, not by reading an error.

## Silent-wrong (verify passes, output is wrong)

| trap | symptom | fix |
|---|---|---|
| Spine column referenced bare (`[P&L]`) instead of qualified by the **data-model element name** (`[Scenario PnL/P&L]`) | every downstream tile: "Reference to errored column" | qualify; and make the workbook table's `name` differ from the data-model element's |
| Pivot `sort: {"columnId": …}` | sorts the dimension alphabetically, silently | the key is **`by`** |
| Overlapping sibling grid spans | one element silently reorders or disappears | keep spans disjoint |
| Multiple `rowsBy` without `display.rowLayout` | each entity becomes an indented 3-row stack | `"rowLayout":"separate-columns"` |
| A bare `<` inside an HTML-wrapped text body | the whole `{{ }}` renders as literal formula text | use `>=` only, or `&lt;` |
| `{{ }}` placed in a `description` | renders the formula literally | descriptions are plain text; use a text element |
| Date `formatString: "MM/DD/YYYY"` | renders literally | strftime: `%m/%d/%Y` |

## Hard-fail at render (verify passes, tile crashes)

- **`conditionalFormats` on a `kpi-chart`** → Sentry error tile where the KPI should be.
  KPI value-colour rules are UI-only. Use the comparison's `colorGood`/`colorBad` instead.

## Misleading errors

- **`Invalid kind: "<kind>"`** almost always means an unrecognised **field** on that
  element, not a bad `kind`.
- **`conditionalFormats[].value` type mismatch** — if the server demands a *string* for an
  obviously numeric column, your column reference is broken upstream; fixing the reference
  makes it demand a number.
- **Masked 500 on PUT** — usually an unrecognised layout XML tag or an unsubstituted
  `__PLACEHOLDER__`.

## Rejected outright (worth knowing before you write them)

- `style.padding` accepts only `"none"` or omission. For inset, nest inside the grid.
- `cellSpacing`: `"small"`, not `"condensed"`. `borderRadius`: `pill` | `round` | `square`.
- `comparison.direction` accepts only `"none"`; `display` accepts `delta` | `absolute`.
- A pill's `background-color` must be a **literal** — the server validates it at spec time,
  so a pill colour can never be driven by a formula.
- A table element with no `columns` is rejected.
- An element not placed in the layout is rejected — put data spines on a hidden page.
- Sigma's conjunction is the **`and` keyword**; there is no `And()` function. Booleans
  compare bare (`= True`); `= "true"` errors.

## Destructive

- **Never apply pivot cell-colour formatting in the UI.** It permanently breaks GET-spec
  (500) for that workbook, at every version, until it is removed again. Author heatmaps in
  the spec.
- **Never regenerate over a workbook someone has edited by hand.** Patch the live spec.

## Rendering

- PNG export renders only the **active** tab — scope to an element id to inspect another.
- The header panel renders on every tab, which makes it a free formula test bed: drop a
  candidate formula in, render, read the value, restore.
- A PNG taken immediately after a push can show stale or unevaluated content. Wait a few
  seconds. Never debug a formula on the strength of one immediate screenshot.
