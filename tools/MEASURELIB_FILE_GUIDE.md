# measurelib/ Module Guide

The `tools/measurelib/` package provides the glyph-bond alignment measurement
engine, split from the former monolithic `measure_glyph_bond_alignment.py`.

## Module Dependency Flow

```
constants.py  <-- (everyone)
util.py       <-- (everyone except constants)
geometry.py   <-- violations, hatch_detect, haworth_ring, diagnostic_svg, analysis
svg_parse.py  <-- analysis
glyph_model.py <-- lcf_optical, analysis, violations, svg_parse
lcf_optical.py <-- analysis
haworth_ring.py <-- analysis
hatch_detect.py <-- analysis, violations
violations.py  <-- analysis
diagnostic_svg.py <-- analysis
analysis.py   <-- reporting, CLI
reporting.py  <-- CLI
```

No circular dependencies exist between modules.

## Module Descriptions

### constants.py (~37 lines)
All numeric thresholds, tolerance values, and default file paths used across the
measurement pipeline. Every other module imports from here.

Key names: `CANONICAL_LATTICE_ANGLES`, `BOND_GLYPH_GAP_TOLERANCE`,
`LATTICE_ANGLE_TOLERANCE_DEGREES`, `SVG_FLOAT_PATTERN`, `DEFAULT_INPUT_GLOB`.

### util.py (~400 lines)
Shared low-level helpers that have no domain-specific geometry logic.

- Line primitives: `_line_length`, `_line_midpoint`, `_line_endpoints`
- Box/point math: `_normalize_box`, `_point_to_box_signed_distance`,
  `_point_to_ellipse_signed_distance`
- Glyph target distance: `_point_to_glyph_primitive_signed_distance`,
  `_point_to_glyph_primitives_distance`, `_point_in_target_closed`
- Statistics: `_length_stats`, `_alignment_score`
- Display formatting: `_compact_float`, `_display_float`, `_display_point`,
  `_safe_token`, `_compact_sorted_values`, `_rounded_value_counts`
- Counters: `_increment_counter`, `_group_length_append`

### geometry.py (~380 lines)
Pure geometric primitives for segments, boxes, and angles.

- Angles: `_line_angle_degrees`, `_nearest_lattice_angle_error`,
  `_nearest_canonical_lattice_angle`
- Segment intersection: `_segments_intersect`, `_orientation`, `_on_segment`
- Segment-box: `_line_intersects_box_interior`, `_segment_distance_to_box_sq`
- Box overlap: `_boxes_overlap_interior`
- Line relationships: `_lines_share_endpoint`, `_lines_nearly_parallel`,
  `_line_collinear_overlap_length`, `_line_overlap_midpoint`,
  `_line_intersection_point`
- Convex hull: `_convex_hull`
- Point-to-line: `_point_to_infinite_line_distance`,
  `_point_to_segment_distance_sq`

### svg_parse.py (~236 lines)
SVG element collection from parsed XML trees.

- Tag helpers: `_local_tag_name`, `_parse_float`, `_visible_text`
- Coordinate parsing: `_svg_number_tokens`, `_polygon_points`, `_path_points`,
  `_points_bbox`
- Element collectors:
  - `_collect_svg_lines` -- `<line>` elements as bond primitives
  - `_collect_svg_labels` -- `<text>` elements as glyph labels
  - `_collect_svg_ring_primitives` -- filled `<polygon>`/`<path>` for ring detect
  - `_collect_svg_wedge_bonds` -- filled `<polygon>` wedge/stereo bonds (NEW)
- File resolution: `_resolve_svg_paths`
- Namespace: `_svg_tag_with_namespace`, `_node_is_overlay_group`

### glyph_model.py (~500 lines)
Glyph shape model: how text labels map to geometric primitives.

- Label classification: `_is_measurement_label`, `_canonicalize_label_text`
- Font/text path: `_label_text_path`, `_font_family_candidates`,
  `_label_geometry_text`, `_path_line_segments`
- Signed distance to glyph: `_point_to_text_path_signed_distance`,
  `_point_to_label_signed_distance`
- Nearest endpoint: `_nearest_endpoint_to_text_path`,
  `_nearest_endpoint_to_box`, `_nearest_endpoint_to_glyph_primitives`,
  `_line_closest_endpoint_to_box`, `_line_closest_endpoint_to_target`
- Glyph primitives: `_glyph_char_advance`, `_glyph_char_vertical_bounds`,
  `_glyph_text_width`, `_glyph_primitive_from_char`,
  `_label_svg_estimated_primitives`, `_glyph_primitives_bounds`,
  `_primitive_center`, `_label_svg_estimated_box`

### lcf_optical.py (~570 lines)
Letter Center Finder via optical isolation rendering. Uses rsvg-convert + OpenCV
to render individual glyphs and compute their optical centers and convex hull
boundaries.

- Entry point: `_optical_center_via_isolation_render`
- Internal: all `_lcf_*` helper functions, `_LCF_CHAR_CACHE`
- Dependencies: cv2, numpy, scipy.spatial (optional graceful fallback)

### haworth_ring.py (~239 lines)
Haworth sugar ring detection from line cycles and filled primitive clusters.

- Graph building: `_clustered_endpoint_graph`
- Cycle finding: `_find_candidate_cycles`, `_canonical_cycle_key`,
  `_cycle_node_pairs`
- Detection: `_detect_haworth_ring_from_line_cycles`,
  `_detect_haworth_ring_from_primitives`, `_detect_haworth_base_ring`
- Default: `_empty_haworth_ring_detection`

### hatch_detect.py (~141 lines)
Hatched bond (dashed behind-plane stereo) detection from line primitives.

- Stroke classification: `_is_hatch_stroke_candidate`,
  `_is_hashed_carrier_candidate`
- Carrier detection: `_detect_hashed_carrier_map`
- Location labeling: `_overlap_origin`, `_default_overlap_origin`,
  `_quadrant_label`, `_ring_region_label`

### violations.py (~359 lines)
Overlap and violation counting for all geometry check categories.

- `_count_lattice_angle_violations` -- bonds outside canonical angles
- `_count_glyph_glyph_overlaps` -- text box intersections
- `_count_bond_bond_overlaps` -- bond line crossings
- `_count_hatched_thin_conflicts` -- hashed carrier vs non-hatch line conflicts
- `_count_bond_glyph_overlaps` -- bond lines (and wedge bonds) penetrating
  label boxes

### diagnostic_svg.py (~400 lines)
Diagnostic SVG overlay writer. Generates annotated copies of input SVGs with
colored markers for alignment centers, endpoints, label boxes, and violations.

- Bounds: `_viewbox_bounds`, `_diagnostic_bounds`
- Drawing helpers: `_clip_infinite_line_to_bounds`, `_diagnostic_color`
- Metric extraction: `_metric_alignment_center`, `_metric_endpoint`,
  `_select_alignment_primitive`
- Writer: `_write_diagnostic_svg`

### analysis.py (~500 lines)
Core per-file analysis. Orchestrates SVG parsing, glyph model building, Haworth
ring exclusion, connector matching, alignment measurement, and violation counting.

- Entry point: `analyze_svg_file(svg_path, ...)`
- Calls into every other module to produce a comprehensive per-file report dict

### reporting.py (~900 lines)
Multi-file summary statistics and human-readable report generation.

- `_summary_stats` -- aggregate metrics across file reports
- `_top_misses` -- worst alignment misses
- `_format_stats_line` -- compact stats formatting
- `_violation_summary` -- compact violation dict for JSON
- `_json_summary_compact` -- filter large arrays from summary
- `_text_report` -- full human-readable text report

### __init__.py
Re-exports all public names from submodules. Defines `__all__` so that
`from measurelib import *` works correctly for backward compatibility.

## CLI Entry Point

`tools/measure_glyph_bond_alignment.py` is the slim CLI wrapper (~260 lines).
It re-imports all names from measurelib submodules for backward compatibility
with test code that loads the module via `importlib.util.spec_from_file_location`.

## Enhancements Over Original

1. **Wedge bond detection**: `_collect_svg_wedge_bonds()` in `svg_parse.py`
   detects filled `<polygon>` elements as stereo wedge bonds. These are checked
   for label box overlap in `_count_bond_glyph_overlaps()`.

2. **Diagnostic SVG path printing**: When analyzing a single file with
   `--write-diagnostic-svg`, the diagnostic SVG path is printed as a
   `file://` URL for easy terminal click-to-open.
