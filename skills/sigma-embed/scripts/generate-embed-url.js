#!/usr/bin/env node
/**
 * Generate a signed Sigma embed URL from environment variables.
 *
 * Required env vars:
 *   SIGMA_EMBED_CLIENT_ID  — Embed Client ID (JWT kid header)
 *   SIGMA_EMBED_SECRET     — Embed Secret (HS256 HMAC key)
 *   SIGMA_WORKBOOK_URL     — Workbook base URL (from Sigma → Publish → Embed)
 *   SIGMA_EMBED_EMAIL      — Email address to embed as (JWT sub claim)
 *
 * Optional env vars:
 *   SIGMA_EMBED_TAG        — Version tag name (e.g. customer-acme, env-prod)
 *                            Omit to embed the current published version.
 *
 * Usage (Claude Code):
 *   SIGMA_EMBED_CLIENT_ID=... SIGMA_EMBED_SECRET=... \
 *   SIGMA_WORKBOOK_URL=https://app.sigmacomputing.com/embed/1-xxx \
 *   SIGMA_EMBED_EMAIL=user@example.com \
 *   node "${CLAUDE_PLUGIN_ROOT}/skills/sigma-embed/scripts/generate-embed-url.js"
 *
 * Usage (generic):
 *   SIGMA_EMBED_CLIENT_ID=... SIGMA_EMBED_SECRET=... \
 *   SIGMA_WORKBOOK_URL=... SIGMA_EMBED_EMAIL=... \
 *   node <repo-root>/skills/sigma-embed/scripts/generate-embed-url.js
 */

'use strict';

const { createHmac, randomUUID } = require('node:crypto');

const required = ['SIGMA_EMBED_CLIENT_ID', 'SIGMA_EMBED_SECRET', 'SIGMA_WORKBOOK_URL', 'SIGMA_EMBED_EMAIL'];
const missing = required.filter((k) => !process.env[k]);
if (missing.length) {
  process.stderr.write(`Error: missing required env var(s): ${missing.join(', ')}\n`);
  process.exit(1);
}

const clientId   = process.env.SIGMA_EMBED_CLIENT_ID;
const secret     = process.env.SIGMA_EMBED_SECRET;
const workbookUrl = process.env.SIGMA_WORKBOOK_URL;
const email      = process.env.SIGMA_EMBED_EMAIL;
const tagName    = process.env.SIGMA_EMBED_TAG || null;

const encodeB64Url = (obj) => Buffer.from(JSON.stringify(obj)).toString('base64url');

const now     = Math.floor(Date.now() / 1000);
const header  = { alg: 'HS256', typ: 'JWT', kid: clientId };
const payload = { sub: email, iat: now, exp: now + 300, jti: randomUUID() };

const unsigned = `${encodeB64Url(header)}.${encodeB64Url(payload)}`;
const sig      = createHmac('sha256', secret).update(unsigned).digest('base64url');
const token    = `${unsigned}.${sig}`;

const base = tagName ? `${workbookUrl}/tag/${tagName}` : workbookUrl;
const url  = `${base}?:jwt=${encodeURIComponent(token)}&:embed=true`;

process.stdout.write(url + '\n');
