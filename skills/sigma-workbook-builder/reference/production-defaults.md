# Production defaults

Every rule here replaces a first-pass mistake that a reviewer had to correct. Treat them
as the default; deviating needs a reason you can say out loud.

## 1. Reach for the native element before composing one

The single most common failure: building a "KPI card" out of a container + a label text +
a value + a limit text + a status text. Five elements that don't resize, don't theme,
don't inherit interactions, and can't be maintained.

Sigma's `kpi-chart` already does value, title, subtitle, and comparison-against-a-target.
The target is just a constant-formula column:

```jsonc
{"kind":"kpi-chart","source":{"kind":"table","elementId":"t-scn"},
 "columns":[{"id":"kv","formula":"<metric>","format":{"kind":"number","formatString":",.0f"}},
            {"id":"kl","formula":"-400000","name":"Limit -400,000"}],
 "value":{"columnId":"kv"}, "comparisonColumn":{"columnId":"kl"},
 "comparison":{"display":"delta","colorGood":"#1E7A3C","colorBad":"#B4231A"},
 "name":"Spot −10% / Vol +20%"}
```

That renders `↑ 3,158,415 vs Limit -400,000`, green above the limit and red below,
**automatically from the sign** — no status formula, no conditional colour logic, five
elements collapse to one. Ask the same question of every tile you are about to hand-build.

## 2. Titles are element properties, not text elements

Use the element's own `name` and `description`:

```jsonc
"name": {"fontWeight":"bold","text":"Market Shock Matrix"},
"description": {"text":"index/ETF shock · total portfolio P&L across the grid"}
```

A caption text element above a chart is an anti-pattern: it doesn't move with the element,
doesn't theme, and doubles your layout bookkeeping. Note `description` is **plain text** —
`{{ }}` will not interpolate there, and on a `kpi-chart` it renders as an ⓘ tooltip rather
than visible text.

## 3. Page headers are a panel, not a container at the top of page 1

```jsonc
"panels":   [{"id":"h1","type":"header","title":"Header 1","pages":["pg","util"]}],
"settings": {"navigation":{"pageHeader":"enabled"}}
```
plus a `<Panel …>` tag as a **sibling of `<Page>`** in the layout XML. A real header
persists across pages and tabs; a container does not. (Older guidance calling page headers
UI-only is out of date.)

## 4. Let the theme carry styling

Set the theme once — colours, fonts, `pageWidth`, `space`, `tableStyles` — and then write
**almost no per-element `style`**. Use Sigma's typography classes in text bodies rather
than hardcoded sizes and colours:

```html
<p class="p-large">**Options Arbitrage Risk Report**</p>
<p class="p-small">Report group **OPTIONS ARB (8873)**</p>
```

Per-element hex fights the design system, breaks under a theme change, and is the reason a
code-built workbook looks "almost right." Reserve literal hex for intentional accents:
heatmap bands, status colours, a brand chip.

## 5. Every number in prose is a formula

If a sentence states a count, a total, or a date, it must be computed:

```html
<p class="p-small">Snapshot {{Now()}} · **{{CountDistinct([Positions/Position ID])}}**
positions / **{{CountDistinct([Underliers/Symbol])}}** underliers</p>
```

Typed constants rot silently and are the fastest way to lose a room's trust. This applies
to callouts and footnotes too — "165 names in the low-vol tier" should be
`{{CountDistinct(...) - CountIf(... >= 30)}}`, not `165`.

Keep genuine **policy constants** static — thresholds, limits, window lengths, report
codes. Those are inputs, not measurements.

> `{{ }}` interpolates in a text element **`body` only**. A bare `<` inside an
> HTML-wrapped body is parsed as a tag open and kills the interpolation, so write
> conditions with `>=` only (flip the operands) or escape as `&lt;`.

## 6. Pivot defaults

```jsonc
"totals":  {"showGrandTotals":"hidden","showSubtotals":"when-collapsed"},
"display": {"rowLayout":"separate-columns"},
"rowsBy":  [{"id":"sym","sort":{"by":"pnl","direction":"descending"}}]
```

- **Grand totals off** unless the source report shows them.
- **`separate-columns`** whenever there is more than one row dimension — otherwise each
  entity collapses into an indented three-row stack instead of real side-by-side columns.
- **Sort by the value column**, using `by` (not `columnId`, which verifies and then
  silently sorts alphabetically). If a subtitle says "largest first", make it true.

## 7. Information architecture mirrors the source

If you are rebuilding something, its nav is the answer — same tabs, same order, same
wording. Put everything inside the tabbed container so the tab list is the whole IA. Give
each content tab a wrapper container so it reads as one card, and keep the element inside
it flat to avoid a double border.

Keep sibling grid spans **disjoint** — overlapping siblings silently reorder or drop.

## 8. Two-tier sourcing

Data model holds the SQL-backed tables. The workbook holds thin **spine tables**, one per
data-model node, on a hidden page. Every visual sources from a spine table. Swapping
environments then becomes one id change rather than an edit to every tile.

Spine columns must be qualified with the **data-model element's name**
(`[Scenario PnL/P&L]`); a bare `[P&L]` passes verify and then renders every downstream tile
as "Reference to errored column". So the workbook table's `name` must differ from the
data-model element's name.

## 9. Add the thing a static report cannot do

One agent bound to the underlying tables, with instructions stating the real metric
definitions and what "bad" looks like. This is the concrete answer to "why not keep
emailing the PDF" — the recipient can ask a follow-up without the author re-running
anything. A `chat` element silently drops `name`/`description`, so give that tab a text
heading.

## 10. Iterate against the live spec

Once anyone has touched the workbook in the UI, never regenerate over it — a generated
spec is a full replacement. Patch the live spec: `get_spec()` → mutate → `verify` →
`update`, fetching at runtime (Sigma enforces optimistic concurrency on a round-tripped
spec) and keeping layout edits idempotent.

---

## First-pass checklist

Run this before you call a build done. Each line is something that took a review cycle:

- [ ] Every KPI is a real `kpi-chart`; no card is assembled from text elements
- [ ] Limits/targets use `comparisonColumn`, not a hand-written status formula
- [ ] No caption text elements — titles are `name` + `description`
- [ ] Header is a `panels` entry, not a container
- [ ] Text elements carry almost no `style`; typography comes from `p-*` classes
- [ ] No typed number anywhere in prose
- [ ] Grand totals hidden; `separate-columns` on every multi-row pivot
- [ ] Every "top/largest/worst" claim is backed by a real `sort.by`
- [ ] Tabs match the source IA in order and wording
- [ ] All visuals source from spine tables, not the data model directly
- [ ] An agent exists and is bound to the right tables
- [ ] **You have looked at a rendered PNG of every tab**
