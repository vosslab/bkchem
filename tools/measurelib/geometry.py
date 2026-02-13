"""Primitive geometry operations for glyph-bond alignment measurement."""

# Standard Library
import math

from measurelib.constants import (
	BOND_GLYPH_INTERIOR_EPSILON,
	CANONICAL_LATTICE_ANGLES,
)
from measurelib.util import (
	line_endpoints,
	normalize_box,
	point_distance_sq,
)


#============================================
def line_angle_degrees(line: dict) -> float:
	"""Return one line direction angle in degrees in [0, 360)."""
	return math.degrees(math.atan2(line["y2"] - line["y1"], line["x2"] - line["x1"])) % 360.0


#============================================
def nearest_lattice_angle_error(angle_degrees: float) -> float:
	"""Return minimum absolute error to canonical lattice angles."""
	return min(
		abs(((angle_degrees - lattice_angle + 180.0) % 360.0) - 180.0)
		for lattice_angle in CANONICAL_LATTICE_ANGLES
	)


#============================================
def nearest_canonical_lattice_angle(angle_degrees: float) -> float:
	"""Return nearest canonical lattice angle for one measured angle."""
	return min(
		CANONICAL_LATTICE_ANGLES,
		key=lambda lattice_angle: abs(((angle_degrees - lattice_angle + 180.0) % 360.0) - 180.0),
	)


#============================================
def boxes_overlap_interior(
		box_a: tuple[float, float, float, float],
		box_b: tuple[float, float, float, float],
		epsilon: float = 0.5) -> bool:
	"""Return True when two boxes overlap with non-trivial interior area."""
	ax1, ay1, ax2, ay2 = normalize_box(box_a)
	bx1, by1, bx2, by2 = normalize_box(box_b)
	overlap_x = min(ax2, bx2) - max(ax1, bx1)
	overlap_y = min(ay2, by2) - max(ay1, by1)
	return overlap_x > epsilon and overlap_y > epsilon


#============================================
def points_close(
		point_a: tuple[float, float],
		point_b: tuple[float, float],
		tol: float = 1.0) -> bool:
	"""Return True when two points are within one distance tolerance."""
	return point_distance_sq(point_a, point_b) <= (tol * tol)


#============================================
def point_to_segment_distance_sq(
		point: tuple[float, float],
		seg_start: tuple[float, float],
		seg_end: tuple[float, float]) -> float:
	"""Return squared distance from one point to one segment."""
	px, py = point
	x1, y1 = seg_start
	x2, y2 = seg_end
	dx = x2 - x1
	dy = y2 - y1
	denominator = (dx * dx) + (dy * dy)
	if denominator <= 1e-12:
		return ((px - x1) * (px - x1)) + ((py - y1) * (py - y1))
	t_value = ((px - x1) * dx + (py - y1) * dy) / denominator
	t_value = max(0.0, min(1.0, t_value))
	closest_x = x1 + (dx * t_value)
	closest_y = y1 + (dy * t_value)
	return ((px - closest_x) * (px - closest_x)) + ((py - closest_y) * (py - closest_y))


#============================================
def orientation(
		p1: tuple[float, float],
		p2: tuple[float, float],
		p3: tuple[float, float]) -> int:
	"""Return orientation sign for one ordered point triplet."""
	value = ((p2[1] - p1[1]) * (p3[0] - p2[0])) - ((p2[0] - p1[0]) * (p3[1] - p2[1]))
	if abs(value) <= 1e-12:
		return 0
	return 1 if value > 0.0 else 2


#============================================
def on_segment(
		p1: tuple[float, float],
		p2: tuple[float, float],
		query: tuple[float, float]) -> bool:
	"""Return True when query point lies on segment p1-p2."""
	return (
		min(p1[0], p2[0]) - 1e-12 <= query[0] <= max(p1[0], p2[0]) + 1e-12
		and min(p1[1], p2[1]) - 1e-12 <= query[1] <= max(p1[1], p2[1]) + 1e-12
	)


#============================================
def segments_intersect(
		p1: tuple[float, float],
		p2: tuple[float, float],
		q1: tuple[float, float],
		q2: tuple[float, float]) -> bool:
	"""Return True when two finite segments intersect."""
	o1 = orientation(p1, p2, q1)
	o2 = orientation(p1, p2, q2)
	o3 = orientation(q1, q2, p1)
	o4 = orientation(q1, q2, p2)
	if o1 != o2 and o3 != o4:
		return True
	if o1 == 0 and on_segment(p1, p2, q1):
		return True
	if o2 == 0 and on_segment(p1, p2, q2):
		return True
	if o3 == 0 and on_segment(q1, q2, p1):
		return True
	if o4 == 0 and on_segment(q1, q2, p2):
		return True
	return False


#============================================
def distance_sq_segment_to_segment(
		p1: tuple[float, float],
		p2: tuple[float, float],
		q1: tuple[float, float],
		q2: tuple[float, float]) -> float:
	"""Return squared minimum distance between two finite segments."""
	if segments_intersect(p1, p2, q1, q2):
		return 0.0
	return min(
		point_to_segment_distance_sq(p1, q1, q2),
		point_to_segment_distance_sq(p2, q1, q2),
		point_to_segment_distance_sq(q1, p1, p2),
		point_to_segment_distance_sq(q2, p1, p2),
	)


#============================================
def segment_distance_to_box_sq(
		seg_start: tuple[float, float],
		seg_end: tuple[float, float],
		box: tuple[float, float, float, float]) -> float:
	"""Return squared minimum distance from one segment to one box."""
	x1, y1, x2, y2 = normalize_box(box)
	edges = (
		((x1, y1), (x2, y1)),
		((x2, y1), (x2, y2)),
		((x2, y2), (x1, y2)),
		((x1, y2), (x1, y1)),
	)
	start_inside = x1 <= seg_start[0] <= x2 and y1 <= seg_start[1] <= y2
	end_inside = x1 <= seg_end[0] <= x2 and y1 <= seg_end[1] <= y2
	if start_inside or end_inside:
		return 0.0
	for edge_start, edge_end in edges:
		if segments_intersect(seg_start, seg_end, edge_start, edge_end):
			return 0.0
	distances = [
		distance_sq_segment_to_segment(seg_start, seg_end, edge_start, edge_end)
		for edge_start, edge_end in edges
	]
	return min(distances)


#============================================
def line_intersects_box_interior(
		line: dict,
		box: tuple[float, float, float, float],
		epsilon: float = BOND_GLYPH_INTERIOR_EPSILON) -> bool:
	"""Return True when one stroked line penetrates one box interior."""
	x1, y1, x2, y2 = normalize_box(box)
	inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
	if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
		return False
	seg_start = (line["x1"], line["y1"])
	seg_end = (line["x2"], line["y2"])
	half_width = max(0.35, float(line.get("width", 1.0)) * 0.5)
	distance_sq = segment_distance_to_box_sq(seg_start, seg_end, inner_box)
	return distance_sq < (half_width * half_width)


#============================================
def lines_share_endpoint(line_a: dict, line_b: dict, tol: float = 0.75) -> bool:
	"""Return True when two lines share one endpoint within tolerance."""
	a1, a2 = line_endpoints(line_a)
	b1, b2 = line_endpoints(line_b)
	return (
		points_close(a1, b1, tol=tol)
		or points_close(a1, b2, tol=tol)
		or points_close(a2, b1, tol=tol)
		or points_close(a2, b2, tol=tol)
	)


#============================================
def parallel_error_degrees(angle_a: float, angle_b: float) -> float:
	"""Return smallest parallel-or-antiparallel angular difference."""
	diff = abs(((angle_a - angle_b + 180.0) % 360.0) - 180.0)
	return min(diff, abs(diff - 180.0))


#============================================
def angle_difference_degrees(angle_a: float, angle_b: float) -> float:
	"""Return smallest absolute angle difference in [0, 180]."""
	return abs(((angle_a - angle_b + 180.0) % 360.0) - 180.0)


#============================================
def lines_nearly_parallel(line_a: dict, line_b: dict, tol_deg: float = 6.0) -> bool:
	"""Return True when two lines are nearly parallel or anti-parallel."""
	angle_a = line_angle_degrees(line_a)
	angle_b = line_angle_degrees(line_b)
	return parallel_error_degrees(angle_a, angle_b) <= tol_deg


#============================================
def line_collinear_overlap_length(line_a: dict, line_b: dict, tol: float = 1e-6) -> float:
	"""Return collinear overlap length between two segments, or 0 when none."""
	p1, p2 = line_endpoints(line_a)
	q1, q2 = line_endpoints(line_b)
	if orientation(p1, p2, q1) != 0 or orientation(p1, p2, q2) != 0:
		return 0.0
	dx = abs(p2[0] - p1[0])
	dy = abs(p2[1] - p1[1])
	if dx >= dy:
		a1, a2 = sorted((p1[0], p2[0]))
		b1, b2 = sorted((q1[0], q2[0]))
	else:
		a1, a2 = sorted((p1[1], p2[1]))
		b1, b2 = sorted((q1[1], q2[1]))
	overlap = min(a2, b2) - max(a1, b1)
	if overlap <= tol:
		return 0.0
	return float(overlap)


#============================================
def line_overlap_midpoint(line_a: dict, line_b: dict) -> tuple[float, float] | None:
	"""Return representative midpoint of collinear overlap segment, if any."""
	p1, p2 = line_endpoints(line_a)
	q1, q2 = line_endpoints(line_b)
	if orientation(p1, p2, q1) != 0 or orientation(p1, p2, q2) != 0:
		return None
	dx = p2[0] - p1[0]
	dy = p2[1] - p1[1]
	denominator = (dx * dx) + (dy * dy)
	if denominator <= 1e-12:
		return p1
	t_q1 = ((q1[0] - p1[0]) * dx + (q1[1] - p1[1]) * dy) / denominator
	t_q2 = ((q2[0] - p1[0]) * dx + (q2[1] - p1[1]) * dy) / denominator
	lo = max(0.0, min(t_q1, t_q2))
	hi = min(1.0, max(t_q1, t_q2))
	if hi < lo:
		return None
	mid_t = (lo + hi) * 0.5
	return (p1[0] + (dx * mid_t), p1[1] + (dy * mid_t))


#============================================
def line_intersection_point(
		p1: tuple[float, float],
		p2: tuple[float, float],
		q1: tuple[float, float],
		q2: tuple[float, float]) -> tuple[float, float] | None:
	"""Return exact segment intersection point, or None when parallel/non-point overlap."""
	x1, y1 = p1
	x2, y2 = p2
	x3, y3 = q1
	x4, y4 = q2
	denominator = ((x1 - x2) * (y3 - y4)) - ((y1 - y2) * (x3 - x4))
	if abs(denominator) <= 1e-12:
		return None
	det1 = (x1 * y2) - (y1 * x2)
	det2 = (x3 * y4) - (y3 * x4)
	ix = ((det1 * (x3 - x4)) - ((x1 - x2) * det2)) / denominator
	iy = ((det1 * (y3 - y4)) - ((y1 - y2) * det2)) / denominator
	intersection = (ix, iy)
	if on_segment(p1, p2, intersection) and on_segment(q1, q2, intersection):
		return intersection
	return None


#============================================
def convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
	"""Return convex hull points in counter-clockwise order."""
	unique = sorted({(float(point[0]), float(point[1])) for point in points})
	if len(unique) <= 1:
		return unique
	def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
		return ((a[0] - o[0]) * (b[1] - o[1])) - ((a[1] - o[1]) * (b[0] - o[0]))
	lower: list[tuple[float, float]] = []
	for point in unique:
		while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= 0.0:
			lower.pop()
		lower.append(point)
	upper: list[tuple[float, float]] = []
	for point in reversed(unique):
		while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= 0.0:
			upper.pop()
		upper.append(point)
	return lower[:-1] + upper[:-1]


#============================================
def point_to_infinite_line_distance(
		point: tuple[float, float],
		line_start: tuple[float, float],
		line_end: tuple[float, float]) -> float:
	"""Return perpendicular distance from one point to one infinite line."""
	x0, y0 = point
	x1, y1 = line_start
	x2, y2 = line_end
	dx = x2 - x1
	dy = y2 - y1
	denominator = math.hypot(dx, dy)
	if denominator <= 1e-12:
		return math.hypot(x0 - x1, y0 - y1)
	numerator = abs((dy * x0) - (dx * y0) + (x2 * y1) - (y2 * x1))
	return numerator / denominator
