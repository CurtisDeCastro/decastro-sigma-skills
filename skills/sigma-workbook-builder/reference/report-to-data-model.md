# Deriving the data model from a report

A report image tells you more about the model than it looks like. Read it properly and the
table list falls out; guess at it and every tile inherits the mistake.

## Find the engines, not the sections

A report with nine sections usually has **two or three computations** behind it, rendered
several ways. Ask of each section: *what would I have to compute to produce this?* Sections
that share an answer share a table.

Worked example — an options-desk risk report with nine nav items resolved to four tables:

| the report showed | the engine behind it |
|---|---|
| 3 headline shock cards, and an 11×9 spot × vol matrix | **one** grid: every position repriced at every (spot, vol) pair |
| a per-name matrix across −3…+3 earnings moves | a second reprice, bucketed by move size |
| a per-name vol table with tier-based shock policy | the instrument dimension |
| "775 positions / 220 underliers" in the header | counts over the position fact |

Three headline cards and a 99-cell matrix are **the same table**, queried differently. That
recognition is the whole exercise — build one table per engine, never one per section.

## Name the grain in one sentence, before any SQL

Write it down literally: *"one row per position per spot-shock per vol-shock."* If you
cannot say it in a sentence, the table is doing two jobs. Most operational reports need
some combination of:

- **dimension** — one row per entity (instrument, account, store, patient, SKU)
- **fact** — one row per underlying record (position, order, claim, ticket, visit)
- **scenario grid** — fact × parameter × parameter, one row per cell
- **bucketed** — entity × bucket, one row per (entity, bucket)

## Read the axes for the parameters

A matrix hands you its own parameter space. Column headers `-40% … +40%` and row headers
`-40% … +40%` mean a cross join of two shock vectors against the fact table. Bucket headers
`−3 −2 −1 +0 +1 +2 +3` mean a bucket dimension joined to a per-entity reprice. Take the
literal values from the image — they are the customer's chosen grid, not yours to round.

## Emit two forms of anything you both display and match on

Axis labels want a decimal formatted `.0%` so the header reads `-40%`. Card lookups want an
**integer percent**, because exact equality against a binary float (`-0.1`) is not safe.
Emit both columns and use each where it belongs.

## Where the numbers come from

The calculation already exists somewhere — a script, a notebook, a stored proc, a vendor
system. Your job is to land its *result shape* in the warehouse and put a governed model
over it. In priority order:

1. **An existing warehouse table** that already holds the output. Best case; just model it.
2. **Port the calculation into SQL/dbt** so it runs where the data lives. This is the right
   answer for anything recomputed on a schedule.
3. **Land the script's output** on a schedule if the logic can't move (a pricing library, a
   vendor risk engine). The model reads the landed table.

What you must not do is **invent the numbers to make the picture look right.** If a value
can't be sourced yet, say so and stub the column visibly — an empty tile is honest, a
plausible fabricated one is not. See `demo-vs-production.md`.

## Calibrate before you build any UI

Publish the model, then check row counts and magnitudes against the report. Headline
figures should land in the same order of magnitude, with the same signs and the same shape
(if the source matrix is U-shaped, yours should be too — that shape encodes real behaviour).

A mismatch here is a model bug. Fix it upstream; do not tune a constant until the tile
looks right. That single habit is most of the difference between a production workbook and
a demo.
