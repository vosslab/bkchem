"""Overlap and violation counting for glyph-bond alignment measurement."""

# Standard Library
import math

from measurelib.constants import (
	BOND_GLYPH_INTERIOR_EPSILON,
	GLYPH_BOX_OVERLAP_EPSILON,
	HASHED_SHARED_ENDPOINT_PARALLEL_TOLERANCE_DEGREES,
	LATTICE_ANGLE_TOLERANCE_DEGREES,
	MIN_BOND_LENGTH_FOR_ANGLE_CHECK,
)
from measurelib.util import (
	line_endpoints,
	line_length,
	line_midpoint,
	normalize_box,
	point_to_box_signed_distance,
)
from measurelib.geometry import (
	boxes_overlap_interior,
	line_angle_degrees,
	line_collinear_overlap_length,
	line_intersects_box_interior,
	line_intersection_point,
	line_overlap_midpoint,
	lines_nearly_parallel,
	lines_share_endpoint,
	nearest_canonical_lattice_angle,
	nearest_lattice_angle_error,
	parallel_error_degrees,
	segments_intersect,
)
from measurelib.glyph_model import (
	line_closest_endpoint_to_box,
	point_to_label_signed_distance,
)
from measurelib.hatch_detect import (
	detect_hashed_carrier_map,
	is_hatch_stroke_candidate,
	overlap_origin,
	quadrant_label,
	ring_region_label,
)


#============================================
def count_lattice_angle_violations(
		lines: list[dict],
		checked_line_indexes: list[int],
		haworth_base_ring: dict) -> tuple[int, list[dict]]:
	"""Count bond lines outside canonical lattice angles with location context."""
	violations = []
	origin = overlap_origin(lines, haworth_base_ring)
	for line_index in checked_line_indexes:
		line = lines[line_index]
		seg_length = line_length(line)
		if seg_length < MIN_BOND_LENGTH_FOR_ANGLE_CHECK:
			continue
		angle = line_angle_degrees(line)
		nearest_angle = nearest_canonical_lattice_angle(angle)
		error = nearest_lattice_angle_error(angle)
		if error > LATTICE_ANGLE_TOLERANCE_DEGREES:
			midpoint = line_midpoint(line)
			violations.append(
				{
					"line_index": line_index,
					"angle_degrees": angle,
					"nearest_canonical_angle_degrees": nearest_angle,
					"nearest_error_degrees": error,
					"length": seg_length,
					"angle_quadrant": quadrant_label(midpoint, origin=origin),
					"angle_ring_region": ring_region_label(midpoint, haworth_base_ring=haworth_base_ring),
					"measurement_point": [midpoint[0], midpoint[1]],
				}
			)
	return len(violations), violations


#============================================
def count_glyph_glyph_overlaps(labels: list[dict], checked_label_indexes: list[int]) -> tuple[int, list[dict]]:
	"""Count text-glyph box overlaps."""
	overlaps = []
	for index, label_index in enumerate(checked_label_indexes):
		box_a = labels[label_index].get("box")
		if box_a is None:
			continue
		for other_label_index in checked_label_indexes[index + 1:]:
			box_b = labels[other_label_index].get("box")
			if box_b is None:
				continue
			if not boxes_overlap_interior(box_a, box_b, epsilon=GLYPH_BOX_OVERLAP_EPSILON):
				continue
			overlaps.append(
				{
					"label_index_a": label_index,
					"label_text_a": labels[label_index]["text"],
					"label_index_b": other_label_index,
					"label_text_b": labels[other_label_index]["text"],
				}
			)
	return len(overlaps), overlaps


#============================================
def count_bond_bond_overlaps(
		lines: list[dict],
		checked_line_indexes: list[int],
		haworth_base_ring: dict) -> tuple[int, list[dict]]:
	"""Count bond-line overlaps and annotate overlap location metadata."""
	overlaps = []
	origin = overlap_origin(lines, haworth_base_ring)
	for index, line_index in enumerate(checked_line_indexes):
		line_a = lines[line_index]
		p1, p2 = line_endpoints(line_a)
		for other_line_index in checked_line_indexes[index + 1:]:
			line_b = lines[other_line_index]
			q1, q2 = line_endpoints(line_b)
			if not segments_intersect(p1, p2, q1, q2):
				continue
			share_endpoint = lines_share_endpoint(line_a, line_b, tol=0.75)
			if share_endpoint:
				# Common chemical topology joins at a shared endpoint should not count
				# as overlaps unless segments actually overlap along a non-trivial span.
				overlap_length = line_collinear_overlap_length(line_a, line_b)
				if overlap_length <= 0.75:
					continue
			if lines_nearly_parallel(line_a, line_b):
				overlap_length = line_collinear_overlap_length(line_a, line_b)
				if overlap_length <= 0.75:
					continue
			overlap_point = line_intersection_point(p1, p2, q1, q2)
			if overlap_point is None:
				overlap_point = line_overlap_midpoint(line_a, line_b)
			if overlap_point is None:
				midpoint_a = line_midpoint(line_a)
				midpoint_b = line_midpoint(line_b)
				overlap_point = (
					(midpoint_a[0] + midpoint_b[0]) * 0.5,
					(midpoint_a[1] + midpoint_b[1]) * 0.5,
				)
			overlap_quadrant = quadrant_label(overlap_point, origin=origin)
			overlap_ring_region = ring_region_label(overlap_point, haworth_base_ring=haworth_base_ring)
			overlaps.append(
				{
					"line_index_a": line_index,
					"line_index_b": other_line_index,
					"overlap_point": [overlap_point[0], overlap_point[1]],
					"overlap_quadrant": overlap_quadrant,
					"overlap_ring_region": overlap_ring_region,
				}
			)
	return len(overlaps), overlaps


#============================================
def count_hatched_thin_conflicts(
		lines: list[dict],
		checked_line_indexes: list[int],
		haworth_base_ring: dict) -> tuple[int, list[dict], dict[int, list[int]]]:
	"""Count hashed-carrier overlaps with non-hatch lines for diagnosis."""
	conflicts = []
	carrier_map = detect_hashed_carrier_map(lines=lines, checked_line_indexes=checked_line_indexes)
	if not carrier_map:
		return 0, conflicts, carrier_map
	origin = overlap_origin(lines, haworth_base_ring)
	seen_line_pairs: set[tuple[int, int]] = set()
	for carrier_index in sorted(carrier_map.keys()):
		carrier_line = lines[carrier_index]
		carrier_start, carrier_end = line_endpoints(carrier_line)
		cluster_indexes = set(carrier_map[carrier_index])
		cluster_indexes.add(carrier_index)
		for other_line_index in checked_line_indexes:
			if other_line_index in cluster_indexes:
				continue
			if other_line_index < 0 or other_line_index >= len(lines):
				continue
			other_line = lines[other_line_index]
			if is_hatch_stroke_candidate(other_line):
				continue
			pair_key = (min(carrier_index, other_line_index), max(carrier_index, other_line_index))
			if pair_key in seen_line_pairs:
				continue
			other_start, other_end = line_endpoints(other_line)
			if not segments_intersect(carrier_start, carrier_end, other_start, other_end):
				continue
			share_endpoint = lines_share_endpoint(carrier_line, other_line, tol=0.75)
			overlap_length = line_collinear_overlap_length(carrier_line, other_line)
			carrier_angle = line_angle_degrees(carrier_line)
			other_angle = line_angle_degrees(other_line)
			parallel_error = parallel_error_degrees(carrier_angle, other_angle)
			conflict_type = "crossing_intersection"
			if share_endpoint and overlap_length <= 0.75:
				if parallel_error <= HASHED_SHARED_ENDPOINT_PARALLEL_TOLERANCE_DEGREES:
					conflict_type = "shared_endpoint_near_parallel"
				else:
					continue
			if lines_nearly_parallel(carrier_line, other_line):
				if overlap_length <= 0.75:
					if conflict_type != "shared_endpoint_near_parallel":
						continue
				else:
					conflict_type = "collinear_overlap"
			seen_line_pairs.add(pair_key)
			overlap_point = line_intersection_point(carrier_start, carrier_end, other_start, other_end)
			if overlap_point is None:
				overlap_point = line_overlap_midpoint(carrier_line, other_line)
			if overlap_point is None:
				carrier_midpoint = line_midpoint(carrier_line)
				other_midpoint = line_midpoint(other_line)
				overlap_point = (
					(carrier_midpoint[0] + other_midpoint[0]) * 0.5,
					(carrier_midpoint[1] + other_midpoint[1]) * 0.5,
				)
			conflicts.append(
				{
					"carrier_line_index": carrier_index,
					"carrier_line_width": float(carrier_line.get("width", 1.0)),
					"carrier_hatch_stroke_count": len(carrier_map[carrier_index]),
					"other_line_index": other_line_index,
					"other_line_width": float(other_line.get("width", 1.0)),
					"other_line_linecap": str(other_line.get("linecap") or "butt"),
					"conflict_type": conflict_type,
					"overlap_length": float(overlap_length),
					"overlap_point": [overlap_point[0], overlap_point[1]],
					"overlap_quadrant": quadrant_label(overlap_point, origin=origin),
					"overlap_ring_region": ring_region_label(overlap_point, haworth_base_ring=haworth_base_ring),
				}
			)
	return len(conflicts), conflicts, carrier_map


#============================================
def count_bond_glyph_overlaps(
		lines: list[dict],
		labels: list[dict],
		checked_line_indexes: list[int],
		checked_label_indexes: list[int],
		aligned_connector_pairs: set[tuple[int, int]],
		haworth_base_ring: dict,
		gap_tolerance: float,
		wedge_bonds: list[dict] | None = None) -> tuple[int, list[dict]]:
	"""Count bond-vs-glyph overlaps from independent SVG geometry only."""
	overlaps = []
	origin = overlap_origin(lines, haworth_base_ring)
	for line_index in checked_line_indexes:
		line = lines[line_index]
		for label_index in checked_label_indexes:
			label = labels[label_index]
			label_box = label.get("svg_estimated_box")
			if label_box is None:
				continue
			is_aligned_connector = (line_index, label_index) in aligned_connector_pairs
			bond_end_point, _ = line_closest_endpoint_to_box(line=line, box=label_box)
			bond_end_signed_distance = point_to_label_signed_distance(
				point=bond_end_point,
				label=label,
			)
			if not math.isfinite(bond_end_signed_distance):
				bond_end_signed_distance = point_to_box_signed_distance(bond_end_point, label_box)
			bond_end_overlap = bond_end_signed_distance <= 0.0
			bond_end_too_close = (bond_end_signed_distance > 0.0) and (
				bond_end_signed_distance <= float(gap_tolerance)
			)
			interior_overlap = (
				bond_end_overlap
				or line_intersects_box_interior(
					line,
					label_box,
					epsilon=BOND_GLYPH_INTERIOR_EPSILON,
				)
			)
			near_overlap = (
				bond_end_too_close
				or line_intersects_box_interior(
					line,
					label_box,
					epsilon=-float(gap_tolerance),
				)
			)
			overlap_classification = None
			if is_aligned_connector:
				if bond_end_overlap:
					overlap_classification = "interior_overlap"
				elif bond_end_too_close:
					overlap_classification = "gap_tolerance_violation"
			else:
				if interior_overlap:
					overlap_classification = "interior_overlap"
				elif near_overlap:
					overlap_classification = "gap_tolerance_violation"
			if overlap_classification is None:
				continue
			box_x1, box_y1, box_x2, box_y2 = normalize_box(label_box)
			glyph_center = (
				(box_x1 + box_x2) * 0.5,
				(box_y1 + box_y2) * 0.5,
			)
			overlap_point = line_midpoint(line)
			overlaps.append(
				{
					"line_index": line_index,
					"label_index": label_index,
					"label_text": label["text"],
					"glyph_center": [glyph_center[0], glyph_center[1]],
					"overlap_point": [overlap_point[0], overlap_point[1]],
					"overlap_quadrant": quadrant_label(overlap_point, origin=origin),
					"overlap_ring_region": ring_region_label(overlap_point, haworth_base_ring=haworth_base_ring),
					"aligned_connector_pair": bool(is_aligned_connector),
					"overlap_classification": overlap_classification,
					"gap_tolerance": float(gap_tolerance),
					"bond_end_point": [bond_end_point[0], bond_end_point[1]],
					"bond_end_to_glyph_distance": float(bond_end_signed_distance),
					"bond_end_distance_tolerance": float(gap_tolerance),
					"bond_end_overlap": bool(bond_end_overlap),
					"bond_end_too_close": bool(bond_end_too_close),
					"overlap_detection_mode": "independent_svg_geometry",
				}
			)
	# Check wedge bonds against label boxes
	if wedge_bonds:
		for wedge_index, wedge in enumerate(wedge_bonds):
			spine_start = wedge["spine_start"]
			spine_end = wedge["spine_end"]
			wedge_line = {
				"x1": spine_start[0], "y1": spine_start[1],
				"x2": spine_end[0], "y2": spine_end[1],
				"width": 1.0,
			}
			for label_index in checked_label_indexes:
				label = labels[label_index]
				label_box = label.get("svg_estimated_box")
				if label_box is None:
					continue
				if not line_intersects_box_interior(wedge_line, label_box, epsilon=BOND_GLYPH_INTERIOR_EPSILON):
					continue
				box_x1, box_y1, box_x2, box_y2 = normalize_box(label_box)
				glyph_center = ((box_x1 + box_x2) * 0.5, (box_y1 + box_y2) * 0.5)
				midpoint = ((spine_start[0] + spine_end[0]) * 0.5, (spine_start[1] + spine_end[1]) * 0.5)
				overlaps.append({
					"line_index": None,
					"wedge_bond_index": wedge_index,
					"label_index": label_index,
					"label_text": label["text"],
					"glyph_center": [glyph_center[0], glyph_center[1]],
					"overlap_point": [midpoint[0], midpoint[1]],
					"overlap_quadrant": quadrant_label(midpoint, origin=origin),
					"overlap_ring_region": ring_region_label(midpoint, haworth_base_ring=haworth_base_ring),
					"aligned_connector_pair": False,
					"overlap_classification": "wedge_bond_overlap",
					"gap_tolerance": float(gap_tolerance),
					"bond_end_point": [spine_start[0], spine_start[1]],
					"bond_end_to_glyph_distance": 0.0,
					"bond_end_distance_tolerance": float(gap_tolerance),
					"bond_end_overlap": True,
					"bond_end_too_close": False,
					"overlap_detection_mode": "wedge_bond_polygon",
				})
	return len(overlaps), overlaps
