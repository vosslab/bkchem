"""Core SVG file analysis for glyph-bond alignment measurement."""

# Standard Library
import pathlib

import defusedxml.ElementTree as ET

from measurelib.constants import (
	ALIGNMENT_INFINITE_LINE_FONT_TOLERANCE_FACTOR,
	BOND_GLYPH_GAP_TOLERANCE,
	CANONICAL_LATTICE_ANGLES,
	LATTICE_ANGLE_TOLERANCE_DEGREES,
	MAX_ENDPOINT_TO_LABEL_DISTANCE_FACTOR,
	MIN_ALIGNMENT_DISTANCE_TOLERANCE,
	MIN_CONNECTOR_LINE_WIDTH,
)
from measurelib.util import (
	group_length_append,
	length_stats,
	line_length,
	line_midpoint,
	rounded_sorted_values,
	rounded_value_counts,
)
from measurelib.geometry import point_to_infinite_line_distance
from measurelib.svg_parse import (
	collect_svg_labels,
	collect_svg_lines,
	collect_svg_ring_primitives,
	collect_svg_wedge_bonds,
)
from measurelib.glyph_model import (
	label_svg_estimated_box,
	label_svg_estimated_primitives,
	label_text_path,
	nearest_endpoint_to_glyph_primitives,
	nearest_endpoint_to_text_path,
	point_to_label_signed_distance,
	primitive_center,
)
from measurelib.lcf_optical import optical_center_via_isolation_render
from measurelib.haworth_ring import detect_haworth_base_ring
from measurelib.hatch_detect import (
	detect_hashed_carrier_map,
	overlap_origin,
	quadrant_label,
	ring_region_label,
)
from measurelib.violations import (
	count_bond_bond_overlaps,
	count_bond_glyph_overlaps,
	count_glyph_glyph_overlaps,
	count_hatched_thin_conflicts,
	count_lattice_angle_violations,
)
from measurelib.diagnostic_svg import write_diagnostic_svg as do_write_diagnostic_svg


#============================================
def analyze_svg_file(
		svg_path: pathlib.Path,
		render_geometry=None,
		exclude_haworth_base_ring: bool = True,
		bond_glyph_gap_tolerance: float = BOND_GLYPH_GAP_TOLERANCE,
		write_diagnostic_svg: bool = False,
		diagnostic_svg_dir: pathlib.Path | None = None) -> dict:
	"""Analyze one SVG file and return independent geometry and alignment metrics."""
	root = ET.parse(svg_path).getroot()
	lines = collect_svg_lines(root)
	labels = collect_svg_labels(root)
	ring_primitives = collect_svg_ring_primitives(root)
	wedge_bonds = collect_svg_wedge_bonds(root)
	for label in labels:
		label["svg_text_path"] = label_text_path(label)
		label["svg_estimated_primitives"] = label_svg_estimated_primitives(label)
		label["svg_estimated_box"] = label_svg_estimated_box(label)
		label["_source_svg_path"] = str(svg_path)
	measurement_label_indexes = [
		index for index, label in enumerate(labels) if label["is_measurement_label"]
	]
	haworth_base_ring = detect_haworth_base_ring(lines, labels, ring_primitives)
	excluded_line_indexes = set()
	if exclude_haworth_base_ring and haworth_base_ring["detected"]:
		excluded_line_indexes = set(haworth_base_ring["line_indexes"])
	checked_line_indexes = [
		index for index in range(len(lines)) if index not in excluded_line_indexes
	]
	pre_hashed_carrier_map = detect_hashed_carrier_map(lines, checked_line_indexes)
	pre_decorative_hatched_stroke_index_set = {
		stroke_index
		for stroke_indexes in pre_hashed_carrier_map.values()
		for stroke_index in stroke_indexes
	}
	pre_hashed_carrier_index_set = set(pre_hashed_carrier_map.keys())
	width_pool = [
		float(lines[index].get("width", 1.0))
		for index in checked_line_indexes
		if index not in pre_decorative_hatched_stroke_index_set
		and index not in pre_hashed_carrier_index_set
	]
	if width_pool:
		width_pool_sorted = sorted(width_pool)
		width_median = float(width_pool_sorted[len(width_pool_sorted) // 2])
	else:
		width_median = float(MIN_CONNECTOR_LINE_WIDTH)
	min_connector_width = max(0.55 * width_median, 0.4)
	connector_candidate_line_indexes = [
		index
		for index in checked_line_indexes
		if index not in pre_decorative_hatched_stroke_index_set
		and float(lines[index].get("width", 1.0)) >= min_connector_width
	]
	if not connector_candidate_line_indexes:
		fallback_pool = [
			index
			for index in checked_line_indexes
			if index not in pre_decorative_hatched_stroke_index_set
		]
		if not fallback_pool:
			fallback_pool = list(checked_line_indexes)
		if fallback_pool:
			k_value = min(6, len(fallback_pool))
			connector_candidate_line_indexes = sorted(
				fallback_pool,
				key=lambda idx: float(lines[idx].get("width", 1.0)),
				reverse=True,
			)[:k_value]
		else:
			connector_candidate_line_indexes = []
	# Hashed carrier lines are real bonds drawn thin with hatch strokes;
	# include them as connector candidates regardless of width.
	for carrier_index in sorted(pre_hashed_carrier_index_set):
		if carrier_index not in connector_candidate_line_indexes:
			connector_candidate_line_indexes.append(carrier_index)
	connector_candidate_line_indexes.sort()
	checked_label_indexes = list(range(len(labels)))
	line_lengths_all = [line_length(line) for line in lines]
	line_lengths_checked_raw = [
		line_lengths_all[index]
		for index in checked_line_indexes
		if 0 <= index < len(line_lengths_all)
	]
	label_metrics = []
	aligned_count = 0
	missed_count = 0
	no_connector_count = 0
	connector_line_indexes = set()
	for label_index in measurement_label_indexes:
		label = labels[label_index]
		independent_primitives = label.get("svg_estimated_primitives", [])
		# Determine alignment character by element priority
		canonical_text = str(label.get("canonical_text", label.get("text", "")))
		alignment_center_char = None
		for char in ("C", "O", "N", "S", "P", "H"):
			if char in canonical_text.upper():
				alignment_center_char = char
				break
		if alignment_center_char is None and independent_primitives:
			first = min(independent_primitives, key=lambda p: int(p.get("char_index", 10**9)))
			alignment_center_char = str(first.get("char", "")) or None
		# Get initial position estimate from primitive (for SVG character matching)
		alignment_center = None
		if alignment_center_char:
			for p in sorted(independent_primitives, key=lambda p: int(p.get("char_index", 10**9))):
				if str(p.get("char", "")).upper() == alignment_center_char.upper():
					alignment_center = primitive_center(p)
					if alignment_center is not None:
						break
		independent_text_path = label.get("svg_text_path")
		independent_model_name = "svg_text_path_outline"
		if independent_text_path is not None:
			(
				independent_endpoint,
				independent_distance,
				independent_line_index,
				independent_signed_distance,
			) = nearest_endpoint_to_text_path(
				lines=lines,
				line_indexes=connector_candidate_line_indexes,
				path_obj=independent_text_path,
			)
		else:
			(
				independent_endpoint,
				independent_distance,
				independent_line_index,
				independent_signed_distance,
			) = nearest_endpoint_to_glyph_primitives(
				lines=lines,
				line_indexes=connector_candidate_line_indexes,
				primitives=independent_primitives,
			)
			independent_model_name = "svg_primitives_ellipse_box"
		optical_gate_debug = {}
		alignment_center, alignment_center_char = optical_center_via_isolation_render(
			label=label,
			center=alignment_center,
			center_char=alignment_center_char,
			svg_path=str(svg_path),
			gate_debug=optical_gate_debug,
		)
		if independent_endpoint is not None and independent_signed_distance is None:
			independent_signed_distance = point_to_label_signed_distance(independent_endpoint, label)
		search_limit = max(6.0, float(label["font_size"]) * MAX_ENDPOINT_TO_LABEL_DISTANCE_FACTOR)
		best_endpoint = independent_endpoint
		best_distance = independent_distance
		best_line_index = independent_line_index
		best_line_width = 1.0
		if best_line_index is not None and 0 <= best_line_index < len(lines):
			best_line_width = float(lines[best_line_index].get("width", 1.0))
		if best_endpoint is None or best_distance is None or best_distance > search_limit:
			no_connector_count += 1
			hull_boundary_points = None
			hull_ellipse_fit = None
			hull_contact_point = None
			hull_signed_gap = None
			if optical_gate_debug:
				hull_boundary_points = optical_gate_debug.get("hull_boundary_points")
				hull_ellipse_fit = optical_gate_debug.get("ellipse_fit")
				hull_contact_point = optical_gate_debug.get("hull_contact_point")
				hull_signed_gap = optical_gate_debug.get("hull_signed_gap_along_bond")
			independent_gap_distance = None
			independent_penetration_depth = None
			if independent_signed_distance is not None:
				independent_gap_distance = max(0.0, float(independent_signed_distance))
				independent_penetration_depth = max(0.0, -float(independent_signed_distance))
			label_metrics.append(
				{
					"label_index": label_index,
					"text": label["text"],
					"text_raw": label.get("text_raw", label["text"]),
					"anchor": label["anchor"],
					"font_size": label["font_size"],
						"endpoint": None,
					"endpoint_distance_to_label": None,
					"endpoint_distance_to_target": None,
					"endpoint_alignment_error": None,
					"endpoint_distance_to_glyph_body": independent_distance,
					"endpoint_signed_distance_to_glyph_body": independent_signed_distance,
					"endpoint_distance_to_c_center": None,
					"c_center_point": None,
					"endpoint_perpendicular_distance_to_alignment_center": None,
					"alignment_center_point": (
						[alignment_center[0], alignment_center[1]]
						if alignment_center is not None else None
					),
						"alignment_center_char": alignment_center_char,
						"optical_gate_debug": optical_gate_debug if optical_gate_debug else None,
						"hull_boundary_points": hull_boundary_points,
						"hull_ellipse_fit": hull_ellipse_fit,
						"hull_contact_point": hull_contact_point,
						"hull_signed_gap_along_bond": hull_signed_gap,
						"endpoint_gap_distance_to_glyph_body": independent_gap_distance,
					"endpoint_penetration_depth_to_glyph_body": independent_penetration_depth,
					"endpoint_distance_to_glyph_body_independent": independent_distance,
					"endpoint_signed_distance_to_glyph_body_independent": independent_signed_distance,
						"independent_connector_line_index": independent_line_index,
						"independent_endpoint": (
							[independent_endpoint[0], independent_endpoint[1]]
							if independent_endpoint is not None else None
						),
						"independent_glyph_model": independent_model_name,
					"aligned": False,
					"reason": "no_nearby_connector",
					"connector_line_index": None,
					"attach_policy": None,
					"endpoint_target_kind": None,
					"alignment_mode": "independent_glyph_primitives",
				}
			)
			continue
		if best_line_index is not None:
			connector_line_indexes.add(best_line_index)
		alignment_tolerance = max(
			MIN_ALIGNMENT_DISTANCE_TOLERANCE,
			best_line_width * 0.55,
			float(label["font_size"]) * ALIGNMENT_INFINITE_LINE_FONT_TOLERANCE_FACTOR,
		)
		alignment_error = None
		if best_line_index is not None and 0 <= best_line_index < len(lines) and alignment_center is not None:
			line = lines[best_line_index]
			alignment_error = point_to_infinite_line_distance(
				point=alignment_center,
				line_start=(line["x1"], line["y1"]),
				line_end=(line["x2"], line["y2"]),
			)
		else:
			alignment_error = float(best_distance)
		is_aligned = alignment_error <= alignment_tolerance
		if not is_aligned:
			alignment_reason = "bond_line_not_pointing_to_primitive_center"
		else:
			alignment_reason = "ok"
		independent_gap_distance = None
		independent_penetration_depth = None
		hull_boundary_points = None
		hull_ellipse_fit = None
		hull_contact_point = None
		hull_signed_gap = None
		reported_signed_distance_to_glyph_body = independent_signed_distance
		reported_distance_to_glyph_body = independent_distance
		if optical_gate_debug:
			hull_boundary_points = optical_gate_debug.get("hull_boundary_points")
			hull_ellipse_fit = optical_gate_debug.get("ellipse_fit")
			hull_contact_point = optical_gate_debug.get("hull_contact_point")
			hull_signed_gap = optical_gate_debug.get("hull_signed_gap_along_bond")
		if independent_signed_distance is not None:
			independent_gap_distance = max(0.0, float(independent_signed_distance))
			independent_penetration_depth = max(0.0, -float(independent_signed_distance))
		# Hull stop-at-boundary metric overrides curved-glyph gap metric by design.
		if hull_signed_gap is not None and alignment_center_char in {"C", "S"}:
			independent_gap_distance = max(0.0, float(hull_signed_gap))
			independent_penetration_depth = max(0.0, -float(hull_signed_gap))
			reported_signed_distance_to_glyph_body = float(hull_signed_gap)
			reported_distance_to_glyph_body = abs(float(hull_signed_gap))
		if is_aligned:
			aligned_count += 1
		else:
			missed_count += 1
		label_metrics.append(
				{
					"label_index": label_index,
					"text": label["text"],
					"text_raw": label.get("text_raw", label["text"]),
					"anchor": label["anchor"],
					"font_size": label["font_size"],
					"endpoint": [best_endpoint[0], best_endpoint[1]],
					"endpoint_distance_to_label": best_distance,
					"endpoint_distance_to_target": None,
					"endpoint_alignment_error": alignment_error,
					"endpoint_distance_to_glyph_body": reported_distance_to_glyph_body,
					"endpoint_signed_distance_to_glyph_body": reported_signed_distance_to_glyph_body,
					"endpoint_distance_to_c_center": None,
					"c_center_point": None,
					"endpoint_perpendicular_distance_to_alignment_center": alignment_error,
					"alignment_center_point": (
						[alignment_center[0], alignment_center[1]]
						if alignment_center is not None else None
					),
						"alignment_center_char": alignment_center_char,
						"optical_gate_debug": optical_gate_debug if optical_gate_debug else None,
						"hull_boundary_points": hull_boundary_points,
						"hull_ellipse_fit": hull_ellipse_fit,
						"hull_contact_point": hull_contact_point,
						"hull_signed_gap_along_bond": hull_signed_gap,
						"endpoint_gap_distance_to_glyph_body": independent_gap_distance,
					"endpoint_penetration_depth_to_glyph_body": independent_penetration_depth,
					"endpoint_distance_to_glyph_body_independent": independent_distance,
					"endpoint_signed_distance_to_glyph_body_independent": independent_signed_distance,
					"independent_connector_line_index": independent_line_index,
					"independent_endpoint": (
						[independent_endpoint[0], independent_endpoint[1]]
						if independent_endpoint is not None else None
					),
					"independent_glyph_model": independent_model_name,
					"alignment_tolerance": alignment_tolerance,
					"aligned": bool(is_aligned),
					"reason": alignment_reason,
					"connector_line_index": best_line_index,
					"attach_policy": None,
					"endpoint_target_kind": None,
					"alignment_mode": "independent_glyph_primitives",
				}
			)
	aligned_connector_pairs = set()
	for metric in label_metrics:
		connector_index = metric.get("connector_line_index")
		label_index = metric.get("label_index")
		if connector_index is None or label_index is None:
			continue
		aligned_connector_pairs.add((int(connector_index), int(label_index)))
	lattice_angle_violation_count, lattice_angle_violations = count_lattice_angle_violations(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	glyph_glyph_overlap_count, glyph_glyph_overlaps = count_glyph_glyph_overlaps(
		labels=labels,
		checked_label_indexes=checked_label_indexes,
	)
	bond_bond_overlap_count, bond_bond_overlaps = count_bond_bond_overlaps(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	hatched_thin_conflict_count, hatched_thin_conflicts, hashed_carrier_map = count_hatched_thin_conflicts(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	decorative_hatched_stroke_indexes = sorted(
		{
			stroke_index
			for stroke_indexes in hashed_carrier_map.values()
			for stroke_index in stroke_indexes
		}
	)
	decorative_hatched_stroke_index_set = set(decorative_hatched_stroke_indexes)
	checked_bond_line_indexes = [
		index for index in checked_line_indexes if index not in decorative_hatched_stroke_index_set
	]
	location_origin = overlap_origin(lines, haworth_base_ring)
	checked_bond_lengths_by_quadrant: dict[str, list[float]] = {}
	checked_bond_lengths_by_ring_region: dict[str, list[float]] = {}
	checked_bond_lengths_by_quadrant_ring_region: dict[str, list[float]] = {}
	for line_index in checked_bond_line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		length = line_lengths_all[line_index]
		midpoint = line_midpoint(line)
		quadrant = quadrant_label(midpoint, origin=location_origin)
		ring_region = ring_region_label(midpoint, haworth_base_ring=haworth_base_ring)
		group_length_append(checked_bond_lengths_by_quadrant, quadrant, length)
		group_length_append(checked_bond_lengths_by_ring_region, ring_region, length)
		group_length_append(
			checked_bond_lengths_by_quadrant_ring_region,
			f"{quadrant} | {ring_region}",
			length,
		)
	line_lengths_checked = [
		line_lengths_all[index]
		for index in checked_bond_line_indexes
		if 0 <= index < len(line_lengths_all)
	]
	connector_line_lengths = [
		line_lengths_all[index]
		for index in sorted(connector_line_indexes)
		if index in checked_bond_line_indexes and 0 <= index < len(line_lengths_all)
	]
	non_connector_line_lengths = [
		length
		for index, length in enumerate(line_lengths_all)
		if index in checked_bond_line_indexes and index not in connector_line_indexes
	]
	excluded_line_lengths = [
		line_lengths_all[index]
		for index in sorted(excluded_line_indexes)
		if 0 <= index < len(line_lengths_all)
	]
	decorative_hatched_stroke_lengths = [
		line_lengths_all[index]
		for index in decorative_hatched_stroke_indexes
		if 0 <= index < len(line_lengths_all)
	]
	bond_glyph_overlap_count, bond_glyph_overlaps = count_bond_glyph_overlaps(
		lines=lines,
		labels=labels,
		checked_line_indexes=checked_line_indexes,
		checked_label_indexes=checked_label_indexes,
		aligned_connector_pairs=aligned_connector_pairs,
		haworth_base_ring=haworth_base_ring,
		gap_tolerance=float(bond_glyph_gap_tolerance),
		wedge_bonds=wedge_bonds,
	)
	diagnostic_svg_path = None
	if write_diagnostic_svg and diagnostic_svg_dir is not None:
		diagnostic_svg_name = f"{svg_path.stem}.diagnostic.svg"
		diagnostic_svg_path = (diagnostic_svg_dir / diagnostic_svg_name).resolve()
		do_write_diagnostic_svg(
			svg_path=svg_path,
			output_path=diagnostic_svg_path,
			lines=lines,
			labels=labels,
			label_metrics=label_metrics,
		)
	return {
		"svg": str(svg_path),
		"diagnostic_svg": str(diagnostic_svg_path) if diagnostic_svg_path is not None else None,
		"text_labels_total": len(labels),
		"text_label_values": [str(label.get("text", "")) for label in labels],
		"labels_analyzed": len(measurement_label_indexes),
		"aligned_count": aligned_count,
		"missed_count": missed_count,
		"no_connector_count": no_connector_count,
		"alignment_outside_tolerance_count": missed_count + no_connector_count,
		"labels": label_metrics,
		"lattice_angle_violation_count": lattice_angle_violation_count,
		"glyph_glyph_overlap_count": glyph_glyph_overlap_count,
		"bond_bond_overlap_count": bond_bond_overlap_count,
		"hatched_thin_conflict_count": hatched_thin_conflict_count,
		"bond_glyph_overlap_count": bond_glyph_overlap_count,
		"wedge_bond_count": len(wedge_bonds),
		"geometry_checks": {
			"canonical_angles_degrees": list(CANONICAL_LATTICE_ANGLES),
			"angle_tolerance_degrees": LATTICE_ANGLE_TOLERANCE_DEGREES,
			"bond_glyph_gap_tolerance": float(bond_glyph_gap_tolerance),
			"alignment_center_mode": "optical",
			"lattice_angle_violations": lattice_angle_violations,
			"glyph_glyph_overlaps": glyph_glyph_overlaps,
			"bond_bond_overlaps": bond_bond_overlaps,
			"hatched_thin_conflicts": hatched_thin_conflicts,
			"hashed_carrier_map": {
				str(line_index): stroke_indexes
				for line_index, stroke_indexes in sorted(hashed_carrier_map.items())
			},
			"bond_glyph_overlaps": bond_glyph_overlaps,
		},
		"haworth_base_ring": {
			"detected": bool(haworth_base_ring["detected"]),
			"excluded": bool(exclude_haworth_base_ring and haworth_base_ring["detected"]),
			"line_indexes": sorted(set(haworth_base_ring["line_indexes"])),
			"line_count": len(set(haworth_base_ring["line_indexes"])),
			"primitive_indexes": sorted(set(haworth_base_ring.get("primitive_indexes", []))),
			"primitive_count": len(set(haworth_base_ring.get("primitive_indexes", []))),
			"node_count": int(haworth_base_ring["node_count"]),
			"centroid": haworth_base_ring["centroid"],
			"radius": float(haworth_base_ring["radius"]),
			"source": haworth_base_ring.get("source"),
		},
		"checked_line_indexes": checked_line_indexes,
		"checked_bond_line_indexes": checked_bond_line_indexes,
		"excluded_line_indexes": sorted(excluded_line_indexes),
		"decorative_hatched_stroke_indexes": decorative_hatched_stroke_indexes,
		"decorative_hatched_stroke_count": len(decorative_hatched_stroke_indexes),
		"line_lengths": {
			"all_lines": line_lengths_all,
			"checked_lines_raw": line_lengths_checked_raw,
			"checked_lines": line_lengths_checked,
			"connector_lines": connector_line_lengths,
			"non_connector_lines": non_connector_line_lengths,
			"excluded_haworth_base_ring_lines": excluded_line_lengths,
			"decorative_hatched_stroke_lines": decorative_hatched_stroke_lengths,
		},
		"line_lengths_rounded_sorted": {
			"all_lines": rounded_sorted_values(line_lengths_all),
			"checked_lines_raw": rounded_sorted_values(line_lengths_checked_raw),
			"checked_lines": rounded_sorted_values(line_lengths_checked),
			"connector_lines": rounded_sorted_values(connector_line_lengths),
			"non_connector_lines": rounded_sorted_values(non_connector_line_lengths),
			"excluded_haworth_base_ring_lines": rounded_sorted_values(excluded_line_lengths),
			"decorative_hatched_stroke_lines": rounded_sorted_values(decorative_hatched_stroke_lengths),
		},
		"line_lengths_grouped": {
			"checked_bonds_by_quadrant": checked_bond_lengths_by_quadrant,
			"checked_bonds_by_ring_region": checked_bond_lengths_by_ring_region,
			"checked_bonds_by_quadrant_ring_region": checked_bond_lengths_by_quadrant_ring_region,
		},
		"line_lengths_grouped_rounded_sorted": {
			"checked_bonds_by_quadrant": {
				key: rounded_sorted_values(values)
				for key, values in sorted(checked_bond_lengths_by_quadrant.items())
			},
			"checked_bonds_by_ring_region": {
				key: rounded_sorted_values(values)
				for key, values in sorted(checked_bond_lengths_by_ring_region.items())
			},
			"checked_bonds_by_quadrant_ring_region": {
				key: rounded_sorted_values(values)
				for key, values in sorted(checked_bond_lengths_by_quadrant_ring_region.items())
			},
		},
		"line_length_rounded_counts": {
			"all_lines": rounded_value_counts(line_lengths_all),
			"checked_lines_raw": rounded_value_counts(line_lengths_checked_raw),
			"checked_lines": rounded_value_counts(line_lengths_checked),
			"connector_lines": rounded_value_counts(connector_line_lengths),
			"non_connector_lines": rounded_value_counts(non_connector_line_lengths),
			"excluded_haworth_base_ring_lines": rounded_value_counts(excluded_line_lengths),
			"decorative_hatched_stroke_lines": rounded_value_counts(decorative_hatched_stroke_lengths),
		},
		"line_length_stats": {
			"all_lines": length_stats(line_lengths_all),
			"checked_lines_raw": length_stats(line_lengths_checked_raw),
			"checked_lines": length_stats(line_lengths_checked),
			"connector_lines": length_stats(connector_line_lengths),
			"non_connector_lines": length_stats(non_connector_line_lengths),
			"excluded_haworth_base_ring_lines": length_stats(excluded_line_lengths),
			"decorative_hatched_stroke_lines": length_stats(decorative_hatched_stroke_lengths),
		},
	}
