# Text-Aware Connector Clipping for All Renderers

## Context

The codebase has three inconsistent approaches to connector-to-label attachment:

1. **BKChem Tk renderer** (`bond.py:329-347`): Clips bonds at label bounding
   box edges using `geometry.intersection_of_line_and_rect()`. Correct.
2. **OASA molecular renderer** (`render_geometry.py:379-474`): Bonds go
   center-to-center, a white mask polygon hides the overlap. No clipping.
3. **OASA Haworth renderer** (`haworth/renderer.py` + 4 helper modules): 13+
   empirical constants nudge connectors and labels into approximate alignment.
   No bounding box, no intersection computation.

The underlying problem is "connector geometry does not respect text extents"
across renderers. Haworth makes the failure obvious because it has many short
connectors terminating at dense labels, but the same issue affects:

- Standard molecule rendering: bonds to atom labels (C, N, Cl, NH3+, charges)
- Any annotation objects that have text with leader lines
- Export backends: SVG, PDF, PNG should all share the same clipping rule

Bond and label attachment is part of the depiction semantics of CDML rendering,
so it belongs in OASA's render-ops pipeline and must be backend-independent.

The correct algorithm (line-rectangle intersection) already exists in
`packages/oasa/oasa/geometry.py:145-199` but is only used by BKChem's Tk
renderer. This plan makes OASA render-ops the source of truth and has all
backends use it. BKChem should not carry its own competing version.

## Phase Status Tracker

- [ ] Phase 1: Shared label bbox and connector clipping
- [ ] Phase 2: Apply to both renderers

## Design decisions

### Proportional constants, not system font metrics

BKChem's Tk renderer queries real font metrics (`font.measure()`,
`font.metrics()['descent']`) to compute label bboxes. This is accurate for
the running system but varies across OSes and font configurations -- the same
CDML file renders differently on macOS vs Linux because font bounding boxes
differ.

The OASA standalone renderers use **fixed proportional constants** (e.g.
`box_width = font_size * 0.75 * text_len`). These are approximate but
deterministic: the same inputs always produce the same bbox regardless of
platform. This means connector-to-label attachment is reproducible without
storing attachment geometry in CDML.

This plan keeps the proportional-constant approach. CDML stores attachment
*intent* (`attach_atom="first|last"`) but not coordinates, because:

- The full label bbox is derivable from `(text, anchor, font_size)` using the
  fixed constants.
- The attachment sub-region within a multi-atom label is derivable from
  `(text, attach_atom, anchor, font_size)`.
- The same `label_bbox()` and `label_attach_bbox()` calls produce identical
  results on every platform.
- Stored pixel coordinates would become stale whenever the user changes font
  size.
- Attachment geometry is a rendering concern; attachment *intent* is chemical
  data (which end of "CH2OH" connects to the bond).

If a future phase requires pixel-accurate text measurement (e.g. for
font-metric-aware collision detection), that can be added as an optional
`label_bbox()` backend without changing the CDML format. The proportional
default remains the portable baseline.

### Single source of truth for label extents

`label_bbox()` is the **only** definition of label extents used anywhere:

- `build_vertex_ops()` mask polygon uses `label_bbox()`.
- Molecular bond clipping uses `label_bbox()`.
- Haworth layout bbox uses `label_bbox()` (replaces `job_text_bbox()`).

This prevents subtle mismatches where the mask and the clip disagree.

### Attachment intent for multi-atom labels

CDML does not store geometry of the attachment, but may store intent for which
part of a multi-character label the connector attaches to.

- Use optional `attach_atom="first|last"` on label-bearing objects.
- `first` and `last` are defined in token order in the label string, not
  screen space, so mirroring/rotation does not change the meaning.
- Default is `first` unless a future label type defines a different default.
- Geometry remains renderer-derived via `label_bbox()` and line-rectangle
  intersection.

"CDML may optionally store attachment intent (attach_atom=\"first|last\") for
multi-atom labels so connectors reliably attach to the chemically meaningful
end of a group label, while geometry remains renderer-derived via label_bbox()
and line-rect intersection."

### Compatibility promise

- Older readers ignore optional `attach_atom` and continue to clip against the
  full label bbox (safe fallback).
- New readers clip multi-atom labels against `label_attach_bbox()`, defaulting
  missing `attach_atom` to `"first"`.
- No structural molecule graph data changes are required for this feature.

### Separation of concerns

- `_baseline_shift()` and `anchor_x_offset()` define **text placement** only
  (where the text origin goes relative to the label center).
- `clip_bond_to_bbox()` defines **connector termination** only (where the
  connector line meets the label boundary).

These two concerns must not be coupled. If this separation is maintained, every
renderer becomes easier to reason about.

### Haworth connector clipping invariant

In Haworth, the connector's `bond_end` must be guaranteed to lie inside the
label bbox so that clipping always occurs deterministically. Pass the label
anchor point (the text origin position) as `bond_end`. Treat "origin inside
bbox" as an explicit invariant backed by unit tests across `start`, `middle`,
and `end` anchors for multi-character labels. This avoids edge cases where a
computed endpoint outside the bbox would bypass clipping.

## Phase 1: Shared label bbox and connector clipping

Extract the label bounding box computation that already exists inline in
`render_geometry.build_vertex_ops()` (lines 400-423) into a reusable function,
and wrap `geometry.intersection_of_line_and_rect()` as a connector clipping
utility.

### Deliverables

**Modify**: `packages/oasa/oasa/render_geometry.py`

Add three public functions:

```python
def label_bbox(x, y, text, anchor, font_size, font_name=None):
    """Compute axis-aligned bounding box for a label at (x, y).

    Returns (x1, y1, x2, y2) in normalized min/max order.
    Uses the same constants already in build_vertex_ops():
      box_width  = font_size * 0.75 * visible_length
      baseline_offset = font_size * 0.375
      top_offset = -font_size * 0.75
      bottom_offset = font_size * 0.125
      start_offset = font_size * 0.3125
    """

def label_attach_bbox(x, y, text, anchor, font_size, attach_atom="first",
                      font_name=None):
    """Compute bbox for the attachment region of a multi-atom label.

    For single-atom labels, returns the same as label_bbox().
    For multi-atom labels, returns the bbox of just the first or last
    atom token (determined by attach_atom), using the same proportional
    constants. This is the region where the bond connector should
    terminate.

    Args:
        attach_atom: "first" or "last". Which atom token in the label
            text is the bond attachment point.
    Returns:
        (x1, y1, x2, y2) -- bbox of the attachment sub-region.
    """

def clip_bond_to_bbox(bond_start, bond_end, bbox):
    """Clip bond_end to the edge of bbox using line-rect intersection.

    If bond_end is inside bbox, returns the intersection point on the
    bbox perimeter.  If bond_end is outside bbox, returns bond_end
    unchanged.  Wraps geometry.intersection_of_line_and_rect().
    """
```

This keeps `clip_bond_to_bbox()` unchanged and makes `attach_atom` handling a
pure attachment-bbox selection problem.

Refactor `build_vertex_ops()` to call `label_bbox()` internally instead of
recomputing the rectangle inline.

**New test file**: `tests/test_label_bbox.py`

Unit tests for `label_bbox()`:
- `test_label_bbox_single_char_middle`: single-char label at origin with
  "middle" anchor returns symmetric bbox.
- `test_label_bbox_multi_char_start`: multi-char "OH" with "start" anchor.
- `test_label_bbox_anchor_matrix`: iterate anchor in {start, middle, end} for
  strings {"O", "OH", "CH2OH", "NH3+", "Cl"} and assert bbox ordering
  (x1 < x2, y1 < y2) and non-zero area.
- `test_label_bbox_origin_inside_bbox_for_anchor_matrix`: for a multi-char
  label (for example "CH2OH"), assert the text origin lies inside the returned
  bbox for anchors `start`, `middle`, and `end`.
- `test_label_bbox_visible_length_strips_tags`: verify `label_bbox()` handles
  subscript markup (e.g. "CH<sub>2</sub>OH" uses visible length 5, not 20).
- `test_label_bbox_matches_vertex_ops_mask`: for a given vertex, the bbox from
  `label_bbox()` matches the white mask polygon emitted by `build_vertex_ops()`.

Unit tests for `label_attach_bbox()`:
- `test_label_attach_bbox_single_atom_same_as_label_bbox`: for "O", "N", "Cl",
  `label_attach_bbox()` returns the same result as `label_bbox()` regardless
  of `attach_atom` value.
- `test_label_attach_bbox_multi_atom_first`: for "CH2OH" with
  `attach_atom="first"`, the returned bbox covers only the "C" region and is
  narrower than `label_bbox()`.
- `test_label_attach_bbox_multi_atom_last`: for "CH2OH" with
  `attach_atom="last"`, the returned bbox covers only the "OH" region at the
  end of the label.
- `test_label_attach_bbox_within_label_bbox`: for all test cases, the attach
  bbox is contained within (or equal to) the full label bbox.
- `test_attach_bbox_first_last_ch2oh`: for `"CH2OH"`, verify the `"first"` bbox
  is on the C-side and the `"last"` bbox is on the OH-side (relative ordering
  in bbox coordinates for each anchor).

Clipping tests:
- `test_clip_bond_inside_bbox`: bond endpoint inside bbox gets clipped to edge.
- `test_clip_bond_outside_bbox`: bond endpoint outside bbox is unchanged.
- `test_clip_bond_vertical`: vertical bond clips correctly.
- `test_clip_bond_horizontal`: horizontal bond clips correctly.
- `test_clip_bond_diagonal`: diagonal bond clips to correct edge.
- `test_clips_to_attach_bbox_not_full_bbox`: for a long multi-atom label where
  full-bbox clipping could hit the wrong character, assert clipping uses the
  attach bbox.

### Done checks

- [ ] `label_bbox()` exists and returns `(x1, y1, x2, y2)`.
- [ ] `label_attach_bbox()` exists and returns `(x1, y1, x2, y2)` for the
      attachment sub-region within a multi-atom label.
- [ ] `clip_bond_to_bbox()` exists and delegates to
      `geometry.intersection_of_line_and_rect()`.
- [ ] `build_vertex_ops()` uses `label_bbox()` internally.
- [ ] All new and existing `test_codec_registry*.py` and
      `test_phase_c_render_pipeline.py` tests still pass.
- [ ] `test_label_bbox.py` passes.

## Phase 2: Apply to both renderers

### 2a: Molecular renderer bond clipping

**Modify**: `packages/oasa/oasa/render_geometry.py`

Change `molecule_to_ops()` to:

1. Pre-compute `full_bbox = label_bbox(...)` for every shown vertex and store
   in a dict keyed by vertex.
2. For every shown multi-atom label, compute
   `attach_mode = vertex.attach_atom if present else "first"` and then compute
   `attach_bbox = label_attach_bbox(..., attach_atom=attach_mode)`; store in a
   second dict keyed by vertex.
3. Use `full_bbox` for white mask polygons in `build_vertex_ops()` (cosmetic).
4. Pass both bbox dicts into `build_bond_ops()` (add parameters).
5. Inside `build_bond_ops()`, clip bond endpoints to `attach_bbox` for shown
   multi-atom labels (defaulting missing `attach_atom` to `"first"`); otherwise
   clip to `full_bbox` for shown labels and keep hidden vertices at atom
   centers.
6. Keep white masks for anti-aliased text backgrounds, but remove reliance on
   mask overlap for connector termination.

**New test file**: `tests/test_connector_clipping.py`

Non-sugar molecular fixtures (broader than Haworth):
- `test_bond_clipped_to_shown_vertex`: build a 2-atom molecule (C-O), render
  ops, verify the bond `LineOp` endpoint at the O end differs from the raw
  atom coordinate (clipped to label bbox edge).
- `test_bond_not_clipped_to_hidden_vertex`: build C-C (both hidden), verify
  bond endpoints match atom coordinates exactly.
- `test_double_bond_clipped`: double bond second line also respects clipping.
- `test_clipped_endpoint_on_bbox_edge`: for a clipped bond, assert the clipped
  endpoint lies exactly on one of the bbox edges (within tolerance), not just
  "shorter than before."
- `test_charged_label_clipping`: build molecule with NH3+ vertex, verify bond
  clips to the wider bbox of the charged label.
- `test_wedge_bond_clipped`: wedge bond to a shown vertex respects clipping.
- `test_multi_atom_label_attach_first`: build molecule with CH2OH group
  (`attach_atom="first"`), verify bond clips to the C-region bbox, not the
  full label bbox.
- `test_multi_atom_label_attach_last`: build molecule with CH2OH group
  (`attach_atom="last"`), verify bond clips to the OH-region bbox at the far
  end of the label.
- `test_multi_atom_label_attach_default_first_when_missing`: build molecule
  with CH2OH group and no `attach_atom` attribute, verify clipping matches the
  `"first"` behavior.

### 2b: Haworth renderer connector clipping

**Modify**: `packages/oasa/oasa/haworth/renderer.py`

Replace the current approach in `_add_simple_label_ops()` (lines 345-401):

Current flow:
1. Compute `end_point = vertex + direction * length`
2. Compute `text_x = end_point.x + anchor_x_offset(text, anchor, font_size)`
3. Compute `text_y = end_point.y + _baseline_shift(direction, font_size, text)`
4. Special-case: override `connector_end` for downward CH\* labels

New flow:
1. Compute the label's target position using the existing direction and length
   to determine where the label center/anchor should go.
2. Compute `full_bbox = label_bbox(...)` at that position.
3. For multi-atom labels, compute
   `attach_mode = label.attach_atom if present else "first"` and then compute
   `attach_bbox = label_attach_bbox(..., attach_atom=attach_mode)`; for
   single-atom labels use `full_bbox`.
4. Pass the label anchor point (text origin, guaranteed inside bbox) as
   `bond_end` to `clip_bond_to_bbox()`, with the ring vertex as `bond_start`,
   clipping against `attach_bbox` for multi-atom labels.
5. Draw `LineOp` from ring vertex to the clipped point.
6. Draw `TextOp` at the label position.

This eliminates:
- The special-case connector override for downward CH\* labels
  (`renderer.py:370-376`).
- Most of the hardcoded offsets in `anchor_x_offset()`
  (`renderer_text.py:78-100`) -- the function can be simplified to just handle
  side-aware hydroxyl text flipping (OH vs HO), not connector positioning.
- The duplicated `_baseline_shift()` function (exists in both `renderer.py:556`
  and `renderer_layout.py:370`).

**Note**: `_baseline_shift()` and `anchor_x_offset()` still have a role for
computing the label text position (where the text origin goes relative to the
label center), but they no longer drive connector endpoint computation. The
connector endpoint is now always the bbox edge intersection, independent of
label-specific offsets.

**Modify**: `packages/oasa/oasa/haworth/renderer_text.py`

Simplify `anchor_x_offset()` -- remove the connector-positioning role. It
should only handle text-origin placement (OH/HO flipping, C-leading/trailing
alignment). The 4 hardcoded OH/HO offset branches and the generic +/-0.12
fallback are replaced by `label_bbox()` + intersection.

**Modify**: `packages/oasa/oasa/haworth/renderer_layout.py`

- Replace `job_text_bbox()` (lines 302-316) with a call to the shared
  `label_bbox()` from `render_geometry`.
- Remove the duplicated `_baseline_shift()` (lines 370-384); import from
  `renderer.py` or a shared location.

**Modify tests**: `tests/test_haworth_renderer.py`

- Existing geometry verification tests
  (`test_render_alpha_glucose_c1_oh_below`, etc.) should continue to pass
  unchanged -- the label positions are the same, only the connector endpoints
  change.
- `test_connector_terminates_at_bbox_edge`: for alpha-D-glucopyranose, verify
  that every connector `LineOp` p2 lies on the perimeter of its corresponding
  label's `label_bbox()` (within floating-point tolerance).
- `test_connector_does_not_enter_bbox`: sample a point slightly past the
  clipped endpoint along the connector direction and assert it is inside the
  bbox, while the clipped endpoint is on the edge. This catches off-by-one
  errors where the clip lands on the wrong side.
- `test_no_connector_passes_through_label`: verify no connector `LineOp`
  extends past the label bbox boundary.
- Remove or update tests that assert specific magic-number connector lengths
  (e.g. `test_sub_length_multiplier_dual_wide`) since the connector length is
  now determined by bbox intersection, not a fixed multiplier.

### Done checks

- [ ] Molecular renderer bonds terminate at label bbox edges for shown vertices.
- [ ] Molecular renderer bonds still reach atom center for hidden vertices.
- [ ] Multi-atom labels clip to the `label_attach_bbox()` sub-region based on
      the vertex's `attach_atom` attribute, defaulting missing values to
      `"first"`.
- [ ] Haworth connectors terminate at label bbox edges.
- [ ] The special-case downward CH\* connector override is removed.
- [ ] `_baseline_shift()` exists in exactly one location (no duplication).
- [ ] `job_text_bbox()` in `renderer_layout.py` delegates to shared
      `label_bbox()`.
- [ ] All existing Haworth geometry tests pass (label positions unchanged).
- [ ] All existing molecular renderer tests pass.
- [ ] Full test suite passes.

## Key files

| Action | Phase | File |
|--------|-------|------|
| Modify | 1 | `packages/oasa/oasa/render_geometry.py` |
| Create | 1 | `tests/test_label_bbox.py` |
| Modify | 2a | `packages/oasa/oasa/render_geometry.py` |
| Create | 2a | `tests/test_connector_clipping.py` |
| Modify | 2b | `packages/oasa/oasa/haworth/renderer.py` |
| Modify | 2b | `packages/oasa/oasa/haworth/renderer_text.py` |
| Modify | 2b | `packages/oasa/oasa/haworth/renderer_layout.py` |
| Modify | 2b | `tests/test_haworth_renderer.py` |

## Reusable existing code

- `geometry.intersection_of_line_and_rect()` -- `packages/oasa/oasa/geometry.py:145-199`
- `geometry.point_distance()` -- `packages/oasa/oasa/geometry.py:202-203`
- `misc.normalize_coords()` -- `packages/oasa/oasa/misc.py:84-90`
- `geometry.do_rectangles_intersect()` -- `packages/oasa/oasa/geometry.py:214-233`
- `render_geometry.build_vertex_ops()` inline bbox constants -- lines 400-423

## Verification

1. `python -m pytest tests/test_label_bbox.py -v`
2. `python -m pytest tests/test_connector_clipping.py -v`
3. `python -m pytest tests/test_haworth_renderer.py -v`
4. `python -m pytest tests/test_codec_registry.py -v`
5. `python -m pytest tests/test_phase_c_render_pipeline.py -v`
6. `python -m pytest tests/ -q` (full regression)
7. `python tools/selftest_sheet.py --format svg` (visual inspection)
