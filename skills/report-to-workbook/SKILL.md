---
name: report-to-workbook
description: >-
  Use when someone has an EXISTING report — a screenshot, PDF, HTML page, or a script
  that generates one — and wants it rebuilt as a live Sigma workbook on their own data.
  Triggers: "turn this report into a Sigma workbook", "we generate this HTML report and
  want it in Sigma", "here's a screenshot of the report we send out", "rebuild this
  report", "make this static report interactive". Self-contained: the build procedure,
  the report-element → Sigma-construct mapping, every verified spec shape needed, and
  the traps that pass spec/verify and still render broken.
---

# Rebuilding an existing report in Sigma

> Pairs with **sigma-workbook-builder** — that skill carries the production defaults, the
> full element-shape reference, and the trap list. This one is the entry point for the
> specific case where the input is a report you already have.

They already have a report that works. Rebuild the *same* report — fidelity is the
requirement, they should recognise it instantly. What Sigma adds is that it stops being a
snapshot: sortable, filterable, drillable, answerable by an agent, and rebuilt by one
command instead of an afternoon of clicking.

## Procedure

1. **Transcribe the image literally, before designing anything.** Title, status pill,
   every field in the metadata line, the nav items, each section heading, each
   sub-caption, the column headers of every matrix. The nav becomes your tabs, same order
   and wording. Sub-captions become element `description`s.
2. **Find the engines, not the sections.** Most operational reports are 2–4 computations
   rendered several ways. One data model table per computation — a scenario grid feeding
   three headline cards *and* a matrix is one table queried two ways.
3. **Publish the data model, then check row counts and magnitudes against the report.**
   Every tile inherits a scale error.
4. **Build the workbook** from the shapes below.
5. **Render it and look at it** — see The loop.

## Report element → Sigma construct

| in the report | build |
|---|---|
| title + chip + metadata line, on every view | a page header **panel** |
| horizontal nav / jump links | a **tabbed container**, tabs in the report's order |
| headline numbers with a threshold | native **`kpi-chart`** + fixed-target comparison |
| a value grid coloured red→blue | **`pivot-table`** + banded `conditionalFormats` |
| descriptive columns before the grid | one pivot, several `rowsBy` + `separate-columns` |
| section heading + sub-caption | the element's own `name` + `description` |
| ranked list ("top contributors") | pivot sorted by its value column (`sort.by`) |
| counts stated in prose | a `{{ }}` formula in a **text body** |
| *nothing in the source* | a **chat element + agent** — what a static report can't do |

24-col grid. Give each content tab a wrapper container so it reads as one card, and keep
the element inside it flat to avoid a double border. **Keep sibling grid spans disjoint —
overlapping siblings silently reorder or drop.** Source tables live on a hidden page; an
unplaced element is rejected.

## Sourcing (two-tier)

Data model holds the SQL-backed tables. The workbook holds thin **spine tables**, one per
data-model node, on a hidden page. Every visual sources from a spine table — so swapping
environments is one id change, not an edit to every tile.

```jsonc
// spine column: qualify with the DATA MODEL ELEMENT'S name
{"id":"c0","name":"P&L","formula":"[Scenario PnL/P&L]"}
```

A bare `[P&L]` passes verify, passes a linter, round-trips through GET — then renders
every downstream tile as **"Reference to errored column."** So the workbook table's own
`name` must differ from the data-model element name. Visuals then use the *workbook* name:
`[Scenario/P&L]`. A table element with no `columns` is rejected outright.

**No `/` in a column name** — it's the element/column separator, so `[Vega $ / pt]` parses
as element "Vega $". Emit both a decimal (for `.0%` axis labels) and an **integer percent**
(for exact-equality lookups; float equality on `-0.1` is not safe).

## Verified shapes

**Page header** — code-representable, all three parts required:
```jsonc
"panels":   [{"id":"h1","type":"header","title":"Header 1","pages":["pg"]}],
"settings": {"navigation":{"pageHeader":"enabled"}}
```
plus a `<Panel …>` tag as a **sibling of `<Page>`** in the layout XML.

**KPI with a limit** — the target is just a constant-formula column:
```jsonc
{"kind":"kpi-chart","source":{"kind":"table","elementId":"t-scn"},
 "columns":[{"id":"kv","formula":"<metric>","format":{"kind":"number","formatString":",.0f"}},
            {"id":"kl","formula":"-400000","name":"Limit -400,000"}],
 "value":{"columnId":"kv"}, "comparisonColumn":{"columnId":"kl"},
 "comparison":{"display":"delta","colorGood":"#1E7A3C","colorBad":"#B4231A"},
 "name":"Spot −10% / Vol +20%"}
```
Renders `↑ 3,158,415 vs Limit -400,000` — **green above the limit, red below, automatically
from the sign.** No status formula needed. `display` takes `delta`/`absolute` only;
`direction` accepts only `"none"` (omit it); `description` is an ⓘ **tooltip**, so anything
that must be read goes in the comparison column's `name`.

**Pivot** — heatmap, layout, totals, sort:
```jsonc
"name":{"fontWeight":"bold","text":"Market Shock Matrix"},
"description":{"text":"…"},
"totals":{"showGrandTotals":"hidden","showSubtotals":"when-collapsed"},
"display":{"rowLayout":"separate-columns"},
"rowsBy":[{"id":"sym","sort":{"by":"pnl","direction":"descending"}}],
"conditionalFormats":[
  {"type":"single","columnIds":["pnl"],"condition":"formula",
   "formula":"[P&L] >= 2400000 and [P&L] < 6600000","includeValues":true,
   "style":{"backgroundColor":"#7FA6CC","color":"#111827"}}]
```
`separate-columns` is what renders multiple `rowsBy` as real side-by-side columns instead
of one indented stack. Bands at ±0.55/0.20/0.05/0.012 of a saturation scale, blue
`#4E7FB3 #7FA6CC #B9CFE4 #DEE9F3` / unpainted / red `#FBE4DE #EFBFB4 #E0937F #D0674B`.
Tables sort differently: top-level `"sort":[{"columnId":…,"direction":…,"nulls":"last"}]`.

**Text, HTML, live numbers:**
```html
<p class="p-small">**{{CountDistinct([Positions/Position ID])}}** positions</p>
<p class="p-small"><span style="color:#FFF; background-color:#59A14E">  Intraday  </span></p>
```
Bodies accept HTML plus `p-large`/`p-small`; markdown nests inside. Pill colour **must be a
literal** — the server validates `background-color` at spec time, so it can never be
conditional. `{{Now()}}` works. Formulas resolve inside `<p>` and without a sourced element
in the same container.

## Traps that pass `spec/verify`

- **`conditionalFormats` on a `kpi-chart` crashes the renderer** (Sentry tile). KPI value
  colour rules are UI-only.
- **A bare `<` in an HTML-wrapped body** is read as a tag open and kills the whole
  interpolation → literal formula text. Write conditions with `>=` only, or `&lt;`.
- **Pivot `sort:{"columnId":…}`** verifies, then silently sorts alphabetically. The working
  key is **`by`**.
- **`{{ }}` does not interpolate in a `description`** — text-element bodies only.
- Boolean compares bare: `= True`. `= "true"` errors.
- Conjunction is the **`and` keyword**; there is no `And()` function.
- `conditionalFormats[].value` must match the column's type. If the server demands a
  *string* for a numeric column, your column reference is broken.
- An unrecognised **field** is masked as `Invalid kind: "<kind>"` — not a bad kind.
- `style.padding` accepts only `"none"`; `cellSpacing` is `"small"`; date `formatString` is
  strftime (`%m/%d/%Y`).
- A `chat` element silently drops `name`/`description` — give that tab a text heading.
- **Never apply pivot cell-colouring in the UI** — it permanently 500s GET-spec for that
  workbook. Author heatmaps in the spec.

## Exemplar

`examples/exemplar-spec.json` is a real GET-back of a finished replication — page header
panel, tabs mirroring the source nav, native KPI cards with fixed-target comparisons,
diverging-heatmap pivots, sorted detail pivots, and an agent. It verifies as a fresh
create payload. **Clone shapes from it rather than authoring from scratch.** Its
`dataModelId` is environment-specific — repoint it, and add a `folderId`.

## The loop

```
generate → spec/verify → push → export PNG → ACTUALLY LOOK AT THE IMAGE → fix
```

`verify` passing means very little: a spec that passed verify, passed the linter, and
round-tripped cleanly through GET once rendered *every* tile as "Reference to errored
column." Only the PNG caught it.

- **PNG export renders only the ACTIVE tab** — render a single element by id to see another.
- **The header panel renders on every tab, so it's a free formula test bed.**
- **Wait a few seconds after a push before rendering** — an immediate PNG can show stale or
  unevaluated content. Never debug a formula on one immediate screenshot.

## Patching a workbook someone has edited by hand

Never regenerate over UI work; a generated spec is a full replacement. Patch the **live**
spec: `get_spec()` → mutate → `verify` → `update`. Sigma enforces optimistic concurrency on
a round-tripped spec ("The document has changed since it was read"), so fetch at runtime,
and make layout edits idempotent.

## Honesty

Say **once, early** if you're standing in sample data rather than their book. Numbers in
prose must be live formulas, never typed constants — a subtitle claiming "largest first"
over an alphabetical sort is what the first analyst in the room notices. Keep genuine
policy constants (thresholds, limits, windows) static; those are inputs, not measurements.
