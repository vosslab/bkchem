"""Diagnostic SVG overlay writer for glyph-bond alignment measurement."""

# Standard Library
import math
import pathlib
import xml.etree.ElementTree as StdET

# Third Party
import defusedxml.ElementTree as ET

from measurelib.util import normalize_box, point_distance_sq
from measurelib.geometry import points_close
from measurelib.svg_parse import svg_number_tokens, svg_tag_with_namespace
from measurelib.glyph_model import primitive_center


#============================================
def viewbox_bounds(svg_root) -> tuple[float, float, float, float] | None:
	"""Return viewBox bounds as (min_x, min_y, max_x, max_y) when available."""
	values = svg_number_tokens(str(svg_root.get("viewBox") or ""))
	if len(values) != 4:
		return None
	min_x, min_y, width, height = values
	if width <= 0.0 or height <= 0.0:
		return None
	return (min_x, min_y, min_x + width, min_y + height)


#============================================
def diagnostic_bounds(svg_root, lines: list[dict], labels: list[dict]) -> tuple[float, float, float, float]:
	"""Return drawing bounds for diagnostic overlays."""
	viewbox = viewbox_bounds(svg_root)
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
			x1, y1, x2, y2 = normalize_box(box)
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
def clip_infinite_line_to_bounds(
		line_start: tuple[float, float],
		line_end: tuple[float, float],
		bounds: tuple[float, float, float, float]) -> tuple[tuple[float, float], tuple[float, float]] | None:
	"""Return endpoints where one infinite line crosses one bounds box."""
	x1, y1 = line_start
	x2, y2 = line_end
	min_x, min_y, max_x, max_y = normalize_box(bounds)
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
		if any(points_close(point, other, tol=1e-5) for other in unique):
			continue
		unique.append(point)
	if len(unique) < 2:
		return None
	best_pair = (unique[0], unique[1])
	best_dist_sq = point_distance_sq(unique[0], unique[1])
	for idx_a in range(len(unique)):
		for idx_b in range(idx_a + 1, len(unique)):
			dist_sq = point_distance_sq(unique[idx_a], unique[idx_b])
			if dist_sq > best_dist_sq:
				best_pair = (unique[idx_a], unique[idx_b])
				best_dist_sq = dist_sq
	return best_pair


#============================================
def diagnostic_color(index: int, aligned: bool | None = None) -> str:
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
def metric_alignment_center(metric: dict) -> tuple[float, float] | None:
	"""Return alignment center from one metric row when available."""
	point = metric.get("alignment_center_point")
	if not isinstance(point, (list, tuple)) or len(point) != 2:
		return None
	try:
		return (float(point[0]), float(point[1]))
	except (TypeError, ValueError):
		return None


#============================================
def metric_endpoint(metric: dict) -> tuple[float, float] | None:
	"""Return endpoint from one metric row when available."""
	point = metric.get("endpoint")
	if not isinstance(point, (list, tuple)) or len(point) != 2:
		return None
	try:
		return (float(point[0]), float(point[1]))
	except (TypeError, ValueError):
		return None


#============================================
def select_alignment_primitive(label: dict, metric: dict) -> dict | None:
	"""Return primitive corresponding to alignment character/center for diagnostics."""
	primitives = list(label.get("svg_estimated_primitives", []))
	if not primitives:
		return None
	target_char = str(metric.get("alignment_center_char") or "").upper()
	target_center = metric_alignment_center(metric)
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
			center = primitive_center(primitive)
			if center is None:
				return float("inf")
			return point_distance_sq(center, target_center)
		primitives = sorted(primitives, key=_distance_sq)
	return primitives[0] if primitives else None


#============================================
def write_diagnostic_svg(
		svg_path: pathlib.Path,
		output_path: pathlib.Path,
		lines: list[dict],
		labels: list[dict],
		label_metrics: list[dict]) -> None:
	"""Write diagnostic overlay SVG with primitives and alignment guide lines."""
	svg_root = ET.parse(svg_path).getroot()
	tag_group = svg_tag_with_namespace(svg_root, "g")
	tag_rect = svg_tag_with_namespace(svg_root, "rect")
	tag_ellipse = svg_tag_with_namespace(svg_root, "ellipse")
	tag_polygon = svg_tag_with_namespace(svg_root, "polygon")
	tag_line = svg_tag_with_namespace(svg_root, "line")
	tag_circle = svg_tag_with_namespace(svg_root, "circle")
	tag_text = svg_tag_with_namespace(svg_root, "text")
	bounds = diagnostic_bounds(svg_root, lines=lines, labels=labels)
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
		color = diagnostic_color(int(label_index), aligned=is_aligned)
		# violations get thicker, bolder strokes to stand out visually
		stroke_w_thin = "0.4" if not is_aligned else "0.25"
		stroke_w_thick = "0.7" if not is_aligned else "0.5"
		stroke_opac = "0.9" if not is_aligned else "0.75"
		group = StdET.Element(tag_group, attrib={"id": f"codex-label-diag-{int(label_index)}"})
		diagnostic_center_point = metric_alignment_center(metric)
		alignment_primitive = select_alignment_primitive(label, metric)
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
				x1, y1, x2, y2 = normalize_box(alignment_primitive["box"])
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
				x1, y1, x2, y2 = normalize_box(label_box)
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
		infinite = clip_infinite_line_to_bounds(start, end, bounds)
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
		# -- distance annotations near the bond endpoint --
		annotation_lines = []
		signed_gap = metric.get("endpoint_signed_distance_to_glyph_body")
		if signed_gap is None:
			signed_gap = metric.get("endpoint_signed_distance_to_glyph_body_independent")
		hull_gap = metric.get("hull_signed_gap_along_bond")
		perp_dist = metric.get("endpoint_perpendicular_distance_to_alignment_center")
		alignment_err = metric.get("endpoint_alignment_error")
		# prefer hull gap when available (curved glyphs); else signed gap
		gap_value = hull_gap if hull_gap is not None else signed_gap
		if gap_value is not None:
			try:
				annotation_lines.append(f"gap={float(gap_value):.2f}")
			except (TypeError, ValueError):
				pass
		if perp_dist is not None:
			try:
				annotation_lines.append(f"perp={float(perp_dist):.2f}")
			except (TypeError, ValueError):
				pass
		if alignment_err is not None:
			try:
				annotation_lines.append(f"err={float(alignment_err):.2f}")
			except (TypeError, ValueError):
				pass
		if annotation_lines and isinstance(endpoint, (list, tuple)) and len(endpoint) == 2:
			ep_x = float(endpoint[0])
			ep_y = float(endpoint[1])
			# offset text perpendicular to bond direction
			dx = end[0] - start[0]
			dy = end[1] - start[1]
			bond_len = math.hypot(dx, dy)
			if bond_len > 1e-12:
				nx = -dy / bond_len
				ny = dx / bond_len
			else:
				nx, ny = 0.0, -1.0
			text_offset = 3.0
			text_x = ep_x + nx * text_offset
			text_y = ep_y + ny * text_offset
			font_sz = 2.5
			for line_idx, line_text in enumerate(annotation_lines):
				annotation_el = StdET.Element(tag_text)
				annotation_el.text = line_text
				annotation_el.set("x", f"{text_x:.2f}")
				annotation_el.set("y", f"{text_y + line_idx * (font_sz + 0.5):.2f}")
				annotation_el.set("font-size", f"{font_sz}")
				annotation_el.set("font-family", "sans-serif")
				annotation_el.set("fill", color)
				annotation_el.set("fill-opacity", "0.9")
				group.append(annotation_el)
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
