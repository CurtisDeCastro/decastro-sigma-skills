# GPU Cluster Utilization Heatmap — the fleet Sigma plugin

Data-center node grid heat-mapped by GPU utilization (the fleet-green health scale; over-temp nodes flagged red), hover tooltips (node/model/util/temp/power), fleet-avg + hot count. Built on operational SQL (per-node utilization/temp/power), not revenue KPIs. Single-file vanilla JS + @sigmacomputing/plugin CDN SDK; synthetic fallback.

**Hosted:** not deployed — see `reference/plugins.md` for deployment options.
Redeploy: `netlify deploy --prod --dir . --site <your-site-id>`
