"""Row-allocating layout composer for Sigma workbook pages.

The canned generator hardcodes every row band (`gridRow="13 / 17"`), so inserting or
omitting a block means renumbering everything below it by hand — which is why there is
exactly one composition. This module replaces the constants with a cursor: blocks declare
their own height, the page stacks them, and the XML falls out.

    page = Page("pg", "Command Center")
    page.add(Block("c-hdr", height=4, xml=header_xml))
    page.add(Row([                                  # side-by-side, one shared height
        Block("tc", cols=17, xml=tabs_xml),
        Block("c-chat", cols=7, xml=rail_xml),
    ], height=54))
    layout_xml = page.xml()

Guarantees that matter:
  * 24-column grid, always. Column spans in a Row are proportional and always sum to 24.
  * A Row's children share ONE height, so the rail can't drift out of sync with the
    tabbed container beside it (that coupling is two duplicated literals in the canned
    generator and a silent bug when they disagree).
  * Element ids are collected as the page is built, so the caller can assert that the
    element array and the layout XML describe the same set — the two hand-maintained
    orderings that silently diverge today.

Layout only. This module never emits element JSON, so it can be unit-tested with no org,
no credentials, and no network.

## Spec format (changed under us, verified live 2026-08-10)

Sigma moved to a `document` envelope and the OLD shape is now rejected outright:

    pages[].elements + <LayoutElement>  -> HTTP 400 "Expecting { schemaVersion: 1 } at document"
    document{} + <Element>              -> valid
    document{} + <LayoutElement>        -> HTTP 500

So: elements are a FLAT `document.elements[]` array, a page is metadata only, and an
element belongs to a page purely because the layout places it there. The tags are
`<Element>` (leaf) and `<Container>` (has children); `<TabbedContainer>`/`<Tab>` keep
their own names. Use `workbook()` below to assemble the envelope.
"""
from __future__ import annotations

from dataclasses import dataclass, field

COLS = 24


def _span(start: int, size: int) -> str:
    """Grid lines are 1-based and the end is exclusive: col 1, width 6 -> "1 / 7"."""
    return f"{start} / {start + size}"


@dataclass
class Block:
    """One placed thing. `xml` renders the block's own markup given its grid position.

    xml(col_span, row_span) -> str, where both are ready-to-use "a / b" strings.
    Pass `ids` for every element id the markup places, so the page can report them.
    """
    id: str
    height: int
    xml: callable
    cols: int = COLS
    ids: tuple[str, ...] = ()

    def render(self, col_start: int, row_start: int) -> tuple[str, list[str]]:
        col = _span(col_start, self.cols)
        row = _span(row_start, self.height)
        return self.xml(col, row), [self.id, *self.ids]


@dataclass
class Row:
    """Several blocks side by side, sharing one row band.

    Child `cols` are relative weights. They're normalised to sum to 24 so a caller can
    say 17/7 or 2/1 and always get a legal grid.
    """
    blocks: list[Block]
    height: int

    def render(self, col_start: int, row_start: int) -> tuple[str, list[str]]:
        total = sum(b.cols for b in self.blocks) or 1
        widths = [max(1, round(b.cols * COLS / total)) for b in self.blocks]
        widths[-1] = COLS - sum(widths[:-1])   # absorb rounding drift in the last block
        if widths[-1] < 1:
            raise ValueError(
                f"Row does not fit in {COLS} columns: weights "
                f"{[b.cols for b in self.blocks]} -> widths {widths}"
            )
        out, ids, col = [], [], col_start
        for b, w in zip(self.blocks, widths):
            frag, bids = Block(b.id, self.height, b.xml, w, b.ids).render(col, row_start)
            out.append(frag)
            ids += bids
            col += w
        return "\n".join(out), ids


@dataclass
class Page:
    """A page that allocates rows top-to-bottom as blocks are added."""
    id: str
    name: str
    kind: str = "grid"
    gap: int = 0                      # blank rows between blocks
    _cursor: int = field(default=1, init=False)
    _frags: list[str] = field(default_factory=list, init=False)
    _ids: list[str] = field(default_factory=list, init=False)

    def add(self, block: Block | Row) -> "Page":
        frag, ids = block.render(1, self._cursor)
        self._frags.append(frag)
        self._ids += ids
        self._cursor += block.height + self.gap
        return self

    @property
    def height(self) -> int:
        """Rows consumed so far — the thing you could never know before."""
        return self._cursor - 1

    @property
    def placed_ids(self) -> list[str]:
        return list(self._ids)

    def xml(self) -> str:
        attrs = (f'<Page type="{self.kind}" gridTemplateColumns="repeat({COLS}, 1fr)" '
                 f'gridTemplateRows="auto" id="{self.id}">')
        return "\n".join([attrs, *self._frags, "</Page>"])


def layout(*pages: Page) -> str:
    """Top-level `layout` string: one XML prolog, every <Page> a sibling."""
    return '<?xml version="1.0" encoding="utf-8"?>\n' + "\n".join(p.xml() for p in pages)


# ---------------------------------------------------------------- container helpers

def container(cid: str, children: list[tuple[str, int, int]], height: int,
              rows: int | None = None, cols: int = COLS) -> Block:
    """A <Container> with children placed on its own inner grid.

    children: (element_id, col_start, col_size) tuples, stacked vertically in order.
    `rows` sets gridTemplateRows="repeat(rows,1fr)" — use it for KPI cards, where "auto"
    sizes rows to content and makes one card taller than its neighbours.
    """
    inner_rows = rows or len(children)

    def render(col: str, row: str) -> str:
        tr = f"repeat({inner_rows},1fr)" if rows else "auto"
        out = [f'  <Container elementId="{cid}" type="grid" gridColumn="{col}" '
               f'gridRow="{row}" gridTemplateColumns="repeat({COLS}, 1fr)" '
               f'gridTemplateRows="{tr}">']
        for i, (eid, cs, cw) in enumerate(children, start=1):
            out.append(f'    <Element elementId="{eid}" '
                       f'gridColumn="{_span(cs, cw)}" gridRow="{_span(i, 1)}"/>')
        out.append("  </Container>")
        return "\n".join(out)

    return Block(cid, height, render, cols, tuple(c[0] for c in children))


def tabs(tid: str, tab_contents: list[list[tuple[str, int, int]]], height: int,
         cols: int = COLS) -> Block:
    """A <TabbedContainer>. Tab labels live in the element JSON and match BY POSITION.

    Each tab is a list of (element_id, col_start, col_size) placed side by side, full
    height. Bare <Element> children only — a <Container> inside a <Tab> scrambles render
    order. Note <TabbedContainer> carries NO gridTemplateColumns/Rows of its own; each
    <Tab> carries its own.
    """
    def render(col: str, row: str) -> str:
        out = [f'  <TabbedContainer elementId="{tid}" type="tabbed-container" '
               f'gridColumn="{col}" gridRow="{row}">']
        for contents in tab_contents:
            out.append(f'    <Tab gridTemplateColumns="repeat({COLS}, 1fr)" '
                       f'gridTemplateRows="auto">')
            for eid, cs, cw in contents:
                out.append(f'      <Element elementId="{eid}" '
                           f'gridColumn="{_span(cs, cw)}" gridRow="1 / 22"/>')
            out.append("    </Tab>")
        out.append("  </TabbedContainer>")
        return "\n".join(out)

    ids = tuple(eid for tab in tab_contents for eid, _, _ in tab)
    return Block(tid, height, render, cols, ids)


def element(eid: str, height: int, cols: int = COLS) -> Block:
    """A bare element, no container."""
    return Block(eid, height,
                 lambda col, row: f'  <Element elementId="{eid}" '
                                  f'gridColumn="{col}" gridRow="{row}"/>',
                 cols)


def band(ids: list[str], height: int, each: int | None = None) -> Row:
    """N equal-width blocks in one row — a KPI band of any size.

    The canned generator can only do 4 (`KG[i]` over four gradients, and `1+i*6` column
    math that only tiles 24 columns at N=4). Here 3, 5 and 6 work the same way.
    """
    n = len(ids)
    if n == 0:
        raise ValueError("band() needs at least one id")
    return Row([element(i, height, each or 1) for i in ids], height)


def pages_meta(*pages: Page) -> list[dict]:
    """`document.pages` is metadata ONLY — no elements. Membership comes from layout."""
    return [{"id": p.id, "name": p.name} for p in pages]


def envelope(name: str, folder_id: str, elements: list[dict],
             pages_meta: list[dict], layout_xml: str,
             schema_version: int = 1, theme_overrides: dict | None = None,
             theme_name: str | None = None, agents: list[dict] | None = None,
             overlays: list[dict] | None = None,
             description: str | None = None) -> dict:
    """Assemble the POST/PUT body from ALREADY-BUILT pages metadata + layout XML.

    `workbook()` below is the ergonomic wrapper for callers that use Page objects. This
    is the raw entry point for generators that emit layout XML as literal strings (the
    canned command-center does). Both funnel through here so the envelope shape lives in
    exactly ONE place — the last format change had to be applied in four.
    """
    doc: dict = {"kind": "workbook", "schemaVersion": schema_version,
                 "elements": elements, "pages": pages_meta, "layout": layout_xml}
    theme: dict = {}
    if theme_name:
        theme["name"] = theme_name
    if theme_overrides:
        theme["overrides"] = theme_overrides
    if theme:
        doc["settings"] = {"theme": theme}
    if agents:
        doc["agents"] = agents
    if overlays:
        doc["overlays"] = overlays
    body: dict = {"name": name, "folderId": folder_id, "document": doc}
    if description:
        body["description"] = description
    return body


def workbook(name: str, folder_id: str, elements: list[dict], pages: list[Page],
             schema_version: int = 1, theme_overrides: dict | None = None,
             theme_name: str | None = None, agents: list[dict] | None = None,
             overlays: list[dict] | None = None, description: str | None = None,
             hidden_pages: set[str] | None = None) -> dict:
    """Assemble the POST/PUT body for /v2/workbooks/spec.

    `name`, `folderId` and `description` sit at the TOP level; everything else lives
    inside `document`. Response-only fields (workbookId, url, createdAt, ...) are ignored
    on write, so a GET-back can be resubmitted without stripping them.
    """
    pages_meta = [{"id": p.id, "name": p.name,
                   **({"visibility": "hidden"}
                      if hidden_pages and p.id in hidden_pages else {})}
                  for p in pages]
    return envelope(name, folder_id, elements, pages_meta, layout(*pages),
                    schema_version, theme_overrides, theme_name, agents, overlays,
                    description)
