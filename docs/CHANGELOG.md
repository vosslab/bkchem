# Changelog

## 2026-02-14
- Add "Zoom to Content" button and View menu entry that resets zoom, computes
  bounding box of drawn content only (excluding page background), scales to fit
  with 10% margin capped at 400%, and centers the viewport on the molecules.
  New `_content_bbox()` helper and `zoom_to_content()` method in
  [packages/bkchem/bkchem/paper.py](packages/bkchem/bkchem/paper.py); button
  and menu wiring in
  [packages/bkchem/bkchem/main.py](packages/bkchem/bkchem/main.py).
- Shorten wavy bond wavelength from `ref * 1.2` to `ref * 0.5` (floor 2.0) in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  for tighter, more visible wave oscillations.
- Add gap/perp gate harness
  [tools/gap_perp_gate.py](tools/gap_perp_gate.py) that runs glyph-bond
  alignment measurement on fixture buckets (haworth, oasa_generic, bkchem)
  and emits compact JSON with per-label stats and failure reason counts.
  Phase 0 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add gate test
  [tests/test_gap_perp_gate.py](tests/test_gap_perp_gate.py) verifying gate
  report structure, reason tallies, empty-bucket handling, and haworth
  corpus file count.
- Add shared gap/perp spec constants (`ATTACH_GAP_TARGET`, `ATTACH_GAP_MIN`,
  `ATTACH_GAP_MAX`, `ATTACH_PERP_TOLERANCE`) to
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Add `alignment_tolerance` field to `AttachConstraints` (default 0.07) and
  replace hardcoded `max(line_width * 0.5, 0.25)` tolerance in
  `resolve_label_connector_endpoint_from_text_origin()` with
  `constraints.alignment_tolerance`. Phase 1 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 1 tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py) verifying
  shared constants, default/custom alignment tolerance, and no fallback to
  old hardcoded tolerance expression.

- Add wavy bond to GUI draw mode bond type submenu so users can select and
  draw wavy bonds from the toolbar (the rendering was already implemented but
  not wired into the GUI).
- Fix wavy bond rendering in GUI: scale amplitude/wavelength off `wedge_width`
  (not `line_width`) so waves are visible, use 4 sparse control points per
  wavelength with 1.5x amplitude overshoot so Tk's B-spline `smooth=1`
  produces genuinely smooth curves instead of visible straight-line segments,
  and widen stroke by 10% in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
- Fix hashed bond rendering in GUI: rewrite `_hashed_ops()` to compute each
  hash line perpendicular to the bond axis (unit-vector math) instead of
  connecting points on converging wedge edges, so all hash lines are parallel;
  linearly interpolate hash line length from `line_width` at the narrow end to
  `wedge_width` at the wide end; tighten spacing to `0.4 * wedge_width` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
- Rewrite
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md)
  into a focused execution plan for getting gap/perp into spec across shared
  OASA and BKChem rendering paths (not Haworth-only), with current baseline
  metrics, phased implementation, and hard acceptance gates.
- Update glyph-bond measurement pass/fail criteria in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) so labels are
  marked aligned only when `1.3 <= gap <= 1.7` and `perp <= 0.07`; all other
  cases are violations.
- Replace `err = perp` with a normalized combined metric in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py):
  `err = ((gap - 1.5)/0.2)^2 + (perp/0.07)^2`.
- Add explicit alignment gap/perp constants in
  [tools/measurelib/constants.py](tools/measurelib/constants.py).
- Update alignment tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to validate the new combined error formula and pass/fail rule.
- Add per-label `bond_len` reporting to
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) and include
  `bond_len=...` in diagnostic SVG annotation blocks in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py),
  alongside `gap/perp/err`.
- Propagate per-label bond lengths through JSON/report data points in
  [tools/measurelib/reporting.py](tools/measurelib/reporting.py).

## 2026-02-13
- Tighten gap and perp renderer parameters to meet gap 1.3-1.7 and perp < 0.07
  spec. Change `TARGET_GAP_FRACTION` from 0.04 to 0.058 in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  (yields target_gap=0.70 at font_size=12). Tighten renderer alignment tolerance
  from `max(line_width * 0.5, 0.25)` to 0.07 in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Add post-gap re-alignment pass after gap retreat to catch perpendicular drift.
  Result: OH gap=1.37, HO gap=1.30, CH2OH gap=1.70 (all in spec). Perp values
  unchanged (structural limitation of composite target geometry).
- Add median to `length_stats()` in
  [tools/measurelib/util.py](tools/measurelib/util.py). Per-label alignment
  summary now shows avg/stddev/median for both bond_end_gap and perp_offset.
- Tighten perpendicular alignment tolerance from ~1.0 to 0.07 in
  [tools/measurelib/constants.py](tools/measurelib/constants.py) and simplify
  formula in [tools/measurelib/analysis.py](tools/measurelib/analysis.py).
  Rename alignment columns to `bond_end_gap` and `perp_offset` for clarity.
- Switch per-label `gap_distance_stats` to use signed distance (negative when
  bond endpoint penetrates glyph body) in
  [tools/measurelib/reporting.py](tools/measurelib/reporting.py).
- Add distance annotations (gap, perp, err) to diagnostic SVGs near each bond
  endpoint in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py).
- Create standalone
  [tools/alignment_summary.py](tools/alignment_summary.py) script that reads
  existing JSON report and prints per-label alignment summary without re-running
  the full analysis.
- Replace duplicate inline console code in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  `main()` with `print_summary()` call.
- Add `_avoid_cross_label_overlaps()` to
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 4 of OASA-Wide Glyph-Bond Awareness plan). Retreats bond endpoints
  away from non-own-vertex label targets using capsule intersection tests and
  `retreat_endpoint_until_legal()`. Integrated into `build_bond_ops()` for
  single, double (asymmetric and symmetric), and triple bond paths. Includes
  minimum bond length guard (`max(half_width * 4.0, 1.0)`) to prevent bonds
  from collapsing when surrounded by labels. Note: Haworth renderer uses its
  own pipeline and is not yet affected by this change.
- Add 6 unit tests for `_avoid_cross_label_overlaps` in
  [tests/test_render_geometry.py](tests/test_render_geometry.py): cross-target
  exclusion of own vertices, near-end retreat, near-start retreat,
  no-intersection passthrough, and minimum-length guard.
- Re-baseline plan metrics in
  [OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md):
  record post-connector-fix measurements (362/362 alignment, 0 misses), update
  acceptance criteria to current baseline, relabel Phases 1-3 from DONE to
  IMPLEMENTED, add per-atom optical centering feasibility note.
- Update [refactor_progress.md](refactor_progress.md) with re-baselined gate
  status and connector selection fix diagnosis.
- Include hashed bond carrier lines as connector candidates in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py). Carrier lines
  for hatched (behind-the-plane) bonds are intentionally drawn thin with
  perpendicular hatch strokes; the width filter was excluding them, causing
  labels like CH2OH to match distant unrelated bonds instead of the actual
  hatched bond.
- Add unit tests for `_retreat_to_target_gap`, `_correct_endpoint_for_alignment`,
  and `_perpendicular_distance_to_line` in new
  [tests/test_render_geometry.py](tests/test_render_geometry.py).
- Move
  [OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md)
  to `docs/active_plans/` and add NOT STARTED labels to Changes 6, 7, 8.
- Add consumer adoption note to OASA-Wide Glyph-Bond Awareness plan clarifying
  that `target_gap` and `alignment_center` are consumed by Haworth first; other
  consumers adopt when their rendering paths are ready.
- Extract `TARGET_GAP_FRACTION` constant in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  replacing 4 occurrences of `font_size * 0.04`.
- Run full acceptance metrics and record gate results in
  `output_smoke/acceptance_gate_results_2026-02-13.txt`.
- Port `letter-center-finder` algorithms directly into
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  as `_lcf_*` prefixed functions (SVG parsing, glyph isolation rendering,
  contour extraction, convex hull, ellipse fitting), removing the external
  sibling-repo dependency on `/Users/vosslab/nsh/letter-center-finder/`.
- Extend optical glyph centering to all alphanumeric characters, not just O/C.
  Change `_lcf_extract_chars_from_string` guard from `char in ('O', 'C')` to
  `char.isalnum()`.
- Delete fallback centering functions `_alignment_primitive_center`,
  `_first_carbon_primitive_center`, and `_first_primitive_center_for_char` from
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py).
  Optical centering failures now propagate visibly instead of silently falling
  back to inaccurate heuristics.
- Remove `--alignment-center-mode` CLI argument and hardcode optical mode in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py).
- Add `numpy`, `opencv-python`, and `scipy` to
  [pip_extras.txt](pip_extras.txt) as optional dependencies for glyph optical
  center fitting.
- Use Cairo font-metric label box width in `_label_box_coords()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 1 of OASA-Wide Glyph-Bond Awareness plan). Replace hardcoded
  `font_size * 0.75 * char_count` with `sum(_text_char_advances(...))`,
  making the full label box consistent with the sub-label attach box that
  already used Cairo metrics.
- Add `target_gap` and `alignment_center` fields to `AttachConstraints` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 2 and Phase 3 of OASA-Wide Glyph-Bond Awareness plan). Phase 2 adds
  `_retreat_to_target_gap()` for uniform whitespace between connector endpoint
  and glyph body. Phase 3 adds `_correct_endpoint_for_alignment()` to re-aim
  endpoints through the attach atom optical center, reducing bond/glyph overlaps
  from 219 to 211.
