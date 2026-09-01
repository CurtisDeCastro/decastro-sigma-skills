# Filling a visualization gap with a plugin

Sometimes the report you are reproducing shows something Sigma has no native element for —
an order-book depth ladder, a chord diagram of flows between counterparties, a radial
day-part clock. That is what a custom plugin is for.

**Building the plugin itself is `sigma-plugin-development`'s job** (with
`sigma-plugin-patterns` for architecture). This file covers only the three decisions that
belong to the workbook builder: *should* there be a plugin, how to wire it into the spec,
and what to tell the user about getting it into their Sigma instance.

## 1. Decide — native first, always

Work down this list. Stop at the first yes.

1. **Does a native element already do this?** Sigma covers bar / line / area / combo /
   scatter / pie / donut / KPI / pivot / table / map / gauge / waterfall, plus containers,
   tabs, controls, input tables and overlays. A "custom" requirement is often a native
   chart with different encoding or a pivot with conditional formatting.
2. **Can a native element plus conditional formatting get there?** Diverging heatmaps,
   status colouring, data bars and per-cell backgrounds are all spec-authorable — see
   `production-defaults.md`. This closes most "we need a custom grid" requests.
3. **Is the difference cosmetic?** If a stakeholder wants a specific look rather than a
   specific *reading*, take the native element and the maintenance savings.
4. **Otherwise, build the plugin.** The bar is that Sigma genuinely has no equivalent and
   the visual encoding carries real analytical meaning.

Be honest about the cost when you recommend one: a plugin is code the customer now owns,
hosts, upgrades, and secures. It will not inherit theme changes, and it needs its own
accessibility and responsive behaviour. That is a fair trade for a depth ladder; it is not
a fair trade for a bar chart with rounded corners.

Browse `examples/plugins/` for eighteen worked plugins named by what they *do*
(`channel-sankey`, `capital-flow-chord`, `demand-clock`, `project-gantt`, …) — the odds
are decent that something close already exists.

## 2. Wire it into the workbook

A plugin is just another element kind. Register it once, then reference the returned
`pluginId`:

```jsonc
{"id":"scatterviz","kind":"plugin","pluginId":"<registered-plugin-id>",
 "config":{"source":{"kind":"element","elementId":"posfeed"},
           "beta":"pf-beta","contribution":"pf-contrib","marketValue":"pf-mv"}}
```

The `config` keys are the binding names the plugin declares in `configureEditorPanel`.
Two things that bite:

- **`plugin.style` accepts `backgroundColor` only, and it must be a 6-digit hex** —
  `"transparent"` is rejected.
- **PNG export never idles for a plugin that animates continuously or fetches externally**,
  so the render step will hang. Give the plugin a settled end state, or verify that page by
  rendering its other elements individually.

## 3. Hosting — assume localhost, and say so

**Default: run it locally and register the localhost URL.** For a single-file plugin,
`python3 -m http.server 8080` in its directory is enough. Sigma over HTTPS is allowed to
load an HTTP-localhost iframe as a browser secure-context exception, so it renders
correctly on the machine that is serving it.

Tell the user plainly, once: *this plugin renders on your machine only. Anyone else opening
the workbook will see an empty element until it is deployed somewhere they can reach.*

Do not deploy anything on your own initiative.

## 4. If they want it deployed

Only when they ask. Then walk them through it:

**Step 1 — pick a host.** Any static host works; the plugin is one HTML file plus assets.

| option | good when |
|---|---|
| Netlify / Vercel | fastest path; drag-and-drop or CLI, free tier, instant HTTPS |
| Cloudflare Pages | already a Cloudflare shop; generous free tier |
| GitHub Pages | the plugin lives in a repo they already control |
| S3 + CloudFront | AWS shop, or the plugin must sit inside their own cloud boundary |
| internal static host | the plugin must stay behind the corporate network |

**Step 2 — check the governance question before deploying anything.** A plugin built
against their book is account-identifiable work product. Ask whether it may live on a
public URL, or whether it has to be private/behind SSO. If in doubt, private.

**Step 3 — deploy, then register the URL** with `POST /v2/plugins`.

**Step 4 — know that the URL is set-once.** The Sigma Plugins API has **no update
endpoint** (confirmed: PATCH returns 404). Changing a hosting URL means registering a *new*
`pluginId` and re-pushing every workbook that references the old one. Verify the swap by
GET-ing the workbook spec and checking the element's `pluginId` — a successful update
response does not prove the new id is bound.

### MCP tools that can help

If deployment is going to be a recurring task, an MCP server can let the agent do it
directly rather than handing over shell commands. Worth looking for:

- **Netlify**, **Vercel**, and **Cloudflare** all publish official MCP servers covering
  site creation and deploys.
- **GitHub's MCP server** covers repo creation and Pages, if the plugin is going to live
  in a repo anyway.
- **Filesystem / shell** MCP servers are enough if they already have a vendor CLI
  authenticated locally.

Check the MCP registry or the vendor's docs for the current install command — do not assume
one from memory, and confirm the server is available in the user's environment before
promising an automated deploy.
