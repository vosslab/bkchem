"""Summary statistics and report generation for glyph-bond alignment measurement."""

# Standard Library
import datetime
import math
import pathlib

from measurelib.constants import (
	ALIGNMENT_DISTANCE_ZERO_EPSILON,
	BOND_GLYPH_GAP_TOLERANCE,
	CANONICAL_LATTICE_ANGLES,
	LATTICE_ANGLE_TOLERANCE_DEGREES,
)
from measurelib.util import (
	alignment_score,
	compact_float,
	compact_sorted_values,
	compact_value_counts,
	display_float,
	display_point,
	increment_counter,
	length_stats,
	rounded_sorted_values,
	rounded_value_counts,
)


#============================================
def summary_stats(file_reports: list[dict]) -> dict:
	"""Compute overall summary metrics for one analysis run."""
	total_labels = sum(report["labels_analyzed"] for report in file_reports)
	total_text_labels = sum(report.get("text_labels_total", 0) for report in file_reports)
	text_label_counts: dict[str, int] = {}
	aligned = sum(report["aligned_count"] for report in file_reports)
	missed = sum(report["missed_count"] for report in file_reports)
	no_connector = sum(report["no_connector_count"] for report in file_reports)
	alignment_outside_tolerance = sum(
		report.get("alignment_outside_tolerance_count", 0) for report in file_reports
	)
	lattice_angle_violations = sum(report.get("lattice_angle_violation_count", 0) for report in file_reports)
	glyph_glyph_overlaps = sum(report.get("glyph_glyph_overlap_count", 0) for report in file_reports)
	bond_bond_overlaps = sum(report.get("bond_bond_overlap_count", 0) for report in file_reports)
	hatched_thin_conflicts = sum(report.get("hatched_thin_conflict_count", 0) for report in file_reports)
	bond_glyph_overlaps = sum(report.get("bond_glyph_overlap_count", 0) for report in file_reports)
	lattice_angle_violation_quadrants: dict[str, int] = {}
	lattice_angle_violation_ring_regions: dict[str, int] = {}
	lattice_angle_violation_examples = []
	bond_bond_overlap_quadrants: dict[str, int] = {}
	bond_bond_overlap_ring_regions: dict[str, int] = {}
	hatched_thin_conflict_quadrants: dict[str, int] = {}
	hatched_thin_conflict_ring_regions: dict[str, int] = {}
	hatched_thin_conflict_types: dict[str, int] = {}
	bond_glyph_overlap_quadrants: dict[str, int] = {}
	bond_glyph_overlap_ring_regions: dict[str, int] = {}
	bond_glyph_overlap_label_texts: dict[str, int] = {}
	bond_glyph_overlap_classifications: dict[str, int] = {}
	bond_glyph_endpoint_overlap_count = 0
	bond_glyph_endpoint_too_close_count = 0
	bond_glyph_endpoint_signed_distances: list[float] = []
	alignment_by_glyph_measurements: dict[str, list[dict]] = {}
	alignment_distances_all: list[float] = []
	alignment_glyph_body_distances_all: list[float] = []
	alignment_glyph_body_signed_distances_all: list[float] = []
	alignment_scores_all: list[float] = []
	alignment_distance_missing_count = 0
	alignment_glyph_body_distance_missing_count = 0
	bond_lengths_by_quadrant_checked: dict[str, list[float]] = {}
	bond_lengths_by_ring_region_checked: dict[str, list[float]] = {}
	bond_lengths_by_quadrant_ring_region_checked: dict[str, list[float]] = {}
	bond_bond_overlap_examples = []
	hatched_thin_conflict_examples = []
	bond_glyph_overlap_examples = []
	bond_glyph_gap_tolerances: dict[str, int] = {}
	haworth_detected_files = sum(
		1 for report in file_reports if report.get("haworth_base_ring", {}).get("detected")
	)
	haworth_excluded_files = sum(
		1 for report in file_reports if report.get("haworth_base_ring", {}).get("excluded")
	)
	haworth_excluded_lines = sum(len(report.get("excluded_line_indexes", [])) for report in file_reports)
	decorative_hatched_stroke_lines = sum(
		int(report.get("decorative_hatched_stroke_count", 0))
		for report in file_reports
	)
	for report in file_reports:
		for label_text in report.get("text_label_values", []):
			increment_counter(text_label_counts, str(label_text))
		for label in report.get("labels", []):
			glyph_text = str(label.get("text", ""))
			if glyph_text not in alignment_by_glyph_measurements:
				alignment_by_glyph_measurements[glyph_text] = []
			distance_raw = label.get("endpoint_alignment_error")
			if distance_raw is None:
				distance_raw = label.get("endpoint_distance_to_target")
			glyph_body_distance_raw = label.get("endpoint_distance_to_glyph_body")
			if glyph_body_distance_raw is None:
				glyph_body_distance_raw = label.get("endpoint_distance_to_glyph_body_independent")
			glyph_body_signed_distance_raw = label.get("endpoint_signed_distance_to_glyph_body")
			if glyph_body_signed_distance_raw is None:
				glyph_body_signed_distance_raw = label.get("endpoint_signed_distance_to_glyph_body_independent")
			tolerance_raw = label.get("alignment_tolerance")
			distance_value = None
			glyph_body_distance_value = None
			glyph_body_signed_distance_value = None
			tolerance_value = None
			if distance_raw is not None:
				try:
					distance_value = float(distance_raw)
				except (TypeError, ValueError):
					distance_value = None
			if glyph_body_distance_raw is not None:
				try:
					glyph_body_distance_value = float(glyph_body_distance_raw)
				except (TypeError, ValueError):
					glyph_body_distance_value = None
			if glyph_body_signed_distance_raw is not None:
				try:
					glyph_body_signed_distance_value = float(glyph_body_signed_distance_raw)
				except (TypeError, ValueError):
					glyph_body_signed_distance_value = None
			if tolerance_raw is not None:
				try:
					tolerance_value = float(tolerance_raw)
				except (TypeError, ValueError):
					tolerance_value = None
			ratio_value = None
			if (
					distance_value is not None
					and tolerance_value is not None
					and tolerance_value > 0.0
			):
				ratio_value = distance_value / tolerance_value
			score_value = alignment_score(distance_value, tolerance_value)
			if distance_value is None:
				alignment_distance_missing_count += 1
			else:
				alignment_distances_all.append(float(distance_value))
			if glyph_body_distance_value is not None:
				alignment_glyph_body_distances_all.append(float(glyph_body_distance_value))
			else:
				alignment_glyph_body_distance_missing_count += 1
			if glyph_body_signed_distance_value is not None:
				alignment_glyph_body_signed_distances_all.append(float(glyph_body_signed_distance_value))
			alignment_scores_all.append(float(score_value))
			alignment_by_glyph_measurements[glyph_text].append(
				{
					"svg": report.get("svg"),
					"label_index": label.get("label_index"),
					"text": glyph_text,
					"text_raw": label.get("text_raw", glyph_text),
					"aligned": bool(label.get("aligned", False)),
					"reason": str(label.get("reason", "unknown")),
					"distance_to_target": distance_value,
					"alignment_error": distance_value,
					"distance_to_glyph_body": glyph_body_distance_value,
					"signed_distance_to_glyph_body": glyph_body_signed_distance_value,
					"gap_distance_to_glyph_body": label.get("endpoint_gap_distance_to_glyph_body"),
					"penetration_depth_to_glyph_body": label.get("endpoint_penetration_depth_to_glyph_body"),
					"perpendicular_distance_to_alignment_center": (
						label.get("endpoint_perpendicular_distance_to_alignment_center")
					),
					"alignment_center_point": label.get("alignment_center_point"),
					"alignment_center_char": label.get("alignment_center_char"),
					"alignment_tolerance": tolerance_value,
					"distance_to_tolerance_ratio": ratio_value,
					"alignment_score": score_value,
						"connector_line_index": label.get("connector_line_index"),
						"endpoint": label.get("endpoint"),
						"hull_boundary_points": label.get("hull_boundary_points"),
						"hull_ellipse_fit": label.get("hull_ellipse_fit"),
						"hull_contact_point": label.get("hull_contact_point"),
						"hull_signed_gap_along_bond": label.get("hull_signed_gap_along_bond"),
						"optical_gate_debug": label.get("optical_gate_debug"),
						"alignment_mode": label.get("alignment_mode", "independent_glyph_primitives"),
						"bond_len": label.get("bond_len"),
						"connector_line_length": label.get("connector_line_length"),
					}
				)
		geometry_checks = report.get("geometry_checks", {})
		gap_tolerance = str(geometry_checks.get("bond_glyph_gap_tolerance", BOND_GLYPH_GAP_TOLERANCE))
		increment_counter(bond_glyph_gap_tolerances, gap_tolerance)
		for violation in geometry_checks.get("lattice_angle_violations", []):
			quadrant = str(violation.get("angle_quadrant", "unknown"))
			ring_region = str(violation.get("angle_ring_region", "unknown"))
			increment_counter(lattice_angle_violation_quadrants, quadrant)
			increment_counter(lattice_angle_violation_ring_regions, ring_region)
			if len(lattice_angle_violation_examples) < 12:
				lattice_angle_violation_examples.append(
					{
						"svg": report.get("svg"),
						"line_index": violation.get("line_index"),
						"angle_degrees": violation.get("angle_degrees"),
						"nearest_canonical_angle_degrees": violation.get("nearest_canonical_angle_degrees"),
						"nearest_error_degrees": violation.get("nearest_error_degrees"),
						"quadrant": quadrant,
						"ring_region": ring_region,
					}
				)
		for overlap in geometry_checks.get("bond_bond_overlaps", []):
			quadrant = str(overlap.get("overlap_quadrant", "unknown"))
			ring_region = str(overlap.get("overlap_ring_region", "unknown"))
			increment_counter(bond_bond_overlap_quadrants, quadrant)
			increment_counter(bond_bond_overlap_ring_regions, ring_region)
			if len(bond_bond_overlap_examples) < 12:
				bond_bond_overlap_examples.append(
					{
						"svg": report.get("svg"),
						"line_index_a": overlap.get("line_index_a"),
						"line_index_b": overlap.get("line_index_b"),
						"overlap_point": overlap.get("overlap_point"),
						"quadrant": quadrant,
						"ring_region": ring_region,
					}
				)
		for conflict in geometry_checks.get("hatched_thin_conflicts", []):
			quadrant = str(conflict.get("overlap_quadrant", "unknown"))
			ring_region = str(conflict.get("overlap_ring_region", "unknown"))
			conflict_type = str(conflict.get("conflict_type", "unknown"))
			increment_counter(hatched_thin_conflict_quadrants, quadrant)
			increment_counter(hatched_thin_conflict_ring_regions, ring_region)
			increment_counter(hatched_thin_conflict_types, conflict_type)
			if len(hatched_thin_conflict_examples) < 12:
				hatched_thin_conflict_examples.append(
					{
						"svg": report.get("svg"),
						"carrier_line_index": conflict.get("carrier_line_index"),
						"other_line_index": conflict.get("other_line_index"),
						"carrier_hatch_stroke_count": conflict.get("carrier_hatch_stroke_count"),
						"carrier_line_width": conflict.get("carrier_line_width"),
						"other_line_width": conflict.get("other_line_width"),
						"type": conflict_type,
						"overlap_point": conflict.get("overlap_point"),
						"quadrant": quadrant,
						"ring_region": ring_region,
					}
				)
		for overlap in geometry_checks.get("bond_glyph_overlaps", []):
			quadrant = str(overlap.get("overlap_quadrant", "unknown"))
			ring_region = str(overlap.get("overlap_ring_region", "unknown"))
			label_text = str(overlap.get("label_text", ""))
			classification = str(overlap.get("overlap_classification", "unspecified"))
			bond_end_overlap = bool(overlap.get("bond_end_overlap", False))
			bond_end_too_close = bool(overlap.get("bond_end_too_close", False))
			if bond_end_overlap:
				bond_glyph_endpoint_overlap_count += 1
			if bond_end_too_close:
				bond_glyph_endpoint_too_close_count += 1
			signed_distance_raw = overlap.get("bond_end_to_glyph_distance")
			if signed_distance_raw is not None:
				try:
					bond_glyph_endpoint_signed_distances.append(float(signed_distance_raw))
				except (TypeError, ValueError):
					pass
			increment_counter(bond_glyph_overlap_quadrants, quadrant)
			increment_counter(bond_glyph_overlap_ring_regions, ring_region)
			increment_counter(bond_glyph_overlap_label_texts, label_text)
			increment_counter(bond_glyph_overlap_classifications, classification)
			if len(bond_glyph_overlap_examples) < 12:
				bond_glyph_overlap_examples.append(
					{
						"svg": report.get("svg"),
						"line_index": overlap.get("line_index"),
						"label_index": overlap.get("label_index"),
						"label_text": label_text,
						"overlap_point": overlap.get("overlap_point"),
						"quadrant": quadrant,
						"ring_region": ring_region,
						"classification": classification,
						"bond_end_to_glyph_distance": overlap.get("bond_end_to_glyph_distance"),
						"bond_end_distance_tolerance": overlap.get("bond_end_distance_tolerance"),
						"bond_end_overlap": bond_end_overlap,
						"bond_end_too_close": bond_end_too_close,
					}
				)
		length_groups = report.get("line_lengths_grouped", {})
		for key, values in length_groups.get("checked_bonds_by_quadrant", {}).items():
			if not isinstance(values, list):
				continue
			target_values = bond_lengths_by_quadrant_checked.setdefault(str(key), [])
			target_values.extend(float(value) for value in values)
		for key, values in length_groups.get("checked_bonds_by_ring_region", {}).items():
			if not isinstance(values, list):
				continue
			target_values = bond_lengths_by_ring_region_checked.setdefault(str(key), [])
			target_values.extend(float(value) for value in values)
		for key, values in length_groups.get("checked_bonds_by_quadrant_ring_region", {}).items():
			if not isinstance(values, list):
				continue
			target_values = bond_lengths_by_quadrant_ring_region_checked.setdefault(str(key), [])
			target_values.extend(float(value) for value in values)
	alignment_rate = 0.0
	if total_labels > 0:
		alignment_rate = aligned / float(total_labels)
	distances = []
	for report in file_reports:
		for label in report["labels"]:
			value = label.get("endpoint_alignment_error")
			if value is None:
				value = label.get("endpoint_distance_to_target")
			if value is None:
				continue
			distances.append(float(value))
	max_miss_distance = 0.0
	mean_miss_distance = 0.0
	if distances:
		max_miss_distance = max(distances)
		mean_miss_distance = sum(distances) / float(len(distances))
	all_lengths = []
	checked_lengths = []
	connector_lengths = []
	non_connector_lengths = []
	excluded_lengths = []
	for report in file_reports:
		lengths = report.get("line_lengths", {})
		all_lengths.extend(lengths.get("all_lines", []))
		checked_lengths.extend(lengths.get("checked_lines", []))
		connector_lengths.extend(lengths.get("connector_lines", []))
		non_connector_lengths.extend(lengths.get("non_connector_lines", []))
		excluded_lengths.extend(lengths.get("excluded_haworth_base_ring_lines", []))
	all_length_stats = length_stats(all_lengths)
	checked_length_stats = length_stats(checked_lengths)
	connector_length_stats = length_stats(connector_lengths)
	non_connector_length_stats = length_stats(non_connector_lengths)
	excluded_length_stats = length_stats(excluded_lengths)
	all_lengths_rounded_sorted = rounded_sorted_values(all_lengths)
	checked_lengths_rounded_sorted = rounded_sorted_values(checked_lengths)
	connector_lengths_rounded_sorted = rounded_sorted_values(connector_lengths)
	non_connector_lengths_rounded_sorted = rounded_sorted_values(non_connector_lengths)
	excluded_lengths_rounded_sorted = rounded_sorted_values(excluded_lengths)
	bond_glyph_endpoint_signed_distance_stats = length_stats(bond_glyph_endpoint_signed_distances)
	alignment_distance_stats = length_stats(alignment_distances_all)
	alignment_glyph_body_distance_stats = length_stats(alignment_glyph_body_distances_all)
	alignment_glyph_body_signed_distance_stats = length_stats(alignment_glyph_body_signed_distances_all)
	alignment_score_stats = length_stats(alignment_scores_all)
	alignment_distances_compact_sorted = compact_sorted_values(alignment_distances_all)
	alignment_distance_compact_counts = compact_value_counts(alignment_distances_all)
	alignment_glyph_body_distances_compact_sorted = compact_sorted_values(alignment_glyph_body_distances_all)
	alignment_glyph_body_distance_compact_counts = compact_value_counts(alignment_glyph_body_distances_all)
	alignment_nonzero_distances = [
		abs(value)
		for value in alignment_distances_all
		if abs(value) > ALIGNMENT_DISTANCE_ZERO_EPSILON
	]
	alignment_glyph_body_nonzero_distances = [
		abs(value)
		for value in alignment_glyph_body_distances_all
		if abs(value) > ALIGNMENT_DISTANCE_ZERO_EPSILON
	]
	alignment_nonzero_distance_count = len(alignment_nonzero_distances)
	alignment_glyph_body_nonzero_distance_count = len(alignment_glyph_body_nonzero_distances)
	alignment_min_nonzero_distance = None
	if alignment_nonzero_distances:
		alignment_min_nonzero_distance = min(alignment_nonzero_distances)
	alignment_glyph_body_min_nonzero_distance = None
	if alignment_glyph_body_nonzero_distances:
		alignment_glyph_body_min_nonzero_distance = min(alignment_glyph_body_nonzero_distances)
	alignment_by_glyph = {}
	glyph_text_to_bond_end_distance = {}
	glyph_alignment_data_points = []
	glyph_to_bond_end_data_points = []
	single_file = len(file_reports) == 1
	for glyph_text in sorted(alignment_by_glyph_measurements.keys()):
		measurements = alignment_by_glyph_measurements[glyph_text]
		distances = [
			float(item["distance_to_target"])
			for item in measurements
			if item.get("distance_to_target") is not None
		]
		glyph_body_distances = [
			float(item["distance_to_glyph_body"])
			for item in measurements
			if item.get("distance_to_glyph_body") is not None
		]
		glyph_body_signed_distances = [
			float(item["signed_distance_to_glyph_body"])
			for item in measurements
			if item.get("signed_distance_to_glyph_body") is not None
		]
		perpendicular_distances = [
			float(item["perpendicular_distance_to_alignment_center"])
			for item in measurements
			if item.get("perpendicular_distance_to_alignment_center") is not None
		]
		scores = [float(item.get("alignment_score", 0.0)) for item in measurements]
		aligned_count = sum(1 for item in measurements if item.get("aligned"))
		no_connector_count = sum(
			1 for item in measurements if item.get("reason") == "no_nearby_connector"
		)
		measurement_rows = []
		for item in measurements:
			row = {
				"label_index": item.get("label_index"),
				"text": item.get("text", glyph_text),
				"text_raw": item.get("text_raw", item.get("text", glyph_text)),
				"pass": bool(item.get("aligned")),
				"aligned": item.get("aligned"),
				"reason": item.get("reason"),
				"distance_to_target": display_float(item.get("distance_to_target")),
				"alignment_error": display_float(item.get("alignment_error")),
				"distance_to_glyph_body": display_float(item.get("distance_to_glyph_body")),
				"signed_distance_to_glyph_body": display_float(item.get("signed_distance_to_glyph_body")),
				"gap_distance_to_glyph_body": display_float(item.get("gap_distance_to_glyph_body")),
				"penetration_depth_to_glyph_body": display_float(item.get("penetration_depth_to_glyph_body")),
				"perpendicular_distance_to_alignment_center": display_float(
					item.get("perpendicular_distance_to_alignment_center")
				),
				"alignment_center_point": display_point(item.get("alignment_center_point")),
				"alignment_center_char": item.get("alignment_center_char"),
				"alignment_tolerance": display_float(item.get("alignment_tolerance")),
				"distance_to_tolerance_ratio": display_float(item.get("distance_to_tolerance_ratio")),
				"alignment_score": display_float(item.get("alignment_score")),
					"connector_line_index": item.get("connector_line_index"),
					"bond_len": display_float(item.get("bond_len")),
					"connector_line_length": display_float(item.get("connector_line_length")),
					"endpoint": display_point(item.get("endpoint")),
					"hull_boundary_points": [
						display_point(point)
						for point in (item.get("hull_boundary_points") or [])
					],
					"hull_ellipse_fit": item.get("hull_ellipse_fit"),
					"hull_contact_point": display_point(item.get("hull_contact_point")),
					"hull_signed_gap_along_bond": display_float(item.get("hull_signed_gap_along_bond")),
					"optical_gate_debug": item.get("optical_gate_debug"),
				}
			if not single_file:
				row["svg"] = item.get("svg")
			measurement_rows.append(row)
			glyph_alignment_data_points.append(
				{
					key: row.get(key)
					for key in (
						"label_index",
						"text",
						"text_raw",
						"pass",
						"aligned",
						"reason",
						"distance_to_target",
						"alignment_tolerance",
						"perpendicular_distance_to_alignment_center",
							"alignment_center_point",
							"alignment_center_char",
							"connector_line_index",
							"bond_len",
							"endpoint",
							"hull_boundary_points",
							"hull_ellipse_fit",
							"hull_contact_point",
							"hull_signed_gap_along_bond",
							"optical_gate_debug",
						)
					}
				)
			glyph_to_bond_end_data_points.append(
				{
					key: row.get(key)
					for key in (
						"label_index",
						"text",
						"text_raw",
						"pass",
						"distance_to_glyph_body",
						"signed_distance_to_glyph_body",
						"alignment_tolerance",
						"perpendicular_distance_to_alignment_center",
							"alignment_center_point",
							"alignment_center_char",
							"connector_line_index",
							"bond_len",
							"endpoint",
							"hull_boundary_points",
							"hull_ellipse_fit",
							"hull_contact_point",
							"hull_signed_gap_along_bond",
							"optical_gate_debug",
						)
					}
				)
		alignment_by_glyph[glyph_text] = {
			"count": len(measurements),
			"aligned_count": aligned_count,
			"outside_tolerance_count": len(measurements) - aligned_count,
			"no_connector_count": no_connector_count,
			"alignment_rate": aligned_count / float(len(measurements)) if measurements else 0.0,
			"gap_distance_stats": length_stats(glyph_body_signed_distances),
			"alignment_distance_stats": length_stats(distances),
			"perpendicular_distance_stats": length_stats(perpendicular_distances),
			"distance_values": [compact_float(value) for value in distances],
			"distance_to_glyph_body_values": [compact_float(value) for value in glyph_body_distances],
			"score_values": [compact_float(value) for value in scores],
			"distance_mean": compact_float(sum(distances) / float(len(distances))) if distances else None,
			"distance_to_glyph_body_mean": (
				compact_float(sum(glyph_body_distances) / float(len(glyph_body_distances)))
				if glyph_body_distances else None
			),
			"score_mean": compact_float(sum(scores) / float(len(scores))) if scores else None,
			"measurements": measurement_rows,
		}
		glyph_text_to_bond_end_distance[glyph_text] = sorted(
			display_float(value)
			for value in glyph_body_signed_distances
		)
	alignment_label_type_stats = {}
	for glyph_text, glyph_data in sorted(alignment_by_glyph.items()):
		alignment_label_type_stats[glyph_text] = {
			"count": glyph_data["count"],
			"aligned_count": glyph_data["aligned_count"],
			"alignment_rate": glyph_data["alignment_rate"],
			"gap_distance_stats": glyph_data["gap_distance_stats"],
			"alignment_distance_stats": glyph_data["alignment_distance_stats"],
			"perpendicular_distance_stats": glyph_data["perpendicular_distance_stats"],
		}
	unique_text_labels = sorted(text_label_counts.keys())
	return {
		"files_analyzed": len(file_reports),
		"text_labels_total": total_text_labels,
		"text_labels_unique_total": len(unique_text_labels),
		"text_labels_unique": unique_text_labels,
		"text_label_counts": text_label_counts,
		"labels_analyzed": total_labels,
		"aligned_labels": aligned,
		"missed_labels": missed,
		"labels_without_connector": no_connector,
		"alignment_outside_tolerance_count": alignment_outside_tolerance,
		"alignment_rate": alignment_rate,
		"max_endpoint_distance_to_target": max_miss_distance,
		"mean_endpoint_distance_to_target": mean_miss_distance,
		"alignment_distance_missing_count": alignment_distance_missing_count,
		"alignment_distance_stats": alignment_distance_stats,
		"alignment_glyph_body_distance_missing_count": alignment_glyph_body_distance_missing_count,
		"alignment_glyph_body_distance_stats": alignment_glyph_body_distance_stats,
		"alignment_glyph_body_signed_distance_stats": alignment_glyph_body_signed_distance_stats,
		"alignment_score_stats": alignment_score_stats,
		"alignment_nonzero_distance_count": alignment_nonzero_distance_count,
		"alignment_min_nonzero_distance": compact_float(alignment_min_nonzero_distance),
		"alignment_distances_compact_sorted": alignment_distances_compact_sorted,
		"alignment_distance_compact_counts": alignment_distance_compact_counts,
		"alignment_glyph_body_nonzero_distance_count": alignment_glyph_body_nonzero_distance_count,
		"alignment_glyph_body_min_nonzero_distance": compact_float(alignment_glyph_body_min_nonzero_distance),
		"alignment_glyph_body_distances_compact_sorted": alignment_glyph_body_distances_compact_sorted,
		"alignment_glyph_body_distance_compact_counts": alignment_glyph_body_distance_compact_counts,
		"alignment_distances_rounded_sorted": alignment_distances_compact_sorted,
		"alignment_distance_rounded_counts": alignment_distance_compact_counts,
		"glyph_to_bond_end_distance_stats": alignment_glyph_body_distance_stats,
		"glyph_to_bond_end_signed_distance_stats": alignment_glyph_body_signed_distance_stats,
		"glyph_to_bond_end_missing_distance_count": alignment_glyph_body_distance_missing_count,
		"glyph_to_bond_end_nonzero_distance_count": alignment_glyph_body_nonzero_distance_count,
		"glyph_to_bond_end_min_nonzero_distance": compact_float(alignment_glyph_body_min_nonzero_distance),
		"glyph_to_bond_end_distances_compact_sorted": alignment_glyph_body_distances_compact_sorted,
		"glyph_to_bond_end_distance_compact_counts": alignment_glyph_body_distance_compact_counts,
		"glyph_text_to_bond_end_distance": glyph_text_to_bond_end_distance,
		"glyph_alignment_data_points": glyph_alignment_data_points,
		"glyph_to_bond_end_data_points": glyph_to_bond_end_data_points,
		"alignment_by_glyph": alignment_by_glyph,
		"alignment_label_type_stats": alignment_label_type_stats,
		"canonical_angles_degrees": list(CANONICAL_LATTICE_ANGLES),
		"lattice_angle_tolerance_degrees": LATTICE_ANGLE_TOLERANCE_DEGREES,
		"lattice_angle_violation_count": lattice_angle_violations,
		"lattice_angle_violation_quadrants": lattice_angle_violation_quadrants,
		"lattice_angle_violation_ring_regions": lattice_angle_violation_ring_regions,
		"lattice_angle_violation_examples": lattice_angle_violation_examples,
		"glyph_glyph_overlap_count": glyph_glyph_overlaps,
		"bond_bond_overlap_count": bond_bond_overlaps,
		"hatched_thin_conflict_count": hatched_thin_conflicts,
		"bond_glyph_overlap_count": bond_glyph_overlaps,
		"bond_bond_overlap_quadrants": bond_bond_overlap_quadrants,
		"bond_bond_overlap_ring_regions": bond_bond_overlap_ring_regions,
		"bond_bond_overlap_examples": bond_bond_overlap_examples,
		"hatched_thin_conflict_quadrants": hatched_thin_conflict_quadrants,
		"hatched_thin_conflict_ring_regions": hatched_thin_conflict_ring_regions,
		"hatched_thin_conflict_types": hatched_thin_conflict_types,
		"hatched_thin_conflict_examples": hatched_thin_conflict_examples,
		"bond_glyph_overlap_quadrants": bond_glyph_overlap_quadrants,
		"bond_glyph_overlap_ring_regions": bond_glyph_overlap_ring_regions,
		"bond_glyph_overlap_label_texts": bond_glyph_overlap_label_texts,
		"bond_glyph_overlap_classifications": bond_glyph_overlap_classifications,
		"bond_glyph_endpoint_overlap_count": bond_glyph_endpoint_overlap_count,
		"bond_glyph_endpoint_too_close_count": bond_glyph_endpoint_too_close_count,
		"bond_glyph_endpoint_signed_distance_stats": bond_glyph_endpoint_signed_distance_stats,
		"bond_glyph_gap_tolerances": bond_glyph_gap_tolerances,
		"bond_glyph_overlap_examples": bond_glyph_overlap_examples,
		"haworth_base_ring_detected_files": haworth_detected_files,
		"haworth_base_ring_excluded_files": haworth_excluded_files,
		"haworth_base_ring_excluded_line_count": haworth_excluded_lines,
		"decorative_hatched_stroke_line_count": decorative_hatched_stroke_lines,
		"bond_length_stats_all": all_length_stats,
		"total_bonds_detected": all_length_stats["count"],
		"total_bonds_checked": checked_length_stats["count"],
		"bond_lengths_rounded_sorted_all": all_lengths_rounded_sorted,
		"bond_lengths_rounded_sorted_checked": checked_lengths_rounded_sorted,
		"bond_lengths_rounded_sorted_connector": connector_lengths_rounded_sorted,
		"bond_lengths_rounded_sorted_non_connector": non_connector_lengths_rounded_sorted,
		"bond_lengths_rounded_sorted_excluded_haworth_base_ring": excluded_lengths_rounded_sorted,
		"bond_length_rounded_counts_all": rounded_value_counts(all_lengths),
		"bond_length_rounded_counts_checked": rounded_value_counts(checked_lengths),
		"bond_length_rounded_counts_connector": rounded_value_counts(connector_lengths),
		"bond_length_rounded_counts_non_connector": rounded_value_counts(non_connector_lengths),
		"bond_length_rounded_counts_excluded_haworth_base_ring": rounded_value_counts(excluded_lengths),
		"bond_length_stats_checked": checked_length_stats,
		"bond_length_stats_connector": connector_length_stats,
		"bond_length_stats_non_connector": non_connector_length_stats,
		"bond_length_stats_excluded_haworth_base_ring": excluded_length_stats,
		"bond_lengths_by_quadrant_checked": {
			key: rounded_sorted_values(values)
			for key, values in sorted(bond_lengths_by_quadrant_checked.items())
		},
		"bond_lengths_by_ring_region_checked": {
			key: rounded_sorted_values(values)
			for key, values in sorted(bond_lengths_by_ring_region_checked.items())
		},
		"bond_lengths_by_quadrant_ring_region_checked": {
			key: rounded_sorted_values(values)
			for key, values in sorted(bond_lengths_by_quadrant_ring_region_checked.items())
		},
	}


#============================================
def top_misses(file_reports: list[dict], limit: int = 20) -> list[dict]:
	"""Return highest-distance misses across all files."""
	entries = []
	for report in file_reports:
		for label in report["labels"]:
			if label["aligned"]:
				continue
			distance = label.get("endpoint_alignment_error")
			if distance is None:
				distance = label.get("endpoint_distance_to_target")
			if distance is None:
				distance = float("inf")
			entries.append(
				{
					"svg": report["svg"],
					"text": label["text"],
					"reason": label["reason"],
					"distance": distance,
					"bond_len": label.get("bond_len"),
					"endpoint": label["endpoint"],
				}
			)
	entries.sort(key=lambda item: item["distance"], reverse=True)
	return entries[:limit]


#============================================
def format_stats_line(label: str, stats: dict) -> str:
	"""Format one length_stats dict into a compact single line."""
	if stats.get("count", 0) == 0:
		return f"{label}: (none)"
	return (
		f"{label}: n={stats['count']}  "
		f"min={stats['min']:.3f}  max={stats['max']:.3f}  "
		f"mean={stats['mean']:.3f}  sd={stats['stddev']:.3f}"
	)


#============================================
def violation_summary(summary: dict, top_misses: list[dict]) -> dict:
	"""Build a compact violation summary for the JSON report."""
	return {
		"alignment_outside_tolerance_count": summary.get("alignment_outside_tolerance_count", 0),
		"missed_labels": summary.get("missed_labels", 0),
		"labels_without_connector": summary.get("labels_without_connector", 0),
		"lattice_angle_violation_count": summary.get("lattice_angle_violation_count", 0),
		"glyph_glyph_overlap_count": summary.get("glyph_glyph_overlap_count", 0),
		"bond_bond_overlap_count": summary.get("bond_bond_overlap_count", 0),
		"bond_glyph_overlap_count": summary.get("bond_glyph_overlap_count", 0),
		"hatched_thin_conflict_count": summary.get("hatched_thin_conflict_count", 0),
		"total_violation_count": (
			summary.get("alignment_outside_tolerance_count", 0)
			+ summary.get("lattice_angle_violation_count", 0)
			+ summary.get("glyph_glyph_overlap_count", 0)
			+ summary.get("bond_bond_overlap_count", 0)
			+ summary.get("bond_glyph_overlap_count", 0)
			+ summary.get("hatched_thin_conflict_count", 0)
		),
		"top_misses": top_misses[:5],
		"lattice_angle_violation_examples": summary.get("lattice_angle_violation_examples", [])[:3],
		"bond_glyph_overlap_examples": summary.get("bond_glyph_overlap_examples", [])[:3],
		"bond_bond_overlap_examples": summary.get("bond_bond_overlap_examples", [])[:3],
		"alignment_label_type_stats": summary.get("alignment_label_type_stats", {}),
	}


#============================================
# keys containing large arrays that belong in debug, not in the compact summary
JSON_SUMMARY_EXCLUDE_KEYS = {
	"glyph_alignment_data_points",
	"glyph_to_bond_end_data_points",
	"bond_lengths_rounded_sorted_all",
	"bond_lengths_rounded_sorted_checked",
	"bond_lengths_rounded_sorted_connector",
	"bond_lengths_rounded_sorted_non_connector",
	"bond_lengths_rounded_sorted_excluded_haworth_base_ring",
	"bond_length_rounded_counts_all",
	"bond_length_rounded_counts_checked",
	"bond_length_rounded_counts_connector",
	"bond_length_rounded_counts_non_connector",
	"bond_length_rounded_counts_excluded_haworth_base_ring",
	"alignment_distances_compact_sorted",
	"alignment_distance_compact_counts",
	"alignment_distances_rounded_sorted",
	"alignment_distance_rounded_counts",
	"alignment_glyph_body_distances_compact_sorted",
	"alignment_glyph_body_distance_compact_counts",
	"glyph_to_bond_end_distances_compact_sorted",
	"glyph_to_bond_end_distance_compact_counts",
	"alignment_by_glyph",
	"bond_lengths_by_quadrant_checked",
	"bond_lengths_by_ring_region_checked",
	"bond_lengths_by_quadrant_ring_region_checked",
	"lattice_angle_violation_examples",
	"bond_bond_overlap_examples",
	"bond_glyph_overlap_examples",
	"hatched_thin_conflict_examples",
}


def json_summary_compact(summary: dict) -> dict:
	"""Return summary dict without large array-valued keys."""
	return {
		key: value
		for key, value in summary.items()
		if key not in JSON_SUMMARY_EXCLUDE_KEYS
	}


#============================================
def text_report(
		summary: dict,
		top_misses: list[dict],
		input_glob: str,
		exclude_haworth_base_ring: bool) -> str:
	"""Build human-readable report text."""
	banner = "=" * 56
	lines = []
	# -- header --
	lines.append(banner)
	lines.append(" GLYPH BOND ALIGNMENT REPORT")
	lines.append(banner)
	haworth_tag = "excluded" if exclude_haworth_base_ring else "included"
	lines.append(
		f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}  "
		f"|  Mode: optical  |  Haworth: {haworth_tag}"
	)
	lines.append(f"Input glob: {input_glob}")
	unique_labels = summary.get("text_labels_unique", [])
	lines.append(
		f"Unique labels ({summary['text_labels_unique_total']}): "
		+ ", ".join(str(label) for label in unique_labels)
	)
	lines.append("")
	# -- alignment summary --
	lines.append(banner)
	lines.append(" ALIGNMENT SUMMARY")
	lines.append(banner)
	alignment_pct = summary["alignment_rate"] * 100.0
	lines.append(f"{'Files analyzed:':<42}{summary['files_analyzed']:>6}")
	lines.append(f"{'Labels analyzed:':<42}{summary['labels_analyzed']:>6}")
	lines.append(
		f"{'  Aligned:':<42}{summary['aligned_labels']:>6}"
		f"  ({alignment_pct:.1f}%)"
	)
	lines.append(f"{'  Missed:':<42}{summary['missed_labels']:>6}")
	lines.append(f"{'  No connector:':<42}{summary['labels_without_connector']:>6}")
	lines.append(
		f"{'Bonds (detected / checked):':<42}"
		f"{summary['total_bonds_detected']:>6} / {summary['total_bonds_checked']}"
	)
	lines.append(f"{'Alignment rate:':<42}{alignment_pct:>6.1f}%")
	data_pt_count = len(summary.get("glyph_alignment_data_points", []))
	lines.append(f"Alignment data points: {data_pt_count} entries (see JSON report for details)")
	lines.append("")
	# -- per-label alignment statistics --
	label_stats = summary.get("alignment_label_type_stats", {})
	if label_stats:
		lines.append(banner)
		lines.append(" PER-LABEL ALIGNMENT STATISTICS")
		lines.append(banner)
		def _fmt_stats_triple(stats: dict) -> str:
			if stats.get("count", 0) == 0:
				return "(none)"
			return f"{stats['mean']:.2f}/{stats['stddev']:.2f}/{stats['median']:.2f}"
		lines.append(
			f"  {'Label':<8}{'n':>5} {'Aligned':>9} {'Rate':>7}"
			f"  {'bond_end_gap(a/s/m)':>21}  {'perp_offset(a/s/m)':>20}"
		)
		# ALL row from global stats
		total_count = summary.get("labels_analyzed", 0)
		total_aligned = summary.get("aligned_labels", 0)
		total_rate = summary.get("alignment_rate", 0.0) * 100.0
		all_gap_s = summary.get("glyph_to_bond_end_signed_distance_stats", {})
		all_align_s = summary.get("alignment_distance_stats", {})
		lines.append(
			f"  {'ALL':<8}{total_count:>5} {total_aligned:>5}/{total_count:<3} {total_rate:>5.1f}%"
			f"  {_fmt_stats_triple(all_gap_s):>18}  {_fmt_stats_triple(all_align_s):>20}"
		)
		for label_text in sorted(label_stats.keys()):
			entry = label_stats[label_text]
			count = entry["count"]
			aligned_ct = entry["aligned_count"]
			rate = entry["alignment_rate"] * 100.0
			gap_s = entry.get("gap_distance_stats", {})
			align_s = entry.get("alignment_distance_stats", {})
			lines.append(
				f"  {label_text:<8}{count:>5} {aligned_ct:>5}/{count:<3} {rate:>5.1f}%"
				f"  {_fmt_stats_triple(gap_s):>18}  {_fmt_stats_triple(align_s):>20}"
			)
		lines.append("")
	# -- geometry checks --
	lines.append(banner)
	lines.append(" GEOMETRY CHECKS")
	lines.append(banner)
	# helper to format a dict as inline key=value pairs
	def _inline_counts(data: dict) -> str:
		if not data:
			return ""
		return "  (" + "  ".join(f"{k}={v}" for k, v in sorted(data.items())) + ")"
	lattice_count = summary["lattice_angle_violation_count"]
	lattice_qs = summary.get("lattice_angle_violation_quadrants", {})
	lines.append(f"{'Lattice angle violations:':<42}{lattice_count:>6}{_inline_counts(lattice_qs)}")
	lines.append(f"{'Glyph/glyph overlaps:':<42}{summary['glyph_glyph_overlap_count']:>6}")
	bb_count = summary["bond_bond_overlap_count"]
	bb_qs = summary.get("bond_bond_overlap_quadrants", {})
	lines.append(f"{'Bond/bond overlaps:':<42}{bb_count:>6}{_inline_counts(bb_qs)}")
	bg_count = summary["bond_glyph_overlap_count"]
	bg_qs = summary.get("bond_glyph_overlap_quadrants", {})
	lines.append(f"{'Bond/glyph overlaps:':<42}{bg_count:>6}{_inline_counts(bg_qs)}")
	hatch_count = summary.get("hatched_thin_conflict_count", 0)
	hatch_types = summary.get("hatched_thin_conflict_types", {})
	lines.append(f"{'Hatched/thin conflicts:':<42}{hatch_count:>6}{_inline_counts(hatch_types)}")
	haworth_det = summary["haworth_base_ring_detected_files"]
	haworth_exc = summary["haworth_base_ring_excluded_files"]
	lines.append(f"{'Haworth rings (detected / excluded):':<42}{haworth_det:>6} / {haworth_exc}")
	# bond/glyph endpoint distance details (only when overlaps exist)
	if bg_count > 0:
		endpoint_stats = summary.get("bond_glyph_endpoint_signed_distance_stats", {})
		if endpoint_stats.get("count", 0) > 0:
			lines.append(
				f"  bond/glyph endpoint distances (signed): "
				f"min={endpoint_stats['min']:.3f}  "
				f"max={endpoint_stats['max']:.3f}  "
				f"mean={endpoint_stats['mean']:.3f}"
			)
		overlap_cls = summary.get("bond_glyph_overlap_classifications", {})
		if overlap_cls:
			lines.append(f"  classifications: {_inline_counts(overlap_cls).strip()}")
	# sample violations
	if summary.get("lattice_angle_violation_examples"):
		lines.append("")
		lines.append("  Sample lattice-angle violations (up to 6):")
		for item in summary["lattice_angle_violation_examples"][:6]:
			lines.append(
				f"    line={item.get('line_index')}"
				f"  angle={item.get('angle_degrees'):.3f}"
				f"  nearest={item.get('nearest_canonical_angle_degrees'):.1f}"
				f"  error={item.get('nearest_error_degrees'):.3f}"
				f"  q={item.get('quadrant')}"
			)
	if summary.get("bond_bond_overlap_examples"):
		lines.append("")
		lines.append("  Sample bond/bond overlaps (up to 6):")
		for item in summary["bond_bond_overlap_examples"][:6]:
			lines.append(
				f"    lines=({item.get('line_index_a')},{item.get('line_index_b')})"
				f"  q={item.get('quadrant')}  region={item.get('ring_region')}"
			)
	if summary.get("bond_glyph_overlap_examples"):
		lines.append("")
		lines.append("  Sample bond/glyph overlaps (up to 6):")
		for item in summary["bond_glyph_overlap_examples"][:6]:
			dist_text = display_float(item.get("bond_end_to_glyph_distance"))
			lines.append(
				f"    label={item.get('label_text')}"
				f"  class={item.get('classification')}"
				f"  dist={dist_text}"
				f"  q={item.get('quadrant')}"
			)
	if summary.get("hatched_thin_conflict_examples"):
		lines.append("")
		lines.append("  Sample hatched/thin conflicts (up to 6):")
		for item in summary["hatched_thin_conflict_examples"][:6]:
			lines.append(
				f"    carrier={item.get('carrier_line_index')}"
				f"  other={item.get('other_line_index')}"
				f"  type={item.get('type')}"
				f"  q={item.get('quadrant')}"
			)
	lines.append("")
	# -- bond length statistics --
	lines.append(banner)
	lines.append(" BOND LENGTH STATISTICS")
	lines.append(banner)
	hatch_excluded = summary.get("decorative_hatched_stroke_line_count", 0)
	if hatch_excluded > 0:
		lines.append(f"Hatch strokes excluded from checked bonds: {hatch_excluded}")
	# use the compact helper for each category
	checked_identical_to_all = (
		summary.get("total_bonds_detected") == summary.get("total_bonds_checked")
	)
	if not checked_identical_to_all:
		lines.append(format_stats_line("All lines", summary["bond_length_stats_all"]))
	lines.append(format_stats_line("Checked", summary["bond_length_stats_checked"]))
	lines.append(format_stats_line("Connector", summary["bond_length_stats_connector"]))
	lines.append(format_stats_line("Non-connector", summary["bond_length_stats_non_connector"]))
	haworth_stats = summary["bond_length_stats_excluded_haworth_base_ring"]
	if haworth_stats.get("count", 0) > 0:
		lines.append(format_stats_line("Excluded Haworth", haworth_stats))
	# bond lengths by location -- count-only summary
	by_quadrant = summary.get("bond_lengths_by_quadrant_checked", {})
	if by_quadrant:
		parts = "  ".join(f"{k}: n={len(v)}" for k, v in sorted(by_quadrant.items()))
		lines.append(f"By quadrant: {parts}")
	by_region = summary.get("bond_lengths_by_ring_region_checked", {})
	if by_region:
		parts = "  ".join(f"{k}: n={len(v)}" for k, v in sorted(by_region.items()))
		lines.append(f"By ring region: {parts}")
	lines.append("")
	# -- top misses --
	lines.append(banner)
	lines.append(f" TOP MISSES (up to {len(top_misses)})")
	lines.append(banner)
	if not top_misses:
		lines.append("(none)")
	else:
		for item in top_misses:
			distance = item["distance"]
			dist_text = "inf" if math.isinf(distance) else f"{distance:.3f}"
			svg_name = pathlib.Path(str(item["svg"])).name
			lines.append(
				f"  {svg_name:<36}  {item['text']:<6}"
				f"  {item['reason']:<32}  {dist_text}"
			)
	lines.append("")
	return "\n".join(lines) + "\n"
