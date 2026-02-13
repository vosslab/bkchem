#!/usr/bin/env python3
"""Measure bond-to-glyph alignment from existing SVG files without re-rendering."""

# Standard Library
import argparse
import datetime
import glob
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as StdET

# Third Party
import defusedxml.ElementTree as ET
try:
	from matplotlib.font_manager import FontProperties
	from matplotlib.path import Path as MplPath
	from matplotlib.textpath import TextPath
	from matplotlib.transforms import Affine2D
	MATPLOTLIB_TEXTPATH_AVAILABLE = True
except Exception:
	FontProperties = None
	MplPath = None
	TextPath = None
	Affine2D = None
	MATPLOTLIB_TEXTPATH_AVAILABLE = False

# Letter Center Finder (sibling repo)
_LETTER_CENTER_FINDER_ROOT = os.path.normpath(os.path.join(
	os.path.dirname(os.path.abspath(__file__)),
	"..", "..", "letter-center-finder"
))
if os.path.isdir(_LETTER_CENTER_FINDER_ROOT):
	sys.path.insert(0, _LETTER_CENTER_FINDER_ROOT)
try:
	from letter_center_finder import svg_parser as lcf_svg_parser
	from letter_center_finder import glyph_renderer as lcf_glyph_renderer
	from letter_center_finder import geometry as lcf_geometry
	LETTER_CENTER_FINDER_AVAILABLE = True
except ImportError:
	LETTER_CENTER_FINDER_AVAILABLE = False

MAX_ENDPOINT_TO_LABEL_DISTANCE_FACTOR = 2.6
MIN_ALIGNMENT_DISTANCE_TOLERANCE = 0.5
MIN_BOND_LENGTH_FOR_ANGLE_CHECK = 4.0
LATTICE_ANGLE_TOLERANCE_DEGREES = 1e-6
CANONICAL_LATTICE_ANGLES = tuple(float(angle) for angle in range(0, 360, 30))
GLYPH_BOX_OVERLAP_EPSILON = 0.5
BOND_GLYPH_INTERIOR_EPSILON = 0.35
BOND_GLYPH_GAP_TOLERANCE = 0.65
HAWORTH_RING_SEARCH_RADIUS = 45.0
HAWORTH_RING_MIN_PRIMITIVES = 5
SVG_FLOAT_PATTERN = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
LENGTH_ROUND_DECIMALS = 3
ALIGNMENT_DISTANCE_ZERO_EPSILON = 1e-9
HATCH_STROKE_MIN_WIDTH = 0.55
HATCH_STROKE_MAX_WIDTH = 1.35
HATCH_STROKE_MIN_LENGTH = 0.55
HATCH_STROKE_MAX_LENGTH = 4.5
HASHED_CARRIER_MAX_WIDTH = 2.20
HASHED_CARRIER_MIN_LENGTH = 6.0
HASHED_CARRIER_MIN_STROKES = 4
HASHED_STROKE_MAX_DISTANCE_TO_CARRIER = 1.35
HASHED_PERPENDICULAR_TOLERANCE_DEGREES = 25.0
HASHED_SHARED_ENDPOINT_PARALLEL_TOLERANCE_DEGREES = 35.0
MIN_CONNECTOR_LINE_WIDTH = 1.0
GLYPH_CURVED_CHAR_SET = set("OCSQGDU0698")
GLYPH_STEM_CHAR_SET = set("HNPMITFLKEXY147")
ALIGNMENT_INFINITE_LINE_FONT_TOLERANCE_FACTOR = 0.09
DEFAULT_INPUT_GLOB = "output_smoke/archive_matrix_previews/generated/*.svg"
DEFAULT_JSON_REPORT = "output_smoke/glyph_bond_alignment_report.json"
DEFAULT_TEXT_REPORT = "output_smoke/glyph_bond_alignment_report.txt"
DEFAULT_DIAGNOSTIC_SVG_DIR = "output_smoke/glyph_bond_alignment_diagnostics"


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
		"--diagnostic-svg-dir",
		dest="diagnostic_svg_dir",
		type=str,
		default=DEFAULT_DIAGNOSTIC_SVG_DIR,
		help="Output directory for diagnostic SVG overlays (one file per input SVG).",
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
		"--write-diagnostic-svg",
		dest="write_diagnostic_svg",
		action="store_true",
		help="Write diagnostic SVG overlays (default: on).",
	)
	parser.add_argument(
		"--no-diagnostic-svg",
		dest="write_diagnostic_svg",
		action="store_false",
		help="Disable diagnostic SVG overlay output.",
	)
	parser.add_argument(
		"--write-diagnostic-png",
		dest="write_diagnostic_png",
		action="store_true",
		help="Write diagnostic PNG set (ROI and full overlays) when optical mode is used (default: on).",
	)
	parser.add_argument(
		"--no-diagnostic-png",
		dest="write_diagnostic_png",
		action="store_false",
		help="Disable diagnostic PNG set output.",
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
	parser.add_argument(
		"--alignment-center-mode",
		dest="alignment_center_mode",
		choices=("primitive", "optical"),
		default="optical",
		help=(
			"Alignment center source: 'optical' uses CairoSVG-backed glyph hull fitting; "
			"'primitive' uses estimated glyph primitive centers."
		),
	)
	parser.set_defaults(fail_on_miss=False)
	parser.set_defaults(exclude_haworth_base_ring=True)
	parser.set_defaults(write_diagnostic_svg=True)
	parser.set_defaults(write_diagnostic_png=True)
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
def _alignment_score(distance_to_target: float | None, alignment_tolerance: float | None) -> float:
	"""Return normalized alignment score in [0, 1] from distance and tolerance."""
	if distance_to_target is None:
		return 0.0
	if alignment_tolerance is None or alignment_tolerance <= 0.0:
		return 0.0
	ratio = float(distance_to_target) / float(alignment_tolerance)
	return max(0.0, 1.0 - ratio)


#============================================
def _compact_float(value: float | None) -> float | None:
	"""Return compact high-precision float for report readability."""
	if value is None:
		return None
	return float(f"{float(value):.12g}")


#============================================
def _display_float(value: float | None, decimals: int = 3) -> float | None:
	"""Return rounded float for human-facing report data points."""
	if value is None:
		return None
	return round(float(value), int(decimals))


#============================================
def _display_point(point, decimals: int = 3):
	"""Return rounded [x, y] point for human-facing report data points."""
	if point is None:
		return None
	if not isinstance(point, (list, tuple)) or len(point) != 2:
		return point
	return [_display_float(point[0], decimals=decimals), _display_float(point[1], decimals=decimals)]


#============================================
def _safe_token(text: str) -> str:
	"""Return filesystem-safe token for one short label/debug string."""
	raw = str(text or "").strip()
	if not raw:
		return "unknown"
	safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
	return safe.strip("_") or "unknown"
#============================================
def _compact_sorted_values(values: list[float]) -> list[float]:
	"""Return sorted compact-float values preserving high precision."""
	return sorted(_compact_float(float(value)) for value in values)


#============================================
def _compact_value_counts(values: list[float]) -> list[dict]:
	"""Return frequency table using compact-float keys (avoids coarse rounding)."""
	counts: dict[float, int] = {}
	for value in values:
		compact = _compact_float(float(value))
		counts[compact] = int(counts.get(compact, 0)) + 1
	return [
		{
			"value": key,
			"count": counts[key],
		}
		for key in sorted(counts.keys())
	]


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
def _point_to_box_signed_distance(point: tuple[float, float], box: tuple[float, float, float, float]) -> float:
	"""Return signed point-to-box distance (negative means inside)."""
	x1, y1, x2, y2 = _normalize_box(box)
	px, py = point
	if x1 <= px <= x2 and y1 <= py <= y2:
		inside_depth = min(px - x1, x2 - px, py - y1, y2 - py)
		return -max(0.0, inside_depth)
	return _point_to_box_distance(point, box)


#============================================
def _point_to_ellipse_signed_distance(
		point: tuple[float, float],
		cx: float,
		cy: float,
		rx: float,
		ry: float) -> float:
	"""Return signed distance from one point to one axis-aligned ellipse."""
	axis_x = max(1e-6, float(rx))
	axis_y = max(1e-6, float(ry))
	px = abs(float(point[0]) - float(cx))
	py = abs(float(point[1]) - float(cy))
	if px <= 1e-12 and py <= 1e-12:
		return -min(axis_x, axis_y)
	def _f(value: float) -> float:
		term_x = (axis_x * px / (value + (axis_x * axis_x))) ** 2
		term_y = (axis_y * py / (value + (axis_y * axis_y))) ** 2
		return term_x + term_y - 1.0
	level = ((px / axis_x) ** 2) + ((py / axis_y) ** 2)
	inside = level <= 1.0
	if inside:
		low = -min(axis_x * axis_x, axis_y * axis_y) + 1e-9
		high = 0.0
	else:
		low = 0.0
		high = max(axis_x * px, axis_y * py, 1.0)
		while _f(high) > 0.0:
			high *= 2.0
			if high > 1e12:
				break
	for _ in range(90):
		mid = (low + high) * 0.5
		value = _f(mid)
		if value > 0.0:
			low = mid
		else:
			high = mid
	t_value = (low + high) * 0.5
	closest_x = (axis_x * axis_x * px) / (t_value + (axis_x * axis_x))
	closest_y = (axis_y * axis_y * py) / (t_value + (axis_y * axis_y))
	distance = math.hypot(px - closest_x, py - closest_y)
	return -distance if inside else distance


#============================================
def _point_to_glyph_primitive_signed_distance(point: tuple[float, float], primitive: dict) -> float:
	"""Return signed distance from one point to one estimated glyph primitive."""
	kind = str(primitive.get("kind", ""))
	if kind == "ellipse":
		return _point_to_ellipse_signed_distance(
			point=point,
			cx=float(primitive.get("cx", 0.0)),
			cy=float(primitive.get("cy", 0.0)),
			rx=float(primitive.get("rx", 0.0)),
			ry=float(primitive.get("ry", 0.0)),
		)
	box = primitive.get("box")
	if box is None:
		return float("inf")
	return _point_to_box_signed_distance(point, box)


#============================================
def _point_to_glyph_primitives_signed_distance(point: tuple[float, float], primitives: list[dict]) -> float:
	"""Return signed distance from one point to union of glyph primitives."""
	if not primitives:
		return float("inf")
	distances = [_point_to_glyph_primitive_signed_distance(point, primitive) for primitive in primitives]
	inside_distances = [distance for distance in distances if distance <= 0.0]
	if inside_distances:
		# For points inside union, keep the boundary-nearest negative depth.
		return max(inside_distances)
	return min(distances)


#============================================
def _point_to_glyph_primitives_distance(point: tuple[float, float], primitives: list[dict]) -> float:
	"""Return non-negative gap from one point to union of glyph primitives."""
	signed_distance = _point_to_glyph_primitives_signed_distance(point, primitives)
	if not math.isfinite(signed_distance):
		return float("inf")
	return max(0.0, signed_distance)


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
	return ("C" in text) or ("S" in text)


#============================================
def _canonicalize_label_text(visible_text: str) -> str:
	"""Return canonical label text for geometry targeting and grouping."""
	text = str(visible_text or "")
	normalized = text.replace("₂", "2").replace("₃", "3")
	if normalized in ("HOH2C", "H2COH", "C2HOH"):
		return "CH2OH"
	return normalized


#============================================
def _label_geometry_text(label: dict) -> str:
	"""Return label text that matches displayed SVG glyph order for geometry."""
	return str(label.get("text_display") or label.get("text_raw") or label.get("text") or "")


#============================================
def _font_family_candidates(font_name: str) -> list[str]:
	"""Return prioritized font-family candidates parsed from SVG font-family."""
	raw = str(font_name or "")
	parts = []
	for token in raw.split(","):
		clean = token.strip().strip("'").strip('"')
		if clean:
			parts.append(clean)
	if not parts:
		parts.append("sans-serif")
	parts.extend(["DejaVu Sans", "Arial", "sans-serif"])
	seen = set()
	unique = []
	for item in parts:
		key = item.lower()
		if key in seen:
			continue
		seen.add(key)
		unique.append(item)
	return unique


#============================================
def _label_text_path(label: dict):
	"""Return transformed matplotlib text path for one SVG label when available."""
	if not MATPLOTLIB_TEXTPATH_AVAILABLE:
		return None
	text = _label_geometry_text(label)
	if not text:
		return None
	font_size = max(1.0, float(label.get("font_size", 12.0)))
	families = _font_family_candidates(str(label.get("font_name", "sans-serif")))
	try:
		prop = FontProperties(family=families)
		base_path = TextPath((0.0, 0.0), text, size=font_size, prop=prop)
	except Exception:
		return None
	bbox = base_path.get_extents()
	x = float(label.get("x", 0.0))
	y = float(label.get("y", 0.0))
	anchor = str(label.get("anchor", "start")).strip().lower()
	if anchor == "middle":
		tx = x - ((bbox.xmin + bbox.xmax) * 0.5)
	elif anchor == "end":
		tx = x - bbox.xmax
	else:
		tx = x - bbox.xmin
	ty = y
	try:
		# Matplotlib text path uses Y-up coordinates, while SVG uses Y-down.
		# Mirror across baseline before placing at SVG text origin.
		return base_path.transformed(Affine2D().scale(1.0, -1.0).translate(tx, ty))
	except Exception:
		return None


#============================================
def _path_line_segments(path_obj) -> list[tuple[tuple[float, float], tuple[float, float]]]:
	"""Return piecewise-linear boundary segments from one matplotlib path."""
	if path_obj is None:
		return []
	try:
		linear = path_obj.interpolated(8)
	except Exception:
		linear = path_obj
	vertices = getattr(linear, "vertices", None)
	codes = getattr(linear, "codes", None)
	if vertices is None or len(vertices) < 2:
		return []
	segments = []
	if codes is None:
		for index in range(1, len(vertices)):
			p1 = (float(vertices[index - 1][0]), float(vertices[index - 1][1]))
			p2 = (float(vertices[index][0]), float(vertices[index][1]))
			segments.append((p1, p2))
		return segments
	sub_start = None
	prev = None
	for vertex, code in zip(vertices, codes):
		point = (float(vertex[0]), float(vertex[1]))
		if code == MplPath.MOVETO:
			sub_start = point
			prev = point
			continue
		if code == MplPath.LINETO:
			if prev is not None:
				segments.append((prev, point))
			prev = point
			continue
		if code == MplPath.CLOSEPOLY:
			if prev is not None and sub_start is not None:
				segments.append((prev, sub_start))
			prev = sub_start
			continue
	return segments


#============================================
def _point_to_text_path_signed_distance(point: tuple[float, float], path_obj) -> float:
	"""Return signed distance from one point to one glyph text path."""
	if path_obj is None:
		return float("inf")
	segments = _path_line_segments(path_obj)
	if not segments:
		return float("inf")
	min_distance_sq = float("inf")
	for seg_start, seg_end in segments:
		distance_sq = _point_to_segment_distance_sq(point, seg_start, seg_end)
		if distance_sq < min_distance_sq:
			min_distance_sq = distance_sq
	distance = math.sqrt(max(0.0, min_distance_sq))
	inside = False
	try:
		inside = bool(path_obj.contains_point(point))
	except Exception:
		inside = False
	return -distance if inside else distance


#============================================
def _point_to_label_signed_distance(point: tuple[float, float], label: dict) -> float:
	"""Return signed point distance to one label using best independent geometry."""
	text_path = label.get("svg_text_path")
	if text_path is not None:
		signed = _point_to_text_path_signed_distance(point, text_path)
		if math.isfinite(signed):
			return signed
	primitives = label.get("svg_estimated_primitives", [])
	if primitives:
		signed = _point_to_glyph_primitives_signed_distance(point, primitives)
		if math.isfinite(signed):
			return signed
	box = label.get("svg_estimated_box")
	if box is not None:
		return _point_to_box_signed_distance(point, box)
	return float("inf")


#============================================
def _nearest_endpoint_to_text_path(
		lines: list[dict],
		line_indexes: list[int],
		path_obj) -> tuple[tuple[float, float] | None, float | None, int | None, float | None]:
	"""Return nearest endpoint to one text path across candidate lines."""
	best_endpoint = None
	best_distance = float("inf")
	best_far_distance = float("-inf")
	best_length = float("-inf")
	best_line_index = None
	best_signed_distance = None
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		s1 = _point_to_text_path_signed_distance(p1, path_obj)
		s2 = _point_to_text_path_signed_distance(p2, path_obj)
		if not math.isfinite(s1) or not math.isfinite(s2):
			continue
		d1 = abs(s1)
		d2 = abs(s2)
		if d1 <= d2:
			endpoint = p1
			distance = d1
			signed_distance = s1
			far_distance = d2
		else:
			endpoint = p2
			distance = d2
			signed_distance = s2
			far_distance = d1
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
			best_signed_distance = signed_distance
	if best_endpoint is None:
		return None, None, None, None
	return best_endpoint, best_distance, best_line_index, best_signed_distance


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
def _nearest_endpoint_to_box(
		lines: list[dict],
		line_indexes: list[int],
		box: tuple[float, float, float, float]) -> tuple[tuple[float, float] | None, float | None, int | None]:
	"""Return nearest endpoint to one box across candidate lines."""
	best_endpoint = None
	best_distance = float("inf")
	best_far_distance = float("-inf")
	best_length = float("-inf")
	best_line_index = None
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		d1 = _point_to_box_distance(p1, box)
		d2 = _point_to_box_distance(p2, box)
		if d1 <= d2:
			endpoint = p1
			distance = d1
			far_distance = d2
		else:
			endpoint = p2
			distance = d2
			far_distance = d1
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
	if best_endpoint is None:
		return None, None, None
	return best_endpoint, best_distance, best_line_index


#============================================
def _nearest_endpoint_to_glyph_primitives(
		lines: list[dict],
		line_indexes: list[int],
		primitives: list[dict]) -> tuple[tuple[float, float] | None, float | None, int | None, float | None]:
	"""Return nearest endpoint to glyph primitive union across candidate lines."""
	best_endpoint = None
	best_distance = float("inf")
	best_far_distance = float("-inf")
	best_length = float("-inf")
	best_line_index = None
	best_signed_distance = None
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		s1 = _point_to_glyph_primitives_signed_distance(p1, primitives)
		s2 = _point_to_glyph_primitives_signed_distance(p2, primitives)
		if not math.isfinite(s1) or not math.isfinite(s2):
			continue
		d1 = max(0.0, s1)
		d2 = max(0.0, s2)
		if d1 <= d2:
			endpoint = p1
			distance = abs(s1)
			signed_distance = s1
			far_distance = abs(s2)
		else:
			endpoint = p2
			distance = abs(s2)
			signed_distance = s2
			far_distance = abs(s1)
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
			best_signed_distance = signed_distance
	if best_endpoint is None:
		return None, None, None, None
	return best_endpoint, best_distance, best_line_index, best_signed_distance


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
def _node_is_overlay_group(node) -> bool:
	"""Return True when one SVG node is an overlay/diagnostic group to ignore."""
	if _local_tag_name(str(node.tag)) != "g":
		return False
	node_id = str(node.get("id") or "").strip().lower()
	if not node_id:
		return False
	if node_id in {"codex-glyph-bond-diagnostic-overlay", "codex-overlay-noise"}:
		return True
	return node_id.startswith("codex-label-diag-")
#============================================
def _collect_svg_lines(svg_root) -> list[dict]:
	"""Collect line primitives from one SVG root."""
	lines = []
	def walk(node, overlay_excluded: bool) -> None:
		excluded_here = overlay_excluded or _node_is_overlay_group(node)
		if (not excluded_here) and _local_tag_name(str(node.tag)) == "line":
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
		for child in list(node):
			walk(child, excluded_here)
	walk(svg_root, False)
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
		canonical_text = _canonicalize_label_text(visible_text)
		labels.append(
			{
				"text": canonical_text,
				"text_raw": visible_text,
				"text_display": visible_text,
				"canonical_text": canonical_text,
				"x": _parse_float(node.get("x"), 0.0),
				"y": _parse_float(node.get("y"), 0.0),
				"anchor": str(node.get("text-anchor") or "start"),
				"font_size": _parse_float(node.get("font-size"), 12.0),
				"font_name": str(node.get("font-family") or "sans-serif"),
				"is_measurement_label": _is_measurement_label(canonical_text),
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
def _svg_tag_with_namespace(svg_root, local_name: str) -> str:
	"""Return namespaced tag when the parsed SVG root has one."""
	root_tag = str(svg_root.tag)
	if root_tag.startswith("{") and "}" in root_tag:
		namespace = root_tag[1:].split("}", 1)[0]
		return f"{{{namespace}}}{local_name}"
	return local_name


#============================================
def _viewbox_bounds(svg_root) -> tuple[float, float, float, float] | None:
	"""Return viewBox bounds as (min_x, min_y, max_x, max_y) when available."""
	values = _svg_number_tokens(str(svg_root.get("viewBox") or ""))
	if len(values) != 4:
		return None
	min_x, min_y, width, height = values
	if width <= 0.0 or height <= 0.0:
		return None
	return (min_x, min_y, min_x + width, min_y + height)


#============================================
def _diagnostic_bounds(svg_root, lines: list[dict], labels: list[dict]) -> tuple[float, float, float, float]:
	"""Return drawing bounds for diagnostic overlays."""
	viewbox = _viewbox_bounds(svg_root)
	if viewbox is not None:
		return viewbox
	x_values = []
	y_values = []
	for line in lines:
		x_values.extend([float(line["x1"]), float(line["x2"])])
		y_values.extend([float(line["y1"]), float(line["y2"])])
	for label in labels:
		box = label.get("svg_estimated_box")
		if box is not None:
			x1, y1, x2, y2 = _normalize_box(box)
			x_values.extend([x1, x2])
			y_values.extend([y1, y2])
	if not x_values or not y_values:
		return (-100.0, -100.0, 100.0, 100.0)
	margin = 8.0
	return (
		min(x_values) - margin,
		min(y_values) - margin,
		max(x_values) + margin,
		max(y_values) + margin,
	)


#============================================
def _clip_infinite_line_to_bounds(
		line_start: tuple[float, float],
		line_end: tuple[float, float],
		bounds: tuple[float, float, float, float]) -> tuple[tuple[float, float], tuple[float, float]] | None:
	"""Return endpoints where one infinite line crosses one bounds box."""
	x1, y1 = line_start
	x2, y2 = line_end
	min_x, min_y, max_x, max_y = _normalize_box(bounds)
	dx = x2 - x1
	dy = y2 - y1
	if math.hypot(dx, dy) <= 1e-12:
		return None
	points: list[tuple[float, float]] = []
	if abs(dx) > 1e-12:
		for x_edge in (min_x, max_x):
			t = (x_edge - x1) / dx
			y_value = y1 + (t * dy)
			if min_y - 1e-9 <= y_value <= max_y + 1e-9:
				points.append((x_edge, y_value))
	if abs(dy) > 1e-12:
		for y_edge in (min_y, max_y):
			t = (y_edge - y1) / dy
			x_value = x1 + (t * dx)
			if min_x - 1e-9 <= x_value <= max_x + 1e-9:
				points.append((x_value, y_edge))
	if len(points) < 2:
		return None
	unique: list[tuple[float, float]] = []
	for point in points:
		if any(_points_close(point, other, tol=1e-5) for other in unique):
			continue
		unique.append(point)
	if len(unique) < 2:
		return None
	best_pair = (unique[0], unique[1])
	best_dist_sq = _point_distance_sq(unique[0], unique[1])
	for idx_a in range(len(unique)):
		for idx_b in range(idx_a + 1, len(unique)):
			dist_sq = _point_distance_sq(unique[idx_a], unique[idx_b])
			if dist_sq > best_dist_sq:
				best_pair = (unique[idx_a], unique[idx_b])
				best_dist_sq = dist_sq
	return best_pair


#============================================
def _diagnostic_color(index: int, aligned: bool | None = None) -> str:
	"""Return deterministic color for one label overlay.

	Args:
		index: label index for deterministic palette cycling.
		aligned: True for green/teal (pass), False for red/orange (violation),
			None for the original neutral palette.
	"""
	if aligned is True:
		# green/teal family -- visually reads as "good"
		palette = ["#2a9d8f", "#06d6a0", "#40916c", "#52b788", "#74c69d", "#95d5b2"]
		return palette[index % len(palette)]
	if aligned is False:
		# red/orange family -- visually reads as "violation"
		palette = ["#d00000", "#e85d04", "#dc2f02", "#f48c06", "#e63946", "#ff6b6b"]
		return palette[index % len(palette)]
	# fallback neutral palette (original behavior)
	palette = ["#ff006e", "#3a86ff", "#ffbe0b", "#2a9d8f", "#8338ec", "#fb5607"]
	return palette[index % len(palette)]


#============================================
def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
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
def _metric_alignment_center(metric: dict) -> tuple[float, float] | None:
	"""Return alignment center from one metric row when available."""
	point = metric.get("alignment_center_point")
	if not isinstance(point, (list, tuple)) or len(point) != 2:
		return None
	try:
		return (float(point[0]), float(point[1]))
	except (TypeError, ValueError):
		return None


#============================================
def _metric_endpoint(metric: dict) -> tuple[float, float] | None:
	"""Return endpoint from one metric row when available."""
	point = metric.get("endpoint")
	if not isinstance(point, (list, tuple)) or len(point) != 2:
		return None
	try:
		return (float(point[0]), float(point[1]))
	except (TypeError, ValueError):
		return None


#============================================
def _select_alignment_primitive(label: dict, metric: dict) -> dict | None:
	"""Return primitive corresponding to alignment character/center for diagnostics."""
	primitives = list(label.get("svg_estimated_primitives", []))
	if not primitives:
		return None
	target_char = str(metric.get("alignment_center_char") or "").upper()
	target_center = _metric_alignment_center(metric)
	if target_char:
		filtered = [
			primitive
			for primitive in primitives
			if str(primitive.get("char", "")).upper() == target_char
		]
		if filtered:
			primitives = filtered
	if target_center is not None:
		def _distance_sq(primitive: dict) -> float:
			center = _primitive_center(primitive)
			if center is None:
				return float("inf")
			return _point_distance_sq(center, target_center)
		primitives = sorted(primitives, key=_distance_sq)
	return primitives[0] if primitives else None
#============================================
def _write_diagnostic_svg(
		svg_path: pathlib.Path,
		output_path: pathlib.Path,
		lines: list[dict],
		labels: list[dict],
		label_metrics: list[dict]) -> None:
	"""Write diagnostic overlay SVG with primitives and alignment guide lines."""
	svg_root = ET.parse(svg_path).getroot()
	tag_group = _svg_tag_with_namespace(svg_root, "g")
	tag_rect = _svg_tag_with_namespace(svg_root, "rect")
	tag_ellipse = _svg_tag_with_namespace(svg_root, "ellipse")
	tag_polygon = _svg_tag_with_namespace(svg_root, "polygon")
	tag_line = _svg_tag_with_namespace(svg_root, "line")
	tag_circle = _svg_tag_with_namespace(svg_root, "circle")
	tag_text = _svg_tag_with_namespace(svg_root, "text")
	bounds = _diagnostic_bounds(svg_root, lines=lines, labels=labels)
	overlay_group = StdET.Element(
		tag_group,
		attrib={
			"id": "codex-glyph-bond-diagnostic-overlay",
			"fill": "none",
			"stroke-linecap": "round",
			"stroke-linejoin": "round",
		},
	)
	for metric in label_metrics:
		label_index = metric.get("label_index")
		line_index = metric.get("connector_line_index")
		endpoint = metric.get("endpoint")
		if label_index is None or line_index is None:
			continue
		if not (0 <= int(label_index) < len(labels) and 0 <= int(line_index) < len(lines)):
			continue
		label = labels[int(label_index)]
		line = lines[int(line_index)]
		is_aligned = bool(metric.get("aligned", False))
		color = _diagnostic_color(int(label_index), aligned=is_aligned)
		# violations get thicker, bolder strokes to stand out visually
		stroke_w_thin = "0.4" if not is_aligned else "0.25"
		stroke_w_thick = "0.7" if not is_aligned else "0.5"
		stroke_opac = "0.9" if not is_aligned else "0.75"
		group = StdET.Element(tag_group, attrib={"id": f"codex-label-diag-{int(label_index)}"})
		diagnostic_center_point = _metric_alignment_center(metric)
		alignment_primitive = _select_alignment_primitive(label, metric)
		drawn_target = False
		hull_boundary_points = metric.get("hull_boundary_points") or []
		hull_fit = metric.get("hull_ellipse_fit")
		hull_contact_point = metric.get("hull_contact_point")
		if len(hull_boundary_points) >= 3:
			group.append(
				StdET.Element(
					tag_polygon,
					attrib={
						"points": " ".join(
							f"{float(point[0]):.6f},{float(point[1]):.6f}"
							for point in hull_boundary_points
						),
						"stroke": color,
						"stroke-width": stroke_w_thin,
						"stroke-opacity": stroke_opac,
						"stroke-dasharray": "2 1",
					},
				)
			)
			drawn_target = True
		if isinstance(hull_fit, dict):
			group.append(
				StdET.Element(
					tag_ellipse,
					attrib={
						"cx": f"{float(hull_fit.get('cx', 0.0)):.6f}",
						"cy": f"{float(hull_fit.get('cy', 0.0)):.6f}",
						"rx": f"{max(0.0, float(hull_fit.get('rx', 0.0))):.6f}",
						"ry": f"{max(0.0, float(hull_fit.get('ry', 0.0))):.6f}",
						"stroke": color,
						"stroke-width": stroke_w_thin,
						"stroke-opacity": stroke_opac,
						"stroke-dasharray": "2 1",
					},
				)
			)
			diagnostic_center_point = (
				float(hull_fit.get("cx", 0.0)),
				float(hull_fit.get("cy", 0.0)),
			)
			drawn_target = True
		if alignment_primitive is not None:
			kind = str(alignment_primitive.get("kind", ""))
			if not drawn_target and kind == "ellipse":
				group.append(
					StdET.Element(
						tag_ellipse,
						attrib={
							"cx": f"{float(alignment_primitive.get('cx', 0.0)):.6f}",
							"cy": f"{float(alignment_primitive.get('cy', 0.0)):.6f}",
							"rx": f"{max(0.0, float(alignment_primitive.get('rx', 0.0))):.6f}",
							"ry": f"{max(0.0, float(alignment_primitive.get('ry', 0.0))):.6f}",
							"stroke": color,
							"stroke-width": stroke_w_thin,
							"stroke-opacity": stroke_opac,
							"stroke-dasharray": "2 1",
						},
					)
				)
				drawn_target = True
				diagnostic_center_point = (
					float(alignment_primitive.get("cx", 0.0)),
					float(alignment_primitive.get("cy", 0.0)),
				)
			if not drawn_target and kind == "box" and alignment_primitive.get("box") is not None:
				x1, y1, x2, y2 = _normalize_box(alignment_primitive["box"])
				group.append(
					StdET.Element(
						tag_rect,
						attrib={
							"x": f"{x1:.6f}",
							"y": f"{y1:.6f}",
							"width": f"{max(0.0, x2 - x1):.6f}",
							"height": f"{max(0.0, y2 - y1):.6f}",
							"stroke": color,
							"stroke-width": stroke_w_thick,
							"stroke-opacity": stroke_opac,
							"stroke-dasharray": "2 1",
						},
					)
				)
				drawn_target = True
				diagnostic_center_point = ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
		if not drawn_target:
			label_box = label.get("svg_estimated_box")
			if label_box is not None:
				x1, y1, x2, y2 = _normalize_box(label_box)
				group.append(
					StdET.Element(
						tag_rect,
						attrib={
							"x": f"{x1:.6f}",
							"y": f"{y1:.6f}",
							"width": f"{max(0.0, x2 - x1):.6f}",
							"height": f"{max(0.0, y2 - y1):.6f}",
							"stroke": color,
							"stroke-width": stroke_w_thin,
							"stroke-opacity": stroke_opac,
							"stroke-dasharray": "2 1",
						},
					)
				)
				diagnostic_center_point = ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
		center_point = diagnostic_center_point
		if center_point is not None:
			group.append(
				StdET.Element(
					tag_circle,
					attrib={
						"cx": f"{center_point[0]:.6f}",
						"cy": f"{center_point[1]:.6f}",
						"r": "1.0",
						"fill": color,
						"fill-opacity": "0.5",
						"stroke-width": "0.2",
					},
				)
			)
		start = (float(line["x1"]), float(line["y1"]))
		end = (float(line["x2"]), float(line["y2"]))
		infinite = _clip_infinite_line_to_bounds(start, end, bounds)
		if infinite is not None:
			pa, pb = infinite
			group.append(
				StdET.Element(
					tag_line,
					attrib={
						"x1": f"{pa[0]:.6f}",
						"y1": f"{pa[1]:.6f}",
							"x2": f"{pb[0]:.6f}",
							"y2": f"{pb[1]:.6f}",
							"stroke": "#00a6fb",
							"stroke-width": "0.1",
						},
					)
				)
		if isinstance(endpoint, (list, tuple)) and len(endpoint) == 2:
			ep_x = float(endpoint[0])
			ep_y = float(endpoint[1])
			if isinstance(hull_contact_point, (list, tuple)) and len(hull_contact_point) == 2:
				group.append(
					StdET.Element(
						tag_line,
						attrib={
							"x1": f"{ep_x:.6f}",
							"y1": f"{ep_y:.6f}",
							"x2": f"{float(hull_contact_point[0]):.6f}",
							"y2": f"{float(hull_contact_point[1]):.6f}",
							"stroke": "#ff5400",
							"stroke-width": "0.2",
						},
					)
				)
				group.append(
					StdET.Element(
						tag_circle,
						attrib={
							"cx": f"{float(hull_contact_point[0]):.6f}",
							"cy": f"{float(hull_contact_point[1]):.6f}",
							"r": "1.0",
							"fill": "#ff5400",
							"fill-opacity": "0.5",
							"stroke-width": "0.2",
						},
					)
				)
			dx = end[0] - start[0]
			dy = end[1] - start[1]
			length = math.hypot(dx, dy)
			if length > 1e-12:
				nx = -dy / length
				ny = dx / length
				half = 6.0
				p1 = (ep_x - (nx * half), ep_y - (ny * half))
				p2 = (ep_x + (nx * half), ep_y + (ny * half))
				group.append(
					StdET.Element(
						tag_line,
						attrib={
							"x1": f"{p1[0]:.6f}",
							"y1": f"{p1[1]:.6f}",
								"x2": f"{p2[0]:.6f}",
								"y2": f"{p2[1]:.6f}",
								"stroke": "#ff5400",
								"stroke-width": "0.2",
							},
						)
					)
		overlay_group.append(group)
	# -- legend: aligned (green) vs violation (red) --
	legend_x = bounds[0] + 2.0
	legend_y = bounds[1] + 6.0
	legend_group = StdET.Element(
		tag_group,
		attrib={"id": "codex-diagnostic-legend", "font-size": "4", "font-family": "sans-serif"},
	)
	# white background
	legend_group.append(
		StdET.Element(
			tag_rect,
			attrib={
				"x": f"{legend_x - 1.0:.1f}",
				"y": f"{legend_y - 5.0:.1f}",
				"width": "36",
				"height": "14",
				"fill": "white",
				"fill-opacity": "0.85",
				"stroke": "#999999",
				"stroke-width": "0.3",
			},
		)
	)
	# aligned swatch (green)
	legend_group.append(
		StdET.Element(
			tag_rect,
			attrib={
				"x": f"{legend_x:.1f}",
				"y": f"{legend_y - 2.5:.1f}",
				"width": "4",
				"height": "3",
				"fill": "none",
				"stroke": "#2a9d8f",
				"stroke-width": "0.25",
			},
		)
	)
	aligned_label = StdET.Element(tag_text)
	aligned_label.text = "Aligned"
	aligned_label.set("x", f"{legend_x + 6.0:.1f}")
	aligned_label.set("y", f"{legend_y:.1f}")
	aligned_label.set("fill", "#2a9d8f")
	legend_group.append(aligned_label)
	# violation swatch (red)
	legend_group.append(
		StdET.Element(
			tag_rect,
			attrib={
				"x": f"{legend_x:.1f}",
				"y": f"{legend_y + 2.0:.1f}",
				"width": "4",
				"height": "3",
				"fill": "none",
				"stroke": "#d00000",
				"stroke-width": "0.4",
			},
		)
	)
	violation_label = StdET.Element(tag_text)
	violation_label.text = "Violation"
	violation_label.set("x", f"{legend_x + 6.0:.1f}")
	violation_label.set("y", f"{legend_y + 4.5:.1f}")
	violation_label.set("fill", "#d00000")
	legend_group.append(violation_label)
	overlay_group.append(legend_group)
	svg_root.append(overlay_group)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	StdET.ElementTree(svg_root).write(output_path, encoding="utf-8", xml_declaration=True)


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


def _glyph_char_advance(font_size: float, char: str) -> float:
	"""Return estimated horizontal advance for one glyph character."""
	size = max(1.0, float(font_size))
	if not char:
		return size * 0.55
	if char.isspace():
		return size * 0.30
	upper = char.upper()
	if upper in ("I", "L", "1"):
		return size * 0.38
	if upper in ("W", "M"):
		return size * 0.82
	if upper in GLYPH_CURVED_CHAR_SET:
		return size * 0.62
	if upper in GLYPH_STEM_CHAR_SET:
		return size * 0.58
	if char.isdigit():
		return size * 0.52
	if char.islower():
		return size * 0.50
	return size * 0.56


#============================================
def _glyph_char_vertical_bounds(
		baseline_y: float,
		font_size: float,
		char: str) -> tuple[float, float]:
	"""Return estimated top/bottom y bounds for one character primitive."""
	size = max(1.0, float(font_size))
	upper = char.upper()
	if char.isdigit():
		# Digits in formulas are often drawn smaller/lower (subscript-like).
		local_baseline = baseline_y + (size * 0.22)
		return (local_baseline - (size * 0.52), local_baseline + (size * 0.18))
	if char.islower():
		return (baseline_y - (size * 0.60), baseline_y + (size * 0.22))
	if upper in ("C", "O", "S", "Q", "G", "D"):
		return (baseline_y - (size * 0.78), baseline_y + (size * 0.16))
	return (baseline_y - (size * 0.80), baseline_y + (size * 0.20))


#============================================
def _glyph_text_width(text: str, font_size: float) -> float:
	"""Return estimated full text width from per-character advances."""
	if not text:
		return max(1.0, float(font_size)) * 0.75
	advances = [_glyph_char_advance(font_size, char) for char in text]
	tracking = max(0.0, float(font_size)) * 0.04
	return sum(advances) + (tracking * float(max(0, len(advances) - 1)))


#============================================
def _glyph_primitive_from_char(
		char: str,
		char_index: int,
		left_x: float,
		right_x: float,
		top_y: float,
		bottom_y: float) -> dict:
	"""Build one estimated glyph primitive from one character box."""
	upper = char.upper()
	width = max(0.2, right_x - left_x)
	height = max(0.2, bottom_y - top_y)
	if upper in GLYPH_CURVED_CHAR_SET:
		# Tune curved glyph hulls so O-like labels are less under-sized and
		# C-like labels do not over-expand into apparent whitespace gaps.
		if upper == "C":
			rx_factor = 0.35
			ry_factor = 0.43
		elif upper in ("O", "Q"):
			rx_factor = 0.47
			ry_factor = 0.53
		else:
			rx_factor = 0.43
			ry_factor = 0.49
		rx = max(0.3, width * rx_factor)
		ry = max(0.3, height * ry_factor)
		return {
			"kind": "ellipse",
			"char": char,
			"char_index": char_index,
			"cx": (left_x + right_x) * 0.5,
			"cy": (top_y + bottom_y) * 0.5,
			"rx": rx,
			"ry": ry,
		}
	inset_x = width * 0.12
	inset_y = height * 0.05
	return {
		"kind": "box",
		"char": char,
		"char_index": char_index,
		"box": (
			left_x + inset_x,
			top_y + inset_y,
			right_x - inset_x,
			bottom_y - inset_y,
		),
	}


#============================================
def _label_svg_estimated_primitives(label: dict) -> list[dict]:
	"""Return renderer-independent glyph primitives derived from SVG text attrs."""
	font_size = max(1.0, float(label.get("font_size", 12.0)))
	text = _label_geometry_text(label)
	if not text:
		return []
	text_width = _glyph_text_width(text, font_size)
	x = float(label.get("x", 0.0))
	y = float(label.get("y", 0.0))
	anchor = str(label.get("anchor", "start")).strip().lower()
	if anchor == "middle":
		cursor_x = x - (text_width * 0.5)
	elif anchor == "end":
		cursor_x = x - text_width
	else:
		cursor_x = x
	tracking = font_size * 0.04
	primitives = []
	for char_index, char in enumerate(text):
		advance = _glyph_char_advance(font_size, char)
		top_y, bottom_y = _glyph_char_vertical_bounds(
			baseline_y=y,
			font_size=font_size,
			char=char,
		)
		primitive = _glyph_primitive_from_char(
			char=char,
			char_index=char_index,
			left_x=cursor_x,
			right_x=cursor_x + advance,
			top_y=top_y,
			bottom_y=bottom_y,
		)
		primitives.append(primitive)
		cursor_x += advance + tracking
	return primitives


#============================================
def _glyph_primitives_bounds(primitives: list[dict]) -> tuple[float, float, float, float] | None:
	"""Return one union bounds box for one glyph primitive list."""
	if not primitives:
		return None
	x_values = []
	y_values = []
	for primitive in primitives:
		kind = str(primitive.get("kind", ""))
		if kind == "box":
			box = primitive.get("box")
			if box is None:
				continue
			x1, y1, x2, y2 = _normalize_box(box)
			x_values.extend([x1, x2])
			y_values.extend([y1, y2])
		elif kind == "ellipse":
			cx = float(primitive.get("cx", 0.0))
			cy = float(primitive.get("cy", 0.0))
			rx = max(0.0, float(primitive.get("rx", 0.0)))
			ry = max(0.0, float(primitive.get("ry", 0.0)))
			x_values.extend([cx - rx, cx + rx])
			y_values.extend([cy - ry, cy + ry])
	if not x_values or not y_values:
		return None
	return (min(x_values), min(y_values), max(x_values), max(y_values))


#============================================
def _primitive_center(primitive: dict) -> tuple[float, float] | None:
	"""Return center point for one glyph primitive."""
	kind = str(primitive.get("kind", ""))
	if kind == "ellipse":
		return (
			float(primitive.get("cx", 0.0)),
			float(primitive.get("cy", 0.0)),
		)
	if kind == "box":
		box = primitive.get("box")
		if box is None:
			return None
		x1, y1, x2, y2 = _normalize_box(box)
		return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
	return None


#============================================
def _first_carbon_primitive_center(primitives: list[dict]) -> tuple[float, float] | None:
	"""Return center of first carbon glyph primitive, when present."""
	carbon_primitives = [
		primitive
		for primitive in primitives
		if str(primitive.get("char", "")).upper() == "C"
	]
	carbon_primitives.sort(key=lambda primitive: int(primitive.get("char_index", 10**9)))
	for primitive in carbon_primitives:
		center = _primitive_center(primitive)
		if center is not None:
			return center
	return None


#============================================
def _first_primitive_center_for_char(primitives: list[dict], target_char: str) -> tuple[float, float] | None:
	"""Return center of first primitive matching one character."""
	candidates = [
		primitive
		for primitive in primitives
		if str(primitive.get("char", "")).upper() == str(target_char).upper()
	]
	candidates.sort(key=lambda primitive: int(primitive.get("char_index", 10**9)))
	for primitive in candidates:
		center = _primitive_center(primitive)
		if center is not None:
			return center
	return None


#============================================
def _alignment_primitive_center(primitives: list[dict], canonical_text: str) -> tuple[tuple[float, float] | None, str | None]:
	"""Return preferred glyph-primitive center for alignment checks."""
	text = str(canonical_text or "").upper()
	priority = [char for char in ("C", "O", "N", "S", "P", "H") if char in text]
	for target_char in priority:
		center = _first_primitive_center_for_char(primitives, target_char)
		if center is not None:
			return center, target_char
	for primitive in sorted(primitives, key=lambda item: int(item.get("char_index", 10**9))):
		center = _primitive_center(primitive)
		if center is not None:
			return center, str(primitive.get("char", "")) or None
	return None, None


_LCF_CHAR_CACHE: dict[str, list[dict]] = {}


#============================================
def _optical_center_via_isolation_render(
		label: dict,
		center: tuple[float, float] | None,
		center_char: str | None,
		svg_path: str,
		gate_debug: dict | None = None) -> tuple[tuple[float, float] | None, str | None]:
	"""Find optical glyph center using per-character SVG isolation rendering."""
	if center is None or not center_char:
		return center, center_char
	target = str(center_char).upper()
	if target not in ("O", "C"):
		return center, center_char
	try:
		# Get parsed characters (cached per SVG file)
		if svg_path not in _LCF_CHAR_CACHE:
			_LCF_CHAR_CACHE[svg_path] = lcf_svg_parser.parse_svg_file(svg_path)
		all_chars = _LCF_CHAR_CACHE[svg_path]
		# Match: same character, closest to primitive center
		matches = [c for c in all_chars if c["character"] == target]
		if not matches:
			return center, center_char
		best = min(matches, key=lambda c: (c["cx"] - center[0]) ** 2 + (c["cy"] - center[1]) ** 2)
		svg_dims = lcf_svg_parser.get_svg_dimensions(svg_path)
		zoom = 10
		# Render isolated glyph
		glyph_image = lcf_glyph_renderer.render_isolated_glyph(svg_path, best, zoom)
		binary_mask = lcf_glyph_renderer.extract_binary_mask(glyph_image)
		contour_points = lcf_glyph_renderer.extract_contour_points(binary_mask)
		hull_result = lcf_geometry.compute_convex_hull(contour_points)
		# C glyphs: fit hull (closes opening); O glyphs: fit contour
		fit_points = hull_result["vertices"] if target == "C" else contour_points
		ellipse = lcf_geometry.fit_axis_aligned_ellipse(fit_points)
		# Map pixel center to SVG coordinates
		pixel_cx, pixel_cy = ellipse["center"]
		svg_cx, svg_cy = lcf_svg_parser.pixel_to_svg(pixel_cx, pixel_cy, svg_dims, zoom)
		# Map semi-axes to SVG units
		vb = svg_dims["viewBox"]
		vp_w = svg_dims["viewport_width"] * zoom
		scale = min(vp_w / vb["width"], svg_dims["viewport_height"] * zoom / vb["height"])
		svg_rx = ellipse["semi_x"] / scale
		svg_ry = ellipse["semi_y"] / scale
		# Populate gate_debug for downstream metrics and diagnostics
		if gate_debug is not None:
			gate_debug["pipeline"] = "letter_center_finder"
			gate_debug["component_point_count"] = int(len(contour_points))
			gate_debug["stripe_applied"] = False
			gate_debug["stripe_point_count"] = int(len(contour_points))
			gate_debug["final_point_count"] = int(len(contour_points))
			gate_debug["hull_point_count"] = int(len(hull_result["vertices"]))
			gate_debug["ellipse_fit"] = {
				"cx": _compact_float(float(svg_cx)),
				"cy": _compact_float(float(svg_cy)),
				"rx": _compact_float(float(svg_rx)),
				"ry": _compact_float(float(svg_ry)),
				"angle_deg": 0.0,
			}
		return (float(svg_cx), float(svg_cy)), center_char
	except Exception:
		return center, center_char


#============================================
def _point_to_infinite_line_distance(
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


#============================================
def _label_svg_estimated_box(label: dict) -> tuple[float, float, float, float]:
	"""Return renderer-independent estimated glyph-union box from text primitives."""
	primitives = _label_svg_estimated_primitives(label)
	box = _glyph_primitives_bounds(primitives)
	if box is not None:
		return box
	font_size = max(1.0, float(label.get("font_size", 12.0)))
	text = _label_geometry_text(label)
	estimated_width = _glyph_text_width(text, font_size)
	x = float(label.get("x", 0.0))
	y = float(label.get("y", 0.0))
	anchor = str(label.get("anchor", "start")).strip().lower()
	if anchor == "middle":
		x1 = x - (estimated_width * 0.5)
		x2 = x + (estimated_width * 0.5)
	elif anchor == "end":
		x1 = x - estimated_width
		x2 = x
	else:
		x1 = x
		x2 = x + estimated_width
	return _normalize_box((x1, y - (font_size * 0.80), x2, y + (font_size * 0.20)))


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
			carrier_angle = _line_angle_degrees(carrier_line)
			other_angle = _line_angle_degrees(other_line)
			parallel_error = _parallel_error_degrees(carrier_angle, other_angle)
			conflict_type = "crossing_intersection"
			if share_endpoint and overlap_length <= 0.75:
				if parallel_error <= HASHED_SHARED_ENDPOINT_PARALLEL_TOLERANCE_DEGREES:
					conflict_type = "shared_endpoint_near_parallel"
				else:
					continue
			if _lines_nearly_parallel(carrier_line, other_line):
				if overlap_length <= 0.75:
					if conflict_type != "shared_endpoint_near_parallel":
						continue
				else:
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
		lines: list[dict],
		labels: list[dict],
		checked_line_indexes: list[int],
		checked_label_indexes: list[int],
		aligned_connector_pairs: set[tuple[int, int]],
		haworth_base_ring: dict,
		gap_tolerance: float) -> tuple[int, list[dict]]:
	"""Count bond-vs-glyph overlaps from independent SVG geometry only."""
	overlaps = []
	origin = _overlap_origin(lines, haworth_base_ring)
	for line_index in checked_line_indexes:
		line = lines[line_index]
		for label_index in checked_label_indexes:
			label = labels[label_index]
			label_box = label.get("svg_estimated_box")
			if label_box is None:
				continue
			is_aligned_connector = (line_index, label_index) in aligned_connector_pairs
			bond_end_point, _ = _line_closest_endpoint_to_box(line=line, box=label_box)
			bond_end_signed_distance = _point_to_label_signed_distance(
				point=bond_end_point,
				label=label,
			)
			if not math.isfinite(bond_end_signed_distance):
				bond_end_signed_distance = _point_to_box_signed_distance(bond_end_point, label_box)
			bond_end_overlap = bond_end_signed_distance <= 0.0
			bond_end_too_close = (bond_end_signed_distance > 0.0) and (
				bond_end_signed_distance <= float(gap_tolerance)
			)
			interior_overlap = (
				bond_end_overlap
				or _line_intersects_box_interior(
					line,
					label_box,
					epsilon=BOND_GLYPH_INTERIOR_EPSILON,
				)
			)
			near_overlap = (
				bond_end_too_close
				or _line_intersects_box_interior(
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
					"overlap_detection_mode": "independent_svg_geometry",
				}
			)
	return len(overlaps), overlaps


#============================================
def analyze_svg_file(
		svg_path: pathlib.Path,
		render_geometry=None,
		exclude_haworth_base_ring: bool = True,
		bond_glyph_gap_tolerance: float = BOND_GLYPH_GAP_TOLERANCE,
		alignment_center_mode: str = "primitive",
		write_diagnostic_svg: bool = False,
		diagnostic_svg_dir: pathlib.Path | None = None) -> dict:
	"""Analyze one SVG file and return independent geometry and alignment metrics."""
	root = ET.parse(svg_path).getroot()
	lines = _collect_svg_lines(root)
	labels = _collect_svg_labels(root)
	ring_primitives = _collect_svg_ring_primitives(root)
	for label in labels:
		label["svg_text_path"] = _label_text_path(label)
		label["svg_estimated_primitives"] = _label_svg_estimated_primitives(label)
		label["svg_estimated_box"] = _label_svg_estimated_box(label)
		label["_source_svg_path"] = str(svg_path)
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
	pre_hashed_carrier_map = _detect_hashed_carrier_map(lines, checked_line_indexes)
	pre_decorative_hatched_stroke_index_set = {
		stroke_index
		for stroke_indexes in pre_hashed_carrier_map.values()
		for stroke_index in stroke_indexes
	}
	width_pool = [
		float(lines[index].get("width", 1.0))
		for index in checked_line_indexes
		if index not in pre_decorative_hatched_stroke_index_set
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
		independent_primitives = label.get("svg_estimated_primitives", [])
		alignment_center, alignment_center_char = _alignment_primitive_center(
			primitives=independent_primitives,
			canonical_text=str(label.get("canonical_text", label.get("text", ""))),
		)
		independent_text_path = label.get("svg_text_path")
		independent_model_name = "svg_text_path_outline"
		if independent_text_path is not None:
			(
				independent_endpoint,
				independent_distance,
				independent_line_index,
				independent_signed_distance,
			) = _nearest_endpoint_to_text_path(
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
			) = _nearest_endpoint_to_glyph_primitives(
				lines=lines,
				line_indexes=connector_candidate_line_indexes,
				primitives=independent_primitives,
			)
			independent_model_name = "svg_primitives_ellipse_box"
		if str(alignment_center_mode).lower() == "optical":
			optical_gate_debug = {}
			if LETTER_CENTER_FINDER_AVAILABLE and str(alignment_center_char).upper() in ("O", "C"):
				alignment_center, alignment_center_char = _optical_center_via_isolation_render(
					label=label,
					center=alignment_center,
					center_char=alignment_center_char,
					svg_path=str(svg_path),
					gate_debug=optical_gate_debug,
				)
		else:
			optical_gate_debug = {}
		if independent_endpoint is not None and independent_signed_distance is None:
			independent_signed_distance = _point_to_label_signed_distance(independent_endpoint, label)
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
			alignment_error = _point_to_infinite_line_distance(
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
	location_origin = _overlap_origin(lines, haworth_base_ring)
	checked_bond_lengths_by_quadrant: dict[str, list[float]] = {}
	checked_bond_lengths_by_ring_region: dict[str, list[float]] = {}
	checked_bond_lengths_by_quadrant_ring_region: dict[str, list[float]] = {}
	for line_index in checked_bond_line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		length = line_lengths_all[line_index]
		midpoint = _line_midpoint(line)
		quadrant = _quadrant_label(midpoint, origin=location_origin)
		ring_region = _ring_region_label(midpoint, haworth_base_ring=haworth_base_ring)
		_group_length_append(checked_bond_lengths_by_quadrant, quadrant, length)
		_group_length_append(checked_bond_lengths_by_ring_region, ring_region, length)
		_group_length_append(
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
	bond_glyph_overlap_count, bond_glyph_overlaps = _count_bond_glyph_overlaps(
		lines=lines,
		labels=labels,
		checked_line_indexes=checked_line_indexes,
		checked_label_indexes=checked_label_indexes,
		aligned_connector_pairs=aligned_connector_pairs,
		haworth_base_ring=haworth_base_ring,
		gap_tolerance=float(bond_glyph_gap_tolerance),
	)
	diagnostic_svg_path = None
	if write_diagnostic_svg and diagnostic_svg_dir is not None:
		diagnostic_svg_name = f"{svg_path.stem}.diagnostic.svg"
		diagnostic_svg_path = (diagnostic_svg_dir / diagnostic_svg_name).resolve()
		_write_diagnostic_svg(
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
		"geometry_checks": {
			"canonical_angles_degrees": list(CANONICAL_LATTICE_ANGLES),
			"angle_tolerance_degrees": LATTICE_ANGLE_TOLERANCE_DEGREES,
			"bond_glyph_gap_tolerance": float(bond_glyph_gap_tolerance),
			"alignment_center_mode": str(alignment_center_mode),
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
		"line_lengths_grouped": {
			"checked_bonds_by_quadrant": checked_bond_lengths_by_quadrant,
			"checked_bonds_by_ring_region": checked_bond_lengths_by_ring_region,
			"checked_bonds_by_quadrant_ring_region": checked_bond_lengths_by_quadrant_ring_region,
		},
		"line_lengths_grouped_rounded_sorted": {
			"checked_bonds_by_quadrant": {
				key: _rounded_sorted_values(values)
				for key, values in sorted(checked_bond_lengths_by_quadrant.items())
			},
			"checked_bonds_by_ring_region": {
				key: _rounded_sorted_values(values)
				for key, values in sorted(checked_bond_lengths_by_ring_region.items())
			},
			"checked_bonds_by_quadrant_ring_region": {
				key: _rounded_sorted_values(values)
				for key, values in sorted(checked_bond_lengths_by_quadrant_ring_region.items())
			},
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
			_increment_counter(text_label_counts, str(label_text))
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
			score_value = _alignment_score(distance_value, tolerance_value)
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
					}
				)
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
	alignment_distance_stats = _length_stats(alignment_distances_all)
	alignment_glyph_body_distance_stats = _length_stats(alignment_glyph_body_distances_all)
	alignment_glyph_body_signed_distance_stats = _length_stats(alignment_glyph_body_signed_distances_all)
	alignment_score_stats = _length_stats(alignment_scores_all)
	alignment_distances_compact_sorted = _compact_sorted_values(alignment_distances_all)
	alignment_distance_compact_counts = _compact_value_counts(alignment_distances_all)
	alignment_glyph_body_distances_compact_sorted = _compact_sorted_values(alignment_glyph_body_distances_all)
	alignment_glyph_body_distance_compact_counts = _compact_value_counts(alignment_glyph_body_distances_all)
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
		glyph_body_gap_distances = []
		for item in measurements:
			gap_value = item.get("gap_distance_to_glyph_body")
			if gap_value is None:
				signed_value = item.get("signed_distance_to_glyph_body")
				if signed_value is not None:
					gap_value = max(0.0, float(signed_value))
			if gap_value is None:
				continue
			glyph_body_gap_distances.append(float(gap_value))
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
				"distance_to_target": _display_float(item.get("distance_to_target")),
				"alignment_error": _display_float(item.get("alignment_error")),
				"distance_to_glyph_body": _display_float(item.get("distance_to_glyph_body")),
				"signed_distance_to_glyph_body": _display_float(item.get("signed_distance_to_glyph_body")),
				"gap_distance_to_glyph_body": _display_float(item.get("gap_distance_to_glyph_body")),
				"penetration_depth_to_glyph_body": _display_float(item.get("penetration_depth_to_glyph_body")),
				"perpendicular_distance_to_alignment_center": _display_float(
					item.get("perpendicular_distance_to_alignment_center")
				),
				"alignment_center_point": _display_point(item.get("alignment_center_point")),
				"alignment_center_char": item.get("alignment_center_char"),
				"alignment_tolerance": _display_float(item.get("alignment_tolerance")),
				"distance_to_tolerance_ratio": _display_float(item.get("distance_to_tolerance_ratio")),
				"alignment_score": _display_float(item.get("alignment_score")),
					"connector_line_index": item.get("connector_line_index"),
					"endpoint": _display_point(item.get("endpoint")),
					"hull_boundary_points": [
						_display_point(point)
						for point in (item.get("hull_boundary_points") or [])
					],
					"hull_ellipse_fit": item.get("hull_ellipse_fit"),
					"hull_contact_point": _display_point(item.get("hull_contact_point")),
					"hull_signed_gap_along_bond": _display_float(item.get("hull_signed_gap_along_bond")),
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
			"distance_values": [_compact_float(value) for value in distances],
			"distance_to_glyph_body_values": [_compact_float(value) for value in glyph_body_distances],
			"score_values": [_compact_float(value) for value in scores],
			"distance_mean": _compact_float(sum(distances) / float(len(distances))) if distances else None,
			"distance_to_glyph_body_mean": (
				_compact_float(sum(glyph_body_distances) / float(len(glyph_body_distances)))
				if glyph_body_distances else None
			),
			"score_mean": _compact_float(sum(scores) / float(len(scores))) if scores else None,
			"measurements": measurement_rows,
		}
		glyph_text_to_bond_end_distance[glyph_text] = sorted(
			_display_float(value)
			for value in glyph_body_gap_distances
		)
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
		"alignment_min_nonzero_distance": _compact_float(alignment_min_nonzero_distance),
		"alignment_distances_compact_sorted": alignment_distances_compact_sorted,
		"alignment_distance_compact_counts": alignment_distance_compact_counts,
		"alignment_glyph_body_nonzero_distance_count": alignment_glyph_body_nonzero_distance_count,
		"alignment_glyph_body_min_nonzero_distance": _compact_float(alignment_glyph_body_min_nonzero_distance),
		"alignment_glyph_body_distances_compact_sorted": alignment_glyph_body_distances_compact_sorted,
		"alignment_glyph_body_distance_compact_counts": alignment_glyph_body_distance_compact_counts,
		"alignment_distances_rounded_sorted": alignment_distances_compact_sorted,
		"alignment_distance_rounded_counts": alignment_distance_compact_counts,
		"glyph_to_bond_end_distance_stats": alignment_glyph_body_distance_stats,
		"glyph_to_bond_end_signed_distance_stats": alignment_glyph_body_signed_distance_stats,
		"glyph_to_bond_end_missing_distance_count": alignment_glyph_body_distance_missing_count,
		"glyph_to_bond_end_nonzero_distance_count": alignment_glyph_body_nonzero_distance_count,
		"glyph_to_bond_end_min_nonzero_distance": _compact_float(alignment_glyph_body_min_nonzero_distance),
		"glyph_to_bond_end_distances_compact_sorted": alignment_glyph_body_distances_compact_sorted,
		"glyph_to_bond_end_distance_compact_counts": alignment_glyph_body_distance_compact_counts,
		"glyph_text_to_bond_end_distance": glyph_text_to_bond_end_distance,
		"glyph_alignment_data_points": glyph_alignment_data_points,
		"glyph_to_bond_end_data_points": glyph_to_bond_end_data_points,
		"alignment_by_glyph": alignment_by_glyph,
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
		"bond_lengths_by_quadrant_checked": {
			key: _rounded_sorted_values(values)
			for key, values in sorted(bond_lengths_by_quadrant_checked.items())
		},
		"bond_lengths_by_ring_region_checked": {
			key: _rounded_sorted_values(values)
			for key, values in sorted(bond_lengths_by_ring_region_checked.items())
		},
		"bond_lengths_by_quadrant_ring_region_checked": {
			key: _rounded_sorted_values(values)
			for key, values in sorted(bond_lengths_by_quadrant_ring_region_checked.items())
		},
	}


#============================================
def _top_misses(file_reports: list[dict], limit: int = 20) -> list[dict]:
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
					"endpoint": label["endpoint"],
				}
			)
	entries.sort(key=lambda item: item["distance"], reverse=True)
	return entries[:limit]


#============================================
def _format_stats_line(label: str, stats: dict) -> str:
	"""Format one _length_stats dict into a compact single line."""
	if stats.get("count", 0) == 0:
		return f"{label}: (none)"
	return (
		f"{label}: n={stats['count']}  "
		f"min={stats['min']:.3f}  max={stats['max']:.3f}  "
		f"mean={stats['mean']:.3f}  sd={stats['stddev']:.3f}"
	)


#============================================
def _violation_summary(summary: dict, top_misses: list[dict]) -> dict:
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
	}


#============================================
# keys containing large arrays that belong in debug, not in the compact summary
_JSON_SUMMARY_EXCLUDE_KEYS = {
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


def _json_summary_compact(summary: dict) -> dict:
	"""Return summary dict without large array-valued keys."""
	return {
		key: value
		for key, value in summary.items()
		if key not in _JSON_SUMMARY_EXCLUDE_KEYS
	}


#============================================
def _text_report(
		summary: dict,
		top_misses: list[dict],
		input_glob: str,
		exclude_haworth_base_ring: bool,
		alignment_center_mode: str = "primitive") -> str:
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
		f"|  Mode: {alignment_center_mode}  |  Haworth: {haworth_tag}"
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
			dist_text = _display_float(item.get("bond_end_to_glyph_distance"))
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
		lines.append(_format_stats_line("All lines", summary["bond_length_stats_all"]))
	lines.append(_format_stats_line("Checked", summary["bond_length_stats_checked"]))
	lines.append(_format_stats_line("Connector", summary["bond_length_stats_connector"]))
	lines.append(_format_stats_line("Non-connector", summary["bond_length_stats_non_connector"]))
	haworth_stats = summary["bond_length_stats_excluded_haworth_base_ring"]
	if haworth_stats.get("count", 0) > 0:
		lines.append(_format_stats_line("Excluded Haworth", haworth_stats))
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


#============================================
def main() -> None:
	"""Run SVG alignment measurement and write reports."""
	args = parse_args()
	repo_root = get_repo_root()
	svg_paths = _resolve_svg_paths(repo_root, args.input_glob)
	if not svg_paths:
		raise RuntimeError(f"No SVG files matched input_glob: {args.input_glob!r}")
	diagnostic_svg_dir = pathlib.Path(args.diagnostic_svg_dir)
	if not diagnostic_svg_dir.is_absolute():
		diagnostic_svg_dir = (repo_root / diagnostic_svg_dir).resolve()
	file_reports = [
		analyze_svg_file(
			path,
			exclude_haworth_base_ring=args.exclude_haworth_base_ring,
			bond_glyph_gap_tolerance=args.bond_glyph_gap_tolerance,
			alignment_center_mode=args.alignment_center_mode,
			write_diagnostic_svg=bool(args.write_diagnostic_svg),
			diagnostic_svg_dir=diagnostic_svg_dir,
		)
		for path in svg_paths
	]
	summary = _summary_stats(file_reports)
	top_misses = _top_misses(file_reports, limit=20)
	# -- build JSON report with compact summary and debug section --
	json_report = {
		"schema_version": 2,
		"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
		"input_glob": args.input_glob,
		"alignment_center_mode": str(args.alignment_center_mode),
		"exclude_haworth_base_ring": bool(args.exclude_haworth_base_ring),
		"bond_glyph_gap_tolerance": float(args.bond_glyph_gap_tolerance),
		"summary": _json_summary_compact(summary),
		"violation_summary": _violation_summary(summary, top_misses),
		"top_misses": top_misses,
		"debug": {
			"repo_root": str(repo_root),
			"full_summary": summary,
			"files": file_reports,
		},
	}
	text_report = _text_report(
		summary=summary,
		top_misses=top_misses,
		input_glob=args.input_glob,
		exclude_haworth_base_ring=bool(args.exclude_haworth_base_ring),
		alignment_center_mode=str(args.alignment_center_mode),
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
	# -- concise console output --
	print(f"Wrote JSON report: {json_report_path}")
	print(f"Wrote text report: {text_report_path}")
	if args.write_diagnostic_svg:
		print(f"Wrote diagnostic SVGs to: {diagnostic_svg_dir}")
	print()
	alignment_pct = summary["alignment_rate"] * 100.0
	print(f"{'Files analyzed:':<42}{summary['files_analyzed']:>6}")
	print(f"{'Labels analyzed:':<42}{summary['labels_analyzed']:>6}")
	print(
		f"{'  Aligned:':<42}{summary['aligned_labels']:>6}"
		f"  ({alignment_pct:.1f}%)"
	)
	print(
		f"{'Bonds (detected / checked):':<42}"
		f"{summary['total_bonds_detected']:>6} / {summary['total_bonds_checked']}"
	)
	print()
	# violation summary -- only print nonzero categories
	violation_total = (
		summary.get("alignment_outside_tolerance_count", 0)
		+ summary.get("lattice_angle_violation_count", 0)
		+ summary.get("glyph_glyph_overlap_count", 0)
		+ summary.get("bond_bond_overlap_count", 0)
		+ summary.get("bond_glyph_overlap_count", 0)
		+ summary.get("hatched_thin_conflict_count", 0)
	)
	print(f"{'Violations:':<42}{violation_total:>6}")
	if violation_total > 0:
		violation_items = [
			("  Alignment outside tolerance", "alignment_outside_tolerance_count"),
			("  Lattice angle violations", "lattice_angle_violation_count"),
			("  Glyph/glyph overlaps", "glyph_glyph_overlap_count"),
			("  Bond/bond overlaps", "bond_bond_overlap_count"),
			("  Bond/glyph overlaps", "bond_glyph_overlap_count"),
			("  Hatched/thin conflicts", "hatched_thin_conflict_count"),
		]
		for label, key in violation_items:
			count = summary.get(key, 0)
			if count > 0:
				print(f"{label + ':':<42}{count:>6}")
	print()
	# top misses -- show at most 3
	if top_misses:
		print("Top misses:")
		for item in top_misses[:3]:
			dist = item["distance"]
			dist_text = "inf" if math.isinf(dist) else f"{dist:.3f}"
			svg_name = pathlib.Path(str(item["svg"])).stem
			print(
				f"  {svg_name:<28}  label={item['text']:<6}"
				f"  reason={item['reason']:<30}  dist={dist_text}"
			)
		remaining = len(top_misses) - 3
		if remaining > 0:
			print(f"  ... and {remaining} more (see text report)")
	if args.fail_on_miss and (summary["missed_labels"] > 0 or summary["labels_without_connector"] > 0):
		raise SystemExit(2)


if __name__ == "__main__":
	main()
