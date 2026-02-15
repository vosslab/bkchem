"""Hatched bond detection for glyph-bond alignment measurement."""

# Standard Library
import math

from measurelib.constants import (
	DOUBLE_BOND_LENGTH_RATIO_MIN,
	DOUBLE_BOND_PARALLEL_TOLERANCE_DEGREES,
	DOUBLE_BOND_PERP_DISTANCE_MAX,
	DOUBLE_BOND_PERP_DISTANCE_MIN,
	HASHED_CARRIER_MAX_WIDTH,
	HASHED_CARRIER_MIN_LENGTH,
	HASHED_CARRIER_MIN_STROKES,
	HASHED_PERPENDICULAR_TOLERANCE_DEGREES,
	HASHED_STROKE_MAX_DISTANCE_TO_CARRIER,
	HATCH_STROKE_MAX_LENGTH,
	HATCH_STROKE_MAX_WIDTH,
	HATCH_STROKE_MIN_LENGTH,
	HATCH_STROKE_MIN_WIDTH,
)
from measurelib.util import line_endpoints, line_length, line_midpoint
from measurelib.geometry import (
	angle_difference_degrees,
	line_angle_degrees,
	point_to_segment_distance_sq,
	segments_intersect,
)


#============================================
def is_hatch_stroke_candidate(line: dict) -> bool:
	"""Return True when one line looks like one short hashed-stroke primitive."""
	linecap = str(line.get("linecap") or "").strip().lower()
	if linecap != "butt":
		return False
	width = float(line.get("width", 1.0))
	length = line_length(line)
	return (
		HATCH_STROKE_MIN_WIDTH <= width <= HATCH_STROKE_MAX_WIDTH
		and HATCH_STROKE_MIN_LENGTH <= length <= HATCH_STROKE_MAX_LENGTH
	)


#============================================
def is_hashed_carrier_candidate(line: dict) -> bool:
	"""Return True when one line looks like one hashed-bond carrier line."""
	width = float(line.get("width", 1.0))
	length = line_length(line)
	return width <= HASHED_CARRIER_MAX_WIDTH and length >= HASHED_CARRIER_MIN_LENGTH


#============================================
def detect_hashed_carrier_map(lines: list[dict], checked_line_indexes: list[int]) -> dict[int, list[int]]:
	"""Return carrier->stroke-index map for hashed bonds inferred from line primitives."""
	stroke_indexes = [
		index for index in checked_line_indexes
		if 0 <= index < len(lines) and is_hatch_stroke_candidate(lines[index])
	]
	carrier_map: dict[int, list[int]] = {}
	for carrier_index in checked_line_indexes:
		if carrier_index < 0 or carrier_index >= len(lines):
			continue
		carrier_line = lines[carrier_index]
		if not is_hashed_carrier_candidate(carrier_line):
			continue
		carrier_start, carrier_end = line_endpoints(carrier_line)
		carrier_angle = line_angle_degrees(carrier_line)
		supporting_strokes = []
		for stroke_index in stroke_indexes:
			if stroke_index == carrier_index:
				continue
			stroke_line = lines[stroke_index]
			stroke_midpoint = line_midpoint(stroke_line)
			distance = math.sqrt(
				point_to_segment_distance_sq(stroke_midpoint, carrier_start, carrier_end)
			)
			if distance > HASHED_STROKE_MAX_DISTANCE_TO_CARRIER:
				continue
			stroke_angle = line_angle_degrees(stroke_line)
			angle_diff = angle_difference_degrees(carrier_angle, stroke_angle)
			perpendicular_error = abs(angle_diff - 90.0)
			if perpendicular_error > HASHED_PERPENDICULAR_TOLERANCE_DEGREES:
				continue
			if not segments_intersect(carrier_start, carrier_end, *(line_endpoints(stroke_line))):
				continue
			supporting_strokes.append(stroke_index)
		if len(supporting_strokes) < HASHED_CARRIER_MIN_STROKES:
			continue
		carrier_map[carrier_index] = sorted(set(supporting_strokes))
	return carrier_map


#============================================
def detect_double_bond_pairs(
		lines: list[dict],
		checked_line_indexes: list[int],
		excluded_indexes: set[int] | None = None) -> list[tuple[int, int]]:
	"""Return (primary, secondary) index pairs for double bond offset lines.

	Two lines form a double bond pair when they are nearly parallel, similar
	length, and separated by a small perpendicular distance.  For asymmetric
	pairs the round-cap line is primary and the butt-cap line is secondary.

	Args:
		lines: full list of SVG line primitives.
		checked_line_indexes: indexes eligible for pairing.
		excluded_indexes: indexes already classified (hatch strokes, etc.)
			that should not participate.

	Returns:
		list of (primary_index, secondary_index) tuples.
	"""
	if excluded_indexes is None:
		excluded_indexes = set()
	# build candidate list excluding already-classified lines
	candidates = [
		idx for idx in checked_line_indexes
		if 0 <= idx < len(lines) and idx not in excluded_indexes
	]
	paired: set[int] = set()
	pairs: list[tuple[int, int]] = []
	for i_pos in range(len(candidates)):
		idx_a = candidates[i_pos]
		if idx_a in paired:
			continue
		line_a = lines[idx_a]
		len_a = line_length(line_a)
		if len_a < 1e-6:
			continue
		angle_a = line_angle_degrees(line_a)
		start_a, end_a = line_endpoints(line_a)
		best_partner = None
		best_perp = float("inf")
		for j_pos in range(i_pos + 1, len(candidates)):
			idx_b = candidates[j_pos]
			if idx_b in paired:
				continue
			line_b = lines[idx_b]
			len_b = line_length(line_b)
			if len_b < 1e-6:
				continue
			# check parallel
			angle_b = line_angle_degrees(line_b)
			angle_diff = angle_difference_degrees(angle_a, angle_b)
			parallel_err = min(angle_diff, abs(angle_diff - 180.0))
			if parallel_err > DOUBLE_BOND_PARALLEL_TOLERANCE_DEGREES:
				continue
			# check length ratio
			ratio = min(len_a, len_b) / max(len_a, len_b)
			if ratio < DOUBLE_BOND_LENGTH_RATIO_MIN:
				continue
			# check perpendicular distance: midpoint of B to segment A
			mid_b = line_midpoint(line_b)
			perp_dist = math.sqrt(
				point_to_segment_distance_sq(mid_b, start_a, end_a)
			)
			if not (DOUBLE_BOND_PERP_DISTANCE_MIN <= perp_dist <= DOUBLE_BOND_PERP_DISTANCE_MAX):
				continue
			if perp_dist < best_perp:
				best_perp = perp_dist
				best_partner = idx_b
		if best_partner is None:
			continue
		# determine primary vs secondary by linecap
		cap_a = str(lines[idx_a].get("linecap", "")).strip().lower()
		cap_b = str(lines[best_partner].get("linecap", "")).strip().lower()
		if cap_a == "round" and cap_b == "butt":
			# asymmetric: round is primary, butt is secondary
			primary_idx = idx_a
			secondary_idx = best_partner
		elif cap_b == "round" and cap_a == "butt":
			primary_idx = best_partner
			secondary_idx = idx_a
		else:
			# symmetric: keep lower index as primary
			primary_idx = min(idx_a, best_partner)
			secondary_idx = max(idx_a, best_partner)
		paired.add(primary_idx)
		paired.add(secondary_idx)
		pairs.append((primary_idx, secondary_idx))
	return pairs


#============================================
def default_overlap_origin(lines: list[dict]) -> tuple[float, float]:
	"""Return default overlap-classification origin from line geometry extents."""
	if not lines:
		return (0.0, 0.0)
	x_values = []
	y_values = []
	for line in lines:
		x_values.extend([line["x1"], line["x2"]])
		y_values.extend([line["y1"], line["y2"]])
	return (
		(min(x_values) + max(x_values)) * 0.5,
		(min(y_values) + max(y_values)) * 0.5,
	)


#============================================
def overlap_origin(lines: list[dict], haworth_base_ring: dict) -> tuple[float, float]:
	"""Return classification origin using Haworth centroid when available."""
	centroid = haworth_base_ring.get("centroid")
	if centroid is not None and len(centroid) == 2:
		return (float(centroid[0]), float(centroid[1]))
	return default_overlap_origin(lines)


#============================================
def quadrant_label(point: tuple[float, float], origin: tuple[float, float], tol: float = 0.6) -> str:
	"""Return quadrant label for one point relative to one origin."""
	dx = point[0] - origin[0]
	dy = point[1] - origin[1]
	if abs(dx) <= tol or abs(dy) <= tol:
		return "axis"
	if dx > 0.0 and dy < 0.0:
		return "upper-right"
	if dx < 0.0 and dy < 0.0:
		return "upper-left"
	if dx < 0.0 and dy > 0.0:
		return "lower-left"
	return "lower-right"


#============================================
def ring_region_label(point: tuple[float, float], haworth_base_ring: dict) -> str:
	"""Return inside/outside classification relative to detected Haworth base ring."""
	if not haworth_base_ring.get("detected"):
		return "unknown"
	centroid = haworth_base_ring.get("centroid")
	radius = float(haworth_base_ring.get("radius", 0.0))
	if centroid is None or len(centroid) != 2 or radius <= 0.0:
		return "unknown"
	distance = math.hypot(point[0] - float(centroid[0]), point[1] - float(centroid[1]))
	return "inside_base_ring" if distance <= (radius * 1.15) else "outside_base_ring"
