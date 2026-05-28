---
name: sigma-embed
description: >-
  Generate server-side Sigma embed URLs (JWT signing, workbook URL
  construction) and manage per-customer workbook variants via version tags.
  Use whenever the user wants to embed a Sigma workbook in a host application,
  generate a signed embed URL, configure SIGMA_EMBED_CLIENT_ID /
  SIGMA_EMBED_SECRET / SIGMA_WORKBOOK_URL, set up per-customer column
  variants, apply workbook version tags, or automate tag provisioning via
  the Sigma REST API. Prerequisite: obtain admin API credentials via the
  sigma-api skill if tag provisioning is needed.
---

# Sigma Embed

Generate server-side embed URLs that open a Sigma workbook inside a host application. This skill covers JWT signing, per-customer workbook variants via version tags, and automated tag provisioning.

**Requirements:** Node.js 18+ (uses built-in `node:crypto` — no npm packages required). For tag provisioning via the Sigma REST API, also complete the `sigma-api` skill first to set `$SIGMA_BASE_URL` and `$SIGMA_API_TOKEN`.

## Embed vs. Admin Credentials

Sigma embeds use **two separate credential sets**. Never substitute one for the other.

| Set | Where to find | Used for |
|-----|--------------|----------|
| **Embed Client ID** + **Embed Secret** | Sigma → Administration → Developer Access → Embed credentials | JWT `kid` header + HS256 signing key |
| **Admin Client ID** + **Admin Client Secret** | Sigma → Administration → Developer Access → API credentials | REST API tag writes (see `sigma-api` skill) |

```sh
# Embed credentials — server env only, never browser-facing
export SIGMA_EMBED_CLIENT_ID="your-embed-client-id"
export SIGMA_EMBED_SECRET="your-embed-secret"
export SIGMA_WORKBOOK_URL="https://app.sigmacomputing.com/embed/1-xxxx"
```

## Step 1 — Generate a Basic Embed URL

The JWT `kid` header must equal the Embed Client ID. `jti` must be a fresh UUID per request. Set `exp` short — 5 minutes is standard. **Never generate embed URLs in browser code.**

### Preferred: bundled helper script

`scripts/generate-embed-url.js` reads the four env vars and prints a single signed URL to stdout:

- **Claude Code:** `node ${CLAUDE_PLUGIN_ROOT}/skills/sigma-embed/scripts/generate-embed-url.js`
- **Generic:** `node <repo-root>/skills/sigma-embed/scripts/generate-embed-url.js`

| In (env) | Out (stdout) |
|----------|--------------|
| `SIGMA_EMBED_CLIENT_ID`, `SIGMA_EMBED_SECRET`, `SIGMA_WORKBOOK_URL`, `SIGMA_EMBED_EMAIL` | A single embed URL |

Optional: set `SIGMA_EMBED_TAG` to target a specific tagged version (see Step 2).

### Inline reference implementation (Node.js)

Uses only built-in `node:crypto` — no `npm install` needed.

```js
import { createHmac, randomUUID } from 'node:crypto';

function buildEmbedUrl(workbookUrl, tagName = null) {
  const {
    SIGMA_EMBED_CLIENT_ID: clientId,
    SIGMA_EMBED_SECRET: secret,
    SIGMA_EMBED_EMAIL: email,
  } = process.env;

  if (!clientId || !secret || !email) {
    throw new Error('SIGMA_EMBED_CLIENT_ID, SIGMA_EMBED_SECRET, and SIGMA_EMBED_EMAIL must be set');
  }

  const encodeB64Url = (obj) =>
    Buffer.from(JSON.stringify(obj)).toString('base64url');

  const now = Math.floor(Date.now() / 1000);
  const header  = { alg: 'HS256', typ: 'JWT', kid: clientId };
  const payload = { sub: email, iat: now, exp: now + 300, jti: randomUUID() };

  const unsigned = `${encodeB64Url(header)}.${encodeB64Url(payload)}`;
  const sig = createHmac('sha256', secret).update(unsigned).digest('base64url');
  const token = `${unsigned}.${sig}`;

  const base = tagName ? `${workbookUrl}/tag/${tagName}` : workbookUrl;
  return `${base}?:jwt=${encodeURIComponent(token)}&:embed=true`;
}
```

Wire this into a server route (Express, Fastify, Next.js API route, etc.) — return only the signed URL to the browser, never the token components.

## Step 2 — Target a Tagged Workbook Version

Without a tag, embeds always show the current published state. Tags freeze a named snapshot — use them for per-customer variants, staging/production separation, and safe rollouts.

Insert the tag name as a **path segment** before the query string:

```
{workbookUrl}/tag/{tagName}?:jwt=...&:embed=true
```

This is purely a URL change — the JWT signing logic is identical.

```js
// Production variant
const url = buildEmbedUrl(process.env.SIGMA_WORKBOOK_URL, 'env-prod');

// Per-customer variant
const url = buildEmbedUrl(process.env.SIGMA_WORKBOOK_URL, `customer-${slug}`);
```

**Tag naming conventions:**

| Purpose | Pattern | Example |
|---------|---------|---------|
| Per-customer variant | `customer-<slug>` | `customer-acme` |
| Base template (never embedded directly) | `template` | `template` |
| Environment separation | `env-<name>` | `env-prod` |

A slug is the customer identifier lowercased, non-alphanumeric runs replaced by `-`, leading/trailing `-` stripped.

## Step 3 — Per-Customer Column Variants

If different customers need different columns or visible elements, maintain a `CUSTOMER_CONFIG` object in code and derive workbook specs programmatically. Push each derived spec and apply a `customer-<slug>` tag. Concurrent embed requests are safe because tags are immutable snapshots.

Load `reference/customer-config.md` for the full pattern: `CUSTOMER_CONFIG` shape, `buildSpec()`, `buildTemplateSpec()`, slug derivation, and embed route integration.

## Step 4 — Automate Tag Provisioning

Spec pushes and tag applications are orchestrated by a shared library, not by the embed URL path. The library supports an auto dry-run mode (logs payloads, no API calls) when admin credentials are absent, so the application runs fully without live credentials.

Load `reference/tag-sync.md` for the `makeClient` / `onEvent` pattern, per-customer sync, template propagation, CLI entry point, and Express/serverless wiring.

## Step 5 — When to Escalate

The workbook-tag approach handles most per-customer use cases. Load `reference/escalation.md` when customers need different source databases, row-level security policies differ per customer, or per-customer column names are driven by warehouse schema rather than a config object.

## Verifying an Embed

Open browser DevTools on the host page and confirm:
1. The `iframe src` contains `?:jwt=` and `&:embed=true`.
2. `SIGMA_EMBED_SECRET` does not appear in any Network request from the host page.
3. The JWT is not stored in a JS variable accessible to the page (it should only be used as the iframe `src`).

## Security Notes

- Never generate embed URLs in browser JavaScript — the secret would be exposed.
- Never log `SIGMA_EMBED_SECRET` or return it in API responses.
- Set `exp` ≤ 10 minutes; long-lived tokens weaken replay protection.
- Always generate a fresh `jti` UUID per request — Sigma rejects replayed tokens.
- Admin REST credentials and embed signing credentials are distinct; never substitute one for the other.
- Protect any route that triggers spec pushes or tag writes — these are write operations on live workbooks.
