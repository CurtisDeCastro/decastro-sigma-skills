# Per-Customer Workbook Configuration

This reference covers the `CUSTOMER_CONFIG` pattern: maintaining per-customer column sets in code and deriving workbook specs programmatically, without creating N separate workbooks in Sigma UI.

## Why Not User Attributes

Sigma user attributes can parameterize formula *values* at embed time. They cannot change column display names. If per-customer column names are required, spec composition with version tags is the correct approach.

## The Config Object

```js
// lib/embed.js

const BASE_COLUMNS = [
  // Columns every customer receives — shared baseline
  { id: 'col-name',    name: 'Name',    type: 'text',     source: 'name' },
  { id: 'col-status',  name: 'Status',  type: 'text',     source: 'status' },
  { id: 'col-created', name: 'Created', type: 'datetime', source: 'created_at' },
];

const CUSTOMER_CONFIG = {
  acme: {
    extraColumns: [
      { id: 'acme-revenue', name: 'Revenue', type: 'number', source: 'revenue' },
    ],
  },
  beta: {
    extraColumns: [],   // base columns only; still gets its own tag for isolation
  },
};
```

## Spec Composition

```js
// Named constants — confirm IDs by exporting the workbook spec once via the API
const PAGE_ID    = 'page-1';
const ELEMENT_ID = 'element-1';
const BASE_SOURCE = { type: 'table', schema: 'PUBLIC', table: 'orders' };

// Per-customer spec: base + extra columns
function buildSpec(customerId) {
  const customer = CUSTOMER_CONFIG[customerId];
  if (!customer) throw new Error(`Unknown customer: ${customerId}`);
  const columns = [...BASE_COLUMNS, ...(customer.extraColumns ?? [])];
  return {
    name: `Customer ${customerId}`,
    pages: [{
      id: PAGE_ID,
      name: 'Page 1',
      elements: [{
        id: ELEMENT_ID,
        kind: 'table',
        source: BASE_SOURCE,
        columns,
        order: columns.map((c) => c.id),
        visibleAsSource: false,
      }],
    }],
  };
}

// Template spec: base columns only, never embedded directly
function buildTemplateSpec() {
  const columns = [...BASE_COLUMNS];
  return {
    name: 'Template',
    pages: [{
      id: PAGE_ID,
      name: 'Page 1',
      elements: [{
        id: ELEMENT_ID,
        kind: 'table',
        source: BASE_SOURCE,
        columns,
        order: columns.map((c) => c.id),
        visibleAsSource: false,
      }],
    }],
  };
}
```

## Slug Derivation

Tag names must be URL-safe. Derive slugs deterministically from the customer identifier:

```js
function slugify(customerId) {
  return 'customer-' + String(customerId)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
// slugify('Acme Corp') → 'customer-acme-corp'
// slugify('beta')     → 'customer-beta'
```

## Embed Route Integration

The embed route derives the tag name from the customer ID and signs a JWT. It does **not** push specs — spec pushes happen during provisioning (see `tag-sync.md`).

```js
app.post('/api/embed-url', (req, res) => {
  const { customerId, userEmail } = req.body;
  if (!CUSTOMER_CONFIG[customerId]) {
    return res.status(400).json({ error: 'Unknown customer' });
  }
  const url = buildEmbedUrl(process.env.SIGMA_WORKBOOK_URL, slugify(customerId), userEmail);
  res.json({ url });
});
```

## Adding a New Customer

1. Add an entry to `CUSTOMER_CONFIG` with the desired `extraColumns`.
2. Run the sync script or trigger the "Sync customer tags" action.
3. The new `customer-<slug>` tag is created; existing tags are unaffected.

## Rules

- `buildSpec` and `buildTemplateSpec` are pure functions — no API calls, safe to unit test in isolation.
- Never call a spec push API from the embed URL request path. Tags are immutable; the embed path only needs to sign a JWT.
- Element and page IDs must match the canonical workbook exactly. Export the workbook spec via `GET /v2/workbooks/{workbookId}/spec` to confirm them, then define them as named constants.
