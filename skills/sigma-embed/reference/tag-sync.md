# Tag Provisioning Library

This reference covers the shared provisioning library used by CLI scripts, Express routes, and serverless functions to push workbook specs and apply version tags via the Sigma REST API.

Requires admin OAuth credentials — complete the `sigma-api` skill first to obtain `SIGMA_BASE_URL` and `SIGMA_API_TOKEN`, or use the `makeClient` helper below which handles the token exchange internally from `SIGMA_CLIENT_ID` / `SIGMA_CLIENT_SECRET`.

## Library Layout

All business logic lives in `lib/tag-sync.js`. Entry points supply env vars, wire the `onEvent` callback, and handle transport-specific response shapes.

```
lib/
  embed.js          ← CUSTOMER_CONFIG, buildSpec, buildTemplateSpec, slugify
  tag-sync.js       ← makeClient, pushWorkbookSpec, tagWorkbookVersion,
                       syncCustomer, syncAllCustomers, propagateTemplate
scripts/
  sync-tags.js      ← CLI entry point
server.js           ← Express routes: POST /api/sync-tags, POST /api/propagate-template,
                                       GET /api/sync-status
netlify/functions/
  sync-tags.js      ← Netlify / Lambda wrapper
  propagate-template.js
```

## `makeClient` — Auto Dry-Run

When admin credentials are absent the client runs in **dry-run mode**: it logs every payload but skips all API calls. The application is fully runnable for demos without real credentials.

```js
async function makeClient({ apiBase, clientId, clientSecret, onEvent }) {
  const dryRun = !clientId || !clientSecret;
  if (dryRun) {
    onEvent?.({ level: 'warn', op: 'init', msg: 'No credentials — running in dry-run mode' });
    return { dryRun: true, onEvent };
  }
  const credentials = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
  const res = await fetch(`${apiBase}/v2/auth/token`, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${credentials}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: 'grant_type=client_credentials',
  });
  if (!res.ok) throw new Error(`Token exchange failed: ${res.status}`);
  const { access_token } = await res.json();
  return { apiBase, accessToken: access_token, dryRun: false, onEvent };
}
```

Transition from dry-run to live: set `SIGMA_CLIENT_ID` and `SIGMA_CLIENT_SECRET`. No code changes required.

## Core Operations

### Push Workbook Spec

```js
async function pushWorkbookSpec(client, workbookId, spec) {
  client.onEvent?.({ level: 'info', op: 'push-spec', workbookId, dryRun: client.dryRun });
  if (client.dryRun) return;
  const res = await fetch(`${client.apiBase}/v2/workbooks/${workbookId}/spec`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${client.accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(spec),
  });
  if (!res.ok) throw new Error(`Spec push failed (${res.status}): ${await res.text()}`);
}
```

### Apply Version Tag

```js
async function tagWorkbookVersion(client, workbookId, tagName) {
  client.onEvent?.({ level: 'info', op: 'tag', workbookId, tagName, dryRun: client.dryRun });
  if (client.dryRun) return;
  const res = await fetch(`${client.apiBase}/v2/workbooks/tag`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${client.accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ workbookId, tagName }),
  });
  if (!res.ok) throw new Error(`Tag failed (${res.status}): ${await res.text()}`);
}
```

### Sync One Customer

Errors are caught per-customer so one failure does not abort the batch.

```js
async function syncCustomer(client, customerId) {
  const { buildSpec, slugify, CANONICAL } = require('./embed');
  const tagName = slugify(customerId);
  try {
    await pushWorkbookSpec(client, CANONICAL.workbookId, buildSpec(customerId));
    await tagWorkbookVersion(client, CANONICAL.workbookId, tagName);
    client.onEvent?.({ level: 'info', op: 'sync', customer: customerId, tag: tagName, status: 'ok' });
    return { customer: customerId, tag: tagName, status: 'ok' };
  } catch (err) {
    client.onEvent?.({ level: 'error', op: 'sync', customer: customerId, msg: err.message });
    return { customer: customerId, status: 'error', error: err.message };
  }
}

async function syncAllCustomers(client) {
  const { CUSTOMER_CONFIG } = require('./embed');
  return Promise.all(Object.keys(CUSTOMER_CONFIG).map((id) => syncCustomer(client, id)));
}
```

### Propagate Template

Push template spec → tag as `template` → sync all customers.

```js
async function propagateTemplate(client) {
  const { buildTemplateSpec, CANONICAL } = require('./embed');
  await pushWorkbookSpec(client, CANONICAL.workbookId, buildTemplateSpec());
  await tagWorkbookVersion(client, CANONICAL.workbookId, 'template');
  return syncAllCustomers(client);
}
```

## The `onEvent` Callback

Every operation emits a structured event. Callers supply their own handler — the library has no transport concerns.

```js
// CLI: JSON-per-line to stdout
const onEvent = (e) => process.stdout.write(JSON.stringify(e) + '\n');

// Express / Netlify: accumulate for the response body
const events = [];
const onEvent = (e) => events.push(e);
```

Event shape: `{ level: 'info'|'warn'|'error', op: string, customer?: string, tag?: string, msg?: string }`

## Express Routes

```js
async function runTagSync(res, op) {
  const events = [];
  try {
    const client = await makeClient({
      apiBase:      process.env.SIGMA_API_BASE,
      clientId:     process.env.SIGMA_CLIENT_ID,
      clientSecret: process.env.SIGMA_CLIENT_SECRET,
      onEvent: (e) => events.push(e),
    });
    const result = await op(client);
    res.json({ dryRun: client.dryRun, events, result });
  } catch (err) {
    res.status(500).json({ error: err.message, events });
  }
}

app.post('/api/sync-tags',          (_req, res) => runTagSync(res, syncAllCustomers));
app.post('/api/propagate-template', (_req, res) => runTagSync(res, propagateTemplate));

// Read-only probe — checks credential presence only, no Sigma API calls
app.get('/api/sync-status', (_req, res) => {
  res.json({ dryRun: !(process.env.SIGMA_CLIENT_ID && process.env.SIGMA_CLIENT_SECRET) });
});
```

**Never use `POST /api/sync-tags` as the dry-run probe.** Use the dedicated `GET /api/sync-status` endpoint — the POST runs the full sync on every call.

## CLI Entry Point

```js
// scripts/sync-tags.js
// Flags: --mode customers|template (default: customers)
//        --customer <id>           (single-customer sync)
//        --dry-run                 (force dry-run regardless of credentials)

const args = process.argv.slice(2);
const mode    = args.includes('--mode')     ? args[args.indexOf('--mode') + 1]     : 'customers';
const target  = args.includes('--customer') ? args[args.indexOf('--customer') + 1] : null;
const forceDry = args.includes('--dry-run');

(async () => {
  const client = await makeClient({
    apiBase:      process.env.SIGMA_API_BASE,
    clientId:     forceDry ? null : process.env.SIGMA_CLIENT_ID,
    clientSecret: forceDry ? null : process.env.SIGMA_CLIENT_SECRET,
    onEvent: (e) => process.stdout.write(JSON.stringify(e) + '\n'),
  });
  const results = mode === 'template'
    ? await propagateTemplate(client)
    : target ? [await syncCustomer(client, target)] : await syncAllCustomers(client);
  process.exit(results.some((r) => r.status === 'error') ? 1 : 0);
})();
```
