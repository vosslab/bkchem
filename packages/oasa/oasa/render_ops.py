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

"""Render ops for shared Cairo/SVG drawing."""

# Standard Library
import dataclasses
import json
import math

# local repo modules
from . import dom_extensions
from . import geometry
from . import misc
from . import wedge_geometry


#============================================
@dataclasses.dataclass(frozen=True)
class LineOp:
	p1: tuple[float, float]
	p2: tuple[float, float]
	width: float
	cap: str = "butt"
	join: str = ""
	color: object | None = None
	z: int = 0
	op_id: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class PolygonOp:
	points: tuple[tuple[float, float], ...]
	fill: object | None
	stroke: object | None = None
	stroke_width: float = 0.0
	z: int = 0
	op_id: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class CircleOp:
	center: tuple[float, float]
	radius: float
	fill: object | None
	stroke: object | None = None
	stroke_width: float = 0.0
	z: int = 0
	op_id: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class PathOp:
	commands: tuple[tuple[str, tuple[float, ...] | None], ...]
	fill: object | None
	stroke: object | None = None
	stroke_width: float = 0.0
	cap: str = ""
	join: str = ""
	z: int = 0
	op_id: str | None = None


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


#============================================
def _normalize_hex_color(text):
	if text.lower() == "none":
		return "none"
	if not text.startswith("#"):
		return text
	value = text[1:]
	if len(value) == 3:
		value = "".join(ch * 2 for ch in value)
	if len(value) != 6:
		return text
	return "#" + value.lower()


#============================================
def _color_tuple_to_hex(color):
	if len(color) not in (3, 4):
		return None
	values = list(color[:3])
	scale = 255.0
	if max(values) <= 1.0:
		scale = 255.0
	else:
		scale = 1.0
	channels = []
	for value in values:
		channel = int(round(value * scale))
		channel = max(0, min(channel, 255))
		channels.append(channel)
	return "#%02x%02x%02x" % (channels[0], channels[1], channels[2])


#============================================
def color_to_hex(color):
	if color is None:
		return None
	if isinstance(color, str):
		text = color.strip()
		if not text:
			return None
		return _normalize_hex_color(text)
	if isinstance(color, (tuple, list)):
		return _color_tuple_to_hex(color)
	return None


#============================================
def _color_to_rgba(color):
	if color is None:
		return None
	if isinstance(color, str):
		text = color.strip()
		if not text or text.lower() == "none":
			return None
		if not text.startswith("#"):
			return None
		value = text[1:]
		if len(value) == 3:
			value = "".join(ch * 2 for ch in value)
		if len(value) != 6:
			return None
		r = int(value[0:2], 16) / 255.0
		g = int(value[2:4], 16) / 255.0
		b = int(value[4:6], 16) / 255.0
		return (r, g, b, 1.0)
	if isinstance(color, (tuple, list)):
		if len(color) not in (3, 4):
			return None
		scale = 1.0
		values = list(color)
		if max(values) > 1.0:
			scale = 1.0 / 255.0
		r = values[0] * scale
		g = values[1] * scale
		b = values[2] * scale
		a = values[3] if len(values) == 4 else 1.0
		if max(r, g, b, a) > 1.0:
			r = min(r, 1.0)
			g = min(g, 1.0)
			b = min(b, 1.0)
			a = min(a, 1.0)
		return (r, g, b, a)
	return None


#============================================
def sort_ops(ops):
	ordered = []
	for index, op in sorted(enumerate(ops), key=lambda item: (getattr(item[1], "z", 0), item[0])):
		ordered.append(op)
	return ordered


#============================================
def _serialize_number(value, digits):
	if isinstance(value, int):
		return value
	if isinstance(value, float):
		return round(value, digits)
	return value


#============================================
def _serialize_list(value, digits):
	return [ _serialize_number(item, digits) for item in value ]


#============================================
def ops_to_json_dict(ops, round_digits=3):
	serialized = []
	for op in sort_ops(ops):
		if isinstance(op, LineOp):
			entry = {
				"kind": "line",
				"p1": _serialize_list(op.p1, round_digits),
				"p2": _serialize_list(op.p2, round_digits),
				"width": _serialize_number(op.width, round_digits),
				"cap": op.cap,
				"join": op.join,
				"color": color_to_hex(op.color),
				"z": op.z,
			}
		elif isinstance(op, PolygonOp):
			entry = {
				"kind": "polygon",
				"points": [ _serialize_list(point, round_digits) for point in op.points ],
				"fill": color_to_hex(op.fill),
				"stroke": color_to_hex(op.stroke),
				"stroke_width": _serialize_number(op.stroke_width, round_digits),
				"z": op.z,
			}
		elif isinstance(op, CircleOp):
			entry = {
				"kind": "circle",
				"center": _serialize_list(op.center, round_digits),
				"radius": _serialize_number(op.radius, round_digits),
				"fill": color_to_hex(op.fill),
				"stroke": color_to_hex(op.stroke),
				"stroke_width": _serialize_number(op.stroke_width, round_digits),
				"z": op.z,
			}
		elif isinstance(op, PathOp):
			commands = []
			for cmd, payload in op.commands:
				if payload is None:
					commands.append([cmd, None])
					continue
				commands.append([cmd, [ _serialize_number(item, round_digits) for item in payload ]])
			entry = {
				"kind": "path",
				"commands": commands,
				"fill": color_to_hex(op.fill),
				"stroke": color_to_hex(op.stroke),
				"stroke_width": _serialize_number(op.stroke_width, round_digits),
				"cap": op.cap,
				"join": op.join,
				"z": op.z,
			}
		else:
			continue
		if op.op_id:
			entry["id"] = op.op_id
		serialized.append(entry)
	return serialized


#============================================
def ops_to_json_text(ops, round_digits=3):
	return json.dumps(ops_to_json_dict(ops, round_digits=round_digits), indent=2, sort_keys=True)


#============================================
def _set_cairo_color(context, color):
	rgba = _color_to_rgba(color)
	if not rgba:
		return False
	r, g, b, a = rgba
	if a >= 1.0:
		context.set_source_rgb(r, g, b)
	else:
		context.set_source_rgba(r, g, b, a)
	return True


#============================================
def ops_to_svg(parent, ops):
	for op in sort_ops(ops):
		if isinstance(op, LineOp):
			color = color_to_hex(op.color) or "#000"
			attrs = (( 'x1', str(op.p1[0])),
					( 'y1', str(op.p1[1])),
					( 'x2', str(op.p2[0])),
					( 'y2', str(op.p2[1])),
					( 'stroke-width', str(op.width)),
					( 'stroke', color))
			if op.cap:
				attrs += (( 'stroke-linecap', op.cap),)
			if op.join:
				attrs += (( 'stroke-linejoin', op.join),)
			dom_extensions.elementUnder(parent, 'line', attrs)
			continue
		if isinstance(op, PolygonOp):
			points_text = " ".join("%s,%s" % (x, y) for x, y in op.points)
			fill = color_to_hex(op.fill) or "none"
			attrs = (( 'points', points_text),
					( 'fill', fill))
			stroke = color_to_hex(op.stroke)
			if stroke:
				attrs += (( 'stroke', stroke),
						( 'stroke-width', str(op.stroke_width)))
			else:
				attrs += (( 'stroke', "none"),)
			dom_extensions.elementUnder(parent, 'polygon', attrs)
			continue
		if isinstance(op, CircleOp):
			fill = color_to_hex(op.fill) or "none"
			attrs = (( 'cx', str(op.center[0])),
					( 'cy', str(op.center[1])),
					( 'r', str(op.radius)),
					( 'fill', fill))
			stroke = color_to_hex(op.stroke)
			if stroke:
				attrs += (( 'stroke', stroke),
						( 'stroke-width', str(op.stroke_width)))
			else:
				attrs += (( 'stroke', "none"),)
			dom_extensions.elementUnder(parent, 'circle', attrs)
			continue
		if isinstance(op, PathOp):
			d_parts = []
			for cmd, payload in op.commands:
				if cmd == "Z":
					d_parts.append("Z")
					continue
				if cmd == "M":
					d_parts.append("M %s %s" % (payload[0], payload[1]))
					continue
				if cmd == "L":
					d_parts.append("L %s %s" % (payload[0], payload[1]))
					continue
				if cmd == "ARC":
					cx, cy, r, angle1, angle2 = payload
					x = cx + r * math.cos(angle2)
					y = cy + r * math.sin(angle2)
					large_arc = 1 if abs(angle2 - angle1) > math.pi else 0
					sweep = 1 if angle2 >= angle1 else 0
					d_parts.append("A %s %s 0 %s %s %s %s" % (r, r, large_arc, sweep, x, y))
			fill = color_to_hex(op.fill) or "none"
			attrs = (( 'd', " ".join(d_parts)),
					( 'fill', fill))
			stroke = color_to_hex(op.stroke)
			if stroke:
				attrs += (( 'stroke', stroke),
						( 'stroke-width', str(op.stroke_width)))
			else:
				attrs += (( 'stroke', "none"),)
			if op.cap:
				attrs += (( 'stroke-linecap', op.cap),)
			if op.join:
				attrs += (( 'stroke-linejoin', op.join),)
			dom_extensions.elementUnder(parent, 'path', attrs)


#============================================
def ops_to_cairo(context, ops):
	for op in sort_ops(ops):
		if isinstance(op, LineOp):
			context.set_line_width(op.width)
			if op.cap == "round":
				context.set_line_cap(1)
			elif op.cap == "square":
				context.set_line_cap(2)
			else:
				context.set_line_cap(0)
			if op.join == "round":
				context.set_line_join(1)
			elif op.join == "bevel":
				context.set_line_join(2)
			else:
				context.set_line_join(0)
			if not _set_cairo_color(context, op.color):
				context.set_source_rgb(0, 0, 0)
			context.move_to(op.p1[0], op.p1[1])
			context.line_to(op.p2[0], op.p2[1])
			context.stroke()
			continue
		if isinstance(op, PolygonOp):
			points = list(op.points)
			if not points:
				continue
			context.new_path()
			context.move_to(points[0][0], points[0][1])
			for x, y in points[1:]:
				context.line_to(x, y)
			context.close_path()
			if op.fill and op.fill != "none":
				if not _set_cairo_color(context, op.fill):
					context.set_source_rgb(0, 0, 0)
				if op.stroke:
					context.fill_preserve()
				else:
					context.fill()
			if op.stroke:
				if not _set_cairo_color(context, op.stroke):
					context.set_source_rgb(0, 0, 0)
				context.set_line_width(op.stroke_width)
				context.stroke()
			continue
		if isinstance(op, CircleOp):
			context.new_path()
			context.arc(op.center[0], op.center[1], op.radius, 0, 2 * math.pi)
			if op.fill and op.fill != "none":
				if not _set_cairo_color(context, op.fill):
					context.set_source_rgb(0, 0, 0)
				if op.stroke:
					context.fill_preserve()
				else:
					context.fill()
			if op.stroke:
				if not _set_cairo_color(context, op.stroke):
					context.set_source_rgb(0, 0, 0)
				context.set_line_width(op.stroke_width)
				context.stroke()
			continue
		if isinstance(op, PathOp):
			context.new_path()
			for cmd, payload in op.commands:
				if cmd == "Z":
					context.close_path()
					continue
				if cmd == "M":
					context.move_to(payload[0], payload[1])
					continue
				if cmd == "L":
					context.line_to(payload[0], payload[1])
					continue
				if cmd == "ARC":
					cx, cy, r, angle1, angle2 = payload
					if angle2 >= angle1:
						context.arc(cx, cy, r, angle1, angle2)
					else:
						context.arc_negative(cx, cy, r, angle1, angle2)
			if op.fill and op.fill != "none":
				if not _set_cairo_color(context, op.fill):
					context.set_source_rgb(0, 0, 0)
				if op.stroke:
					context.fill_preserve()
				else:
					context.fill()
			if op.stroke:
				if op.cap == "round":
					context.set_line_cap(1)
				elif op.cap == "square":
					context.set_line_cap(2)
				else:
					context.set_line_cap(0)
				if op.join == "round":
					context.set_line_join(1)
				elif op.join == "bevel":
					context.set_line_join(2)
				else:
					context.set_line_join(0)
				if not _set_cairo_color(context, op.stroke):
					context.set_source_rgb(0, 0, 0)
				context.set_line_width(op.stroke_width)
				context.stroke()


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
	return [LineOp(start, end, width=width, cap="round", color=color)]


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
	return color_to_hex(color)


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
		color1 = color_to_hex(context.atom_colors.get(v1.symbol, (0, 0, 0))) or "#000"
		color2 = color_to_hex(context.atom_colors.get(v2.symbol, (0, 0, 0))) or "#000"
		if has_shown_vertex and color1 != color2:
			return color1, color2, True
		return color1, color2, False
	return "#000", "#000", False


#============================================
def _line_ops(start, end, width, color1, color2, gradient, cap):
	if gradient and color1 and color2 and color1 != color2:
		mid = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
		return [
			LineOp(start, mid, width=width, cap="butt", color=color1),
			LineOp(mid, end, width=width, cap="butt", color=color2),
		]
	return [LineOp(start, end, width=width, cap=cap, color=color1 or "#000")]


#============================================
def _rounded_wedge_ops(start, end, line_width, wedge_width, color):
	geom = wedge_geometry.rounded_wedge_geometry(start, end, wedge_width, line_width)
	return [PathOp(commands=geom["path_commands"], fill=color or "#000")]


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
		ops.append(LineOp((coords[0], coords[1]), (coords[2], coords[3]),
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
	return [PathOp(commands=tuple(commands), fill="none", stroke=color or "#000",
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
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="butt"))
			return ops
		for i in (1, -1):
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], i * context.bond_width * 0.5
			)
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
