#!/usr/bin/env python3
"""Measure bond-to-glyph alignment from existing SVG files without re-rendering."""

# Standard Library
import argparse
import datetime
import glob
import json
import math
import pathlib
import re
import subprocess
import sys

# Third Party
import defusedxml.ElementTree as ET

MAX_ENDPOINT_TO_LABEL_DISTANCE_FACTOR = 2.6
MIN_ALIGNMENT_DISTANCE_TOLERANCE = 0.5
MIN_BOND_LENGTH_FOR_ANGLE_CHECK = 4.0
LATTICE_ANGLE_TOLERANCE_DEGREES = 0.0
CANONICAL_LATTICE_ANGLES = tuple(float(angle) for angle in range(0, 360, 30))
GLYPH_BOX_OVERLAP_EPSILON = 0.5
BOND_GLYPH_INTERIOR_EPSILON = 0.35
BOND_GLYPH_GAP_TOLERANCE = 0.65
HAWORTH_RING_SEARCH_RADIUS = 45.0
HAWORTH_RING_MIN_PRIMITIVES = 5
SVG_FLOAT_PATTERN = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
LENGTH_ROUND_DECIMALS = 3
HATCH_STROKE_MIN_WIDTH = 0.55
HATCH_STROKE_MAX_WIDTH = 1.35
HATCH_STROKE_MIN_LENGTH = 0.55
HATCH_STROKE_MAX_LENGTH = 4.5
HASHED_CARRIER_MAX_WIDTH = 2.20
HASHED_CARRIER_MIN_LENGTH = 6.0
HASHED_CARRIER_MIN_STROKES = 4
HASHED_STROKE_MAX_DISTANCE_TO_CARRIER = 1.35
HASHED_PERPENDICULAR_TOLERANCE_DEGREES = 25.0
DEFAULT_INPUT_GLOB = "output_smoke/archive_matrix_previews/generated/*.svg"
DEFAULT_JSON_REPORT = "output_smoke/glyph_bond_alignment_report.json"
DEFAULT_TEXT_REPORT = "output_smoke/glyph_bond_alignment_report.txt"


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments for alignment analysis."""
	parser = argparse.ArgumentParser(
		description="Measure bond endpoint alignment against glyph attach targets from existing SVG files.",
	)
	parser.add_argument(
		"-i",
		"--input-glob",
		dest="input_glob",
		type=str,
		default=DEFAULT_INPUT_GLOB,
		help="Glob pattern for SVG files to analyze.",
	)
	parser.add_argument(
		"-j",
		"--json-report",
		dest="json_report",
		type=str,
		default=DEFAULT_JSON_REPORT,
		help="Output path for JSON report.",
	)
	parser.add_argument(
		"-t",
		"--text-report",
		dest="text_report",
		type=str,
		default=DEFAULT_TEXT_REPORT,
		help="Output path for text summary report.",
	)
	parser.add_argument(
		"-f",
		"--fail-on-miss",
		dest="fail_on_miss",
		action="store_true",
		help="Exit non-zero when any label has no connector or misses attach target.",
	)
	parser.add_argument(
		"-p",
		"--pass-on-miss",
		dest="fail_on_miss",
		action="store_false",
		help="Always exit zero, even when misses are detected.",
	)
	parser.add_argument(
		"--exclude-haworth-base-ring",
		dest="exclude_haworth_base_ring",
		action="store_true",
		help="Exclude detected Haworth base-ring template geometry from checks (default: on).",
	)
	parser.add_argument(
		"--include-haworth-base-ring",
		dest="exclude_haworth_base_ring",
		action="store_false",
		help="Include detected Haworth base-ring template geometry in checks.",
	)
	parser.add_argument(
		"--bond-glyph-gap-tolerance",
		dest="bond_glyph_gap_tolerance",
		type=float,
		default=BOND_GLYPH_GAP_TOLERANCE,
		help=(
			"Additional gap tolerance for bond/glyph proximity diagnostics; "
			"larger values flag near-miss crowding as violations."
		),
	)
	parser.set_defaults(fail_on_miss=False)
	parser.set_defaults(exclude_haworth_base_ring=True)
	return parser.parse_args()


#============================================
def get_repo_root() -> pathlib.Path:
	"""Return repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		raise RuntimeError("Could not detect repo root via git rev-parse --show-toplevel")
	return pathlib.Path(result.stdout.strip())


#============================================
def _load_render_geometry(repo_root: pathlib.Path):
	"""Import shared render geometry module used for attach-target definitions."""
	try:
		import oasa.render_geometry as render_geometry
	except ImportError:
		oasa_path = repo_root / "packages" / "oasa"
		if str(oasa_path) not in sys.path:
			sys.path.insert(0, str(oasa_path))
		import oasa.render_geometry as render_geometry
	return render_geometry


#============================================
def _local_tag_name(tag: str) -> str:
	"""Return local XML tag name without namespace prefix."""
	if "}" in tag:
		return tag.rsplit("}", 1)[-1]
	return tag


#============================================
def _parse_float(raw_value: str | None, default_value: float) -> float:
	"""Parse one SVG numeric attribute with a default fallback."""
	if raw_value is None:
		return float(default_value)
	try:
		return float(str(raw_value).strip())
	except ValueError:
		return float(default_value)


#============================================
def _visible_text(text_node) -> str:
	"""Return SVG text content with whitespace removed."""
	text_value = "".join(str(part) for part in text_node.itertext())
	return re.sub(r"\s+", "", text_value or "")


#============================================
def _line_length(line: dict) -> float:
	"""Return Euclidean length for one line primitive."""
	return math.hypot(line["x2"] - line["x1"], line["y2"] - line["y1"])


#============================================
def _length_stats(lengths: list[float]) -> dict:
	"""Return descriptive statistics for one list of line lengths."""
	if not lengths:
		return {
			"count": 0,
			"min": 0.0,
			"max": 0.0,
			"mean": 0.0,
			"stddev": 0.0,
			"coefficient_of_variation": 0.0,
		}
	count = len(lengths)
	mean_value = sum(lengths) / float(count)
	variance = sum((value - mean_value) ** 2 for value in lengths) / float(count)
	stddev = math.sqrt(variance)
	coefficient = 0.0
	if mean_value > 0.0:
		coefficient = stddev / mean_value
	return {
		"count": count,
		"min": min(lengths),
		"max": max(lengths),
		"mean": mean_value,
		"stddev": stddev,
		"coefficient_of_variation": coefficient,
	}


#============================================
def _group_length_append(groups: dict[str, list[float]], key: str, value: float) -> None:
	"""Append one length into one grouped-length dictionary key."""
	if key not in groups:
		groups[key] = []
	groups[key].append(float(value))


#============================================
def _rounded_sorted_values(lengths: list[float], decimals: int = LENGTH_ROUND_DECIMALS) -> list[float]:
	"""Return sorted rounded length values (individual values retained)."""
	return sorted(round(float(value), decimals) for value in lengths)


#============================================
def _rounded_value_counts(lengths: list[float], decimals: int = LENGTH_ROUND_DECIMALS) -> list[dict]:
	"""Return sorted frequency table for rounded length values."""
	counts: dict[float, int] = {}
	for value in lengths:
		rounded = round(float(value), decimals)
		counts[rounded] = int(counts.get(rounded, 0)) + 1
	return [
		{
			"length": key,
			"count": counts[key],
		}
		for key in sorted(counts.keys())
	]


#============================================
def _point_to_box_distance(point: tuple[float, float], box: tuple[float, float, float, float]) -> float:
	"""Return Euclidean distance from one point to one axis-aligned box."""
	x1, y1, x2, y2 = box
	px, py = point
	dx = 0.0
	dy = 0.0
	if px < x1:
		dx = x1 - px
	elif px > x2:
		dx = px - x2
	if py < y1:
		dy = y1 - py
	elif py > y2:
		dy = py - y2
	return math.hypot(dx, dy)


#============================================
def _point_in_target_closed(
		point: tuple[float, float],
		target,
		tol: float = 1e-6) -> bool:
	"""Return True when one point is inside one attach target."""
	if target.kind == "box":
		x1, y1, x2, y2 = target.box
		return (x1 - tol) <= point[0] <= (x2 + tol) and (y1 - tol) <= point[1] <= (y2 + tol)
	if target.kind == "circle":
		cx, cy = target.center
		distance = math.hypot(point[0] - cx, point[1] - cy)
		return distance <= (float(target.radius) + tol)
	if target.kind == "composite":
		for child in target.targets or ():
			if _point_in_target_closed(point, child, tol=tol):
				return True
		return False
	if target.kind == "segment":
		return False
	raise ValueError(f"Unsupported attach target kind: {target.kind!r}")


#============================================
def _point_to_target_distance(point: tuple[float, float], target) -> float:
	"""Return minimal point distance to one attach target."""
	if target.kind == "box":
		return _point_to_box_distance(point, target.box)
	if target.kind == "circle":
		cx, cy = target.center
		distance = math.hypot(point[0] - cx, point[1] - cy)
		return max(0.0, distance - float(target.radius))
	if target.kind == "composite":
		distances = [_point_to_target_distance(point, child) for child in (target.targets or ())]
		if not distances:
			return float("inf")
		return min(distances)
	if target.kind == "segment":
		x1, y1 = target.p1
		x2, y2 = target.p2
		dx = x2 - x1
		dy = y2 - y1
		segment_len2 = (dx * dx) + (dy * dy)
		if segment_len2 <= 0.0:
			return math.hypot(point[0] - x1, point[1] - y1)
		t = ((point[0] - x1) * dx + (point[1] - y1) * dy) / segment_len2
		t = max(0.0, min(1.0, t))
		closest = (x1 + (t * dx), y1 + (t * dy))
		return math.hypot(point[0] - closest[0], point[1] - closest[1])
	raise ValueError(f"Unsupported attach target kind: {target.kind!r}")


#============================================
def _point_to_target_signed_distance(point: tuple[float, float], target) -> float:
	"""Return signed point distance to one target (negative means inside)."""
	if target.kind == "box":
		x1, y1, x2, y2 = target.box
		if x1 <= point[0] <= x2 and y1 <= point[1] <= y2:
			inside_depth = min(
				point[0] - x1,
				x2 - point[0],
				point[1] - y1,
				y2 - point[1],
			)
			return -max(0.0, inside_depth)
		return _point_to_box_distance(point, target.box)
	if target.kind == "circle":
		cx, cy = target.center
		return math.hypot(point[0] - cx, point[1] - cy) - float(target.radius)
	if target.kind == "composite":
		values = [_point_to_target_signed_distance(point, child) for child in (target.targets or ())]
		if not values:
			return float("inf")
		if any(value <= 0.0 for value in values):
			return min(values)
		return min(values)
	if target.kind == "segment":
		x1, y1 = target.p1
		x2, y2 = target.p2
		dx = x2 - x1
		dy = y2 - y1
		segment_len2 = (dx * dx) + (dy * dy)
		if segment_len2 <= 0.0:
			return math.hypot(point[0] - x1, point[1] - y1)
		t = ((point[0] - x1) * dx + (point[1] - y1) * dy) / segment_len2
		t = max(0.0, min(1.0, t))
		closest = (x1 + (t * dx), y1 + (t * dy))
		return math.hypot(point[0] - closest[0], point[1] - closest[1])
	raise ValueError(f"Unsupported attach target kind: {target.kind!r}")


#============================================
def _is_measurement_label(visible_text: str) -> bool:
	"""Return True for labels expected to own a bond connector endpoint."""
	text = str(visible_text or "")
	if text in ("OH", "HO"):
		return True
	return "C" in text


#============================================
def _resolve_svg_paths(repo_root: pathlib.Path, input_glob: str) -> list[pathlib.Path]:
	"""Resolve sorted SVG paths from one glob pattern."""
	pattern = str(input_glob)
	if not pattern.startswith("/"):
		pattern = str(repo_root / pattern)
	paths = [pathlib.Path(raw).resolve() for raw in glob.glob(pattern, recursive=True)]
	return sorted(path for path in paths if path.is_file())


#============================================
def _line_closest_endpoint_to_box(line: dict, box: tuple[float, float, float, float]) -> tuple[tuple[float, float], float]:
	"""Return line endpoint and distance closest to one target box."""
	p1 = (line["x1"], line["y1"])
	p2 = (line["x2"], line["y2"])
	d1 = _point_to_box_distance(p1, box)
	d2 = _point_to_box_distance(p2, box)
	if d1 <= d2:
		return p1, d1
	return p2, d2


#============================================
def _line_closest_endpoint_to_target(line: dict, target) -> tuple[tuple[float, float], float, float]:
	"""Return nearest endpoint, nearest distance, and far-end distance for one target."""
	p1 = (line["x1"], line["y1"])
	p2 = (line["x2"], line["y2"])
	d1 = _point_to_target_distance(p1, target)
	d2 = _point_to_target_distance(p2, target)
	if d1 <= d2:
		return p1, d1, d2
	return p2, d2, d1


#============================================
def _collect_svg_lines(svg_root) -> list[dict]:
	"""Collect line primitives from one SVG root."""
	lines = []
	for node in svg_root.iter():
		if _local_tag_name(str(node.tag)) != "line":
			continue
		lines.append(
			{
				"x1": _parse_float(node.get("x1"), 0.0),
				"y1": _parse_float(node.get("y1"), 0.0),
				"x2": _parse_float(node.get("x2"), 0.0),
				"y2": _parse_float(node.get("y2"), 0.0),
				"width": _parse_float(node.get("stroke-width"), 1.0),
				"linecap": str(node.get("stroke-linecap") or "butt").strip().lower(),
			}
		)
	return lines


#============================================
def _collect_svg_labels(svg_root) -> list[dict]:
	"""Collect text labels from one SVG root with measurement eligibility tags."""
	labels = []
	for node in svg_root.iter():
		if _local_tag_name(str(node.tag)) != "text":
			continue
		visible_text = _visible_text(node)
		if not visible_text:
			continue
		labels.append(
			{
				"text": visible_text,
				"x": _parse_float(node.get("x"), 0.0),
				"y": _parse_float(node.get("y"), 0.0),
				"anchor": str(node.get("text-anchor") or "start"),
				"font_size": _parse_float(node.get("font-size"), 12.0),
				"font_name": str(node.get("font-family") or "sans-serif"),
				"is_measurement_label": _is_measurement_label(visible_text),
			}
		)
	return labels


#============================================
def _svg_number_tokens(text_value: str) -> list[float]:
	"""Return all float-like numeric tokens parsed from one SVG attribute string."""
	return [float(token) for token in SVG_FLOAT_PATTERN.findall(str(text_value or ""))]


#============================================
def _points_bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float] | None:
	"""Return bbox for a point list, or None when list is empty."""
	if not points:
		return None
	x_values = [point[0] for point in points]
	y_values = [point[1] for point in points]
	return (min(x_values), min(y_values), max(x_values), max(y_values))


#============================================
def _polygon_points(points_text: str) -> list[tuple[float, float]]:
	"""Parse SVG polygon points string into coordinate tuples."""
	points = []
	coordinates = _svg_number_tokens(points_text)
	for index in range(0, len(coordinates) - 1, 2):
		points.append((coordinates[index], coordinates[index + 1]))
	return points


#============================================
def _path_points(path_d: str) -> list[tuple[float, float]]:
	"""Parse SVG path coordinate numbers into point tuples (heuristic)."""
	coordinates = _svg_number_tokens(path_d)
	points = []
	for index in range(0, len(coordinates) - 1, 2):
		points.append((coordinates[index], coordinates[index + 1]))
	return points


#============================================
def _collect_svg_ring_primitives(svg_root) -> list[dict]:
	"""Collect filled polygon/path primitives usable for Haworth ring detection."""
	primitives = []
	for node in svg_root.iter():
		tag_name = _local_tag_name(str(node.tag))
		if tag_name not in ("polygon", "path"):
			continue
		fill_value = str(node.get("fill") or "").strip().lower()
		if fill_value in ("", "none", "transparent"):
			continue
		points: list[tuple[float, float]] = []
		if tag_name == "polygon":
			points = _polygon_points(str(node.get("points") or ""))
		elif tag_name == "path":
			points = _path_points(str(node.get("d") or ""))
		bbox = _points_bbox(points)
		if bbox is None:
			continue
		cx = (bbox[0] + bbox[2]) * 0.5
		cy = (bbox[1] + bbox[3]) * 0.5
		primitives.append(
			{
				"kind": tag_name,
				"bbox": bbox,
				"centroid": (cx, cy),
			}
		)
	return primitives


#============================================
def _line_angle_degrees(line: dict) -> float:
	"""Return one line direction angle in degrees in [0, 360)."""
	return math.degrees(math.atan2(line["y2"] - line["y1"], line["x2"] - line["x1"])) % 360.0


#============================================
def _nearest_lattice_angle_error(angle_degrees: float) -> float:
	"""Return minimum absolute error to canonical lattice angles."""
	return min(
		abs(((angle_degrees - lattice_angle + 180.0) % 360.0) - 180.0)
		for lattice_angle in CANONICAL_LATTICE_ANGLES
	)


#============================================
def _nearest_canonical_lattice_angle(angle_degrees: float) -> float:
	"""Return nearest canonical lattice angle for one measured angle."""
	return min(
		CANONICAL_LATTICE_ANGLES,
		key=lambda lattice_angle: abs(((angle_degrees - lattice_angle + 180.0) % 360.0) - 180.0),
	)


#============================================
def _normalize_box(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
	"""Return normalized (x1, y1, x2, y2) with ascending corners."""
	x1, y1, x2, y2 = box
	return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


#============================================
def _boxes_overlap_interior(
		box_a: tuple[float, float, float, float],
		box_b: tuple[float, float, float, float],
		epsilon: float = GLYPH_BOX_OVERLAP_EPSILON) -> bool:
	"""Return True when two boxes overlap with non-trivial interior area."""
	ax1, ay1, ax2, ay2 = _normalize_box(box_a)
	bx1, by1, bx2, by2 = _normalize_box(box_b)
	overlap_x = min(ax2, bx2) - max(ax1, bx1)
	overlap_y = min(ay2, by2) - max(ay1, by1)
	return overlap_x > epsilon and overlap_y > epsilon


#============================================
def _point_distance_sq(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
	"""Return squared Euclidean distance between two points."""
	dx = point_a[0] - point_b[0]
	dy = point_a[1] - point_b[1]
	return (dx * dx) + (dy * dy)


#============================================
def _points_close(
		point_a: tuple[float, float],
		point_b: tuple[float, float],
		tol: float = 1.0) -> bool:
	"""Return True when two points are within one distance tolerance."""
	return _point_distance_sq(point_a, point_b) <= (tol * tol)


#============================================
def _point_to_segment_distance_sq(
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
def _orientation(
		p1: tuple[float, float],
		p2: tuple[float, float],
		p3: tuple[float, float]) -> int:
	"""Return orientation sign for one ordered point triplet."""
	value = ((p2[1] - p1[1]) * (p3[0] - p2[0])) - ((p2[0] - p1[0]) * (p3[1] - p2[1]))
	if abs(value) <= 1e-12:
		return 0
	return 1 if value > 0.0 else 2


#============================================
def _on_segment(
		p1: tuple[float, float],
		p2: tuple[float, float],
		query: tuple[float, float]) -> bool:
	"""Return True when query point lies on segment p1-p2."""
	return (
		min(p1[0], p2[0]) - 1e-12 <= query[0] <= max(p1[0], p2[0]) + 1e-12
		and min(p1[1], p2[1]) - 1e-12 <= query[1] <= max(p1[1], p2[1]) + 1e-12
	)


#============================================
def _segments_intersect(
		p1: tuple[float, float],
		p2: tuple[float, float],
		q1: tuple[float, float],
		q2: tuple[float, float]) -> bool:
	"""Return True when two finite segments intersect."""
	o1 = _orientation(p1, p2, q1)
	o2 = _orientation(p1, p2, q2)
	o3 = _orientation(q1, q2, p1)
	o4 = _orientation(q1, q2, p2)
	if o1 != o2 and o3 != o4:
		return True
	if o1 == 0 and _on_segment(p1, p2, q1):
		return True
	if o2 == 0 and _on_segment(p1, p2, q2):
		return True
	if o3 == 0 and _on_segment(q1, q2, p1):
		return True
	if o4 == 0 and _on_segment(q1, q2, p2):
		return True
	return False


#============================================
def _distance_sq_segment_to_segment(
		p1: tuple[float, float],
		p2: tuple[float, float],
		q1: tuple[float, float],
		q2: tuple[float, float]) -> float:
	"""Return squared minimum distance between two finite segments."""
	if _segments_intersect(p1, p2, q1, q2):
		return 0.0
	return min(
		_point_to_segment_distance_sq(p1, q1, q2),
		_point_to_segment_distance_sq(p2, q1, q2),
		_point_to_segment_distance_sq(q1, p1, p2),
		_point_to_segment_distance_sq(q2, p1, p2),
	)


#============================================
def _segment_distance_to_box_sq(
		seg_start: tuple[float, float],
		seg_end: tuple[float, float],
		box: tuple[float, float, float, float]) -> float:
	"""Return squared minimum distance from one segment to one box."""
	x1, y1, x2, y2 = _normalize_box(box)
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
		if _segments_intersect(seg_start, seg_end, edge_start, edge_end):
			return 0.0
	distances = [
		_distance_sq_segment_to_segment(seg_start, seg_end, edge_start, edge_end)
		for edge_start, edge_end in edges
	]
	return min(distances)


#============================================
def _line_intersects_box_interior(
		line: dict,
		box: tuple[float, float, float, float],
		epsilon: float = BOND_GLYPH_INTERIOR_EPSILON) -> bool:
	"""Return True when one stroked line penetrates one box interior."""
	x1, y1, x2, y2 = _normalize_box(box)
	inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
	if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
		return False
	seg_start = (line["x1"], line["y1"])
	seg_end = (line["x2"], line["y2"])
	half_width = max(0.35, float(line.get("width", 1.0)) * 0.5)
	distance_sq = _segment_distance_to_box_sq(seg_start, seg_end, inner_box)
	return distance_sq < (half_width * half_width)


#============================================
def _line_endpoints(line: dict) -> tuple[tuple[float, float], tuple[float, float]]:
	"""Return line endpoints as two point tuples."""
	return ((line["x1"], line["y1"]), (line["x2"], line["y2"]))


#============================================
def _lines_share_endpoint(line_a: dict, line_b: dict, tol: float = 0.75) -> bool:
	"""Return True when two lines share one endpoint within tolerance."""
	a1, a2 = _line_endpoints(line_a)
	b1, b2 = _line_endpoints(line_b)
	return (
		_points_close(a1, b1, tol=tol)
		or _points_close(a1, b2, tol=tol)
		or _points_close(a2, b1, tol=tol)
		or _points_close(a2, b2, tol=tol)
	)


#============================================
def _parallel_error_degrees(angle_a: float, angle_b: float) -> float:
	"""Return smallest parallel-or-antiparallel angular difference."""
	diff = abs(((angle_a - angle_b + 180.0) % 360.0) - 180.0)
	return min(diff, abs(diff - 180.0))


#============================================
def _angle_difference_degrees(angle_a: float, angle_b: float) -> float:
	"""Return smallest absolute angle difference in [0, 180]."""
	return abs(((angle_a - angle_b + 180.0) % 360.0) - 180.0)


#============================================
def _lines_nearly_parallel(line_a: dict, line_b: dict, tol_deg: float = 6.0) -> bool:
	"""Return True when two lines are nearly parallel or anti-parallel."""
	angle_a = _line_angle_degrees(line_a)
	angle_b = _line_angle_degrees(line_b)
	return _parallel_error_degrees(angle_a, angle_b) <= tol_deg


#============================================
def _line_collinear_overlap_length(line_a: dict, line_b: dict, tol: float = 1e-6) -> float:
	"""Return collinear overlap length between two segments, or 0 when none."""
	p1, p2 = _line_endpoints(line_a)
	q1, q2 = _line_endpoints(line_b)
	if _orientation(p1, p2, q1) != 0 or _orientation(p1, p2, q2) != 0:
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
def _line_midpoint(line: dict) -> tuple[float, float]:
	"""Return midpoint of one line segment."""
	return (
		(line["x1"] + line["x2"]) * 0.5,
		(line["y1"] + line["y2"]) * 0.5,
	)


#============================================
def _is_hatch_stroke_candidate(line: dict) -> bool:
	"""Return True when one line looks like one short hashed-stroke primitive."""
	linecap = str(line.get("linecap") or "").strip().lower()
	if linecap != "butt":
		return False
	width = float(line.get("width", 1.0))
	length = _line_length(line)
	return (
		HATCH_STROKE_MIN_WIDTH <= width <= HATCH_STROKE_MAX_WIDTH
		and HATCH_STROKE_MIN_LENGTH <= length <= HATCH_STROKE_MAX_LENGTH
	)


#============================================
def _is_hashed_carrier_candidate(line: dict) -> bool:
	"""Return True when one line looks like one hashed-bond carrier line."""
	width = float(line.get("width", 1.0))
	length = _line_length(line)
	return width <= HASHED_CARRIER_MAX_WIDTH and length >= HASHED_CARRIER_MIN_LENGTH


#============================================
def _detect_hashed_carrier_map(lines: list[dict], checked_line_indexes: list[int]) -> dict[int, list[int]]:
	"""Return carrier->stroke-index map for hashed bonds inferred from line primitives."""
	stroke_indexes = [
		index for index in checked_line_indexes
		if 0 <= index < len(lines) and _is_hatch_stroke_candidate(lines[index])
	]
	carrier_map: dict[int, list[int]] = {}
	for carrier_index in checked_line_indexes:
		if carrier_index < 0 or carrier_index >= len(lines):
			continue
		carrier_line = lines[carrier_index]
		if not _is_hashed_carrier_candidate(carrier_line):
			continue
		carrier_start, carrier_end = _line_endpoints(carrier_line)
		carrier_angle = _line_angle_degrees(carrier_line)
		supporting_strokes = []
		for stroke_index in stroke_indexes:
			if stroke_index == carrier_index:
				continue
			stroke_line = lines[stroke_index]
			stroke_midpoint = _line_midpoint(stroke_line)
			distance = math.sqrt(
				_point_to_segment_distance_sq(stroke_midpoint, carrier_start, carrier_end)
			)
			if distance > HASHED_STROKE_MAX_DISTANCE_TO_CARRIER:
				continue
			stroke_angle = _line_angle_degrees(stroke_line)
			angle_diff = _angle_difference_degrees(carrier_angle, stroke_angle)
			perpendicular_error = abs(angle_diff - 90.0)
			if perpendicular_error > HASHED_PERPENDICULAR_TOLERANCE_DEGREES:
				continue
			if not _segments_intersect(carrier_start, carrier_end, *(_line_endpoints(stroke_line))):
				continue
			supporting_strokes.append(stroke_index)
		if len(supporting_strokes) < HASHED_CARRIER_MIN_STROKES:
			continue
		carrier_map[carrier_index] = sorted(set(supporting_strokes))
	return carrier_map


#============================================
def _line_overlap_midpoint(line_a: dict, line_b: dict) -> tuple[float, float] | None:
	"""Return representative midpoint of collinear overlap segment, if any."""
	p1, p2 = _line_endpoints(line_a)
	q1, q2 = _line_endpoints(line_b)
	if _orientation(p1, p2, q1) != 0 or _orientation(p1, p2, q2) != 0:
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
def _line_intersection_point(
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
	if _on_segment(p1, p2, intersection) and _on_segment(q1, q2, intersection):
		return intersection
	return None


#============================================
def _default_overlap_origin(lines: list[dict]) -> tuple[float, float]:
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
def _overlap_origin(lines: list[dict], haworth_base_ring: dict) -> tuple[float, float]:
	"""Return classification origin using Haworth centroid when available."""
	centroid = haworth_base_ring.get("centroid")
	if centroid is not None and len(centroid) == 2:
		return (float(centroid[0]), float(centroid[1]))
	return _default_overlap_origin(lines)


#============================================
def _quadrant_label(point: tuple[float, float], origin: tuple[float, float], tol: float = 0.6) -> str:
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
def _ring_region_label(point: tuple[float, float], haworth_base_ring: dict) -> str:
	"""Return inside/outside classification relative to detected Haworth base ring."""
	if not haworth_base_ring.get("detected"):
		return "unknown"
	centroid = haworth_base_ring.get("centroid")
	radius = float(haworth_base_ring.get("radius", 0.0))
	if centroid is None or len(centroid) != 2 or radius <= 0.0:
		return "unknown"
	distance = math.hypot(point[0] - float(centroid[0]), point[1] - float(centroid[1]))
	return "inside_base_ring" if distance <= (radius * 1.15) else "outside_base_ring"


#============================================
def _increment_counter(counter: dict[str, int], key: str) -> None:
	"""Increment one dictionary counter key."""
	counter[key] = int(counter.get(key, 0)) + 1


#============================================
def _target_bounds(target):
	"""Return bounding box for one attach target, or None when unsupported."""
	if target.kind == "box":
		return _normalize_box(target.box)
	if target.kind == "circle":
		cx, cy = target.center
		radius = max(0.0, float(target.radius))
		return (cx - radius, cy - radius, cx + radius, cy + radius)
	if target.kind == "composite":
		boxes = []
		for child in target.targets or ():
			child_box = _target_bounds(child)
			if child_box is None:
				continue
			boxes.append(child_box)
		if not boxes:
			return None
		return (
			min(box[0] for box in boxes),
			min(box[1] for box in boxes),
			max(box[2] for box in boxes),
			max(box[3] for box in boxes),
		)
	if target.kind == "segment":
		x1, y1 = target.p1
		x2, y2 = target.p2
		return _normalize_box((x1, y1, x2, y2))
	return None


#============================================
def _label_box(render_geometry, label: dict):
	"""Return one label bounding box from one label full-target object."""
	target = label.get("full_target")
	if target is None:
		target = render_geometry.label_target_from_text_origin(
			text_x=label["x"],
			text_y=label["y"],
			text=label["text"],
			anchor=label["anchor"],
			font_size=label["font_size"],
			font_name=label["font_name"],
		)
	return _target_bounds(target)


#============================================
def _label_full_target(render_geometry, label: dict):
	"""Return one label full target using shared runtime geometry APIs."""
	return render_geometry.label_target_from_text_origin(
		text_x=label["x"],
		text_y=label["y"],
		text=label["text"],
		anchor=label["anchor"],
		font_size=label["font_size"],
		font_name=label["font_name"],
	)


#============================================
def _canonical_cycle_key(node_indexes: list[int]) -> tuple[int, ...]:
	"""Return rotation- and direction-invariant tuple for one cycle."""
	sequence = tuple(node_indexes)
	reverse_sequence = tuple(reversed(node_indexes))
	candidates = []
	for sequence_variant in (sequence, reverse_sequence):
		for start in range(len(sequence_variant)):
			candidate = sequence_variant[start:] + sequence_variant[:start]
			candidates.append(candidate)
	return min(candidates)


#============================================
def _cycle_node_pairs(node_cycle: tuple[int, ...]) -> list[tuple[int, int]]:
	"""Return normalized node-pairs for one closed cycle."""
	pairs = []
	for index, node_value in enumerate(node_cycle):
		next_node = node_cycle[(index + 1) % len(node_cycle)]
		pairs.append((min(node_value, next_node), max(node_value, next_node)))
	return pairs


#============================================
def _clustered_endpoint_graph(
		lines: list[dict],
		line_indexes: list[int],
		merge_tol: float = 1.5):
	"""Build clustered endpoint graph for a subset of line indexes."""
	nodes: list[tuple[float, float]] = []
	line_to_nodes: dict[int, tuple[int, int]] = {}
	adjacency: dict[int, set[int]] = {}
	edge_to_lines: dict[tuple[int, int], list[int]] = {}
	for line_index in line_indexes:
		line = lines[line_index]
		p1, p2 = _line_endpoints(line)
		node_indexes = []
		for point in (p1, p2):
			matched_node = None
			for node_index, node_point in enumerate(nodes):
				if _points_close(point, node_point, tol=merge_tol):
					matched_node = node_index
					break
			if matched_node is None:
				nodes.append(point)
				matched_node = len(nodes) - 1
			node_indexes.append(matched_node)
		n1, n2 = node_indexes
		if n1 == n2:
			continue
		line_to_nodes[line_index] = (n1, n2)
		adjacency.setdefault(n1, set()).add(n2)
		adjacency.setdefault(n2, set()).add(n1)
		key = (min(n1, n2), max(n1, n2))
		edge_to_lines.setdefault(key, []).append(line_index)
	return nodes, line_to_nodes, adjacency, edge_to_lines


#============================================
def _find_candidate_cycles(adjacency: dict[int, set[int]], min_size: int = 5, max_size: int = 6) -> list[tuple[int, ...]]:
	"""Find simple cycles of allowed sizes in one undirected adjacency graph."""
	cycles: set[tuple[int, ...]] = set()
	for start in sorted(adjacency.keys()):
		stack = [(start, [start])]
		while stack:
			node_value, path = stack.pop()
			if len(path) > max_size:
				continue
			for neighbor in adjacency.get(node_value, set()):
				if neighbor == start and min_size <= len(path) <= max_size:
					cycle = _canonical_cycle_key(path[:])
					cycles.add(cycle)
					continue
				if neighbor in path:
					continue
				if len(path) >= max_size:
					continue
				stack.append((neighbor, path + [neighbor]))
	return sorted(cycles)


#============================================
def _empty_haworth_ring_detection() -> dict:
	"""Return default no-detection payload for Haworth base ring analysis."""
	return {
		"detected": False,
		"line_indexes": [],
		"primitive_indexes": [],
		"node_count": 0,
		"centroid": None,
		"radius": 0.0,
		"score": None,
		"source": None,
	}


#============================================
def _detect_haworth_ring_from_line_cycles(lines: list[dict], labels: list[dict]) -> dict:
	"""Detect Haworth-like base ring cycle from line geometry."""
	line_indexes = list(range(len(lines)))
	if len(line_indexes) < HAWORTH_RING_MIN_PRIMITIVES:
		return _empty_haworth_ring_detection()
	nodes, _, adjacency, edge_to_lines = _clustered_endpoint_graph(lines, line_indexes, merge_tol=1.5)
	cycles = _find_candidate_cycles(adjacency, min_size=5, max_size=6)
	best = None
	for cycle in cycles:
		node_pairs = _cycle_node_pairs(cycle)
		cycle_line_indexes = []
		for pair in node_pairs:
			line_options = edge_to_lines.get(pair, [])
			if not line_options:
				cycle_line_indexes = []
				break
			cycle_line_indexes.append(line_options[0])
		if len(cycle_line_indexes) < HAWORTH_RING_MIN_PRIMITIVES:
			continue
		node_points = [nodes[node_index] for node_index in cycle]
		centroid_x = sum(point[0] for point in node_points) / float(len(node_points))
		centroid_y = sum(point[1] for point in node_points) / float(len(node_points))
		centroid = (centroid_x, centroid_y)
		radii = [math.hypot(point[0] - centroid_x, point[1] - centroid_y) for point in node_points]
		radius_stats = _length_stats(radii)
		if radius_stats["mean"] <= 4.0 or radius_stats["mean"] > HAWORTH_RING_SEARCH_RADIUS:
			continue
		if radius_stats["coefficient_of_variation"] > 0.55:
			continue
		cycle_lengths = [_line_length(lines[line_index]) for line_index in cycle_line_indexes]
		length_stats = _length_stats(cycle_lengths)
		if length_stats["mean"] <= 2.0 or length_stats["coefficient_of_variation"] > 0.7:
			continue
		has_oxygen = False
		for label in labels:
			if str(label["text"]).upper() != "O":
				continue
			distance = math.hypot(label["x"] - centroid_x, label["y"] - centroid_y)
			if distance <= (radius_stats["mean"] * 1.8):
				has_oxygen = True
				break
		score = (
			radius_stats["coefficient_of_variation"]
			+ length_stats["coefficient_of_variation"]
			+ abs(len(cycle) - 6) * 0.15
		)
		if has_oxygen:
			score -= 0.15
		candidate = {
			"detected": True,
			"line_indexes": sorted(set(cycle_line_indexes)),
			"primitive_indexes": [],
			"node_count": len(cycle),
			"centroid": [centroid_x, centroid_y],
			"radius": radius_stats["mean"],
			"score": score,
			"source": "line_cycle",
		}
		if best is None or candidate["score"] < best["score"]:
			best = candidate
	if best is not None:
		return best
	return _empty_haworth_ring_detection()


#============================================
def _detect_haworth_ring_from_primitives(primitives: list[dict], labels: list[dict]) -> dict:
	"""Detect Haworth-like base ring from filled polygon/path primitive clusters."""
	if len(primitives) < HAWORTH_RING_MIN_PRIMITIVES:
		return _empty_haworth_ring_detection()
	best_candidate = None
	for index, primitive in enumerate(primitives):
		center_x, center_y = primitive["centroid"]
		members = []
		for other_index, other in enumerate(primitives):
			ox, oy = other["centroid"]
			if math.hypot(ox - center_x, oy - center_y) <= HAWORTH_RING_SEARCH_RADIUS:
				members.append(other_index)
		if len(members) < HAWORTH_RING_MIN_PRIMITIVES:
			continue
		member_centers = [primitives[member]["centroid"] for member in members]
		candidate_center_x = sum(point[0] for point in member_centers) / float(len(member_centers))
		candidate_center_y = sum(point[1] for point in member_centers) / float(len(member_centers))
		radii = [
			math.hypot(point[0] - candidate_center_x, point[1] - candidate_center_y)
			for point in member_centers
		]
		radius_stats = _length_stats(radii)
		if radius_stats["mean"] <= 2.0 or radius_stats["mean"] > HAWORTH_RING_SEARCH_RADIUS:
			continue
		if radius_stats["coefficient_of_variation"] > 0.8:
			continue
		oxygen_bonus = 0.0
		for label in labels:
			if str(label["text"]).upper() != "O":
				continue
			distance = math.hypot(label["x"] - candidate_center_x, label["y"] - candidate_center_y)
			if distance <= (radius_stats["mean"] * 2.2):
				oxygen_bonus = 0.15
				break
		score = radius_stats["coefficient_of_variation"] - oxygen_bonus - (0.02 * len(members))
		candidate = {
			"detected": True,
			"line_indexes": [],
			"primitive_indexes": sorted(set(members)),
			"node_count": len(members),
			"centroid": [candidate_center_x, candidate_center_y],
			"radius": radius_stats["mean"],
			"score": score,
			"source": "filled_primitive_cluster",
		}
		if best_candidate is None or candidate["score"] < best_candidate["score"]:
			best_candidate = candidate
	if best_candidate is not None:
		return best_candidate
	return _empty_haworth_ring_detection()


#============================================
def _detect_haworth_base_ring(lines: list[dict], labels: list[dict], ring_primitives: list[dict]) -> dict:
	"""Detect Haworth base ring using line-cycle and filled-primitive heuristics."""
	line_detection = _detect_haworth_ring_from_line_cycles(lines, labels)
	primitive_detection = _detect_haworth_ring_from_primitives(ring_primitives, labels)
	if not line_detection["detected"] and not primitive_detection["detected"]:
		return _empty_haworth_ring_detection()
	if line_detection["detected"] and not primitive_detection["detected"]:
		return line_detection
	if primitive_detection["detected"] and not line_detection["detected"]:
		return primitive_detection
	if primitive_detection["score"] <= line_detection["score"]:
		return primitive_detection
	return line_detection


#============================================
def _count_lattice_angle_violations(
		lines: list[dict],
		checked_line_indexes: list[int],
		haworth_base_ring: dict) -> tuple[int, list[dict]]:
	"""Count bond lines outside canonical lattice angles with location context."""
	violations = []
	origin = _overlap_origin(lines, haworth_base_ring)
	for line_index in checked_line_indexes:
		line = lines[line_index]
		line_length = _line_length(line)
		if line_length < MIN_BOND_LENGTH_FOR_ANGLE_CHECK:
			continue
		angle = _line_angle_degrees(line)
		nearest_angle = _nearest_canonical_lattice_angle(angle)
		error = _nearest_lattice_angle_error(angle)
		if error > LATTICE_ANGLE_TOLERANCE_DEGREES:
			midpoint = _line_midpoint(line)
			violations.append(
				{
					"line_index": line_index,
					"angle_degrees": angle,
					"nearest_canonical_angle_degrees": nearest_angle,
					"nearest_error_degrees": error,
					"length": line_length,
					"angle_quadrant": _quadrant_label(midpoint, origin=origin),
					"angle_ring_region": _ring_region_label(midpoint, haworth_base_ring=haworth_base_ring),
					"measurement_point": [midpoint[0], midpoint[1]],
				}
			)
	return len(violations), violations


#============================================
def _count_glyph_glyph_overlaps(labels: list[dict], checked_label_indexes: list[int]) -> tuple[int, list[dict]]:
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
			if not _boxes_overlap_interior(box_a, box_b, epsilon=GLYPH_BOX_OVERLAP_EPSILON):
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
def _count_bond_bond_overlaps(
		lines: list[dict],
		checked_line_indexes: list[int],
		haworth_base_ring: dict) -> tuple[int, list[dict]]:
	"""Count bond-line overlaps and annotate overlap location metadata."""
	overlaps = []
	origin = _overlap_origin(lines, haworth_base_ring)
	for index, line_index in enumerate(checked_line_indexes):
		line_a = lines[line_index]
		p1, p2 = _line_endpoints(line_a)
		for other_line_index in checked_line_indexes[index + 1:]:
			line_b = lines[other_line_index]
			q1, q2 = _line_endpoints(line_b)
			if not _segments_intersect(p1, p2, q1, q2):
				continue
			share_endpoint = _lines_share_endpoint(line_a, line_b, tol=0.75)
			if share_endpoint:
				# Common chemical topology joins at a shared endpoint should not count
				# as overlaps unless segments actually overlap along a non-trivial span.
				overlap_length = _line_collinear_overlap_length(line_a, line_b)
				if overlap_length <= 0.75:
					continue
			if _lines_nearly_parallel(line_a, line_b):
				overlap_length = _line_collinear_overlap_length(line_a, line_b)
				if overlap_length <= 0.75:
					continue
			overlap_point = _line_intersection_point(p1, p2, q1, q2)
			if overlap_point is None:
				overlap_point = _line_overlap_midpoint(line_a, line_b)
			if overlap_point is None:
				midpoint_a = _line_midpoint(line_a)
				midpoint_b = _line_midpoint(line_b)
				overlap_point = (
					(midpoint_a[0] + midpoint_b[0]) * 0.5,
					(midpoint_a[1] + midpoint_b[1]) * 0.5,
				)
			overlap_quadrant = _quadrant_label(overlap_point, origin=origin)
			overlap_ring_region = _ring_region_label(overlap_point, haworth_base_ring=haworth_base_ring)
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
def _count_hatched_thin_conflicts(
		lines: list[dict],
		checked_line_indexes: list[int],
		haworth_base_ring: dict) -> tuple[int, list[dict], dict[int, list[int]]]:
	"""Count hashed-carrier overlaps with non-hatch lines for diagnosis."""
	conflicts = []
	carrier_map = _detect_hashed_carrier_map(lines=lines, checked_line_indexes=checked_line_indexes)
	if not carrier_map:
		return 0, conflicts, carrier_map
	origin = _overlap_origin(lines, haworth_base_ring)
	seen_line_pairs: set[tuple[int, int]] = set()
	for carrier_index in sorted(carrier_map.keys()):
		carrier_line = lines[carrier_index]
		carrier_start, carrier_end = _line_endpoints(carrier_line)
		cluster_indexes = set(carrier_map[carrier_index])
		cluster_indexes.add(carrier_index)
		for other_line_index in checked_line_indexes:
			if other_line_index in cluster_indexes:
				continue
			if other_line_index < 0 or other_line_index >= len(lines):
				continue
			other_line = lines[other_line_index]
			if _is_hatch_stroke_candidate(other_line):
				continue
			pair_key = (min(carrier_index, other_line_index), max(carrier_index, other_line_index))
			if pair_key in seen_line_pairs:
				continue
			other_start, other_end = _line_endpoints(other_line)
			if not _segments_intersect(carrier_start, carrier_end, other_start, other_end):
				continue
			share_endpoint = _lines_share_endpoint(carrier_line, other_line, tol=0.75)
			overlap_length = _line_collinear_overlap_length(carrier_line, other_line)
			if share_endpoint and overlap_length <= 0.75:
				continue
			conflict_type = "crossing_intersection"
			if _lines_nearly_parallel(carrier_line, other_line):
				if overlap_length <= 0.75:
					continue
				conflict_type = "collinear_overlap"
			seen_line_pairs.add(pair_key)
			overlap_point = _line_intersection_point(carrier_start, carrier_end, other_start, other_end)
			if overlap_point is None:
				overlap_point = _line_overlap_midpoint(carrier_line, other_line)
			if overlap_point is None:
				carrier_midpoint = _line_midpoint(carrier_line)
				other_midpoint = _line_midpoint(other_line)
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
					"overlap_quadrant": _quadrant_label(overlap_point, origin=origin),
					"overlap_ring_region": _ring_region_label(overlap_point, haworth_base_ring=haworth_base_ring),
				}
			)
	return len(conflicts), conflicts, carrier_map


#============================================
def _count_bond_glyph_overlaps(
		render_geometry,
		lines: list[dict],
		labels: list[dict],
		checked_line_indexes: list[int],
		checked_label_indexes: list[int],
		aligned_connector_pairs: set[tuple[int, int]],
		haworth_base_ring: dict,
		gap_tolerance: float) -> tuple[int, list[dict]]:
	"""Count bond-vs-glyph penetrations with attach-target legality checks."""
	overlaps = []
	origin = _overlap_origin(lines, haworth_base_ring)
	contract_cache: dict[tuple[int, float], object | None] = {}
	for line_index in checked_line_indexes:
		line = lines[line_index]
		line_start = (line["x1"], line["y1"])
		line_end = (line["x2"], line["y2"])
		line_width = max(0.0, float(line.get("width", 1.0)))
		for label_index in checked_label_indexes:
			label = labels[label_index]
			full_target = label.get("full_target")
			if full_target is None:
				full_target = _label_full_target(render_geometry, label)
				label["full_target"] = full_target
			label_box = label.get("box")
			if label_box is None:
				label_box = _target_bounds(full_target)
				label["box"] = label_box
			cache_key = (label_index, round(line_width, 3))
			if cache_key not in contract_cache:
				try:
					contract_cache[cache_key] = _label_attach_contract(
						render_geometry=render_geometry,
						label=label,
						line_width=line_width,
					)
				except Exception:
					contract_cache[cache_key] = None
			contract = contract_cache.get(cache_key)
			is_aligned_connector = (line_index, label_index) in aligned_connector_pairs
			allowed_regions = []
			if contract is not None and is_aligned_connector:
				# For diagnostics, allow only the strict endpoint target footprint,
				# not full broad allowed corridors, so near-glyph crowding is visible.
				allowed_regions = [contract.endpoint_target]
			is_legal = False
			try:
				is_legal = render_geometry.validate_attachment_paint(
					line_start=line_start,
					line_end=line_end,
					line_width=line_width,
					forbidden_regions=[full_target],
					allowed_regions=allowed_regions,
					epsilon=BOND_GLYPH_INTERIOR_EPSILON,
				)
			except Exception:
				if label_box is None:
					continue
				is_legal = not _line_intersects_box_interior(
					line,
					label_box,
					epsilon=BOND_GLYPH_INTERIOR_EPSILON,
				)
			overlap_classification = "interior_overlap"
			if is_legal:
				is_gap_legal = True
				try:
					is_gap_legal = render_geometry.validate_attachment_paint(
						line_start=line_start,
						line_end=line_end,
						line_width=line_width,
						forbidden_regions=[full_target],
						allowed_regions=allowed_regions,
						epsilon=-float(gap_tolerance),
					)
				except Exception:
					if label_box is not None:
						is_gap_legal = not _line_intersects_box_interior(
							line,
							label_box,
							epsilon=-float(gap_tolerance),
						)
				if is_gap_legal:
					continue
				overlap_classification = "gap_tolerance_violation"
			bond_end_point, _, _ = _line_closest_endpoint_to_target(
				line=line,
				target=full_target,
			)
			bond_end_signed_distance = _point_to_target_signed_distance(
				bond_end_point,
				full_target,
			)
			bond_end_overlap = bond_end_signed_distance <= 0.0
			bond_end_too_close = (bond_end_signed_distance > 0.0) and (
				bond_end_signed_distance <= float(gap_tolerance)
			)
			box_x1, box_y1, box_x2, box_y2 = _normalize_box(label_box)
			glyph_center = (
				(box_x1 + box_x2) * 0.5,
				(box_y1 + box_y2) * 0.5,
			)
			overlap_point = _line_midpoint(line)
			overlaps.append(
				{
					"line_index": line_index,
					"label_index": label_index,
					"label_text": label["text"],
					"glyph_center": [glyph_center[0], glyph_center[1]],
					"overlap_point": [overlap_point[0], overlap_point[1]],
					"overlap_quadrant": _quadrant_label(overlap_point, origin=origin),
					"overlap_ring_region": _ring_region_label(overlap_point, haworth_base_ring=haworth_base_ring),
					"aligned_connector_pair": bool(is_aligned_connector),
					"overlap_classification": overlap_classification,
					"gap_tolerance": float(gap_tolerance),
					"bond_end_point": [bond_end_point[0], bond_end_point[1]],
					"bond_end_to_glyph_distance": float(bond_end_signed_distance),
					"bond_end_distance_tolerance": float(gap_tolerance),
					"bond_end_overlap": bool(bond_end_overlap),
					"bond_end_too_close": bool(bond_end_too_close),
					"overlap_detection_mode": "target_paint_validation",
				}
			)
	return len(overlaps), overlaps


#============================================
def _label_attach_contract(render_geometry, label: dict, line_width: float):
	"""Resolve one deterministic runtime attach contract for one SVG label."""
	return render_geometry.label_attach_contract_from_text_origin(
		text_x=label["x"],
		text_y=label["y"],
		text=label["text"],
		anchor=label["anchor"],
		font_size=label["font_size"],
		line_width=max(0.0, float(line_width)),
		chain_attach_site="core_center",
		font_name=label["font_name"],
	)


#============================================
def analyze_svg_file(
		svg_path: pathlib.Path,
		render_geometry,
		exclude_haworth_base_ring: bool = True,
		bond_glyph_gap_tolerance: float = BOND_GLYPH_GAP_TOLERANCE) -> dict:
	"""Analyze one SVG file and return independent geometry and alignment metrics."""
	root = ET.parse(svg_path).getroot()
	lines = _collect_svg_lines(root)
	labels = _collect_svg_labels(root)
	ring_primitives = _collect_svg_ring_primitives(root)
	for label in labels:
		label["full_target"] = _label_full_target(render_geometry, label)
		label["box"] = _label_box(render_geometry, label)
	measurement_label_indexes = [
		index for index, label in enumerate(labels) if label["is_measurement_label"]
	]
	haworth_base_ring = _detect_haworth_base_ring(lines, labels, ring_primitives)
	excluded_line_indexes = set()
	if exclude_haworth_base_ring and haworth_base_ring["detected"]:
		excluded_line_indexes = set(haworth_base_ring["line_indexes"])
	checked_line_indexes = [
		index for index in range(len(lines)) if index not in excluded_line_indexes
	]
	checked_label_indexes = list(range(len(labels)))
	line_lengths_all = [_line_length(line) for line in lines]
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
		search_limit = max(6.0, float(label["font_size"]) * MAX_ENDPOINT_TO_LABEL_DISTANCE_FACTOR)
		best_endpoint = None
		best_distance = float("inf")
		best_far_distance = float("-inf")
		best_length = float("-inf")
		best_line_index = None
		best_line_width = 1.0
		best_contract = None
		for line_index in checked_line_indexes:
			line = lines[line_index]
			contract = _label_attach_contract(
				render_geometry=render_geometry,
				label=label,
				line_width=float(line.get("width", 1.0)),
			)
			endpoint, distance, far_distance = _line_closest_endpoint_to_target(
				line=line,
				target=contract.endpoint_target,
			)
			line_length = _line_length(line)
			if (
					distance < best_distance
					or (
						math.isclose(distance, best_distance, abs_tol=1e-9)
						and far_distance > best_far_distance
					)
					or (
						math.isclose(distance, best_distance, abs_tol=1e-9)
						and math.isclose(far_distance, best_far_distance, abs_tol=1e-9)
						and line_length > best_length
					)
			):
				best_endpoint = endpoint
				best_distance = distance
				best_far_distance = far_distance
				best_length = line_length
				best_line_index = line_index
				best_line_width = float(line.get("width", 1.0))
				best_contract = contract
		if best_endpoint is None or best_distance > search_limit:
			no_connector_count += 1
			label_metrics.append(
				{
					"label_index": label_index,
					"text": label["text"],
					"anchor": label["anchor"],
					"font_size": label["font_size"],
					"endpoint": None,
					"endpoint_distance_to_label": None,
					"endpoint_distance_to_target": None,
					"aligned": False,
					"reason": "no_nearby_connector",
					"connector_line_index": None,
					"attach_policy": None,
					"endpoint_target_kind": None,
				}
			)
			continue
		if best_line_index is not None:
			connector_line_indexes.add(best_line_index)
		contract = best_contract
		if contract is None:
			contract = _label_attach_contract(
				render_geometry=render_geometry,
				label=label,
				line_width=best_line_width,
			)
		endpoint_target = contract.endpoint_target
		target_distance = _point_to_target_distance(best_endpoint, endpoint_target)
		alignment_tolerance = max(MIN_ALIGNMENT_DISTANCE_TOLERANCE, best_line_width * 0.55)
		is_aligned = _point_in_target_closed(best_endpoint, endpoint_target)
		if not is_aligned and target_distance <= alignment_tolerance:
			is_aligned = True
		if is_aligned:
			aligned_count += 1
		else:
			missed_count += 1
		label_metrics.append(
			{
				"label_index": label_index,
				"text": label["text"],
				"anchor": label["anchor"],
				"font_size": label["font_size"],
				"endpoint": [best_endpoint[0], best_endpoint[1]],
				"endpoint_distance_to_label": best_distance,
				"endpoint_distance_to_target": target_distance,
				"alignment_tolerance": alignment_tolerance,
				"aligned": bool(is_aligned),
				"reason": "ok" if is_aligned else "endpoint_missed_target",
				"connector_line_index": best_line_index,
				"attach_policy": {
					"attach_atom": contract.policy.attach_atom,
					"attach_element": contract.policy.attach_element,
					"attach_site": contract.policy.attach_site,
					"target_kind": contract.policy.target_kind,
				},
				"endpoint_target_kind": endpoint_target.kind,
			}
		)
	aligned_connector_pairs = set()
	for metric in label_metrics:
		connector_index = metric.get("connector_line_index")
		label_index = metric.get("label_index")
		if connector_index is None or label_index is None:
			continue
		if metric.get("aligned"):
			aligned_connector_pairs.add((int(connector_index), int(label_index)))
	lattice_angle_violation_count, lattice_angle_violations = _count_lattice_angle_violations(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	glyph_glyph_overlap_count, glyph_glyph_overlaps = _count_glyph_glyph_overlaps(
		labels=labels,
		checked_label_indexes=checked_label_indexes,
	)
	bond_bond_overlap_count, bond_bond_overlaps = _count_bond_bond_overlaps(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	hatched_thin_conflict_count, hatched_thin_conflicts, hashed_carrier_map = _count_hatched_thin_conflicts(
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
	bond_glyph_overlap_count, bond_glyph_overlaps = _count_bond_glyph_overlaps(
		render_geometry=render_geometry,
		lines=lines,
		labels=labels,
		checked_line_indexes=checked_line_indexes,
		checked_label_indexes=checked_label_indexes,
		aligned_connector_pairs=aligned_connector_pairs,
		haworth_base_ring=haworth_base_ring,
		gap_tolerance=float(bond_glyph_gap_tolerance),
	)
	return {
		"svg": str(svg_path),
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
		"geometry_checks": {
			"canonical_angles_degrees": list(CANONICAL_LATTICE_ANGLES),
			"angle_tolerance_degrees": LATTICE_ANGLE_TOLERANCE_DEGREES,
			"bond_glyph_gap_tolerance": float(bond_glyph_gap_tolerance),
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
			"all_lines": _rounded_sorted_values(line_lengths_all),
			"checked_lines_raw": _rounded_sorted_values(line_lengths_checked_raw),
			"checked_lines": _rounded_sorted_values(line_lengths_checked),
			"connector_lines": _rounded_sorted_values(connector_line_lengths),
			"non_connector_lines": _rounded_sorted_values(non_connector_line_lengths),
			"excluded_haworth_base_ring_lines": _rounded_sorted_values(excluded_line_lengths),
			"decorative_hatched_stroke_lines": _rounded_sorted_values(decorative_hatched_stroke_lengths),
		},
		"line_length_rounded_counts": {
			"all_lines": _rounded_value_counts(line_lengths_all),
			"checked_lines_raw": _rounded_value_counts(line_lengths_checked_raw),
			"checked_lines": _rounded_value_counts(line_lengths_checked),
			"connector_lines": _rounded_value_counts(connector_line_lengths),
			"non_connector_lines": _rounded_value_counts(non_connector_line_lengths),
			"excluded_haworth_base_ring_lines": _rounded_value_counts(excluded_line_lengths),
			"decorative_hatched_stroke_lines": _rounded_value_counts(decorative_hatched_stroke_lengths),
		},
		"line_length_stats": {
			"all_lines": _length_stats(line_lengths_all),
			"checked_lines_raw": _length_stats(line_lengths_checked_raw),
			"checked_lines": _length_stats(line_lengths_checked),
			"connector_lines": _length_stats(connector_line_lengths),
			"non_connector_lines": _length_stats(non_connector_line_lengths),
			"excluded_haworth_base_ring_lines": _length_stats(excluded_line_lengths),
			"decorative_hatched_stroke_lines": _length_stats(decorative_hatched_stroke_lengths),
		},
	}


#============================================
def _summary_stats(file_reports: list[dict]) -> dict:
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
			_increment_counter(text_label_counts, str(label_text))
		geometry_checks = report.get("geometry_checks", {})
		gap_tolerance = str(geometry_checks.get("bond_glyph_gap_tolerance", BOND_GLYPH_GAP_TOLERANCE))
		_increment_counter(bond_glyph_gap_tolerances, gap_tolerance)
		for violation in geometry_checks.get("lattice_angle_violations", []):
			quadrant = str(violation.get("angle_quadrant", "unknown"))
			ring_region = str(violation.get("angle_ring_region", "unknown"))
			_increment_counter(lattice_angle_violation_quadrants, quadrant)
			_increment_counter(lattice_angle_violation_ring_regions, ring_region)
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
			_increment_counter(bond_bond_overlap_quadrants, quadrant)
			_increment_counter(bond_bond_overlap_ring_regions, ring_region)
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
			_increment_counter(hatched_thin_conflict_quadrants, quadrant)
			_increment_counter(hatched_thin_conflict_ring_regions, ring_region)
			_increment_counter(hatched_thin_conflict_types, conflict_type)
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
			_increment_counter(bond_glyph_overlap_quadrants, quadrant)
			_increment_counter(bond_glyph_overlap_ring_regions, ring_region)
			_increment_counter(bond_glyph_overlap_label_texts, label_text)
			_increment_counter(bond_glyph_overlap_classifications, classification)
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
	alignment_rate = 0.0
	if total_labels > 0:
		alignment_rate = aligned / float(total_labels)
	distances = []
	for report in file_reports:
		for label in report["labels"]:
			value = label["endpoint_distance_to_target"]
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
	all_length_stats = _length_stats(all_lengths)
	checked_length_stats = _length_stats(checked_lengths)
	connector_length_stats = _length_stats(connector_lengths)
	non_connector_length_stats = _length_stats(non_connector_lengths)
	excluded_length_stats = _length_stats(excluded_lengths)
	all_lengths_rounded_sorted = _rounded_sorted_values(all_lengths)
	checked_lengths_rounded_sorted = _rounded_sorted_values(checked_lengths)
	connector_lengths_rounded_sorted = _rounded_sorted_values(connector_lengths)
	non_connector_lengths_rounded_sorted = _rounded_sorted_values(non_connector_lengths)
	excluded_lengths_rounded_sorted = _rounded_sorted_values(excluded_lengths)
	bond_glyph_endpoint_signed_distance_stats = _length_stats(bond_glyph_endpoint_signed_distances)
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
		"bond_length_rounded_counts_all": _rounded_value_counts(all_lengths),
		"bond_length_rounded_counts_checked": _rounded_value_counts(checked_lengths),
		"bond_length_rounded_counts_connector": _rounded_value_counts(connector_lengths),
		"bond_length_rounded_counts_non_connector": _rounded_value_counts(non_connector_lengths),
		"bond_length_rounded_counts_excluded_haworth_base_ring": _rounded_value_counts(excluded_lengths),
		"bond_length_stats_checked": checked_length_stats,
		"bond_length_stats_connector": connector_length_stats,
		"bond_length_stats_non_connector": non_connector_length_stats,
		"bond_length_stats_excluded_haworth_base_ring": excluded_length_stats,
	}


#============================================
def _top_misses(file_reports: list[dict], limit: int = 20) -> list[dict]:
	"""Return highest-distance misses across all files."""
	entries = []
	for report in file_reports:
		for label in report["labels"]:
			if label["aligned"]:
				continue
			distance = label["endpoint_distance_to_target"]
			if distance is None:
				distance = float("inf")
			entries.append(
				{
					"svg": report["svg"],
					"text": label["text"],
					"reason": label["reason"],
					"distance": distance,
					"endpoint": label["endpoint"],
				}
			)
	entries.sort(key=lambda item: item["distance"], reverse=True)
	return entries[:limit]


#============================================
def _text_report(
		summary: dict,
		top_misses: list[dict],
		input_glob: str,
		exclude_haworth_base_ring: bool) -> str:
	"""Build human-readable report text."""
	lines = []
	lines.append("Glyph Bond Alignment Report")
	lines.append(f"Generated at: {datetime.datetime.now().isoformat(timespec='seconds')}")
	lines.append(f"Input glob: {input_glob}")
	lines.append(
		f"Exclude Haworth base ring: {'ON' if exclude_haworth_base_ring else 'OFF'}"
	)
	lines.append("")
	lines.append(f"Files analyzed: {summary['files_analyzed']}")
	lines.append(f"Text labels seen: {summary['text_labels_total']}")
	lines.append(f"Text labels unique: {summary['text_labels_unique_total']}")
	lines.append(f"Text labels list: {summary.get('text_labels_unique', [])}")
	lines.append(f"Total bonds detected: {summary['total_bonds_detected']}")
	lines.append(f"Total bonds checked: {summary['total_bonds_checked']}")
	lines.append(f"Labels analyzed: {summary['labels_analyzed']}")
	lines.append(f"Aligned labels: {summary['aligned_labels']}")
	lines.append(f"Missed labels: {summary['missed_labels']}")
	lines.append(f"Labels without nearby connector: {summary['labels_without_connector']}")
	lines.append(
		f"Alignment outside tolerance count: {summary['alignment_outside_tolerance_count']}"
	)
	lines.append(f"Alignment rate: {summary['alignment_rate'] * 100.0:.2f}%")
	lines.append(
		f"Mean endpoint distance to target: {summary['mean_endpoint_distance_to_target']:.3f}"
	)
	lines.append(
		f"Max endpoint distance to target: {summary['max_endpoint_distance_to_target']:.3f}"
	)
	lines.append("")
	lines.append("Standalone geometry checks:")
	lines.append(
		f"- canonical lattice angles: {summary['canonical_angles_degrees']} "
		f"(tolerance={summary['lattice_angle_tolerance_degrees']:.1f} deg)"
	)
	lines.append(
		f"- bonds outside canonical lattice angles: {summary['lattice_angle_violation_count']}"
	)
	lines.append(
		f"  lattice-violation quadrants: {summary.get('lattice_angle_violation_quadrants', {})}"
	)
	lines.append(
		"  lattice-violation ring regions: "
		f"{summary.get('lattice_angle_violation_ring_regions', {})}"
	)
	if summary.get("lattice_angle_violation_examples"):
		lines.append("  sample lattice-angle violations:")
		for item in summary["lattice_angle_violation_examples"][:6]:
			lines.append(
				"    "
				f"- {item.get('svg')} "
				f"line={item.get('line_index')} "
				f"angle={item.get('angle_degrees'):.3f} "
				f"nearest={item.get('nearest_canonical_angle_degrees'):.1f} "
				f"error={item.get('nearest_error_degrees'):.3f} "
				f"quadrant={item.get('quadrant')} region={item.get('ring_region')}"
			)
	lines.append(f"- glyph/glyph overlap count: {summary['glyph_glyph_overlap_count']}")
	lines.append(f"- bond/bond overlap count: {summary['bond_bond_overlap_count']}")
	lines.append(
		f"  bond/bond overlap quadrants: {summary.get('bond_bond_overlap_quadrants', {})}"
	)
	lines.append(
		f"  bond/bond overlap ring regions: {summary.get('bond_bond_overlap_ring_regions', {})}"
	)
	lines.append(
		"- hatched/thin line conflict count: "
		f"{summary.get('hatched_thin_conflict_count', 0)}"
	)
	lines.append(
		"  hatched/thin conflict types: "
		f"{summary.get('hatched_thin_conflict_types', {})}"
	)
	lines.append(
		"  hatched/thin conflict quadrants: "
		f"{summary.get('hatched_thin_conflict_quadrants', {})}"
	)
	lines.append(
		"  hatched/thin conflict ring regions: "
		f"{summary.get('hatched_thin_conflict_ring_regions', {})}"
	)
	lines.append(f"- bond/glyph overlap count: {summary['bond_glyph_overlap_count']}")
	single_gap_tolerance = None
	gap_tolerances = summary.get("bond_glyph_gap_tolerances", {})
	if len(gap_tolerances) == 1:
		single_gap_tolerance = next(iter(gap_tolerances.keys()))
	if single_gap_tolerance is not None:
		lines.append(f"  bond/glyph gap tolerance: {single_gap_tolerance}")
	else:
		lines.append(
			"  bond/glyph gap tolerance values: "
			f"{gap_tolerances}"
		)
	lines.append(
		"  bond/glyph endpoint overlap count (distance <= 0): "
		f"{summary.get('bond_glyph_endpoint_overlap_count', 0)}"
	)
	lines.append(
		"  bond/glyph endpoint too-close count "
		"(0 < distance <= tolerance): "
		f"{summary.get('bond_glyph_endpoint_too_close_count', 0)}"
	)
	lines.append(
		"  bond/glyph overlap classifications: "
		f"{summary.get('bond_glyph_overlap_classifications', {})}"
	)
	endpoint_stats = summary.get("bond_glyph_endpoint_signed_distance_stats", {})
	if endpoint_stats.get("count", 0) > 0:
		lines.append(
			"  bond/glyph endpoint distance stats "
			"(signed, negative=overlap): "
			f"count={endpoint_stats.get('count', 0)} "
			f"min={endpoint_stats.get('min', 0.0):.3f} "
			f"max={endpoint_stats.get('max', 0.0):.3f} "
			f"mean={endpoint_stats.get('mean', 0.0):.3f}"
		)
	lines.append(
		f"  bond/glyph overlap label text counts: {summary.get('bond_glyph_overlap_label_texts', {})}"
	)
	lines.append(
		f"  bond/glyph overlap quadrants: {summary.get('bond_glyph_overlap_quadrants', {})}"
	)
	lines.append(
		f"  bond/glyph overlap ring regions: {summary.get('bond_glyph_overlap_ring_regions', {})}"
	)
	lines.append(
		f"- Haworth base ring detected files: {summary['haworth_base_ring_detected_files']}"
	)
	lines.append(
		f"- Haworth base ring excluded files: {summary['haworth_base_ring_excluded_files']}"
	)
	lines.append(
		f"- Haworth base ring excluded line count: {summary['haworth_base_ring_excluded_line_count']}"
	)
	if summary.get("bond_bond_overlap_examples"):
		lines.append("  sample bond/bond overlaps:")
		for item in summary["bond_bond_overlap_examples"][:6]:
			lines.append(
				"    "
				f"- {item.get('svg')} "
				f"lines=({item.get('line_index_a')},{item.get('line_index_b')}) "
				f"quadrant={item.get('quadrant')} region={item.get('ring_region')} "
				f"point={item.get('overlap_point')}"
			)
	if summary.get("bond_glyph_overlap_examples"):
		lines.append("  sample bond/glyph overlaps:")
		for item in summary["bond_glyph_overlap_examples"][:6]:
			lines.append(
				"    "
				f"- {item.get('svg')} "
				f"line={item.get('line_index')} label={item.get('label_text')} "
				f"class={item.get('classification')} "
				f"quadrant={item.get('quadrant')} region={item.get('ring_region')} "
				f"bond_end_distance={item.get('bond_end_to_glyph_distance')} "
				f"tolerance={item.get('bond_end_distance_tolerance')} "
				f"overlap={item.get('bond_end_overlap')} "
				f"too_close={item.get('bond_end_too_close')} "
				f"point={item.get('overlap_point')}"
			)
	if summary.get("hatched_thin_conflict_examples"):
		lines.append("  sample hatched/thin conflicts:")
		for item in summary["hatched_thin_conflict_examples"][:6]:
			lines.append(
				"    "
				f"- {item.get('svg')} "
				f"carrier={item.get('carrier_line_index')} "
				f"other={item.get('other_line_index')} "
				f"type={item.get('type')} "
				f"strokes={item.get('carrier_hatch_stroke_count')} "
				f"quadrant={item.get('quadrant')} region={item.get('ring_region')} "
				f"point={item.get('overlap_point')}"
			)
	lines.append("")
	lines.append("Bond length stats (line segments from analyzed SVGs):")
	lines.append(
		"- decorative hashed hatch strokes excluded from checked bond lengths: "
		f"{summary.get('decorative_hatched_stroke_line_count', 0)}"
	)
	checked_identical_to_all = (
		summary.get("total_bonds_detected") == summary.get("total_bonds_checked")
		and summary.get("bond_lengths_rounded_sorted_all", [])
		== summary.get("bond_lengths_rounded_sorted_checked", [])
	)
	if checked_identical_to_all:
		lines.append("- checked lines are identical to all lines")
	else:
		lines.append(
			f"- all lines: count={summary['bond_length_stats_all']['count']} "
			f"min={summary['bond_length_stats_all']['min']:.3f} "
			f"max={summary['bond_length_stats_all']['max']:.3f} "
			f"mean={summary['bond_length_stats_all']['mean']:.3f} "
			f"stddev={summary['bond_length_stats_all']['stddev']:.3f} "
			f"cv={summary['bond_length_stats_all']['coefficient_of_variation']:.3f}"
		)
	lines.append(
		f"- checked lines: count={summary['bond_length_stats_checked']['count']} "
		f"min={summary['bond_length_stats_checked']['min']:.3f} "
		f"max={summary['bond_length_stats_checked']['max']:.3f} "
		f"mean={summary['bond_length_stats_checked']['mean']:.3f} "
		f"stddev={summary['bond_length_stats_checked']['stddev']:.3f} "
		f"cv={summary['bond_length_stats_checked']['coefficient_of_variation']:.3f}"
	)
	lines.append(
		f"- connector lines: count={summary['bond_length_stats_connector']['count']} "
		f"min={summary['bond_length_stats_connector']['min']:.3f} "
		f"max={summary['bond_length_stats_connector']['max']:.3f} "
		f"mean={summary['bond_length_stats_connector']['mean']:.3f} "
		f"stddev={summary['bond_length_stats_connector']['stddev']:.3f} "
		f"cv={summary['bond_length_stats_connector']['coefficient_of_variation']:.3f}"
	)
	lines.append(
		f"- non-connector lines: count={summary['bond_length_stats_non_connector']['count']} "
		f"min={summary['bond_length_stats_non_connector']['min']:.3f} "
		f"max={summary['bond_length_stats_non_connector']['max']:.3f} "
		f"mean={summary['bond_length_stats_non_connector']['mean']:.3f} "
		f"stddev={summary['bond_length_stats_non_connector']['stddev']:.3f} "
		f"cv={summary['bond_length_stats_non_connector']['coefficient_of_variation']:.3f}"
	)
	lines.append(
		"- excluded Haworth base ring lines: "
		f"count={summary['bond_length_stats_excluded_haworth_base_ring']['count']} "
		f"min={summary['bond_length_stats_excluded_haworth_base_ring']['min']:.3f} "
		f"max={summary['bond_length_stats_excluded_haworth_base_ring']['max']:.3f} "
		f"mean={summary['bond_length_stats_excluded_haworth_base_ring']['mean']:.3f} "
		f"stddev={summary['bond_length_stats_excluded_haworth_base_ring']['stddev']:.3f} "
		"cv="
		f"{summary['bond_length_stats_excluded_haworth_base_ring']['coefficient_of_variation']:.3f}"
	)
	lines.append("")
	lines.append("Top misses:")
	if not top_misses:
		lines.append("- none")
	else:
		for item in top_misses:
			distance = item["distance"]
			if math.isinf(distance):
				distance_text = "inf"
			else:
				distance_text = f"{distance:.3f}"
			lines.append(
				f"- {item['svg']} | text={item['text']} | reason={item['reason']} | distance={distance_text}"
			)
	return "\n".join(lines) + "\n"


#============================================
def main() -> None:
	"""Run SVG alignment measurement and write reports."""
	args = parse_args()
	repo_root = get_repo_root()
	render_geometry = _load_render_geometry(repo_root)
	svg_paths = _resolve_svg_paths(repo_root, args.input_glob)
	if not svg_paths:
		raise RuntimeError(f"No SVG files matched input_glob: {args.input_glob!r}")
	file_reports = [
		analyze_svg_file(
			path,
			render_geometry,
			exclude_haworth_base_ring=args.exclude_haworth_base_ring,
			bond_glyph_gap_tolerance=args.bond_glyph_gap_tolerance,
		)
		for path in svg_paths
	]
	summary = _summary_stats(file_reports)
	top_misses = _top_misses(file_reports, limit=20)
	json_report = {
		"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
		"repo_root": str(repo_root),
		"input_glob": args.input_glob,
		"exclude_haworth_base_ring": bool(args.exclude_haworth_base_ring),
		"bond_glyph_gap_tolerance": float(args.bond_glyph_gap_tolerance),
		"summary": summary,
		"top_misses": top_misses,
		"files": file_reports,
	}
	text_report = _text_report(
		summary=summary,
		top_misses=top_misses,
		input_glob=args.input_glob,
		exclude_haworth_base_ring=bool(args.exclude_haworth_base_ring),
	)
	json_report_path = pathlib.Path(args.json_report)
	text_report_path = pathlib.Path(args.text_report)
	if not json_report_path.is_absolute():
		json_report_path = (repo_root / json_report_path).resolve()
	if not text_report_path.is_absolute():
		text_report_path = (repo_root / text_report_path).resolve()
	json_report_path.parent.mkdir(parents=True, exist_ok=True)
	text_report_path.parent.mkdir(parents=True, exist_ok=True)
	json_report_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")
	text_report_path.write_text(text_report, encoding="utf-8")
	print(f"Wrote JSON report: {json_report_path}")
	print(f"Wrote text report: {text_report_path}")
	print("Key stats:")
	print(f"- files analyzed: {summary['files_analyzed']}")
	print(f"- text labels seen: {summary['text_labels_total']}")
	print(f"- text labels unique: {summary['text_labels_unique_total']}")
	print(f"- text labels list: {summary.get('text_labels_unique', [])}")
	print(f"- total bonds detected: {summary['total_bonds_detected']}")
	print(f"- total bonds checked: {summary['total_bonds_checked']}")
	print(
		"- decorative hashed hatch strokes excluded from checked bonds: "
		f"{summary.get('decorative_hatched_stroke_line_count', 0)}"
	)
	print(
		f"- rounded line lengths sorted (all primitives, {LENGTH_ROUND_DECIMALS} dp): "
		f"{summary.get('bond_lengths_rounded_sorted_all', [])}"
	)
	print(
		"- rounded line length counts (all primitives): "
		f"{summary.get('bond_length_rounded_counts_all', [])}"
	)
	print(
		f"- rounded bond lengths sorted (checked bonds, {LENGTH_ROUND_DECIMALS} dp): "
		f"{summary.get('bond_lengths_rounded_sorted_checked', [])}"
	)
	print(
		"- rounded bond length counts (checked bonds): "
		f"{summary.get('bond_length_rounded_counts_checked', [])}"
	)
	print(f"- labels analyzed: {summary['labels_analyzed']}")
	print(f"- alignment rate: {summary['alignment_rate'] * 100.0:.2f}%")
	print(f"- alignment outside tolerance: {summary['alignment_outside_tolerance_count']}")
	print(f"- lattice angle violations: {summary['lattice_angle_violation_count']}")
	print(f"  quadrants: {summary.get('lattice_angle_violation_quadrants', {})}")
	print(f"  ring regions: {summary.get('lattice_angle_violation_ring_regions', {})}")
	if summary.get("lattice_angle_violation_examples"):
		samples = []
		for item in summary["lattice_angle_violation_examples"][:3]:
			samples.append(
				f"line={item.get('line_index')} angle={item.get('angle_degrees'):.3f} "
				f"nearest={item.get('nearest_canonical_angle_degrees'):.1f} "
				f"q={item.get('quadrant')}"
			)
		print(f"  sample measured angles: {samples}")
	print(f"- glyph/glyph overlaps: {summary['glyph_glyph_overlap_count']}")
	print(f"- bond/bond overlaps: {summary['bond_bond_overlap_count']}")
	print(f"  quadrants: {summary.get('bond_bond_overlap_quadrants', {})}")
	print(f"  ring regions: {summary.get('bond_bond_overlap_ring_regions', {})}")
	print(f"- hatched/thin conflicts: {summary.get('hatched_thin_conflict_count', 0)}")
	print(f"  types: {summary.get('hatched_thin_conflict_types', {})}")
	print(f"  quadrants: {summary.get('hatched_thin_conflict_quadrants', {})}")
	print(f"  ring regions: {summary.get('hatched_thin_conflict_ring_regions', {})}")
	if summary.get("hatched_thin_conflict_examples"):
		examples = []
		for item in summary["hatched_thin_conflict_examples"][:3]:
			examples.append(
				f"carrier={item.get('carrier_line_index')} other={item.get('other_line_index')} "
				f"type={item.get('type')} q={item.get('quadrant')}"
			)
		print(f"  samples: {examples}")
	print(f"- bond/glyph overlaps: {summary['bond_glyph_overlap_count']}")
	gap_tolerances = summary.get("bond_glyph_gap_tolerances", {})
	if len(gap_tolerances) == 1:
		print(f"  gap tolerance: {next(iter(gap_tolerances.keys()))}")
	else:
		print(f"  gap tolerance values: {gap_tolerances}")
	print(
		"  endpoint overlap count (distance <= 0): "
		f"{summary.get('bond_glyph_endpoint_overlap_count', 0)}"
	)
	print(
		"  endpoint too-close count (0 < distance <= tolerance): "
		f"{summary.get('bond_glyph_endpoint_too_close_count', 0)}"
	)
	endpoint_stats = summary.get("bond_glyph_endpoint_signed_distance_stats", {})
	if endpoint_stats.get("count", 0) > 0:
		print(
			"  endpoint distance stats (signed, negative=overlap): "
			f"min={endpoint_stats.get('min', 0.0):.3f} "
			f"max={endpoint_stats.get('max', 0.0):.3f} "
			f"mean={endpoint_stats.get('mean', 0.0):.3f}"
		)
	print(
		"  classifications: "
		f"{summary.get('bond_glyph_overlap_classifications', {})}"
	)
	print(f"  glyph text counts: {summary.get('bond_glyph_overlap_label_texts', {})}")
	print(f"  quadrants: {summary.get('bond_glyph_overlap_quadrants', {})}")
	print(f"  ring regions: {summary.get('bond_glyph_overlap_ring_regions', {})}")
	if summary.get("bond_glyph_overlap_examples"):
		examples = []
		for item in summary["bond_glyph_overlap_examples"][:3]:
			examples.append(
				f"label={item.get('label_text')} "
				f"distance={item.get('bond_end_to_glyph_distance')} "
				f"tol={item.get('bond_end_distance_tolerance')} "
				f"overlap={item.get('bond_end_overlap')} "
				f"too_close={item.get('bond_end_too_close')}"
			)
		print(f"  sample endpoint diagnostics: {examples}")
	print(f"- Haworth base ring detected files: {summary['haworth_base_ring_detected_files']}")
	print(f"- Haworth base ring excluded files: {summary['haworth_base_ring_excluded_files']}")
	if args.fail_on_miss and (summary["missed_labels"] > 0 or summary["labels_without_connector"] > 0):
		raise SystemExit(2)


if __name__ == "__main__":
	main()
