# Changelog

## 2026-02-15
- Add beta-sheet CDML test fixtures for non-Haworth bond alignment testing.
  New script [tools/render_beta_sheets.py](tools/render_beta_sheets.py) builds
  parallel and antiparallel beta-sheet molecules programmatically (4 residues x
  2 strands each, 40 atoms per molecule) and renders SVG/CDML output. Fixtures
  written to [tests/fixtures/oasa_generic/](tests/fixtures/oasa_generic/),
  SVGs to `output_smoke/oasa_generic_renders/`. Each file contains 24 label-bond
  junctions (NH, O, R labels) providing non-Haworth test coverage for the
  glyph-bond alignment measurement pipeline.
- Fix gap retreat reference mismatch: change `_retreat_to_target_gap()` in
  `resolve_label_connector_endpoint_from_text_origin` to use
  `contract.endpoint_target` (per-character glyph model) instead of
  `contract.full_target` (full label bounding box). The measurement tool
  measures from the tight glyph body outline, which sits inside the bbox by
  0.5-1.3 px, causing measured gaps to overshoot by that inset. Using the
  tighter endpoint target aligns the retreat reference with the measurement
  reference. Legality retreat still uses `full_target` to prevent text overlap.
  Expand `_point_in_target_closed` tolerance in the chain2 label solver
  ([packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py))
  by `ATTACH_GAP_TARGET` so the endpoint validity check accommodates the
  intentional gap distance. Update chain2 resolver test to use matching
  `epsilon=1e-3` and `make_attach_constraints()` factory call.
- Fix Haworth renderer gap target mismatch: pass `target_gap=ATTACH_GAP_TARGET`
  (1.5 px) explicitly at all 6 `make_attach_constraints()` call sites in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  Previously the renderer used the font-relative fallback (`12.0 * 0.058 = 0.696 px`),
  which fell outside the measurement spec's 1.3-1.7 px window.
- Add `make_attach_constraints()` factory and `ATTACH_GAP_FONT_FRACTION` constant
  to [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Three-tier gap resolution: explicit `target_gap` > font-relative > absolute default.
  Delete Haworth-only `TARGET_GAP_FRACTION` constant and replace all inline
  `AttachConstraints()` calls across Haworth, cairo_out, svg_out, bond_render_ops,
  and bond_drawing with the shared factory. Phase 5 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Wire shared gap/perp constraints through `BondRenderContext` into
  `build_bond_ops()`. Add `attach_constraints` field to `BondRenderContext` and
  `attach_gap_target`/`attach_perp_tolerance` style keys to `molecule_to_ops()`.
  Update `cairo_out.py`, `svg_out.py`, `bond_render_ops.py`, and `bond_drawing.py`
  to construct and pass `AttachConstraints` with shared constants. Phase 4 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Fix zoom viewport drift caused by orphaned canvas items leaking during
  redraw.  Non-showing atoms (carbon) in
  [packages/bkchem/bkchem/atom.py](packages/bkchem/bkchem/atom.py) called
  `get_xy_on_paper()` which created a `vertex_item`, then overwrote
  `self.vertex_item = self.item`, orphaning the first item.  These leaked
  items accumulated at stale `canvas.scale()` coordinates, inflating the
  content bounding box and causing cumulative drift (571 px after 6 zoom
  steps).  Fix computes coordinates directly via `real_to_canvas()`.
- Fix bond position drift during zoom by repositioning `vertex_item`
  coordinates to `model_coord * scale` at the top of `molecule.redraw()`
  in [packages/bkchem/bkchem/molecule.py](packages/bkchem/bkchem/molecule.py).
  Bonds redraw before atoms for z-ordering and read atom positions from
  `vertex_item`; without the reset they used stale canvas-scaled coords.
- Add `_center_viewport_on_canvas()` helper to
  [packages/bkchem/bkchem/paper.py](packages/bkchem/bkchem/paper.py) and
  call it after `update_scrollregion()` in `scale_all()` to re-center the
  viewport on the zoom origin.  Refactor `zoom_to_content()` to use the
  new helper.
- Fix interactive zoom drift: remove redundant `canvas.scale('all', ox, oy,
  factor, factor)` from `scale_all()` in
  [packages/bkchem/bkchem/paper.py](packages/bkchem/bkchem/paper.py).
  `redraw_all()` already redraws content from model coords at the new scale,
  but the background rectangle (`self.background`) is not in `self.stack` and
  was never reset by `redraw_all()`.  The `canvas.scale()` call scaled it
  around the viewport center while `redraw_all()` scales from the origin,
  causing the background and content to diverge.  Fix explicitly resets the
  background via `create_background()` + `scale(background, 0, 0, scale,
  scale)` after `redraw_all()`.
- Fix Tk canvas inset bug in `_center_viewport_on_canvas()` fraction formula
  in [packages/bkchem/bkchem/paper.py](packages/bkchem/bkchem/paper.py).
  Tk's `xview moveto` internally subtracts the canvas inset
  (`borderwidth + highlightthickness`) from the computed origin.  The
  fraction formula must include a `+inset` correction so that `canvasx()`
  lands on the target point after scrolling.  Without this fix, each zoom
  step introduced a systematic ~3 px centering error (matching the default
  inset of 3), causing cumulative viewport drift across zoom operations.
- Upgrade zoom test assertions in
  [tests/test_bkchem_gui_zoom.py](tests/test_bkchem_gui_zoom.py):
  convert idempotency and drift warnings to hard assertions (5% scale
  tolerance, 50 px bbox/viewport drift tolerance), add per-zoom-step
  snapshots with canvas item counts.
- Add `test_zoom_model_coords_stable` and `test_zoom_roundtrip_symmetry` to
  [tests/test_bkchem_gui_zoom.py](tests/test_bkchem_gui_zoom.py).
  Model-coords test verifies `atom.x`/`atom.y` are unchanged after zoom_in
  x50, zoom_out x100, and zoom reset.  Roundtrip-symmetry test zooms from
  1000% to ~250% (8 steps) and back, checking model-space viewport drift
  stays under 3.0 px.
- Add [docs/TKINTER_WINDOW_DEBUGGING.md](docs/TKINTER_WINDOW_DEBUGGING.md)
  documenting Tk Canvas zoom debugging techniques, the orphaned
  `vertex_item` root cause, and the `redraw()` ordering pitfall.

## 2026-02-14
- Replace "first child that changes endpoint" behavior in composite target branch
  of `_correct_endpoint_for_alignment()` with scoring-based candidate selection
  that minimizes perpendicular error to the desired centerline and tiebreaks by
  distance from original endpoint. Phase 3 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 3 composite target alignment tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py).
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
- Add `_resolve_endpoint_with_constraints()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  full 4-step constraint pipeline (boundary resolve, centerline correction,
  legality retreat, target-gap retreat) replacing `_clip_to_target()` at all
  6 bond-clipping call sites in `build_bond_ops()` (single, double side-path,
  double parallel-pair). Add clipping to triple bond offset lines which
  previously had none. Deprecate `_clip_to_target()`. Phase 2 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 2 tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py): none-target
  passthrough, backward compatibility with `_clip_to_target()`, alignment
  correction, gap retreat, legality retreat, and triple bond offset clipping.
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
