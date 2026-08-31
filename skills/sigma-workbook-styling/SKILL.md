---
name: sigma-workbook-styling
description: >-
  Use whenever the goal is to make a Sigma workbook look polished and
  visually designed — not just correct. Covers the element `style` object
  (background, border, radius, padding), theme color tokens, repeated
  containers (cards/lists that repeat over a data source), images and
  data-URI SVG icons, dividers, and the masthead → cards → detail+sidebar
  composition. Trigger on "make this workbook beautiful", "clean up the
  layout", "add repeated cards", "add a header with our logo", "style this
  dashboard", "make it look like a real app", or any request about the
  visual craft of a workbook. Pair with sigma-workbook-conventions (spec
  mechanics/correctness) and branded-dashboard-format (house layout + a
  specific brand kit); this is the reusable visual-craft layer for ANY
  workbook. When reproducing a look, prefer cloning a spec from
  `../sigma-workbook-builder/examples/` over authoring from scratch.
---

# Sigma Workbook Styling

> **Prerequisite — spec shapes come from `sigma-workbooks-cli`.** That skill (installed
> at user level) is the current source of truth for element, source, control, layout and
> formula shapes, and it drives the `sigma` CLI, which is this plugin's only transport.
> This skill adds what it doesn't cover: our house composition, the verified deltas, and
> the build loop. Where the two disagree, probe with
> `sigma api workbooks spec verify` — the server error is the authority.
>
> **Format changed 2026-08-10:** `document` envelope, `elements` FLAT, `<Element>` /
> `<Container>` tags, theme at `document.settings.theme.overrides`, modals in
> `document.overlays[]`, agents in `document.agents`, and an unplaced element is
> rejected. See `sigma-company-dashboard/reference/api-cheatsheet.md`.


## Finding the scripts (do this FIRST — before any `scripts/...` command)

Every `scripts/...` path in this skill is relative to the **plugin root**, NOT
to the working directory and NOT to this skill's own folder. There is no
`scripts/` inside `skills/<this-skill>/` — looking for one is the single most
common failure here.

Resolve it once and reuse the absolute path for the rest of the session (each Bash
call is a fresh shell, so an exported variable will not persist):

```bash
ls -d "$PWD/scripts" 2>/dev/null \
  || ls -d "$HOME"/.claude/plugins/cache/sigma-workbook-builder/*/scripts | sort -V | tail -1
```

So `scripts/api/preflight.sh` below means `<SCRIPTS>/api/preflight.sh`.

Make Sigma workbooks look *designed* — the difference between a functional
dashboard and something that reads like a real, premium application. This skill
is the visual-craft layer, grounded in three real "beautiful" workbooks whose
specs live in `examples/` (Marketing Control Center, Cold Provisions, Demand
Planning). When in doubt about a shape, open `../sigma-workbook-builder/examples/exemplar-spec.json` and copy from it.

Mechanics live elsewhere:
- **`sigma-workbook-conventions`** — element kinds, the 24-col `<Container>`
  layout XML, ID semantics, POST-time gotchas. Read its
  `reference/workbook-spec-api.md` before authoring layout.
- **`sigma-workbook-builder/reference/production-defaults.md`** — the defaults that
  keep a code-built workbook from looking generated. Read it before styling.

## What round-trips as code (and what doesn't)

Verified against the `examples/` specs — most of the polish **is** in the spec,
which corrects a common misconception that Sigma styling is UI-only:

| In the spec (author or clone it) | Configured in the UI |
|---|---|
| Element `style` — `backgroundColor`, `borderColor`, `borderWidth`, `borderRadius`, `padding`, `backgroundImage`, `fit`, `color`, `align`, `textWrap`, `bold` | The **repeat toggle** on a repeating container (bindings round-trip; the "repeat over this source" switch is finicky — clone it) |
| **Theme color tokens** — `{ "kind": "theme", "ref": "colors-backgroundCanvas" }` used as a color value | Fine live-theme editing / theme creation |
| **Images** — CDN URLs, inline data-URI SVGs, and column-bound `{{[Element/Column]}}` urls | |
| **Column bindings** — `{{[Element Name/Column]}}` inside text `body` and image `url` | |
| Element placement — `gridColumn`/`gridRow`/`gridTemplateColumns`/`Rows` | |

Because the repeat *configuration* is the one fragile piece, the reliable
workflow is **clone-and-modify a known-good spec** from `examples/`, then swap
the data source, columns, and copy. Always verify visually after POST — the API
validates neither cross-element resolution nor visual quality.

## The `style` object — the core of "pretty"

Most element kinds carry an optional `style` object (verified on container,
kpi-chart, image, table, divider, control, and every chart kind). This is where
cards get their fills, borders, and rounded corners:

```json
{
  "id": "card-revenue",
  "kind": "container",
  "style": {
    "backgroundColor": "#FFFFFF",
    "borderColor": { "kind": "theme", "ref": "colors-border" },
    "borderWidth": 1,
    "borderRadius": "pill"
  }
}
```

> **`padding` accepts only `"none"`, or omit it.** This example used to ship
> `"padding": "medium"`, which fails CREATE outright — probed 2026-08-13:
> `style.padding: must be 'none' or omitted — default padding is implied by omitting
> the field`. `small` and `large` are rejected the same way. Omit the field to get
> default padding; pass `"none"` to remove it. For visual inset, nest the child inside
> the container's grid (e.g. `gridColumn="2 / 12"`) rather than reaching for padding.

Property vocabulary (values observed in the real specs):

- **`backgroundColor`** — hex (`#FFFFFF`, `#fbfbfb`) or a theme token.
- **`borderColor`** — hex or `{ "kind": "theme", "ref": "colors-border" }`.
- **`borderWidth`** — `0`, `1`, `3`.
- **`borderRadius`** — keywords **`pill`**, **`round`**, **`square`**. `pill` is
  what gives KPI cards and status chips their soft, modern shape; `round` for
  gently-rounded cards; `square` for crisp panels.
- **`padding`** — only `"none"` (removes it) or omitted (default). Any other value is
  rejected at CREATE; see the note above.
- **`backgroundImage`** — a container can carry a background image (hero blocks).
- **`fit`** — for images: **`cover`** (fill, crop) or **`scale-down`** (contain).
- **`color`** — foreground/text color (hex or theme token).
- **`strokeStyle`** (`solid`), **`textWrap`** (`wrap`/`clip`), **`align`**,
  **`horizontalAlign`** (`start`), **`bold`**.

Prefer **theme tokens over hardcoded hex** for borders and text so the workbook
stays internally consistent and survives a theme change. Reserve literal hex for
intentional brand accents (a gradient card, a status color).

## Repeated containers — cards and lists that scale with data

This is the signature move in the reference workbooks: one container styled as a
card (or list row) that **repeats once per row** of a source element, with its
child text/images bound to that row's columns. It's how you get the KPI card
row, the category cards, and the "Holidays"-style side list without hand-placing
each tile.

The bindings that make it work (these round-trip):

- **Text `body`**: `{{[<Source Element Name>/<Column>]}}` — e.g.
  `{{[Stores/Store Name]}}`. Mix literal text and bindings freely.
- **Image `url`**: `{{[<Source Element Name>/<Column>]}}` — e.g.
  `{{[Stores/Store Image Url]}}` renders a per-row image (logo, product photo,
  avatar).

To build one: **clone a repeated container from `examples/`** (Marketing Control
Center and Cold Provisions both have them), point it at your source element, and
rename the columns in the `{{[...]}}` bindings. Authoring the repeat wiring from
a blank spec is unreliable; cloning is not.

Design intent for repeaters:
- Give every repeated card the **same `style`** so the set reads as a unit; vary
  only the bound content.
- For a **gradient KPI row** (like the Marketing Control Center), the sweep is a
  per-card `backgroundColor` stepping across a hue range — clone the four-card
  block and adjust the stops.
- **Status pills**: a small `pill`-radius container whose `backgroundColor` is
  driven by the row's status (green=approved, amber=pending) — a classic
  repeated-list treatment.

## Images and icons

Three image sources, all verified in the specs:

1. **Hosted URL** — `{ "id": "img-logo", "kind": "image", "url": "https://.../logo.svg" }`.
   Use SVG for logos; host at a stable CDN.
2. **Inline data-URI SVG** — `"url": "data:image/svg+xml;base64,…"`. This is how
   the reference workbooks embed **icons** (lucide icons: thermometer, star, and
   an AI "bot" with a gradient stroke). Great for crisp, dependency-free icons in
   card headers and list rows. Keep an icon set handy and drop them inline.
3. **Column-bound** — `"url": "{{[Element/Column]}}"` for per-row images inside a
   repeater.

Control scaling with `style.fit` (`cover` vs `scale-down`). Place logos and
icons *inside* their container (masthead, card header) so they move with the block.

## Composition: the app-like shape

The reference workbooks share a shape that reads as a product, not a report:

- **Masthead** — a full-width container (often tinted or `backgroundImage`) with
  the logo/app name left and user/profile or filters right.
- **KPI / category card row** — a repeated card block, even columns
  (`gridTemplateColumns: "1fr 1fr 1fr 1fr"`), consistent `style`, each with an
  icon, big number, and a sparkline or progress bar.
- **Body** — primary chart(s); use a 2/3 + 1/3 split rather than full-width stacks.
- **Sidebar** — a repeated list (dates, holidays, activity) as pill-radius rows.
- **Detail band** — a table at the bottom with styled status pills.
- **`divider`** elements separate bands cleanly.

Rhythm rules: consistent gutters and one border-radius language throughout;
generous whitespace (don't fill every grid cell); a clear title `text` on every
page (the workbook `name` is metadata, not a heading); KPI tiles ~8–10 grid rows
tall so sparklines breathe.

## Color, spacing, typography

- **Restraint.** One accent plus neutrals. Let the accent mark the primary metric
  or CTA; keep the rest grayscale via theme tokens.
- **Alignment over decoration.** Even columns and consistent gutters do more for
  "pretty" than any color.
- **Typographic hierarchy.** Page title → section labels above each block →
  readable KPI value/label sizing (`bold`, `color`, `align` on text elements).
- **Match the brand** when there is one — pull palette/font from
  `branded-dashboard-format` rather than reinventing.

## Buttons (pending)

Button elements (open link, set control value, open Sigma doc with passed
controls — see `sigma-workbook-conventions` and Sigma's action docs) aren't
present in the current `examples/`. When a workbook with buttons is added
(e.g. the Oasis app), capture its GET-back spec here and document the exact
button `style` + action shape. Until then, treat button styling as verify-on-build.

## Workflow

1. Pick the closest `examples/` spec and **clone the blocks you need** (repeated
   cards, masthead, styled table) rather than authoring from scratch.
2. Swap the data source and rebind `{{[Element/Column]}}` references; restyle via
   the `style` vocabulary, preferring theme tokens.
3. Publish (`scripts/api/publish-workbook.sh post ...`).
4. GET the spec back and commit it as the new source of truth.
5. Verify visually; if you configured a repeat toggle in the UI, note that step
   so it isn't lost on a rebuild.

## Examples

`../sigma-workbook-builder/examples/exemplar-spec.json` is a complete, production-shaped
GET-back to clone from: a page header panel, native KPI cards with fixed-target
comparisons, diverging-heatmap pivots, themed containers, and an agent. It verifies as a
create payload, so every shape in it is known to work.

Treat it as an immutable reference: clone-and-modify, never edit in place. When you build
something worth reusing, GET its spec back and add it alongside.
