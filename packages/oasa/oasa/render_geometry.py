#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program
#
#--------------------------------------------------------------------------

"""Geometry producer for shared Cairo/SVG drawing."""

# Standard Library
import dataclasses
import math
import re

# local repo modules
from . import geometry
from . import misc
from . import render_ops
from . import wedge_geometry


#============================================
@dataclasses.dataclass(frozen=True)
class BondRenderContext:
	molecule: object
	line_width: float
	bond_width: float
	wedge_width: float
	bold_line_width_multiplier: float
	bond_second_line_shortening: float = 0.0
	color_bonds: bool = False
	atom_colors: dict | None = None
	shown_vertices: set | None = None
	bond_coords: dict | None = None
	bond_coords_provider: object | None = None
	point_for_atom: object | None = None
	label_bboxes: dict | None = None
	attach_bboxes: dict | None = None


#============================================
def haworth_front_edge_geometry(start, end, width, overlap=None, front_pad=None):
	x1, y1 = start
	x2, y2 = end
	d = math.hypot(x2 - x1, y2 - y1)
	if d == 0:
		return None
	dx = (x2 - x1) / d
	dy = (y2 - y1) / d
	if overlap is None:
		overlap = max(1.0, 0.25 * width)
	if front_pad is None:
		front_pad = max(overlap, 0.35 * width)
	x1 -= dx * front_pad
	y1 -= dy * front_pad
	x2 += dx * front_pad
	y2 += dy * front_pad
	cap_radius = width / 2.0
	x1 += dx * cap_radius
	y1 += dy * cap_radius
	x2 -= dx * cap_radius
	y2 -= dy * cap_radius
	normal = (-dy, dx)
	return (x1, y1), (x2, y2), normal, cap_radius


#============================================
def haworth_front_edge_ops(start, end, width, color):
	geom = haworth_front_edge_geometry(start, end, width)
	if not geom:
		return []
	(start, end, _normal, _cap_radius) = geom
	return [render_ops.LineOp(start, end, width=width, cap="round", color=color)]


#============================================
def _point_for_atom(context, atom):
	if context.point_for_atom:
		return context.point_for_atom(atom)
	return (atom.x, atom.y)


#============================================
def _edge_wavy_style(edge):
	return (getattr(edge, "wavy_style", None)
			or edge.properties_.get("wavy_style")
			or "sine")


#============================================
def _edge_line_color(edge):
	color = getattr(edge, "line_color", None)
	if not color:
		color = edge.properties_.get("line_color") or edge.properties_.get("color")
	return render_ops.color_to_hex(color)


#============================================
def _edge_line_width(edge, context):
	if edge.type == 'b':
		return context.line_width * context.bold_line_width_multiplier
	return context.line_width


#============================================
def _resolve_edge_colors(edge, context, has_shown_vertex):
	edge_color = _edge_line_color(edge)
	if edge_color:
		return edge_color, edge_color, False
	if context.color_bonds and context.atom_colors:
		v1, v2 = edge.vertices
		color1 = render_ops.color_to_hex(context.atom_colors.get(v1.symbol, (0, 0, 0))) or "#000"
		color2 = render_ops.color_to_hex(context.atom_colors.get(v2.symbol, (0, 0, 0))) or "#000"
		if has_shown_vertex and color1 != color2:
			return color1, color2, True
		return color1, color2, False
	return "#000", "#000", False


#============================================
def _line_ops(start, end, width, color1, color2, gradient, cap):
	if gradient and color1 and color2 and color1 != color2:
		mid = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
		return [
			render_ops.LineOp(start, mid, width=width, cap=cap, color=color1),
			render_ops.LineOp(mid, end, width=width, cap=cap, color=color2),
		]
	return [render_ops.LineOp(start, end, width=width, cap=cap, color=color1 or "#000")]


#============================================
def _rounded_wedge_ops(start, end, line_width, wedge_width, color):
	geom = wedge_geometry.rounded_wedge_geometry(start, end, wedge_width, line_width)
	return [render_ops.PathOp(commands=geom["path_commands"], fill=color or "#000")]


#============================================
def _hashed_ops(start, end, line_width, wedge_width, color1, color2, gradient):
	x1, y1 = start
	x2, y2 = end
	x, y, x0, y0 = geometry.find_parallel(x1, y1, x2, y2, wedge_width / 2.0)
	xa, ya, xb, yb = geometry.find_parallel(x1, y1, x2, y2, line_width / 2.0)
	d = geometry.point_distance(x1, y1, x2, y2)
	if d == 0:
		return []
	dx1 = (x0 - xa) / d
	dy1 = (y0 - ya) / d
	dx2 = (2 * x2 - x0 - 2 * x1 + xa) / d
	dy2 = (2 * y2 - y0 - 2 * y1 + ya) / d
	step_size = 2 * line_width
	ns = round(d / step_size) or 1
	step_size = d / ns
	ops = []
	total = int(round(d / step_size)) + 1
	middle = max(1, total // 2)
	for i in range(1, total):
		coords = [
			xa + dx1 * i * step_size,
			ya + dy1 * i * step_size,
			2 * x1 - xa + dx2 * i * step_size,
			2 * y1 - ya + dy2 * i * step_size,
		]
		if coords[0] == coords[2] and coords[1] == coords[3]:
			if (dx1 + dx2) > (dy1 + dy2):
				coords[0] += 1
			else:
				coords[1] += 1
		color = color1
		if gradient and color2 and i >= middle:
			color = color2
		ops.append(render_ops.LineOp((coords[0], coords[1]), (coords[2], coords[3]),
				width=line_width, cap="butt", color=color))
	return ops


#============================================
def _wave_points(start, end, line_width, style):
	x1, y1 = start
	x2, y2 = end
	d = geometry.point_distance(x1, y1, x2, y2)
	if d == 0:
		return []
	dx = (x2 - x1) / d
	dy = (y2 - y1) / d
	px = -dy
	py = dx
	amplitude = max(line_width * 1.5, 1.0)
	wavelength = max(line_width * 6.0, 6.0)
	steps = int(max(d / (wavelength / 16.0), 16))
	step_size = d / steps
	points = []
	for i in range(steps + 1):
		t = i * step_size
		phase = (t / wavelength)
		if style == "triangle":
			value = 2 * abs(2 * (phase - math.floor(phase + 0.5))) - 1
		elif style == "box":
			value = 1.0 if math.sin(2 * math.pi * phase) >= 0 else -1.0
		elif style == "half-circle":
			half = wavelength / 2.0
			local = (t % half) / half
			value = math.sqrt(max(0.0, 1 - (2 * local - 1) ** 2))
			if int(t / half) % 2:
				value *= -1
		else:
			value = math.sin(2 * math.pi * phase)
		ox = px * amplitude * value
		oy = py * amplitude * value
		points.append((x1 + dx * t + ox, y1 + dy * t + oy))
	return points


#============================================
def _wavy_ops(start, end, line_width, style, color):
	points = _wave_points(start, end, line_width, style)
	if len(points) < 2:
		return []
	commands = [("M", (points[0][0], points[0][1]))]
	for x, y in points[1:]:
		commands.append(("L", (x, y)))
	return [render_ops.PathOp(commands=tuple(commands), fill="none", stroke=color or "#000",
			stroke_width=line_width, cap="round", join="round")]


#============================================
def _double_bond_side(context, v1, v2, start, end, has_shown_vertex):
	side = 0
	in_ring = False
	molecule = context.molecule
	if molecule:
		for ring in molecule.get_smallest_independent_cycles():
			if v1 in ring and v2 in ring:
				in_ring = True
				double_bonds = len([bond for bond in molecule.vertex_subgraph_to_edge_subgraph(ring) if bond.order == 2])
				for atom in ring:
					if atom is v1 or atom is v2:
						continue
					side += double_bonds * geometry.on_which_side_is_point(
						start + end, _point_for_atom(context, atom)
					)
	if not side:
		for atom in v1.neighbors + v2.neighbors:
			if atom is v1 or atom is v2:
				continue
			side += geometry.on_which_side_is_point(start + end, _point_for_atom(context, atom))
	if not side and (in_ring or not has_shown_vertex):
		if in_ring:
			side = 1
		else:
			if len(v1.neighbors) == 1 and len(v2.neighbors) == 1:
				side = 0
			elif len(v1.neighbors) < 3 and len(v2.neighbors) < 3 and molecule:
				side = sum(
					geometry.on_which_side_is_point(start + end, _point_for_atom(context, atom))
					for atom in molecule.vertices
					if atom is not v1 and atom is not v2
				)
				if not side:
					side = 1
	return side


#============================================
def build_bond_ops(edge, start, end, context):
	if start is None or end is None:
		return []
	v1, v2 = edge.vertices
	bbox_v1 = None
	bbox_v2 = None
	if context.attach_bboxes:
		bbox_v1 = context.attach_bboxes.get(v1)
		bbox_v2 = context.attach_bboxes.get(v2)
	if context.label_bboxes:
		if bbox_v1 is None:
			bbox_v1 = context.label_bboxes.get(v1)
		if bbox_v2 is None:
			bbox_v2 = context.label_bboxes.get(v2)
	target_center_v1 = bbox_center(bbox_v1) if bbox_v1 is not None else None
	target_center_v2 = bbox_center(bbox_v2) if bbox_v2 is not None else None
	if bbox_v1 is not None:
		start = directional_attach_edge_intersection(end, bbox_v1, target_center_v1)
	if bbox_v2 is not None:
		end = directional_attach_edge_intersection(start, bbox_v2, target_center_v2)
	has_shown_vertex = False
	if context.shown_vertices:
		has_shown_vertex = v1 in context.shown_vertices or v2 in context.shown_vertices
	color1, color2, gradient = _resolve_edge_colors(edge, context, has_shown_vertex)
	edge_line_width = _edge_line_width(edge, context)
	ops = []

	if edge.order == 1:
		if edge.type == 'w':
			haworth_front = edge.properties_.get("haworth_position") == "front"
			if haworth_front:
				overlap = max(1.0, 0.25 * context.wedge_width)
				d = geometry.point_distance(start[0], start[1], end[0], end[1])
				if d:
					dx = (end[0] - start[0]) / d
					dy = (end[1] - start[1]) / d
					end = (end[0] + dx * overlap, end[1] + dy * overlap)
			ops.extend(_rounded_wedge_ops(start, end, context.line_width,
					context.wedge_width, color1))
			return ops
		if edge.type == 'h':
			ops.extend(_hashed_ops(start, end, context.line_width, context.wedge_width,
					color1, color2, gradient))
			return ops
		if edge.type == 'q':
			ops.extend(haworth_front_edge_ops(start, end, context.wedge_width, color1))
			return ops
		if edge.type == 's':
			ops.extend(_wavy_ops(start, end, edge_line_width, _edge_wavy_style(edge), color1))
			return ops
		ops.extend(_line_ops(start, end, edge_line_width, color1, color2, gradient, cap="round"))
		return ops

	if edge.order == 2:
		side = _double_bond_side(context, v1, v2, start, end, has_shown_vertex)
		if side:
			ops.extend(_line_ops(start, end, edge_line_width, color1, color2, gradient, cap="round"))
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], context.bond_width * misc.signum(side)
			)
			length = geometry.point_distance(x1, y1, x2, y2)
			if length and context.bond_second_line_shortening:
				if not context.shown_vertices or v2 not in context.shown_vertices:
					x2, y2 = geometry.elongate_line(x1, y1, x2, y2,
							-context.bond_second_line_shortening * length)
				if not context.shown_vertices or v1 not in context.shown_vertices:
					x1, y1 = geometry.elongate_line(x2, y2, x1, y1,
							-context.bond_second_line_shortening * length)
			if bbox_v1 is not None:
				x1, y1 = directional_attach_edge_intersection((x2, y2), bbox_v1, target_center_v1)
			if bbox_v2 is not None:
				x2, y2 = directional_attach_edge_intersection((x1, y1), bbox_v2, target_center_v2)
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="butt"))
			return ops
		for i in (1, -1):
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], i * context.bond_width * 0.5
			)
			if bbox_v1 is not None:
				x1, y1 = directional_attach_edge_intersection((x2, y2), bbox_v1, target_center_v1)
			if bbox_v2 is not None:
				x2, y2 = directional_attach_edge_intersection((x1, y1), bbox_v2, target_center_v2)
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="round"))
		return ops

	if edge.order == 3:
		ops.extend(_line_ops(start, end, edge_line_width, color1, color2, gradient, cap="round"))
		for i in (1, -1):
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], i * context.bond_width * 0.7
			)
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="butt"))
	return ops


#============================================
def vertex_is_shown(vertex):
	if vertex.properties_.get("label"):
		return True
	return vertex.symbol != "C" or vertex.charge != 0 or vertex.multiplicity != 1


#============================================
def vertex_label_text(vertex, show_hydrogens_on_hetero):
	label = vertex.properties_.get("label")
	if label:
		text = label
	else:
		text = vertex.symbol
		if show_hydrogens_on_hetero:
			if vertex.free_valency == 1:
				text += "H"
			elif vertex.free_valency > 1:
				text += "H%d" % vertex.free_valency
	if vertex.charge == 1:
		text += "+"
	elif vertex.charge == -1:
		text += "-"
	elif vertex.charge > 1:
		text += str(vertex.charge) + "+"
	elif vertex.charge < -1:
		text += str(vertex.charge)
	return text


#============================================
def _visible_label_text(text):
	return re.sub(r"<[^>]+>", "", text or "")


#============================================
def _visible_label_length(text):
	return max(1, len(_visible_label_text(text)))


#============================================
def _label_text_origin(x, y, anchor, font_size, text_len):
	del text_len
	baseline_offset = font_size * 0.375
	start_offset = font_size * 0.3125
	if anchor == "start":
		return (x - start_offset, y + baseline_offset)
	return (x, y + baseline_offset)


#============================================
def _tokenized_atom_spans(text):
	visible_text = _visible_label_text(text)
	spans = []
	i = 0
	length = len(visible_text)
	while i < length:
		char = visible_text[i]
		if not char.isalpha() or not char.isupper():
			i += 1
			continue
		start = i
		i += 1
		if i < length and visible_text[i].islower():
			i += 1
		symbol = visible_text[start:i]
		# Treat condensed hydrogens as decorations attached to the previous
		# heavy atom token so CH2OH yields token spans for C and OH.
		if symbol != "H":
			if i < length and visible_text[i] == "H":
				i += 1
				while i < length and visible_text[i].isdigit():
					i += 1
		while i < length and visible_text[i].isdigit():
			i += 1
		while i < length and visible_text[i] in "+-":
			i += 1
		spans.append((start, i))
	return spans


#============================================
def label_bbox(x, y, text, anchor, font_size, font_name=None):
	"""Compute axis-aligned bbox for a text label at (x, y)."""
	del font_name
	text_len = _visible_label_length(text)
	box_width = font_size * 0.75 * text_len
	top_offset = -font_size * 0.75
	bottom_offset = font_size * 0.125
	text_x, text_y = _label_text_origin(x, y, anchor, font_size, text_len)
	if anchor == "start":
		x1 = text_x
		x2 = text_x + box_width
	elif anchor == "end":
		x1 = text_x - box_width
		x2 = text_x
	else:
		x1 = text_x - box_width / 2.0
		x2 = text_x + box_width / 2.0
	y1 = text_y + top_offset
	y2 = text_y + bottom_offset
	return misc.normalize_coords((x1, y1, x2, y2))


#============================================
def label_bbox_from_text_origin(text_x, text_y, text, anchor, font_size, font_name=None):
	"""Compute label bbox when text origin and baseline coordinates are known."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_bbox(label_x, label_y, text, anchor, font_size, font_name=font_name)


#============================================
def label_attach_bbox_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		font_name=None):
	"""Compute attach bbox when text origin and baseline coordinates are known."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_attach_bbox(
		label_x,
		label_y,
		text,
		anchor,
		font_size,
		attach_atom=attach_atom,
		font_name=font_name,
	)


#============================================
def label_attach_bbox(x, y, text, anchor, font_size, attach_atom="first", font_name=None):
	"""Compute bbox for the first/last attachable atom token within a label."""
	if attach_atom not in ("first", "last"):
		raise ValueError(f"Invalid attach_atom value: {attach_atom!r}")
	full_bbox = label_bbox(x, y, text, anchor, font_size, font_name=font_name)
	spans = _tokenized_atom_spans(text)
	if len(spans) <= 1:
		return full_bbox
	if attach_atom == "last":
		start_index, end_index = spans[-1]
	else:
		start_index, end_index = spans[0]
	visible_len = _visible_label_length(text)
	if visible_len <= 1:
		return full_bbox
	x1, y1, x2, y2 = full_bbox
	char_width = (x2 - x1) / float(visible_len)
	attach_x1 = x1 + start_index * char_width
	attach_x2 = x1 + end_index * char_width
	return misc.normalize_coords((attach_x1, y1, attach_x2, y2))


#============================================
def clip_bond_to_bbox(bond_start, bond_end, bbox):
	"""Clip bond_end to bbox edge when bond_end lies inside bbox."""
	x1, y1, x2, y2 = misc.normalize_coords(bbox)
	end_x, end_y = bond_end
	is_inside = x1 <= end_x <= x2 and y1 <= end_y <= y2
	if not is_inside:
		return bond_end
	start_x, start_y = bond_start
	if start_x == end_x and start_y == end_y:
		return bond_end
	return geometry.intersection_of_line_and_rect(
		(start_x, start_y, end_x, end_y),
		(x1, y1, x2, y2),
	)


#============================================
def bbox_center(bbox):
	"""Return center point of an axis-aligned bbox."""
	x1, y1, x2, y2 = misc.normalize_coords(bbox)
	return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


#============================================
def directional_attach_edge_intersection(bond_start, attach_bbox, attach_target):
	"""Return directional token-edge endpoint from bond_start toward attach_target.

	Horizontal-dominant approaches terminate on left/right token edges, while
	vertical-dominant approaches terminate on top/bottom edges.
	"""
	x1, y1, x2, y2 = misc.normalize_coords(attach_bbox)
	target_x, target_y = attach_target
	if not (x1 <= target_x <= x2 and y1 <= target_y <= y2):
		target_x, target_y = bbox_center((x1, y1, x2, y2))
	start_x, start_y = bond_start
	dx = target_x - start_x
	dy = target_y - start_y
	abs_dx = abs(dx)
	abs_dy = abs(dy)
	if abs_dx <= 1e-12 and abs_dy <= 1e-12:
		return (target_x, target_y)
	if abs_dx >= abs_dy:
		if abs_dx <= 1e-12:
			return clip_bond_to_bbox((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
		edge_x = x1 if dx > 0.0 else x2
		t_value = (edge_x - start_x) / dx
		y_value = start_y + (dy * t_value)
		y_value = min(max(y_value, y1), y2)
		return (edge_x, y_value)
	if abs_dy <= 1e-12:
		return clip_bond_to_bbox((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
	edge_y = y1 if dy > 0.0 else y2
	t_value = (edge_y - start_y) / dy
	x_value = start_x + (dx * t_value)
	x_value = min(max(x_value, x1), x2)
	return (x_value, edge_y)


#============================================
def _resolved_vertex_label_layout(vertex, show_hydrogens_on_hetero, font_size, font_name):
	if not vertex_is_shown(vertex):
		return None
	text = vertex_label_text(vertex, show_hydrogens_on_hetero)
	if not text:
		return None
	label_anchor = vertex.properties_.get("label_anchor")
	auto_anchor = label_anchor is None
	if label_anchor is None:
		label_anchor = "start"
	text_len = _visible_label_length(text)
	if auto_anchor and text_len == 1:
		label_anchor = "middle"
	bbox = label_bbox(
		vertex.x,
		vertex.y,
		text,
		label_anchor,
		font_size,
		font_name=font_name,
	)
	text_origin = _label_text_origin(vertex.x, vertex.y, label_anchor, font_size, text_len)
	return {
		"text": text,
		"anchor": label_anchor,
		"text_len": text_len,
		"bbox": bbox,
		"text_origin": text_origin,
	}


#============================================
def _transform_bbox(bbox, transform_xy):
	if transform_xy is None:
		return bbox
	x1, y1, x2, y2 = bbox
	tx1, ty1 = transform_xy(x1, y1)
	tx2, ty2 = transform_xy(x2, y2)
	return misc.normalize_coords((tx1, ty1, tx2, ty2))


#============================================
def build_vertex_ops(vertex, transform_xy=None, show_hydrogens_on_hetero=False,
		color_atoms=True, atom_colors=None, font_name="Arial", font_size=16):
	layout = _resolved_vertex_label_layout(
		vertex,
		show_hydrogens_on_hetero=show_hydrogens_on_hetero,
		font_size=font_size,
		font_name=font_name,
	)
	if layout is None:
		return []

	def transform_point(x, y):
		if transform_xy:
			return transform_xy(x, y)
		return (x, y)

	ops = []
	text = layout["text"]
	label_anchor = layout["anchor"]
	x1, y1, x2, y2 = layout["bbox"]
	x, y = layout["text_origin"]
	center_x = (x1 + x2) / 2.0

	if vertex.multiplicity in (2, 3):
		center = transform_point(center_x, y - 17)
		ops.append(render_ops.CircleOp(
			center=center,
			radius=3,
			fill="#000",
			stroke="#fff",
			stroke_width=1.0,
		))
		if vertex.multiplicity == 3:
			center = transform_point(center_x, y + 5)
			ops.append(render_ops.CircleOp(
				center=center,
				radius=3,
				fill="#000",
				stroke="#fff",
				stroke_width=1.0,
			))

	points = (
		transform_point(x1, y1),
		transform_point(x2, y1),
		transform_point(x2, y2),
		transform_point(x1, y2),
	)
	ops.append(render_ops.PolygonOp(
		points=points,
		fill="#fff",
		stroke="#fff",
		stroke_width=1.0,
	))

	if color_atoms and atom_colors:
		color = render_ops.color_to_hex(atom_colors.get(vertex.symbol, (0, 0, 0))) or "#000"
	else:
		color = "#000"

	text_x, text_y = transform_point(x, y)
	ops.append(render_ops.TextOp(
		x=text_x,
		y=text_y,
		text=text,
		font_size=font_size,
		font_name=font_name,
		anchor=label_anchor,
		weight="bold",
		color=color,
	))
	return ops


_DEFAULT_STYLE = {
	"line_width": 2.0,
	"bond_width": 6.0,
	"wedge_width": 6.0,
	"bold_line_width_multiplier": 1.2,
	"bond_second_line_shortening": 0.0,
	"color_atoms": True,
	"color_bonds": True,
	"atom_colors": None,
	"show_hydrogens_on_hetero": False,
	"font_name": "Arial",
	"font_size": 16.0,
	"show_carbon_symbol": False,
}


#============================================
def _resolve_style(style):
	resolved = dict(_DEFAULT_STYLE)
	if style:
		resolved.update(style)
	return resolved


#============================================
def _edge_points(mol, transform_xy):
	points = {}
	for edge in mol.edges:
		v1, v2 = edge.vertices
		if transform_xy:
			points[edge] = (transform_xy(v1.x, v1.y), transform_xy(v2.x, v2.y))
		else:
			points[edge] = ((v1.x, v1.y), (v2.x, v2.y))
	return points


#============================================
def molecule_to_ops(mol, style=None, transform_xy=None):
	"""Convert one molecule into a render-ops list for SVG/Cairo painters."""
	if mol is None:
		return []
	used_style = _resolve_style(style)
	shown_vertices = set()
	for vertex in mol.vertices:
		if used_style["show_carbon_symbol"] and vertex.symbol == "C":
			shown_vertices.add(vertex)
		elif vertex_is_shown(vertex):
			shown_vertices.add(vertex)
	bond_coords = _edge_points(mol, transform_xy=transform_xy)
	label_bboxes = {}
	attach_bboxes = {}
	for vertex in shown_vertices:
		layout = _resolved_vertex_label_layout(
			vertex,
			show_hydrogens_on_hetero=bool(used_style["show_hydrogens_on_hetero"]),
			font_size=float(used_style["font_size"]),
			font_name=str(used_style["font_name"]),
		)
		if layout is None:
			continue
		label_bboxes[vertex] = _transform_bbox(layout["bbox"], transform_xy)
		if len(_tokenized_atom_spans(layout["text"])) <= 1:
			continue
		attach_mode = vertex.properties_.get("attach_atom", "first")
		attach_bbox = label_attach_bbox(
			vertex.x,
			vertex.y,
			layout["text"],
			layout["anchor"],
			float(used_style["font_size"]),
			attach_atom=attach_mode,
			font_name=str(used_style["font_name"]),
		)
		attach_bboxes[vertex] = _transform_bbox(attach_bbox, transform_xy)
	context = BondRenderContext(
		molecule=mol,
		line_width=float(used_style["line_width"]),
		bond_width=float(used_style["bond_width"]),
		wedge_width=float(used_style["wedge_width"]),
		bold_line_width_multiplier=float(used_style["bold_line_width_multiplier"]),
		bond_second_line_shortening=float(used_style["bond_second_line_shortening"]),
		color_bonds=bool(used_style["color_bonds"]),
		atom_colors=used_style["atom_colors"],
		shown_vertices=shown_vertices,
		bond_coords=bond_coords,
		bond_coords_provider=bond_coords.get,
		point_for_atom=None,
		label_bboxes=label_bboxes,
		attach_bboxes=attach_bboxes,
	)
	ops = []
	for edge in mol.edges:
		start, end = bond_coords[edge]
		ops.extend(build_bond_ops(edge, start, end, context))
	for vertex in mol.vertices:
		vertex_ops = build_vertex_ops(
			vertex,
			transform_xy=transform_xy,
			show_hydrogens_on_hetero=bool(used_style["show_hydrogens_on_hetero"]),
			color_atoms=bool(used_style["color_atoms"]),
			atom_colors=used_style["atom_colors"],
			font_name=str(used_style["font_name"]),
			font_size=float(used_style["font_size"]),
		)
		ops.extend(vertex_ops)
	return ops
