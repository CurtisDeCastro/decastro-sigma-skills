# Pace-to-Target Pour — the brewer Sigma plugin

A domain-specific plugin: an animated pint of beer that fills (amber + foam head)
to show a current value vs a target, with % to goal and a RAG status
(Behind / On pace / Goal hit). Beer-native and genuinely useful for volume/revenue
goal tracking on a brewer's dashboard. Single-file vanilla JS + `@sigmacomputing/plugin`
CDN SDK; renders synthetic data standalone.

**Hosted:** not deployed — see `reference/plugins.md` for deployment options.


## Config (editor panel)
source element · Current value column · Target column (optional) · Target-if-no-column ·
Title · format (number/currency).

## Redeploy
`netlify deploy --prod --dir . --site <your-site-id>`
