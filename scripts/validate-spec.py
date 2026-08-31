#!/usr/bin/env python3
"""Pre-POST static validation for a Sigma workbook spec.

Two validators exist and they cover different failures — run both:

  1. THIS script — cross-reference and known-trap checks. Catches the things the
     server accepts happily and then renders wrong (or silently drops).
  2. `POST /v2/workbooks/spec/verify` — the server's own structural validation,
     same as CREATE but it never persists. Catches wrong element kinds, bad
     encodings, missing required fields, with a precise JSON path.
     Wired into `scripts/api/publish-workbook.sh post`.

Neither subsumes the other. Verified 2026-07-30 against a live org: the server's
verify endpoint returns `{"valid":true}` for a layout XML that references an
elementId which does not exist anywhere in the spec, so only `layout-refs-exist`
below finds that. It DOES resolve other cross-references (an unknown `chat.agentId`
or an unknown `sequenceId` are both reported), and it knows element schemas, which
this script does not. Two more server-side quirks worth knowing:
  - `mode`/`kind`-style enums are often unchecked — `greeting.mode:"custom"` and
    `dataSources[].kind:"nonsense"` both pass. Several checks here exist purely to
    catch what the server waves through.
  - a `warehouse-agent` tool makes verify return invalid with "invocable inodes are
    not supported by this host", even when the tool works. That's a false negative:
    read the error text before believing it.

Run before every POST/PUT:

    python3 scripts/validate-spec.py <spec.json>

Exits 0 on success, non-zero on any issue (one issue per line on stderr).
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET


CHECKS = [
    "spec-envelope",
    "no-per-page-layout",
    "elements-placed-in-layout",
    "data-spine-placement",
    "layout-refs-exist",
    "containers-have-children",
    "no-gridcontainer-in-tab",
    "control-id-unique",
    "agent-refs-resolve",
    "sort-direction-spelling",
    "text-vertical-align",
    "padding-value",
    "plugin-config-strings",
    "data-label-singular",
    "background-image-shape",
    "no-field-substring-keys",
    "kpi-on-gradient-needs-bg",
]


def _doc(spec: dict) -> dict:
    """The `document` envelope. Accepts a GET-back (response fields at top level) too.

    Format changed 2026-08-10: elements moved OUT of `pages[]` into a flat
    `document.elements[]`, and `pages` became metadata only. The old shape is rejected by
    the API (`Expecting { schemaVersion: 1 } at document`), so a spec without a
    `document` key is either pre-migration or hand-rolled — flag it loudly rather than
    silently checking nothing.
    """
    return spec.get("document", spec)


def _elements(spec: dict):
    """Yield (index, index, element) for every element. Signature kept for callers.

    Elements are FLAT now; the first slot used to be a page index and no longer means
    anything — an element's page comes from where `layout` places it.
    """
    doc = _doc(spec)
    for ei, el in enumerate(doc.get("elements", []) or []):
        yield 0, ei, el
    # Pre-migration specs (or a stale generator) still nest under pages — walk those too
    # so the checks below still say something useful instead of passing vacuously.
    for p in doc.get("pages", []) or []:
        for ei, el in enumerate(p.get("elements", []) or []):
            yield 0, ei, el


def issues_spec_envelope(spec: dict) -> list[str]:
    """The migration check: is this even the current shape?"""
    issues = []
    if "document" not in spec:
        issues.append(
            "no top-level `document` envelope. The API now requires "
            "{name, folderId, document:{kind:'workbook', schemaVersion, elements, pages, "
            "layout}} and rejects the old flat shape with `Expecting { schemaVersion: 1 } "
            "at document`. See scripts/compose/grid.py::workbook()."
        )
        return issues
    doc = spec["document"]
    if doc.get("kind") != "workbook":
        issues.append(f"document.kind is {doc.get('kind')!r}; must be \"workbook\".")
    if "schemaVersion" not in doc:
        issues.append("document.schemaVersion is required.")
    for p in doc.get("pages", []) or []:
        if "elements" in p:
            issues.append(
                f"document.pages[{p.get('id')}].elements is no longer supported — move "
                "them to the flat document.elements[] array. Page membership comes from "
                "`layout` placement now."
            )
    if "themeOverrides" in doc:
        issues.append(
            "document.themeOverrides is no longer supported. Use "
            "document.settings.theme.overrides instead."
        )
    return issues


def issues_per_page_layout(spec: dict) -> list[str]:
    issues = []
    for i, p in enumerate(_doc(spec).get("pages", [])):
        if p.get("layout"):
            issues.append(
                f"pages[{i}] ({p.get('id')}): has a per-page `layout` field. "
                "Sigma silently discards it — move to the top-level `layout` "
                "string with all <Page> elements as siblings."
            )
    return issues


def _parse_layout(layout: str) -> ET.Element | None:
    if not layout:
        return None
    # Multi-page layout is multiple <Page> siblings under one <?xml ... ?> decl —
    # not a valid single-root XML doc. Wrap to parse.
    cleaned = re.sub(r"<\?xml[^?]*\?>", "", layout).strip()
    wrapped = f"<root>{cleaned}</root>"
    try:
        return ET.fromstring(wrapped)
    except ET.ParseError as e:
        sys.stderr.write(f"validate-spec: layout XML failed to parse: {e}\n")
        return None


def _placed_ids(root: ET.Element) -> set[str]:
    return {
        el.get("elementId")
        for el in root.iter()
        if el.tag in ("Element", "Container", "TabbedContainer")
        and el.get("elementId")
    }


def _unplaced(spec: dict, root: ET.Element | None) -> list[tuple[int, dict]]:
    if root is None:
        return []
    placed = _placed_ids(root)
    return [(pi, el) for pi, _, el in _elements(spec)
            if el.get("id") and el["id"] not in placed]


def _is_data_spine(el: dict) -> bool:
    """A source-only element: fed to other elements, deliberately not on the canvas.

    `visibleAsSource: true` is the marker. The canned generator's custom-SQL base table
    and its synthetic plugin source are both of these, so treating an unplaced spine as
    an error would block Mode A at the wrapper.
    """
    return bool(el.get("visibleAsSource")) and el.get("kind") in ("table", "input-table")


def issues_elements_placed(spec: dict, root: ET.Element | None) -> list[str]:
    if root is None:
        return ["no top-level `layout` field — workbook will have an auto-generated layout"]
    return [
        f"pages[{pi}].elements ({el['id']}, kind={el.get('kind')}): "
        "not placed in the layout XML — will render at the page bottom or not at all."
        for pi, el in _unplaced(spec, root) if not _is_data_spine(el)
    ]


def issues_data_spine_placement(spec: dict, root: ET.Element | None) -> list[str]:
    """Unplaced source elements are now REJECTED, not appended.

    Before the 2026-08-10 format change Sigma tolerated an unplaced element and dropped
    it at the page bottom (ugly but working). The new API rejects the spec outright:
    `elements[0]: element 'tbl' is not placed in layout`. So a data spine MUST be placed
    somewhere — put it on its own page and mark that page hidden
    (`"pages": [..., {"id":"util","name":"Model Sources","visibility":"hidden"}]`).
    """
    return [
        f"element `{el['id']}` (kind={el.get('kind')}) is source-only (visibleAsSource) "
        "and not placed in the layout — the API REJECTS this now ('is not placed in "
        "layout'). Place it on a hidden utility page."
        for _, el in _unplaced(spec, root) if _is_data_spine(el)
    ]


def issues_layout_refs_exist(spec: dict, root: ET.Element | None) -> list[str]:
    """The server's verify endpoint returns valid:true for these — we must catch them."""
    if root is None:
        return []
    declared = {el.get("id") for _, _, el in _elements(spec) if el.get("id")}
    issues = []
    for eid in sorted(i for i in _placed_ids(root) if i not in declared):
        issues.append(
            f"layout XML references elementId `{eid}`, which is not declared in any "
            "page's `elements`. `spec/verify` returns valid:true for this — the element "
            "simply never renders."
        )
    return issues


def issues_containers_have_children(spec: dict, root: ET.Element | None) -> list[str]:
    if root is None:
        return []
    container_ids = [
        el.get("id") for _, _, el in _elements(spec) if el.get("kind") == "container"
    ]
    issues = []
    for cid in container_ids:
        gc = next((el for el in root.iter("Container") if el.get("elementId") == cid), None)
        if gc is None:
            issues.append(
                f"container element `{cid}`: no matching <Container> in layout XML."
            )
        elif len(list(gc)) == 0:
            issues.append(
                f"container element `{cid}`: <Container> has no nested children. "
                "Children must be nested INSIDE the <Container>, not flat siblings."
            )
    return issues


def issues_no_gridcontainer_in_tab(spec: dict, root: ET.Element | None) -> list[str]:
    """Accepted by POST, but verified to scramble render order inside a <Tab>."""
    if root is None:
        return []
    issues = []
    for tab in root.iter("Tab"):
        for gc in tab.iter("GridContainer"):
            issues.append(
                f"<Container elementId=\"{gc.get('elementId')}\"> is nested inside a "
                "<Tab>. POST accepts it, then elements render out of declared order with "
                "large gaps (masked failure). Use bare <Element> children in a Tab."
            )
    return issues



def issues_kpi_on_gradient_bg(spec: dict, root) -> list[str]:
    """A kpi-chart / line-chart placed inside a container that carries a backgroundImage
    (i.e. a gradient KPI card) MUST declare its own solid `style.backgroundColor`.

    Without it the child renders on the theme's default WHITE element background, so the
    white value text lands on a white panel and the KPI is invisible. POST accepts it and
    spec/verify passes -- this is a purely visual, masked failure, and it has shipped twice
    (one build used "transparent", which spec/verify REJECTS as a masked
    `Invalid kind: "kpi-chart"`; omitting the key entirely is what works, 2026-08-19).

    The fix is the gradient's own midpoint hex -- see `_grad_mid()` in the generators.
    """
    if root is None:
        return []
    els = {e.get("id"): e for _, _, e in _elements(spec) if isinstance(e, dict)}
    issues = []
    for cont in root.iter():
        cid = cont.get("elementId")
        if not cid or not isinstance(els.get(cid), dict):
            continue
        if not els[cid].get("backgroundImage"):
            continue
        for child in cont.iter("Element"):
            ce = els.get(child.get("elementId"))
            if not isinstance(ce, dict) or ce.get("kind") not in ("kpi-chart", "line-chart"):
                continue
            bg = (ce.get("style") or {}).get("backgroundColor")
            if isinstance(bg, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", bg):
                continue
            issues.append(
                f"element `{ce.get('id')}` ({ce.get('kind')}) sits inside gradient card "
                f"`{cid}` but its style.backgroundColor is {bg!r}. It will render on the "
                "theme's WHITE element background -> white text on white (invisible KPI). "
                "Set it to the gradient's midpoint hex (_grad_mid); \"transparent\" and "
                "alpha hex are rejected by spec/verify."
            )
    return issues


def issues_control_id_unique(spec: dict) -> list[str]:
    seen: dict[str, str] = {}
    issues = []
    for _, _, el in _elements(spec):
        if el.get("kind") != "control":
            continue
        cid = el.get("controlId")
        if not cid:
            continue
        if cid in seen:
            issues.append(
                f"controlId `{cid}` duplicated on elements {seen[cid]} and {el.get('id')}. "
                "controlId is workbook-wide unique."
            )
        else:
            seen[cid] = el.get("id")
    return issues


def issues_agent_refs(spec: dict) -> list[str]:
    """Agents live in a top-level `agents[]`; `chat` elements point at them by id."""
    agents = _doc(spec).get("agents", []) or []
    agent_ids: dict[str, int] = {}
    issues = []
    for i, a in enumerate(agents):
        aid = a.get("id")
        if not aid:
            issues.append(f"agents[{i}]: missing `id`.")
            continue
        if aid in agent_ids:
            issues.append(f"agents[{i}]: duplicate agent id `{aid}`.")
        agent_ids[aid] = i

    declared_elements = {el.get("id") for _, _, el in _elements(spec) if el.get("id")}

    chats = [(pi, el) for pi, _, el in _elements(spec) if el.get("kind") == "chat"]
    for pi, el in chats:
        aid = el.get("agentId")
        if not aid:
            issues.append(f"pages[{pi}] chat element `{el.get('id')}`: missing `agentId`.")
        elif aid not in agent_ids:
            issues.append(
                f"pages[{pi}] chat element `{el.get('id')}`: agentId `{aid}` is not "
                "declared in the top-level `agents[]` — the panel renders empty."
            )
    if agents and not chats:
        issues.append(
            f"{len(agents)} agent(s) declared but no `chat` element references them — "
            "the agents exist but are unreachable in the workbook."
        )

    for i, a in enumerate(agents):
        for j, ds in enumerate(a.get("dataSources", []) or []):
            eid = ds.get("elementId")
            if not eid:
                issues.append(
                    f"agents[{i}] ({a.get('id')}).dataSources[{j}]: no `elementId`. An agent "
                    "data source must be a workbook ELEMENT — pointing at a dataModel id is "
                    "rejected (`references unknown element`). Put an element on the data "
                    "model and target that."
                )
            elif eid not in declared_elements:
                issues.append(
                    f"agents[{i}] ({a.get('id')}).dataSources[{j}]: elementId `{eid}` "
                    "does not exist — the agent has no data to answer from."
                )
        issues += _greeting_issues(i, a)
        issues += _tool_issues(spec, i, a)
    return issues


# `mode` is NOT enum-validated server-side: "fixed"/"custom"/"none" all pass
# spec/verify as long as `prompt` is present. Only these two branches are real.
_GREETING_MODES = {"generated": "prompt", "static": "message"}

# A distinct `unknown action effect` error is a reliable negative; these three earn it.
_REJECTED_EFFECTS = {"export", "send-notification", "trigger-sequence"}
# Recognized by the server, but with no worked-out payload shape yet.
_UNPROVEN_EFFECTS = {"update-rows", "clear-control", "select-tab", "refresh-element"}


def _greeting_issues(i: int, a: dict) -> list[str]:
    if "greeting" not in a:
        return []  # valid — but the agent then auto-generates its opener
    g = a["greeting"]
    aid = a.get("id")
    if not isinstance(g, dict) or not g:
        return [f"agents[{i}] ({aid}).greeting: `{{}}` / non-object is rejected (HTTP 400). "
                "Omit the key entirely, or give it a mode."]
    mode = g.get("mode")
    if mode not in _GREETING_MODES:
        return [
            f"agents[{i}] ({aid}).greeting.mode = {mode!r}. Only \"generated\" (with "
            "`prompt`) and \"static\" (with `message`) are real. Other values PASS "
            "spec/verify — `mode` isn't enum-checked — so a typo reaches the org silently."
        ]
    need = _GREETING_MODES[mode]
    if not g.get(need):
        return [f"agents[{i}] ({aid}).greeting: mode=\"{mode}\" requires `{need}`."]
    return []


def _tool_issues(spec: dict, i: int, a: dict) -> list[str]:
    # An agent action can only write into a table that already exists in the spec,
    # and can only set a control that exists. Both are masked failures at runtime:
    # the agent reports success and nothing happens.
    by_id = {el.get("id"): el for _, _, el in _elements(spec) if el.get("id")}
    control_ids = {
        el.get("controlId") for _, _, el in _elements(spec)
        if el.get("kind") == "control" and el.get("controlId")
    }
    issues = []
    for j, t in enumerate(a.get("tools", []) or []):
        where = f"agents[{i}] ({a.get('id')}).tools[{j}] ({t.get('toolId')})"
        kind = t.get("kind")
        if kind == "warehouse-agent":
            if not t.get("connectionId") or not t.get("path"):
                issues.append(f"{where}: a warehouse-agent tool needs `connectionId` and "
                              "`path: [database, schema, object]`.")
            continue
        if kind != "action":
            issues.append(f"{where}: kind={kind!r}. Known kinds: \"action\", \"warehouse-agent\".")
            continue
        for k, step in enumerate(t.get("steps", []) or []):
            sk = step.get("kind")
            if sk == "sequence":
                if not step.get("sequenceId"):
                    issues.append(f"{where}.steps[{k}]: a sequence step needs `sequenceId`.")
                continue
            if sk != "effect":
                issues.append(
                    f"{where}.steps[{k}]: kind={sk!r} — `unknown action tool step`. Use "
                    "`{kind:\"effect\",...}` or `{kind:\"sequence\",sequenceId}`."
                )
                continue
            eff = step.get("effect")
            at = f"{where}.steps[{k}]"
            if eff in _REJECTED_EFFECTS:
                issues.append(f"{at}: effect={eff!r} is rejected (`unknown action effect`).")
            elif eff in _UNPROVEN_EFFECTS:
                issues.append(
                    f"{at}: effect={eff!r} is a recognized effect name but its payload shape "
                    "is not worked out — probe it against spec/verify before shipping. "
                    "See reference/agents.md."
                )
            elif eff == "insert-rows":
                issues += _insert_rows_issues(at, step, by_id)
            elif eff == "set-control-value":
                ctrl = step.get("control")
                if not ctrl:
                    issues.append(f"{at}: a set-control-value step needs `control`.")
                elif control_ids and ctrl not in control_ids:
                    issues.append(
                        f"{at}: control `{ctrl}` is not a declared `controlId` in this "
                        "workbook. The agent will report success and nothing will move."
                    )
    return issues


def _insert_rows_issues(at: str, step: dict, by_id: dict) -> list[str]:
    """An agent can only write into an input table that already exists in the spec."""
    tid = step.get("table")
    if not tid:
        return [f"{at}: an insert-rows step needs `table` (an input-table element id)."]
    target = by_id.get(tid)
    if target is None:
        return [
            f"{at}: table `{tid}` does not exist in this spec. An agent cannot create its "
            "own write target — declare the input table first. For a findings/decision log "
            "use an EMPTY input table: {kind:\"input-table\", inputMode:\"explore\", "
            "source:{kind:\"empty\", connectionId:\"<uuid>\"}, columns:[...]}. For projections "
            "use a linked input table. See reference/agents.md."
        ]
    issues = []
    if target.get("kind") != "input-table":
        issues.append(
            f"{at}: table `{tid}` is a `{target.get('kind')}` element, not an `input-table`. "
            "insert-rows can only append to an input table."
        )
        return issues
    mode = target.get("inputMode")
    if mode not in ("edit", "explore", "view"):
        issues.append(
            f"{at}: target input table `{tid}` has inputMode={mode!r}. The enum is "
            "\"edit\" (editors, draft only) / \"explore\" (explore-or-greater, published) / "
            "\"view\" (everyone, published)."
        )
    cols = {c.get("id") for c in (target.get("columns") or []) if c.get("id")}
    for key, val in (step.get("values") or {}).items():
        if isinstance(val, dict) and val.get("type") == "agent-input" and not val.get("inputName"):
            issues.append(
                f"{at}: values[{key}] is an agent-input with no `inputName`. That is now "
                "REJECTED (verified 2026-08-11) and `inputName` doubles as the parameter "
                "description the agent reads — write it as an instruction."
            )
        if key not in cols:
            issues.append(
                f"{at}: values key `{key}` is not a column on input table `{tid}` "
                f"(declared: {sorted(cols)}). Tool values are keyed by column ID."
            )
    return issues


def _walk(node, path="$"):
    """Yield (path, key, value) for every mapping key anywhere in the spec."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k, v
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def issues_sort_direction(spec: dict) -> list[str]:
    """`asc`/`desc` POST "fine", then the whole `sort` key silently vanishes."""
    issues = []
    for path, k, v in _walk(spec):
        if k == "direction" and v in ("asc", "desc"):
            issues.append(
                f"{path}.direction = \"{v}\" — must be \"ascending\"/\"descending\". "
                "The short spelling POSTs without error and then the entire enclosing "
                "`sort` key is silently dropped."
            )
    return issues


def issues_text_vertical_align(spec: dict) -> list[str]:
    issues = []
    for pi, _, el in _elements(spec):
        va = el.get("verticalAlign")
        if el.get("kind") == "text" and va and va != "middle":
            issues.append(
                f"pages[{pi}] text element `{el.get('id')}`: verticalAlign=\"{va}\" is "
                "rejected (masked as `Invalid kind`). Only \"middle\" is accepted."
            )
    return issues


def issues_padding(spec: dict) -> list[str]:
    issues = []
    for path, k, v in _walk(spec):
        if k == "padding" and v != "none":
            issues.append(
                f"{path}.padding = {v!r} — rejected. `\"none\"` is the only accepted value."
            )
    return issues


def issues_plugin_config_strings(spec: dict) -> list[str]:
    """Every plugin config value must be a string, incl. numeric-looking ones."""
    issues = []
    for pi, _, el in _elements(spec):
        if el.get("kind") != "plugin":
            continue
        for k, v in (el.get("config") or {}).items():
            if k == "source":
                continue
            if isinstance(v, dict):
                issues.append(
                    f"pages[{pi}] plugin `{el.get('id')}`.config.{k}: object form "
                    "`{kind:\"column\",...}` is rejected from code (masked as "
                    "`Invalid kind:\"plugin\"`). Use a bare columnId string."
                )
            elif not isinstance(v, str):
                issues.append(
                    f"pages[{pi}] plugin `{el.get('id')}`.config.{k} = {v!r} — plugin "
                    "config values must ALL be strings (masked as `Invalid kind:\"plugin\"`)."
                )
    return issues


def issues_background_image_shape(spec: dict) -> list[str]:
    """CREATE now requires backgroundImage.source; the bare `url` form is rejected.

    Verified 2026-07-30. The live DraftKings workbook's GET-back still shows the OLD
    `{"url": ...}` form, so a round-tripped spec looks fine while a fresh POST of the
    same shape fails with `backgroundImage.source: Invalid value: undefined`. Every
    generator in this repo emitted the old shape until this check was added.
    """
    issues = []
    for pi, _, el in _elements(spec):
        bi = el.get("backgroundImage")
        if not isinstance(bi, dict):
            continue
        src = bi.get("source")
        if not isinstance(src, dict) or "url" not in src:
            issues.append(
                f"pages[{pi}].elements ({el.get('id')}).backgroundImage: needs "
                "`source: {kind: \"url\", url: \"<uri>\"}`. The bare `{url: ...}` form "
                "is rejected by CREATE (`backgroundImage.source: Invalid value: "
                "undefined`) even though older workbooks still GET back that way."
            )
    for pi, _, el in _elements(spec):
        if el.get("kind") != "image":
            continue
        src = el.get("source")
        if not isinstance(src, dict) or "url" not in src:
            issues.append(
                f"pages[{pi}].elements ({el.get('id')}, kind=image): needs "
                "`source: {kind: \"url\", url: \"<uri>\"}`. A bare `url` is rejected as "
                "`Invalid kind: \"image\"` — a MASKED error: the kind is fine, the field "
                "isn't. Run scripts/spec_normalize.py to migrate a spec."
            )
    return issues


def issues_data_label_singular(spec: dict) -> list[str]:
    issues = []
    for pi, _, el in _elements(spec):
        if "dataLabels" in el:
            issues.append(
                f"pages[{pi}] element `{el.get('id')}`: `dataLabels` (plural) is silently "
                "dropped. The accepted key is `dataLabel` (singular)."
            )
    return issues


def issues_field_substring_keys(spec: dict) -> list[str]:
    """Cloudflare's WAF blocks the request outright — you get an HTML block page."""
    bad = sorted({k for _, k, _ in _walk(spec) if "field" in k.lower()})
    return [
        f"JSON key `{k}` contains the substring \"field\" — Cloudflare's WAF blocks the "
        "request and returns an HTML block page instead of a Sigma error. Rename it "
        "(e.g. `...Column`)."
        for k in bad
    ]


def main() -> None:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: validate-spec.py <spec.json>\n")
        sys.exit(2)
    with open(sys.argv[1]) as f:
        spec = json.load(f)

    root = _parse_layout(_doc(spec).get("layout", ""))

    # ERROR blocks the POST. WARN prints but does not block: a real workbook has
    # shipped with it, so it's a documented render risk rather than a hard reject.
    errors: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    for sev, tag, fn in [
        ("E", "spec-envelope",             lambda: issues_spec_envelope(spec)),
        ("E", "no-per-page-layout",        lambda: issues_per_page_layout(spec)),
        ("E", "elements-placed-in-layout", lambda: issues_elements_placed(spec, root)),
        ("E", "data-spine-placement",     lambda: issues_data_spine_placement(spec, root)),
        ("E", "layout-refs-exist",         lambda: issues_layout_refs_exist(spec, root)),
        ("E", "containers-have-children",  lambda: issues_containers_have_children(spec, root)),
        ("W", "no-gridcontainer-in-tab",   lambda: issues_no_gridcontainer_in_tab(spec, root)),
        ("E", "control-id-unique",         lambda: issues_control_id_unique(spec)),
        ("E", "agent-refs-resolve",        lambda: issues_agent_refs(spec)),
        ("E", "sort-direction-spelling",   lambda: issues_sort_direction(spec)),
        ("E", "text-vertical-align",       lambda: issues_text_vertical_align(spec)),
        ("E", "padding-value",             lambda: issues_padding(spec)),
        ("E", "plugin-config-strings",     lambda: issues_plugin_config_strings(spec)),
        ("E", "data-label-singular",       lambda: issues_data_label_singular(spec)),
        ("E", "background-image-shape",    lambda: issues_background_image_shape(spec)),
        ("E", "no-field-substring-keys",   lambda: issues_field_substring_keys(spec)),
        ("E", "kpi-on-gradient-needs-bg",  lambda: issues_kpi_on_gradient_bg(spec, root)),
    ]:
        for msg in fn():
            (errors if sev == "E" else warnings).append((tag, msg))

    for tag, msg in warnings:
        sys.stderr.write(f"[warn: {tag}] {msg}\n")

    if not errors:
        note = f" ({len(warnings)} warning(s))" if warnings else ""
        print(f"validate-spec: {sys.argv[1]} — all {len(CHECKS)} checks passed{note}")
        sys.exit(0)

    for tag, msg in errors:
        sys.stderr.write(f"[{tag}] {msg}\n")
    sys.stderr.write(f"\nvalidate-spec: {len(errors)} error(s) found in {sys.argv[1]}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
