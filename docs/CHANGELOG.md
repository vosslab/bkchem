# Changelog

## 2026-02-15
- Fix regression expectations in
  [tests/test_attach_targets.py](tests/test_attach_targets.py) for
  `label_target()` box geometry after calibrated text top/bottom offsets in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Update legacy-value fixtures for `O`, `OH`, and `NH3+` to current
  deterministic coordinates.
- Speed up
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  by memoizing the expensive render-and-measure result so the suite computes
  it once per test session instead of once per test function.
- Draw perpendicular cross-lines at all bond endpoints in diagnostic SVG
  overlay.  New `_draw_bond_perpendicular_markers()` helper in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py)
  draws short perpendicular lines at both ends of every checked bond line:
  magenta `#ff00ff` for endpoints used for gap measurement, dark blue
  `#00008b` for other endpoints.  Include Haworth base ring bonds in the
  perpendicular marker set so ring bond endpoints are also marked.  Markers
  are drawn as a background layer before per-label overlays.  Remove
  per-metric orange perpendicular line (now redundant).  Change hull contact
  point marker from circle to ellipse (rx=1.5, ry=0.8).  Legend updated with
  perpendicular line swatches for "Connector endpoint" and "Other endpoint".
  Tests in
  [tests/test_measurelib_diagnostic_svg.py](tests/test_measurelib_diagnostic_svg.py)
  cover perpendicular marker presence, backward compatibility, and hull
  contact ellipse.
- Render charge marks as circled symbols in OASA SVG output instead of
  appending +/- as inline text.  Store mark data in vertex `properties_` in
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py), suppress charge
  text suffix in `vertex_label_text()` when marks are present, and generate
  `CircleOp`/`LineOp` for circled plus (blue) and minus (red) marks in
  `build_vertex_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Update bond count expectations in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to account for the 6 new mark lines.
- Fix furanose beta MR OH / ML CH2OH text collision in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  When MR carries a simple hydroxyl and ML carries a chain-like tail
  (e.g. ALRRDM furanose beta), skip the oxygen clearance override entirely so
  the MR OH bond stays at the default 13.5 length instead of being pushed up
  to 18.49 where it collides with the CH2OH text.  Remove unused constant
  `FURANOSE_TOP_RIGHT_HYDROXYL_EXTRA_CLEARANCE_FACTOR` from
  [packages/oasa/oasa/haworth/renderer_config.py](packages/oasa/oasa/haworth/renderer_config.py).
- Rebalance furanose "up" two-carbon tail branch length factors in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  `ho_length_factor` changed from 0.72 to 0.90, `ch2_length_factor` from 1.08
  to 0.95 in `_furanose_two_carbon_tail_profile()`.  This reduces the HO vs
  CH2OH branch length ratio from ~2.5:1 to ~1.3:1.
- Use round linecaps for all Haworth bond lines in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  The hashed-bond carrier line in `_add_branch_connector_ops()` was the only
  remaining `cap="butt"` bond line; changed to `cap="round"` for visual
  consistency with all other bond connectors.  Hatch cross-strokes retain butt
  caps since they are decorative marks, not bond lines.  Add `CircleOp` rounding
  caps at back ring vertices (ML, TL, MR for pyranose) so the thin polygon ring
  edges also appear rounded where they meet instead of showing square corners.
  Make the hashed-bond carrier line fully transparent (`color="none"`) so only
  the hatch cross-strokes are visible.  Add `HASHED_BOND_WEDGE_RATIO` constant
  (4.6, up from hardcoded 2.8) to
  [packages/oasa/oasa/haworth/renderer_config.py](packages/oasa/oasa/haworth/renderer_config.py)
  to widen the hatch bond fan angle.
- Empirically calibrate glyph bounding-box vertical offset in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  `_label_box_coords()` `bottom_offset` changed from `0.035` to `0.008` based
  on rsvg/Pango pixel measurements (actual descent is 0.1 SVG units at 12pt,
  ratio 0.008).  Previous value overestimated descent, inflating glyph boxes
  and causing Haworth ring-edge overlap failures.  Add
  `_text_ink_bearing_correction()` helper that computes the left and right
  bearing gap between Cairo advance width and actual ink extent.
- Increase oxygen exclusion safety margin in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  `_oxygen_exclusion_radius()` safety factor raised from `0.05` to `0.09` to
  compensate for the tighter glyph box: ring edges now maintain visual
  clearance from the oxygen label despite the smaller bounding box.
- Improve glyph calibration tool
  [tools/calibrate_glyph_model.py](tools/calibrate_glyph_model.py).
  `_generate_subscript_svg()` now generates proper SVG `<tspan>` subscript
  structure matching the renderer's output (font-size scaling, dy offsets)
  instead of rendering plain text.  Fix pyflakes lint: remove unused imports
  (`math`, `pathlib`, `glyph_char_advance`, `glyph_text_width`), unused
  variable (`sub_dy`), and unnecessary f-string prefixes.
- Alignment measurement improvement: Haworth OH/HO alignment increased from
  ~52% to 100% (HO) and 94.7% (OH).  Overall alignment (excluding ring
  oxygens) improved from ~33.9% to 81.3%.  Bond-end gap values now land in
  the [1.3, 1.7] target range (avg 1.52) for both alpha and beta anomers.

- Add Cairo PDF parity measurement tool for comparing PDF and SVG renderer
  output.  New `tools/measure_cairo_pdf_parity.py` CLI supports two modes:
  parity mode (SVG+PDF pair comparison) and PDF-only mode (standalone PDF
  analysis).  New modules:
  [tools/measurelib/pdf_parse.py](tools/measurelib/pdf_parse.py) extracts
  lines, labels, ring primitives, and wedge bonds from Cairo-generated PDF
  files via `pdfplumber` with Y-coordinate flipping to SVG space;
  [tools/measurelib/parity.py](tools/measurelib/parity.py) performs
  nearest-neighbor matching of SVG and PDF primitives with configurable
  tolerance and computes a parity score;
  [tools/measurelib/pdf_analysis.py](tools/measurelib/pdf_analysis.py)
  runs the full structural analysis pipeline (Haworth detection, hatch
  detection, violations) on PDF-extracted primitives.  Tests in
  [tests/test_cairo_pdf_parity.py](tests/test_cairo_pdf_parity.py) cover
  PDF extraction, parity matching, file pairing, and standalone PDF
  analysis (19 tests).  Existing SVG measurement tool is unchanged.
- Fix antiparallel reverse-strand terminal text orientation in
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py) so C->N chains
  read as `-OOC ... NH3+` (instead of `COO- ... H3N+`).  Add direction-aware
  terminal label text/position handling (`COO`/`H3N` for forward strands,
  `OOC`/`NH3` for reverse strands) and charge-mark side placement.  Add
  regression coverage in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to assert reverse-strand terminal labels and charge mark positions.
- Add double bond pair detection and exclusion to glyph-bond alignment
  measurement tool.  New `detect_double_bond_pairs()` in
  [tools/measurelib/hatch_detect.py](tools/measurelib/hatch_detect.py) finds
  parallel line pairs (C=O double bonds) and excludes the secondary offset line
  from measurement.  Uses linecap attribute to classify primary (round-cap) vs
  secondary (butt-cap) lines.  Add `DOUBLE_BOND_*` constants to
  [tools/measurelib/constants.py](tools/measurelib/constants.py).  Report now
  includes `decorative_double_bond_offset_count` and `double_bond_pairs`.
- Add multi-bond label support to glyph-bond alignment measurement tool.
  New `all_endpoints_near_glyph_primitives()` and
  `all_endpoints_near_text_path()` in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) return all
  bond endpoints within search distance, grouped by approach side (left/right).
  Per-label measurement loop in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) now builds a
  `connectors` list with independent alignment metrics for each side.  A label
  is aligned only if all its connectors pass.  Backward-compatible top-level
  fields are preserved from the primary (nearest) connector.
- Update re-exports in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  for new double bond and multi-connector public names.
- Add tests for double bond detection and multi-connector labels in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py).
  Update expected bond counts in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to reflect double bond exclusion (42 detected, 6 excluded, 36 checked).
- Fix double-bond perpendicular distance measurement in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py).  Perpendicular
  distance was measured from the glyph optical center to the primary drawn line,
  but for C=O double bonds the two parallel lines are offset ~6 SVG units from
  the true bond axis.  The O glyph center sits on the bond axis (between the
  two lines), giving a spurious perp offset of ~3.  Fix: compute a midline by
  averaging primary and secondary line coordinates, then measure perpendicular
  distance to the midline.  O label perp values drop from 3.03 to 0.03.
  Update infinite-line overlay in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py)
  to draw the midline for double-bond primaries.
- Add gap-ratio filter to multi-connector label detection in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py).  Distant bonds
  from the far side of a label were incorrectly included as secondary connectors
  (e.g. O labels getting a spurious connector with gap=27 alongside the real
  C=O connector with gap=8).  Discard connectors whose gap exceeds
  `MULTI_CONNECTOR_GAP_RATIO_MAX` (3.0) times the minimum gap among all sides.
  Add constant to
  [tools/measurelib/constants.py](tools/measurelib/constants.py).

- Fix double-bond centering inconsistency in OASA generic renderer.
  `molecule_to_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  was passing `point_for_atom=None`, so `_double_bond_side()` compared
  transformed bond coordinates against raw (untransformed) atom positions.
  Neighbor atoms appeared on the wrong side, producing offset double bonds
  where centered was correct.  Fix: pass a `point_for_atom` callback that
  applies the same `transform_xy` used for bond coordinates.
- Add `center` attribute to OASA bond class in
  [packages/oasa/oasa/bond.py](packages/oasa/oasa/bond.py).  Parse
  `center="yes"` from CDML in
  [packages/oasa/oasa/cdml_bond_io.py](packages/oasa/oasa/cdml_bond_io.py).
  Honor the attribute in `build_bond_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  when `edge.center` is set, skip geometric side detection and force centered
  double-bond rendering.

- Add N, O, R, and H-only atoms to the glyph-bond measurement tool.
  `is_measurement_label()` in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) now uses
  first/last letter logic instead of substring search; measurable atoms are
  {C, O, S, N, R} plus H-only labels.  Add R to `GLYPH_STEM_CHAR_SET` in
  [tools/measurelib/constants.py](tools/measurelib/constants.py).  Replace
  element-priority alignment center selection in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) with first/last
  letter logic that picks the connecting character based on which side of the
  label the bond approaches.  Add bounding-box fallback in
  [tools/measurelib/lcf_optical.py](tools/measurelib/lcf_optical.py) to use
  character shape type for optical fitting: curved glyphs (C, O, S) get
  ellipse fitting, stem glyphs (N, H, R) get bounding-box center.  Update
  tests in
  [tests/test_measurelib_glyph_model.py](tests/test_measurelib_glyph_model.py)
  and
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  for new measurement label set and first/last letter alignment.

- Add CPK default colors for charge marks in
  [packages/bkchem/bkchem/marks.py](packages/bkchem/bkchem/marks.py): `plus`
  marks default to blue (`#0000FF`) and `minus` marks default to red
  (`#FF0000`) instead of inheriting the atom's line color.  Override the
  `line_color` property in each subclass with a CPK fallback; explicit color
  set via `set_color()` or `_line_color` still takes precedence.
- Add zoom scaling for all mark subclasses in
  [packages/bkchem/bkchem/marks.py](packages/bkchem/bkchem/marks.py).  Add
  `_scaled_size()` helper to the base `mark` class that multiplies `self.size`
  by `self.paper._scale`.  Update `draw()` in `radical`, `biradical`,
  `electronpair`, `plus`, `minus`, and `text_mark` to use `_scaled_size()`
  for canvas pixel dimensions so marks grow/shrink proportionally with zoom.
  The inset constant in `plus`/`minus` cross/dash lines also scales.  SVG
  export and CDML serialization remain unscaled (model coordinates).  Skip
  `pz_orbital` (mixes model coords with size differently).
- Fix bond drawing after zoom for shown atoms (N, O, R, H3N, COOH).  Bonds
  connected to labeled atoms drew as long diagonal lines after zoom because
  `molecule.redraw()` redraws bonds before atoms, and bonds call `atom.bbox()`
  which read stale pre-zoom canvas positions.  Fix by redrawing atoms first so
  their canvas items are at correct positions, then redrawing bonds, then
  lifting atoms above bonds to restore z-ordering.
- Fix double bond convergence toward labeled atoms (take 2). Secondary
  parallel lines of double/triple bonds were independently resolved against
  label targets, but each offset line approaches the label at a different
  angle, so Steps 1-3 of the constraint pipeline broke parallelism. Remove all
  `_resolve_endpoint_with_constraints` calls from secondary bond lines in
  `build_bond_ops()`. Secondary lines inherit correct clearance from the main
  bond's already-resolved endpoints via `find_parallel()`. Remove the
  now-unused `no_gap_constraints` variable. Cross-label overlap avoidance
  (`_avoid_cross_label_overlaps`) is retained for all lines.
- Rewrite [tools/render_beta_sheets.py](tools/render_beta_sheets.py) to produce
  bkchem-quality beta-sheet CDML and SVG fixtures.  Write CDML directly via
  `xml.dom.minidom` (not `oasa.cdml_writer`) to emit proper bkchem element
  types: `<atom>` for backbone C/N/O, `<query>` for R groups, and
  `<text><ftext>` with `<sub>` markup for terminals.  N-terminus H3N uses
  `<mark type="plus" draw_circle="yes"/>` (bkchem circled charge mark);
  C-terminus COO uses `<mark type="minus" draw_circle="yes"/>` (carboxylate).
  C=O bonds use `type="n2" center="yes" bond_width="6.0"`.  Geometry matches
  the hand-drawn reference template (0.700 cm bond length, 30-degree zigzag).
  Four residues per strand, 19 atoms and 18 bonds each, 38 atoms total per
  file (no cross-strand H-bonds).  SVG rendered via `render_out.render_to_svg()`
  with `show_hydrogens_on_hetero=False`; oasa charge display appends +/- via
  `vertex_label_text`.  Fixtures at
  [tests/fixtures/oasa_generic/](tests/fixtures/oasa_generic/), SVGs at
  `output_smoke/oasa_generic_renders/`.
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
