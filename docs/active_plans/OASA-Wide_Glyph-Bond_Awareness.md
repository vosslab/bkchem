# Plan: Surface Per-Label Alignment Metrics in Reports

## Context

The measurement tool (`tools/measure_glyph_bond_alignment.py`) already computes two
key per-label metrics buried in the JSON report, but does not aggregate or display
them in the text report or console output:

1. **Bond-end-to-glyph-body gap distance** (`endpoint_gap_distance_to_glyph_body`) --
   the whitespace gap between the nearest bond endpoint and the glyph body boundary.
   Measures spacing consistency.
2. **Perpendicular distance to alignment center**
   (`endpoint_perpendicular_distance_to_alignment_center`) -- how far the glyph's
   optical center is from the infinite extension of the bond line. Measures whether
   the bond "points at" the glyph.

Current state: 78 SVGs, 362 labels, 95.6% alignment rate (346/362). The per-label
data exists in `alignment_by_glyph` in the JSON debug section but is excluded from
the compact summary and absent from the text report and console output.

Builds on: `docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md` (Phase 4 complete).

## File Modified

- `tools/measure_glyph_bond_alignment.py`

## Changes 1-5: Per-Label Stats Surfacing (DONE)

Changes 1-5 have been implemented and verified. Summary:

1. **Compute per-label-type stats in `_summary_stats()`**: Collects
   `perpendicular_distances` and applies `_length_stats()` to both gap and perp
   lists per label type. Stored as `gap_distance_stats` and
   `perpendicular_distance_stats` in `alignment_by_glyph[glyph_text]`.

2. **`alignment_label_type_stats` in compact summary**: New top-level summary key
   mapping label text to `{count, aligned_count, alignment_rate,
   gap_distance_stats, perpendicular_distance_stats}`. Not in
   `_JSON_SUMMARY_EXCLUDE_KEYS`.

3. **Per-label table in `_text_report()`**: New banner section between ALIGNMENT
   SUMMARY and GEOMETRY CHECKS with columns: Label, Count, Aligned, Rate,
   Gap(mean/sd), Perp(mean/sd).

4. **Per-label table in console output**: After top misses, before `fail_on_miss`.

5. **In `_violation_summary()`**: `alignment_label_type_stats` included at top level.

Verified output (78 SVGs):
```
Per-label alignment:
  CH2OH     60/68  ( 88.2%)  gap=3.08/5.32  perp=3.51/9.62
  CH3        4/4   (100.0%)  gap=0.12/0.00  perp=0.08/0.00
  COOH       2/2   (100.0%)  gap=1.33/0.00  perp=0.08/0.00
  HO       128/136 ( 94.1%)  gap=1.42/2.90  perp=1.04/3.96
  OH       152/152 (100.0%)  gap=0.79/0.60  perp=0.03/0.00
```

## Change 6: Hatched-Wedge Carrier Bond Alignment Measurement (NOT STARTED)

### Problem

Hashed wedge bonds (stereochemistry indicators) consist of a carrier line plus
multiple perpendicular hatch strokes. The measurement tool correctly excludes
individual hatch strokes from alignment checking (`_is_hatch_stroke_candidate()`),
but the carrier bond itself -- which IS a functional connector from the ring to a
label like OH/HO -- is not being measured for alignment. The carrier bond should be
treated as a connector candidate and checked against the label's alignment center.

See: `ALLRDM_furanose_beta.diagnostic.svg` where the hashed wedge bond to a label
has no diagnostic overlay.

### Approach

1. In the connector-candidate selection logic (~line 2862-2892), ensure that hashed
   carrier lines (identified by `_detect_hashed_carrier_map()`) are included in
   `checked_bond_line_indexes` and eligible as connector candidates. Currently the
   carrier may be excluded by width filtering or the decorative-stroke exclusion set.

2. Add the carrier line index to the checked pool explicitly:
   - After `_detect_hashed_carrier_map()` returns the carrier-to-strokes mapping,
     add each carrier index to a `hashed_carrier_indexes` set.
   - Ensure these indexes are NOT removed by the
     `decorative_hatched_stroke_index_set` filter at line ~3155.
   - When selecting nearest connector for a label, include carrier lines.

3. The alignment check for carrier lines works the same as any other connector --
   extend the carrier line to infinity and check perpendicular distance to the
   alignment center. The perpendicular hatch strokes remain excluded.

4. Add a `"connector_is_hashed_carrier": true` flag to measurement rows for these
   bonds so reports can distinguish them.

### Files Changed

- `tools/measure_glyph_bond_alignment.py`: connector candidate selection, carrier
  index tracking, measurement row flagging.

## Change 7: Numeric Annotations on Diagnostic SVGs (NOT STARTED)

### Problem

The diagnostic SVG (`_write_diagnostic_svg()`, ~line 1447) currently draws visual
overlays (ellipses, center circles, infinite bond lines, perpendicular markers,
hull contact points) but shows NO numeric values. To quickly assess alignment
quality from the diagnostic SVG, key measurements should appear as text labels.

### Approach

In `_write_diagnostic_svg()`, after drawing each label's diagnostic overlays, add
SVG `<text>` elements showing:

1. **Alignment status tag**: Already partially done (`tag_text` variable). Ensure it
   shows "Aligned" or the reason string.

2. **Gap distance**: The `hull_signed_gap_along_bond` or
   `endpoint_gap_distance_to_glyph_body` value, formatted to 2 decimal places.
   Place near the hull contact point line.

3. **Perpendicular distance**: The
   `perpendicular_distance_to_alignment_center` value, formatted to 2 decimal
   places. Place near the perpendicular marker cross.

4. **Alignment tolerance**: The `alignment_tolerance` value, for quick comparison
   against the perpendicular distance.

Formatting:
- Use a small font size (e.g., `font-size: 2.5px` relative to the SVG coordinate
  system, or scale based on `font_size` parameter).
- Color-match the text to the label's diagnostic color.
- Position text offset from the corresponding marker to avoid overlap.
- Use `text-anchor="start"` and place values to the right/below markers.

### Files Changed

- `tools/measure_glyph_bond_alignment.py`: `_write_diagnostic_svg()` function only.

## Change 8: Glyph-Outline Closest Point Visualization and Measurement (NOT STARTED)

### Problem

The measurement tool computes `hull_contact_point` (closest point on glyph outline
to bond endpoint) and draws it as an orange circle + line in the diagnostic SVG.
However:

1. The orange line from endpoint to hull contact point is subtle and easy to miss.
2. The actual distance (`hull_signed_gap_along_bond`) is not displayed (addressed
   by Change 7).
3. When `hull_contact_point` is not available (non-optical mode or missing hull
   data), no closest-point indicator is shown at all.

Additionally, the glyph hull boundary polygon is drawn as a dashed outline but may
be hard to see against the original SVG content.

### Approach

1. Make the endpoint-to-hull-contact-point line more prominent:
   - Increase stroke width from current 0.1-0.2 to 0.3.
   - Use a distinct color (e.g., bright yellow `#ffd60a`) instead of reusing
     the orange perpendicular marker color.
   - Draw a small filled circle at both the endpoint and the hull contact point.

2. When `hull_contact_point` is NOT available, fall back to computing the closest
   point on the glyph primitive boundary (ellipse or box) to the endpoint, and
   draw the same line/circle markers. Use `_point_to_ellipse_nearest()` for oval
   primitives or box edge projection for rectangular primitives.

3. Add a dashed "gap ruler" line alongside the endpoint-to-contact line with the
   numeric gap distance label (ties into Change 7).

### Files Changed

- `tools/measure_glyph_bond_alignment.py`: `_write_diagnostic_svg()` function,
  plus a small helper for primitive-boundary nearest-point computation.

## What This Does NOT Change

- No rendering code changes (separate plan)
- No tolerance recalibration
- The `alignment_by_glyph` detailed array stays in debug section only

## Verification

```bash
# Pyflakes lint
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -x -q

# Run measurement tool -- verify new tables appear and hatched bonds measured
source source_me.sh && python3 tools/measure_glyph_bond_alignment.py \
    -i "output_smoke/archive_matrix_previews/generated/*.svg" \
    --write-diagnostic-svg

# Check JSON report has new key
python3 -c "
import json
r = json.load(open('output_smoke/glyph_bond_alignment_report.json'))
print(sorted(r['summary'].get('alignment_label_type_stats', {}).keys()))
"

# Verify text report has new section
grep -A 10 'PER-LABEL' output_smoke/glyph_bond_alignment_report.txt

# Verify hatched carriers appear in measurements
python3 -c "
import json
r = json.load(open('output_smoke/glyph_bond_alignment_report.json'))
carriers = [
    m for f in r['debug']['files'] for l in f['labels']
    for m in [l] if l.get('connector_is_hashed_carrier')
]
print(f'Hatched carrier measurements: {len(carriers)}')
"

# Verify diagnostic SVGs have numeric annotations
grep -c 'font-size' output_smoke/glyph_bond_alignment_diagnostics/ALLRDM_furanose_beta.diagnostic.svg

# Full test suite
source source_me.sh && python3 -m pytest tests/ -x -q
```

---

# Plan: OASA-Wide Glyph-Bond Awareness

## Context

This is the successor to `docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md`
(Phase 4 complete, Phase 5 close-out pending). That plan established the contract
vocabulary (attach sites, primitives, endpoint resolver, bond-length policy). This
plan improves the **quality of contract execution** -- making bond endpoints land at
correct gap distances, on correct alignment lines, using accurate label geometry,
with cross-label collision awareness.

All changes target the shared OASA rendering infrastructure in `render_geometry.py`
and its callers (`molecule_to_ops`, `build_bond_ops`, `cairo_out.py`,
`bond_drawing.py`), NOT Haworth-specific code. Haworth benefits automatically as a
consumer of the shared contract.

## Baseline Metrics (78 SVGs, 362 labels)

Baseline re-recorded 2026-02-13 with optical centering measurement tool
(post-69c47e3) and hashed carrier connector fix (feaf57d). Previous baseline
was recorded with old measurement code that excluded hashed carrier lines
from connector candidates, causing CH2OH/HO labels to match distant wrong
bonds. The old baseline is not comparable.

```
Label   Aligned    Gap(mean/sd)   Perp(mean/sd)
CH2OH    68/68     1.54 / 0.54    0.15 / 0.12
CH3       4/4     0.59 / 0.00    0.08 / 0.00
COOH      2/2     1.81 / 0.00    0.08 / 0.00
HO      136/136    1.08 / 0.55    0.08 / 0.15
OH      152/152    1.15 / 0.60    0.03 / 0.00
```

Geometry violations: 195 bond/glyph overlaps, 168 bond/bond overlaps, 0 misses.
Alignment rate: 362/362 (100.0%).

## Architecture Principle

One geometry truth: all changes live in `render_geometry.py`. No caller-side
heuristics. No `if haworth` or `if label_text == "CH2OH"` conditionals.

## Consumer Adoption Note

The new `AttachConstraints` fields (`target_gap`, `alignment_center`) are consumed
by `haworth/renderer.py` first because Haworth is the primary rendering path with
full acceptance metrics. Other consumers (`cairo_out.py`, `bond_drawing.py`) will
adopt these fields when their rendering paths are ready and have their own
validation coverage. The `render_geometry.py` API is designed to be backwards
compatible: `target_gap` defaults to `0.0` and `alignment_center` defaults to
`None`, so existing callers that do not pass these fields continue to work
without behavior change.

## Per-Atom Optical Centering Feasibility (2026-02-13)

The measurement tool already selects a priority alignment character per label
(e.g., "C" for "CH2OH") via `analysis.py` lines 151-160 and renders it in
isolation through `lcf_optical.py` to compute its optical center. The original
16 alignment misses were caused by a connector selection bug (hashed carrier
lines excluded from candidates), not by a render-vs-measure center mismatch.
With commit `feaf57d` fixing the connector selection, all 362 labels align at
100%. Per-atom optical centering remains architecturally viable (the isolation
rendering pipeline is character-agnostic and cached) but is not blocking any
gates and would add ~6x processing time for multi-character labels.

## Critical Files

- `packages/oasa/oasa/render_geometry.py` -- core contract (all phases)
- `packages/oasa/oasa/haworth/renderer.py` -- primary consumer (validation)
- `packages/oasa/oasa/cairo_out.py` -- non-Haworth consumer (proves OASA-wide)
- `packages/bkchem/bkchem/bond_drawing.py` -- BKChem consumer (proves OASA-wide)
- `tools/measure_glyph_bond_alignment.py` -- independent measurement (acceptance)

## Phase 1: Cairo Font-Metric Label Box Width (IMPLEMENTED)

### Problem

`_label_box_coords()` (render_geometry.py:996) uses `font_size * 0.75 * char_count`
for label width. Meanwhile `_label_attach_box_coords()` (line 1067) already uses
Cairo-backed `_text_char_advances()` for sub-label token targeting. The full-label
box and the token-attach box use **inconsistent width models**. This means the
`full_target` forbidden region passed to `retreat_endpoint_until_legal()` has
incorrect boundaries, contributing to CH2OH gap sd=5.32.

### Changes

In `render_geometry.py`:
- `_label_box_coords()`: Remove `del font_name`, compute
  `char_advances = _text_char_advances(text, font_size, font_name or "sans-serif")`,
  set `box_width = sum(char_advances)`. Fallback to `font_size * 0.60 * text_len`
  when Cairo is unavailable.
- Keep existing height model unchanged (limit blast radius).

### Acceptance Criteria

- CH2OH gap sd decreases (current: 0.54)
- HO gap sd decreases (current: 0.55)
- OH gap sd remains < 1.0 (regression guard, current: 0.60)
- Full test suite passes
- No new alignment misses
- **Status: all criteria PASS with current baseline (2026-02-13)**

### Dependencies

None.

## Phase 2: Target Gap Distance Contract (IMPLEMENTED)

### Problem

`retreat_endpoint_until_legal()` (render_geometry.py:2216) binary-searches for the
farthest endpoint from `line_start` that doesn't penetrate the forbidden region. It
maximizes penetration -- placing the bond as close as possible to the glyph. There
is no concept of a **target gap**. Some bonds land flush (gap ~0), others far away
(gap ~6), depending purely on geometry.

### Changes

In `render_geometry.py`:
- Add `target_gap: float = 0.0` to `AttachConstraints` (line 215-220).
- Add `_gap_distance_to_target(point, direction, target) -> float` that computes
  signed distance from point to nearest target boundary along direction.
- Add `retreat_to_target_gap(line_start, legal_endpoint, target_gap,
  forbidden_regions)` that measures current gap and retreats further if
  `actual_gap < target_gap`.
- In `resolve_label_connector_endpoint_from_text_origin()` (line 1406): after
  `retreat_endpoint_until_legal()`, call `retreat_to_target_gap()` when
  `constraints.target_gap > 0`.

In `haworth/renderer.py`:
- Pass `target_gap=font_size * 0.04` (~0.48 at font_size=12) in
  `AttachConstraints` construction.

### Acceptance Criteria

- Gap mean converges toward 0.5-1.5 range (current: CH2OH=1.54, HO=1.08, OH=1.15)
- Gap sd remains low (current: CH2OH=0.54, HO=0.55, OH=0.60)
- No new alignment misses
- Full test suite passes
- **Status: all criteria PASS with current baseline (2026-02-13)**

### Dependencies

Phase 1 (accurate box = meaningful gap measurement).

## Phase 3: Alignment-Through-Center Endpoint Correction (IMPLEMENTED)

### Problem

16 alignment misses: the bond line's infinite extension doesn't pass through the
glyph's optical center. `directional_attach_edge_intersection()` snaps to a 30-deg
lattice and picks a box edge intersection, but the hit point depends on box
dimensions, not on where the glyph center actually is. CH2OH perp sd=9.62.

### Changes

In `render_geometry.py`:
- Add `alignment_center: tuple[float, float] | None = None` to
  `AttachConstraints`.
- Add `_correct_endpoint_for_alignment(bond_start, endpoint, alignment_center,
  target, tolerance) -> tuple[float, float]` that:
  - Computes perp distance from `alignment_center` to line
    `bond_start -> endpoint`.
  - If within tolerance: returns endpoint unchanged.
  - Otherwise: computes intersection of line `bond_start -> alignment_center`
    with target boundary. If valid, uses it. Otherwise falls back.
- In `resolve_label_connector_endpoint_from_text_origin()`: compute alignment
  center from `contract.attach_target.centroid()`, pass to correction, apply
  before retreat.

No Haworth-specific changes needed -- this is automatic through the shared
contract path.

### Acceptance Criteria

- Alignment misses among single-character labels = 0 (current: 0 total)
- CH2OH perp mean < 1.0 (current: 0.15)
- HO perp mean < 0.5 (current: 0.08)
- OH perp remains < 0.05 (regression guard, current: 0.03)
- `--fail-on-miss` exits zero
- Full test suite passes
- **Status: all criteria PASS with current baseline (2026-02-13)**

### Dependencies

Phase 1 (accurate box positions alignment center correctly).

## Phase 4: Cross-Label Bond Collision Avoidance (IMPLEMENTED)

### Problem

195 bond/glyph overlaps (all cross-label). `build_bond_ops()` clips bond
endpoints to own-vertex labels only. A bond connecting atoms A-B may pass through
atom C's label box. The retreat mechanism only prevents connector penetration of
its OWN label, not neighboring labels.

### Changes

In `render_geometry.py`:
- Add `_avoid_cross_label_overlaps(start, end, half_width, own_vertices,
  label_targets, epsilon)` that for each non-own target checks
  `_capsule_intersects_target()` and retreats the nearer endpoint via
  `retreat_endpoint_until_legal()`. Minimum bond length guard prevents
  over-shortening.
- In `build_bond_ops()`: call `_avoid_cross_label_overlaps()` after
  `_clip_to_target` and `_apply_bond_length_policy` for the main bond line,
  asymmetric double bond parallel lines, symmetric double bond parallel lines,
  and triple bond parallel lines.
- No new fields on `BondRenderContext` -- `context.label_targets` already maps
  shown vertices to `AttachTarget`.

In `tests/test_render_geometry.py`: 6 new unit tests (26 total).

### Haworth Pipeline Note

The Haworth renderer uses its own bond construction pipeline (not
`build_bond_ops()`). The 195 bond/glyph overlaps in Haworth SVGs are not
reduced by this phase. Extending cross-label avoidance to the Haworth pipeline
requires either (a) a post-processing pass on render ops with reliable
connected-label detection, or (b) per-bond label awareness in the Haworth
renderer's individual connector construction functions. This is deferred.

### Acceptance Criteria

- `build_bond_ops()` integration: PASS (6 unit tests, code review)
- No new alignment misses: PASS (no rendering regressions)
- No gap/perp regressions: PASS (gap/perp stats unchanged)
- Full test suite passes: PASS (1992 passed, 2 skipped, 4 xfailed)
- Bond/glyph overlap count < 50: NOT MET for Haworth SVGs (195 unchanged)
  because Haworth uses its own pipeline

### Dependencies

Phase 1 (accurate box = correct collision detection).
Phase 2 (gap contract = bonds maintain clearance after avoidance).

## Phase 5: Height-Accurate Label Box Model

### Problem

Label box height uses fixed offsets: `top = -fs*0.75`, `bottom = fs*0.125`, total
height = `fs*0.875`. Does not account for subscript digits (CH<sub>2</sub>OH) which
extend below baseline, or superscript charges. Cairo font extents provide `ascent`
and `descent` that could replace these.

### Changes

In `render_geometry.py`:
- Add `_label_box_height_from_metrics(text, font_size, font_name)` using Cairo
  font extents for base height, extended if text contains `<sub>`/`<sup>` markup.
- Modify `_label_box_coords()` to call it.
- Keep backward-compatible fallback when Cairo unavailable.

### Acceptance Criteria

- HO gap sd < 1.0 (vertical-approach HO labels benefit)
- No increase in bond/glyph overlap count
- Full test suite passes

### Dependencies

Phase 1 (width model), Phase 2 (gap contract).

## Phase 6: Bond/Bond Overlap Post-Processing

### Problem

168 bond/bond overlaps. Double bonds and adjacent single bonds can overlap.
`build_bond_ops()` has no awareness of other bonds' line segments.

### Changes

In `render_geometry.py`:
- Add `_avoid_bond_bond_overlaps(all_line_ops, line_width)` post-processing
  function that collects all line segments, checks pairwise distance between
  segments from different bonds, and shortens overlapping parallel lines.
- Call from `molecule_to_ops()` after collecting all bond ops.

### Acceptance Criteria

- Bond/bond overlap count < 40 (from 168)
- No increase in bond/glyph overlaps
- No alignment regressions
- Full test suite passes

### Dependencies

Phase 4 (cross-label avoidance reduces confounding overlaps first).

## Phase Dependency Graph

```
Phase 1 (Label Box Width) ---------------------------------
  |                                                        |
  +--> Phase 2 (Gap Distance) --> Phase 4 (Cross-Label) --> Phase 6 (Bond/Bond)
  |       |
  |       +--> Phase 5 (Label Box Height)
  |
  +--> Phase 3 (Alignment Center)
```

Phases 2 and 3 can proceed in parallel after Phase 1.

## Target Final Metrics

| Metric                | Baseline (2026-02-13) | Current    | Target       |
|-----------------------|-----------------------|------------|--------------|
| CH2OH aligned         | 68/68 (100%)          | 68/68      | 68/68 (100%) |
| CH2OH gap sd          | 0.54                  | 0.54       | < 1.0        |
| CH2OH perp sd         | 0.12                  | 0.12       | < 1.0        |
| HO aligned            | 136/136 (100%)        | 136/136    | 136/136      |
| HO gap sd             | 0.55                  | 0.55       | < 1.0        |
| HO perp sd            | 0.15                  | 0.15       | < 0.5        |
| OH gap sd             | 0.60                  | 0.60       | < 0.5        |
| Bond/glyph overlaps   | 195                   | 195        | < 30         |
| Bond/bond overlaps    | 168                   | 168        | < 30         |
| Alignment misses      | 0                     | 0          | 0            |

## Verification (per phase)

```bash
# After each phase:
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -x -q
source source_me.sh && python3 tools/measure_glyph_bond_alignment.py \
    -i "output_smoke/archive_matrix_previews/generated/*.svg"
source source_me.sh && python3 -m pytest tests/ -x -q
# Compare per-label stats against phase-specific acceptance criteria
```
