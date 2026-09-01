# Matching a source's look

When you are reproducing an existing report, the styling values are **outputs of a matching
exercise, not recommendations**. There is no universally correct canvas tone or border
weight. There is only: what does the source do, and what settings reproduce it.

This is the distinction that matters most in this whole skill:

| | universal | derived from the source |
|---|---|---|
| **structural defaults** — native elements over hand-built cards, `name`/`description` over caption text, header panel, live formulas, hidden grand totals, sort-by-value, two-tier sourcing | ✅ always | |
| **visual values** — canvas tone, surface colour, border weight and radius, element gap, type scale, accent, status colours, heatmap ramp | | ✅ every time |

Applying someone else's visual values to a different source is how you end up with a
workbook that is technically correct and looks nothing like the thing it replaces.

## Extract the system before you write any style

Work the source image once, deliberately, and write the answers down. You are looking for a
small number of decisions that then cascade.

| read this off the image | it becomes |
|---|---|
| page background tone — pure white? warm off-white? cool grey? | `theme.colorOverrides.canvasBackground` |
| card/surface colour, and whether it differs from the page | `theme.colorOverrides.backgroundCanvas`, container `backgroundColor` |
| border weight — hairline, 1px, heavier? and colour | container `borderColor` / `borderWidth` |
| corner treatment — square, gently rounded, pill | `borderRadius` (`square` \| `round` \| `pill`) |
| density — generous or tight? gaps between tiles? | `theme.space` (`unit`, `showElementPadding`), container `elementGap` |
| type scale — how many distinct sizes, how big is the jump? | `p-large` / `p-small` in bodies; theme fonts |
| the one accent colour, and where it is allowed to appear | `theme.colors.highlight` |
| status colours — the exact green/amber/red for OK/warn/breach | `comparison.colorGood` / `colorBad`, status chips |
| heatmap ramp — endpoints, midpoint, whether it diverges | `conditionalFormats` band colours |
| table density and rule style | `theme.tableStyles.preset` / `cellSpacing` |

Sample colours **from the image** rather than guessing a named colour that seems close. A
warm off-white and a cool off-white read very differently next to a white card, and that
difference is most of why a reproduction feels off.

## Then let the theme cascade

Set those values on the theme **once** and write almost no per-element `style`. That is the
universal part — see `production-defaults.md` #4. The reason it matters more when matching
is that a source's look is a *system*: if the canvas, surface and border are set once and
correctly, most tiles land right with no per-element work. Every hardcoded hex you add is a
place the system can't reach.

Two composition details that come up constantly when matching a card-based report:

- A bordered wrapper container with a **flat element inside it** (`transparent`,
  `borderWidth: 0`) reads as one card. Leaving both bordered gives a double border, which
  is the most common visual tell of a code-built reproduction.
- `elementGap: "hidden"` collapses the space between children when the source shows a
  single continuous surface rather than separated tiles.

Neither is a recommendation. Use them when the source looks like that.

## Verify by comparison, not by taste

Render the page and put it **side by side with the source image**. You are not asking "does
this look good" — you are asking "what is different." Work down: overall tone, card
treatment, spacing rhythm, type sizes, colour of the accents, table density.

Expect two or three passes. The first render usually gets structure right and tone wrong.

## When there is no source

Net-new work has no image to match, so this file does not apply — fall back to the
customer's brand system if they have one, or to plain restraint: one accent, neutral
everything else, consistent radius, generous whitespace, and a type scale with no more than
three sizes. The structural defaults still apply in full.
