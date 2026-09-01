# Reference plugins

Eighteen working Sigma plugins, named by **what they do** rather than who they were first
built for. Use them two ways: as a catalogue to check before building something new, and as
the authoring pattern to copy.

| plugin | visual |
|---|---|
| `activity-rings` | concentric progress rings against targets |
| `actual-vs-expected-grid` | A/E ratio grid with variance shading |
| `arrival-lane-tracker` | queue/lane occupancy over time |
| `capital-flow-chord` | chord diagram of flows between entities |
| `care-gap-funnel` | stage-by-stage population funnel |
| `channel-sankey` | sankey of volume across channels |
| `comparison-kpi-card` | KPI with a comparison treatment (simplest — read this first) |
| `daypart-heatmap` | 7×24 hour-of-week heatmap |
| `decline-curve-fan` | decline curves with a P10/P50/P90 fan |
| `demand-clock` | radial 24-hour demand clock |
| `node-utilization-heatmap` | per-node utilization grid |
| `order-book-depth-ladder` | bid/ask depth ladder |
| `pace-to-target` | pace vs target with projection |
| `payment-flow-stream` | streaming flow of transactions between stages |
| `project-gantt` | project/task gantt with dependencies |
| `risk-return-scatter` | risk vs return bubble scatter with quadrants |
| `risk-stratification-pyramid` | tiered population pyramid |
| `turnaround-time-distribution` | distribution of elapsed times with SLA marks |

## What makes them good

- **`configureEditorPanel` declares named bindings**, so the plugin is configurable rather
  than hardcoded to one dataset
- **`ResizeObserver` on the stage element** — Sigma sizes the panel *after* first paint, so
  a window resize listener is not enough
- **A `synth()` fallback** so the plugin renders standalone with nothing bound, which makes
  it reviewable in isolation
- **No infinite animation loop** — a plugin that never idles hangs PNG export forever
- Inline SVG with an explicit `xmlns`

## Before you build a new one

Read `skills/sigma-workbook-builder/reference/plugins.md`. A plugin is code you own, host,
upgrade, and secure — the bar is that Sigma genuinely has no native equivalent and the
encoding carries real analytical meaning. Then use `skills/sigma-plugin-development` to
build it.

## Running one

Serve the directory and register that URL in Sigma:

```bash
cd examples/plugins/<name> && python3 -m http.server 8080
```

Localhost is the default and is fine for development — Sigma over HTTPS may load an
HTTP-localhost iframe. It renders **only on the machine serving it**; anyone else opening
the workbook sees an empty element until it is deployed. Deployment options and the
set-once `pluginId` caveat are in `reference/plugins.md`.

These were originally authored as demo assets and have been renamed and genericised; the
sample data inside each is illustrative, not real.
