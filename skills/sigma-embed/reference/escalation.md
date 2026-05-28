# When to Escalate Beyond Workbook Tags

The workbook-tag approach handles most per-customer embedding scenarios. This reference describes signals that indicate you've reached its ceiling and what to reach for next.

## Signals

| Signal | Implication |
|--------|-------------|
| Customers need different source databases or connection credentials | Workbook tags share the same data connection — escalate to connection-level isolation |
| Row-level security policies differ per customer | Workbook tags share the same query path — data model CLS or warehouse-level RLS is the right layer |
| Per-customer column names are driven by warehouse schema (not a config object) | Column names must be encoded at the data layer, not the workbook layer |
| More than one table or element needs per-customer customization | `CUSTOMER_CONFIG.extraColumns` scales poorly across multiple elements — data model inheritance handles this more cleanly |
| Column names must change dynamically at embed request time | Tags are immutable snapshots — dynamic bindings require a different mechanism |

## The Data Model Escape Hatch

Sigma data models expose a public REST API (`PUT /v2/dataModels/{id}/spec`, see `sigma-data-models` skill) and support version tagging. Workbooks can be bound to a tagged version of a data model via `dataModelSourceTaggedVersions` on `POST /v2/workbooks/tag`.

This means:
- One workbook visual layer shared across all customers
- Per-customer column names and schema differences encoded in the data model spec
- The tag provisioning step binds the workbook to the matching data model tag

## Recommended Progression

```
Stage 1 — Single embed
  One workbook, no customization
  → SKILL.md Step 1

Stage 2 — Per-customer column variants
  One canonical workbook + CUSTOMER_CONFIG + workbook tags
  → SKILL.md Steps 2–4 + reference/customer-config.md + reference/tag-sync.md

Stage 3 — Schema-driven or multi-element customization
  Data model tags bound to workbook tags
  → sigma-data-models skill + reference/tag-sync.md

Stage 4 — Full tenant isolation
  Separate data connections or warehouse schemas per customer
  → Infrastructure-level isolation (outside Sigma embed scope)
```

## What Stays the Same When Escalating

- JWT signing and embed URL construction (SKILL.md Steps 1–2) are identical at every stage.
- The `makeClient` / `onEvent` / dry-run pattern from `reference/tag-sync.md` applies to data model API calls as well.
- Admin credential separation (embed signing vs. admin OAuth) is unchanged.
- The `slugify` convention can be reused for data model tag names.

## Rule of Thumb

Start with workbook tags. Escalate to data model tags only when the customization cannot reasonably be expressed in `CUSTOMER_CONFIG`. Three customers with two extra columns: workbook tags. Twenty customers where column names come from a warehouse metadata table: data models.
