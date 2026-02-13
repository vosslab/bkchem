"""Hatched bond detection for glyph-bond alignment measurement."""

# Standard Library
import math

from measurelib.constants import (
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
