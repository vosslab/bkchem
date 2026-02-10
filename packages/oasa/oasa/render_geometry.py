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
	label_targets: dict | None = None
	attach_targets: dict | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class AttachConstraints:
	"""Shared attachment constraints for endpoint resolution and paint legality."""
	line_width: float = 0.0
	clearance: float = 0.0
	vertical_lock: bool = False
	direction_policy: str = "auto"


#============================================
@dataclasses.dataclass(frozen=True)
class AttachTarget:
	"""Attachment target primitive used by shared endpoint resolution."""
	kind: str
	box: tuple[float, float, float, float] | None = None
	center: tuple[float, float] | None = None
	radius: float | None = None
	p1: tuple[float, float] | None = None
	p2: tuple[float, float] | None = None
	targets: tuple | None = None

	def centroid(self):
		"""Return centroid-like interior hint for this target primitive."""
		if self.kind == "box":
			if self.box is None:
				raise ValueError("Box attach target requires box coordinates")
			x1, y1, x2, y2 = misc.normalize_coords(self.box)
			return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
		if self.kind == "circle":
			if self.center is None:
				raise ValueError("Circle attach target requires center coordinates")
			return self.center
		if self.kind == "segment":
			if self.p1 is None or self.p2 is None:
				raise ValueError("Segment attach target requires p1 and p2")
			return ((self.p1[0] + self.p2[0]) / 2.0, (self.p1[1] + self.p2[1]) / 2.0)
		if self.kind == "composite":
			children = self.targets or ()
			if not children:
				raise ValueError("Composite attach target requires at least one child target")
			first_child = _coerce_attach_target(children[0])
			return first_child.centroid()
		raise ValueError(f"Unsupported attach target kind: {self.kind!r}")

	def contains(self, point, epsilon=0.0):
		"""Return True when point is in strict interior for this target."""
		if self.kind == "box":
			if self.box is None:
				raise ValueError("Box attach target requires box coordinates")
			x1, y1, x2, y2 = misc.normalize_coords(self.box)
			return (x1 + epsilon) < point[0] < (x2 - epsilon) and (y1 + epsilon) < point[1] < (y2 - epsilon)
		if self.kind == "circle":
			if self.center is None or self.radius is None:
				raise ValueError("Circle attach target requires center and radius")
			cx, cy = self.center
			distance = math.hypot(point[0] - cx, point[1] - cy)
			return distance < max(0.0, float(self.radius) - epsilon)
		if self.kind == "segment":
			return False
		if self.kind == "composite":
			return any(_coerce_attach_target(child).contains(point, epsilon=epsilon) for child in (self.targets or ()))
		raise ValueError(f"Unsupported attach target kind: {self.kind!r}")

	def boundary_intersection(self, bond_start, interior_hint=None, constraints=None):
		"""Resolve one boundary endpoint from bond_start toward this target."""
		return resolve_attach_endpoint(
			bond_start=bond_start,
			target=self,
			interior_hint=interior_hint,
			constraints=constraints,
		)


#============================================
def make_box_target(bbox: tuple[float, float, float, float]) -> AttachTarget:
	"""Construct one box attachment target."""
	return AttachTarget(kind="box", box=misc.normalize_coords(bbox))


#============================================
def make_circle_target(center: tuple[float, float], radius: float) -> AttachTarget:
	"""Construct one circle attachment target."""
	return AttachTarget(kind="circle", center=center, radius=float(radius))


#============================================
def make_segment_target(p1: tuple[float, float], p2: tuple[float, float]) -> AttachTarget:
	"""Construct one segment attachment target."""
	return AttachTarget(kind="segment", p1=p1, p2=p2)


#============================================
def make_composite_target(targets: list[AttachTarget] | tuple[AttachTarget, ...]) -> AttachTarget:
	"""Construct one ordered composite target with primary-to-fallback targets."""
	return AttachTarget(kind="composite", targets=tuple(targets))


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
def _context_attach_target_for_vertex(context, vertex):
	"""Resolve attachment target for one vertex."""
	if context.attach_targets and vertex in context.attach_targets:
		return _coerce_attach_target(context.attach_targets[vertex])
	if context.label_targets and vertex in context.label_targets:
		return _coerce_attach_target(context.label_targets[vertex])
	return None


#============================================
def _clip_to_target(bond_start, target):
	"""Clip one endpoint to one target using default Phase B policy."""
	if target is None:
		return bond_start
	return resolve_attach_endpoint(
		bond_start=bond_start,
		target=target,
		interior_hint=target.centroid(),
		constraints=AttachConstraints(direction_policy="auto"),
	)


#============================================
def build_bond_ops(edge, start, end, context):
	if start is None or end is None:
		return []
	v1, v2 = edge.vertices
	target_v1 = _context_attach_target_for_vertex(context, v1)
	target_v2 = _context_attach_target_for_vertex(context, v2)
	if target_v1 is not None:
		start = _clip_to_target(end, target_v1)
	if target_v2 is not None:
		end = _clip_to_target(start, target_v2)
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
			if target_v1 is not None:
				x1, y1 = _clip_to_target((x2, y2), target_v1)
			if target_v2 is not None:
				x2, y2 = _clip_to_target((x1, y1), target_v2)
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="butt"))
			return ops
		for i in (1, -1):
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], i * context.bond_width * 0.5
			)
			if target_v1 is not None:
				x1, y1 = _clip_to_target((x2, y2), target_v1)
			if target_v2 is not None:
				x2, y2 = _clip_to_target((x1, y1), target_v2)
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
	"""Return decorated token spans for visible label text.

	Decorated spans include compact hydrogen/count suffixes (for example `CH2`)
	so existing first/last-token attachment behavior remains stable.
	"""
	return [entry["decorated_span"] for entry in _tokenized_atom_entries(text)]


#============================================
def _label_box_coords(x, y, text, anchor, font_size, font_name=None):
	"""Compute axis-aligned label box coordinates at one label anchor point."""
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
def label_target(x, y, text, anchor, font_size, font_name=None):
	"""Compute one label attachment target at (x, y)."""
	return make_box_target(_label_box_coords(x, y, text, anchor, font_size, font_name=font_name))


#============================================
def label_target_from_text_origin(text_x, text_y, text, anchor, font_size, font_name=None):
	"""Compute one label attachment target from text-origin coordinates."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_target(label_x, label_y, text, anchor, font_size, font_name=font_name)


#============================================
def label_attach_target_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		font_name=None):
	"""Compute one token-attach target from text-origin coordinates."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_attach_target(
		label_x,
		label_y,
		text,
		anchor,
		font_size,
		attach_atom=attach_atom,
		attach_element=attach_element,
		font_name=font_name,
	)


def _label_attach_box_coords(
		x,
		y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		font_name=None):
	"""Compute box coordinates for one selected attachable atom token."""
	if attach_atom is None:
		attach_atom = "first"
	if attach_atom not in ("first", "last"):
		raise ValueError(f"Invalid attach_atom value: {attach_atom!r}")
	full_bbox = _label_box_coords(x, y, text, anchor, font_size, font_name=font_name)
	entries = _tokenized_atom_entries(text)
	spans = [entry["decorated_span"] for entry in entries]
	if len(spans) <= 1:
		return full_bbox
	selected_span = None
	if attach_element is not None:
		if not isinstance(attach_element, str) or not attach_element.strip():
			raise ValueError(f"Invalid attach_element value: {attach_element!r}")
		normalized = _normalize_element_symbol(attach_element)
		# Formula-aware attachment: attach_element resolves to the core element
		# glyph span (for example just "C" in CH2OH), not the decorated token.
		matched = [entry["core_span"] for entry in entries if entry["symbol"] == normalized]
		if matched:
			if attach_atom == "last":
				selected_span = matched[-1]
			else:
				selected_span = matched[0]
	if selected_span is None:
		if attach_atom == "last":
			selected_span = spans[-1]
		else:
			selected_span = spans[0]
	start_index, end_index = selected_span
	visible_len = _visible_label_length(text)
	if visible_len <= 1:
		return full_bbox
	x1, y1, x2, y2 = full_bbox
	# Use glyph-width metrics for attach-span projection instead of full bbox
	# width so core element targeting (for example C in CH2OH) stays aligned with
	# rendered glyph centers.
	glyph_char_width = font_size * 0.60
	glyph_width = glyph_char_width * float(visible_len)
	text_x, _text_y = _label_text_origin(x, y, anchor, font_size, visible_len)
	if anchor == "start":
		glyph_x1 = text_x
	elif anchor == "end":
		glyph_x1 = text_x - glyph_width
	else:
		glyph_x1 = text_x - (glyph_width / 2.0)
	attach_x1 = glyph_x1 + start_index * glyph_char_width
	attach_x2 = glyph_x1 + end_index * glyph_char_width
	# Clamp to full label bbox so attach targets cannot escape label bounds.
	attach_x1 = min(max(attach_x1, x1), x2)
	attach_x2 = min(max(attach_x2, x1), x2)
	return misc.normalize_coords((attach_x1, y1, attach_x2, y2))


#============================================
def label_attach_target(
		x,
		y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		font_name=None):
	"""Compute one attach-token target within a label."""
	return make_box_target(
		_label_attach_box_coords(
			x,
			y,
			text,
			anchor,
			font_size,
			attach_atom=attach_atom,
			attach_element=attach_element,
			font_name=font_name,
		)
	)


#============================================
def _normalize_element_symbol(symbol: str) -> str:
	"""Normalize one element symbol to canonical letter case."""
	text = str(symbol).strip()
	if len(text) == 1:
		return text.upper()
	return text[0].upper() + text[1:].lower()


#============================================
def _tokenized_atom_entries(text):
	"""Return atom token entries with core/decorated span information.

	Each entry exposes:
	- `core_span`: element-symbol-only span (for example `C` in `CH2`)
	- `decorated_span`: element plus compact suffix decoration span
	  (for example `CH2`)
	"""
	visible_text = _visible_label_text(text)
	entries = []
	length = len(visible_text)
	index = 0
	while index < length:
		char = visible_text[index]
		if not char.isupper():
			index += 1
			continue
		core_start = index
		index += 1
		if index < length and visible_text[index].islower():
			index += 1
		core_end = index
		symbol = visible_text[core_start:core_end]
		decorated_end = core_end
		# Optional atom count directly after the symbol, e.g. O3.
		while decorated_end < length and visible_text[decorated_end].isdigit():
			decorated_end += 1
		has_explicit_count = decorated_end > core_end
		# Condensed hydrogens belong to the decorated token unless this atom
		# already had an explicit numeric count (e.g. O3H should tokenize as O3 + H).
		if symbol != "H" and not has_explicit_count and decorated_end < length and visible_text[decorated_end] == "H":
			decorated_end += 1
			while decorated_end < length and visible_text[decorated_end].isdigit():
				decorated_end += 1
		# Optional trailing charge on terminal tokens, e.g. NH3+.
		if decorated_end < length and visible_text[decorated_end] in "+-":
			charge_end = decorated_end + 1
			while charge_end < length and visible_text[charge_end].isdigit():
				charge_end += 1
			if charge_end == length:
				decorated_end = charge_end
		entries.append(
			{
				"symbol": symbol,
				"core_span": (core_start, core_end),
				"decorated_span": (core_start, decorated_end),
			}
		)
		index = max(index, decorated_end)
	return entries


#============================================
def _clip_line_to_box(bond_start, bond_end, bbox):
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
def _box_center(bbox):
	"""Return center point of an axis-aligned bbox."""
	x1, y1, x2, y2 = misc.normalize_coords(bbox)
	return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


#============================================
def _expanded_box(bbox, margin):
	"""Return one bbox expanded by margin in all directions."""
	x1, y1, x2, y2 = misc.normalize_coords(bbox)
	return (x1 - margin, y1 - margin, x2 + margin, y2 + margin)


#============================================
def _resolve_direction_mode(direction_policy, dx, dy):
	"""Return directional mode: side or vertical."""
	if direction_policy == "vertical_preferred":
		return "vertical"
	if direction_policy == "side_preferred":
		return "side"
	return "side" if abs(dx) >= abs(dy) else "vertical"


#============================================
def directional_attach_edge_intersection(
		bond_start,
		attach_bbox,
		attach_target,
		direction_policy="auto"):
	"""Return directional token-edge endpoint from bond_start toward attach_target.

	Horizontal-dominant approaches terminate on left/right token edges, while
	vertical-dominant approaches terminate on top/bottom edges.
	"""
	x1, y1, x2, y2 = misc.normalize_coords(attach_bbox)
	target_x, target_y = attach_target
	if not (x1 <= target_x <= x2 and y1 <= target_y <= y2):
		target_x, target_y = _box_center((x1, y1, x2, y2))
	start_x, start_y = bond_start
	dx = target_x - start_x
	dy = target_y - start_y
	abs_dx = abs(dx)
	abs_dy = abs(dy)
	if abs_dx <= 1e-12 and abs_dy <= 1e-12:
		return (target_x, target_y)
	if direction_policy == "line":
		return _clip_line_to_box((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
	mode = _resolve_direction_mode(direction_policy, abs_dx, abs_dy)
	if mode == "side":
		if abs_dx <= 1e-12:
			return _clip_line_to_box((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
		edge_x = x1 if dx > 0.0 else x2
		t_value = (edge_x - start_x) / dx
		y_value = start_y + (dy * t_value)
		y_value = min(max(y_value, y1), y2)
		return (edge_x, y_value)
	if abs_dy <= 1e-12:
		return _clip_line_to_box((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
	edge_y = y1 if dy > 0.0 else y2
	t_value = (edge_y - start_y) / dy
	x_value = start_x + (dx * t_value)
	x_value = min(max(x_value, x1), x2)
	return (x_value, edge_y)


#============================================
def _coerce_attach_target(target):
	"""Normalize attach target inputs into AttachTarget objects."""
	if isinstance(target, AttachTarget):
		return target
	raise ValueError(f"Unsupported attach target: {target!r}")


#============================================
def _line_circle_intersection(start, end, center, radius):
	"""Return boundary intersection from segment start->end with one circle."""
	sx, sy = start
	ex, ey = end
	cx, cy = center
	dx = ex - sx
	dy = ey - sy
	a_value = (dx * dx) + (dy * dy)
	if a_value <= 1e-12:
		return None
	b_value = 2.0 * (((sx - cx) * dx) + ((sy - cy) * dy))
	c_value = ((sx - cx) ** 2) + ((sy - cy) ** 2) - (radius ** 2)
	discriminant = (b_value * b_value) - (4.0 * a_value * c_value)
	if discriminant < 0.0:
		return None
	sqrt_disc = math.sqrt(discriminant)
	t_candidates = sorted(
		[
			(-b_value - sqrt_disc) / (2.0 * a_value),
			(-b_value + sqrt_disc) / (2.0 * a_value),
		]
	)
	for t_value in t_candidates:
		if 0.0 <= t_value <= 1.0:
			return (sx + (dx * t_value), sy + (dy * t_value))
	return None


#============================================
def _circle_boundary_toward_target(start, center, radius, target=None):
	"""Return one circle boundary point from start toward target/center."""
	start_x, start_y = start
	center_x, center_y = center
	target_point = target or center
	intersect = _line_circle_intersection(start, target_point, center, radius)
	if intersect is not None:
		return intersect
	dx = center_x - start_x
	dy = center_y - start_y
	distance = math.hypot(dx, dy)
	if distance <= 1e-12:
		return (center_x + radius, center_y)
	return (
		center_x - ((dx / distance) * radius),
		center_y - ((dy / distance) * radius),
	)


#============================================
def _vertical_circle_boundary(start, center, radius, hint=None):
	"""Return circle boundary point on the vertical line through start.x."""
	start_x, start_y = start
	center_x, center_y = center
	delta_x = start_x - center_x
	squared = (radius * radius) - (delta_x * delta_x)
	if squared < 0.0:
		return None
	offset_y = math.sqrt(max(0.0, squared))
	candidates = [center_y - offset_y, center_y + offset_y]
	target_y = hint[1] if hint is not None else center_y
	direction = target_y - start_y
	if abs(direction) <= 1e-12:
		direction = center_y - start_y
	if direction >= 0.0:
		candidates.sort(key=lambda value: (value < start_y, abs(value - start_y)))
	else:
		candidates.sort(key=lambda value: (value > start_y, abs(value - start_y)))
	return (start_x, candidates[0])


#============================================
def _closest_point_on_segment(point, p1, p2):
	"""Return closest clamped point on one line segment."""
	px, py = point
	x1, y1 = p1
	x2, y2 = p2
	dx = x2 - x1
	dy = y2 - y1
	denominator = (dx * dx) + (dy * dy)
	if denominator <= 1e-12:
		return p1
	t_value = ((px - x1) * dx + (py - y1) * dy) / denominator
	t_value = max(0.0, min(1.0, t_value))
	return (x1 + (dx * t_value), y1 + (dy * t_value))


#============================================
def _line_intersection(p1, p2, p3, p4):
	"""Return intersection point of two infinite lines, or None when parallel."""
	x1, y1 = p1
	x2, y2 = p2
	x3, y3 = p3
	x4, y4 = p4
	denominator = ((x1 - x2) * (y3 - y4)) - ((y1 - y2) * (x3 - x4))
	if abs(denominator) <= 1e-12:
		return None
	det1 = (x1 * y2) - (y1 * x2)
	det2 = (x3 * y4) - (y3 * x4)
	ix = ((det1 * (x3 - x4)) - ((x1 - x2) * det2)) / denominator
	iy = ((det1 * (y3 - y4)) - ((y1 - y2) * det2)) / denominator
	return (ix, iy)


#============================================
def _point_to_segment_distance_sq(point, seg_start, seg_end):
	"""Return squared distance from one point to one line segment."""
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
def _orientation(p1, p2, p3):
	"""Return orientation sign for ordered triplet of points."""
	value = ((p2[1] - p1[1]) * (p3[0] - p2[0])) - ((p2[0] - p1[0]) * (p3[1] - p2[1]))
	if abs(value) <= 1e-12:
		return 0
	return 1 if value > 0.0 else 2


#============================================
def _on_segment(p1, p2, q):
	"""Return True when q lies on segment p1-p2."""
	return (
		min(p1[0], p2[0]) - 1e-12 <= q[0] <= max(p1[0], p2[0]) + 1e-12
		and min(p1[1], p2[1]) - 1e-12 <= q[1] <= max(p1[1], p2[1]) + 1e-12
	)


#============================================
def _segments_intersect(p1, p2, q1, q2):
	"""Return True when two finite line segments intersect."""
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
def _distance_sq_segment_to_segment(p1, p2, q1, q2):
	"""Return squared minimum distance between two finite line segments."""
	if _segments_intersect(p1, p2, q1, q2):
		return 0.0
	return min(
		_point_to_segment_distance_sq(p1, q1, q2),
		_point_to_segment_distance_sq(p2, q1, q2),
		_point_to_segment_distance_sq(q1, p1, p2),
		_point_to_segment_distance_sq(q2, p1, p2),
	)


#============================================
def _segment_distance_to_box_sq(seg_start, seg_end, box):
	"""Return squared minimum distance from one segment to one axis-aligned box."""
	x1, y1, x2, y2 = misc.normalize_coords(box)
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
def _capsule_intersects_target(seg_start, seg_end, half_width, target, epsilon):
	"""Return True when one stroked segment (capsule) penetrates target interior."""
	resolved = _coerce_attach_target(target)
	if resolved.kind == "box":
		x1, y1, x2, y2 = misc.normalize_coords(resolved.box)
		inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
		if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
			return False
		distance_sq = _segment_distance_to_box_sq(seg_start, seg_end, inner_box)
		return distance_sq < (half_width * half_width)
	if resolved.kind == "circle":
		effective_radius = max(0.0, float(resolved.radius) - epsilon)
		if effective_radius <= 0.0:
			return False
		distance_sq = _point_to_segment_distance_sq(resolved.center, seg_start, seg_end)
		radius_limit = half_width + effective_radius
		return distance_sq < (radius_limit * radius_limit)
	if resolved.kind == "segment":
		return False
	if resolved.kind == "composite":
		return any(
			_capsule_intersects_target(seg_start, seg_end, half_width, child, epsilon)
			for child in (resolved.targets or ())
		)
	raise ValueError(f"Unsupported attach target kind: {resolved.kind!r}")


#============================================
def _point_in_attach_target(point, target, epsilon=0.0):
	"""Return True when point is in strict interior of one target primitive."""
	resolved = _coerce_attach_target(target)
	return resolved.contains(point, epsilon=epsilon)


#============================================
def resolve_attach_endpoint(
		bond_start,
		target,
		interior_hint=None,
		constraints=None):
	"""Resolve one bond endpoint against one attachment target."""
	resolved_target = _coerce_attach_target(target)
	if constraints is None:
		constraints = AttachConstraints()
	line_width = max(0.0, float(constraints.line_width))
	clearance = max(0.0, float(constraints.clearance))
	margin = clearance + (line_width / 2.0)
	if resolved_target.kind == "composite":
		children = resolved_target.targets or ()
		if not children:
			raise ValueError("Composite attach target must include at least one child target")
		last_error = None
		for child in children:
			try:
				return resolve_attach_endpoint(
					bond_start=bond_start,
					target=child,
					interior_hint=interior_hint,
					constraints=constraints,
				)
			except ValueError as error:
				last_error = error
				continue
		if last_error is not None:
			raise last_error
		raise ValueError("Composite attach target did not resolve any child target")
	if resolved_target.kind == "box":
		attach_bbox = _expanded_box(resolved_target.box, margin)
		hint = interior_hint if interior_hint is not None else _box_center(attach_bbox)
		if constraints.vertical_lock:
			vertical = _vertical_box_intersection(bond_start, attach_bbox, hint)
			if vertical is not None:
				return vertical
		return directional_attach_edge_intersection(
			bond_start=bond_start,
			attach_bbox=attach_bbox,
			attach_target=hint,
			direction_policy=constraints.direction_policy,
		)
	if resolved_target.kind == "circle":
		radius = max(0.0, float(resolved_target.radius) + margin)
		center = resolved_target.center
		hint = interior_hint if interior_hint is not None else center
		if constraints.vertical_lock:
			vertical = _vertical_circle_boundary(bond_start, center, radius, hint=hint)
			if vertical is not None:
				return vertical
		return _circle_boundary_toward_target(bond_start, center, radius, target=hint)
	if resolved_target.kind == "segment":
		p1 = resolved_target.p1
		p2 = resolved_target.p2
		hint = interior_hint if interior_hint is not None else (
			(p1[0] + p2[0]) / 2.0,
			(p1[1] + p2[1]) / 2.0,
		)
		if constraints.vertical_lock:
			candidate = _line_intersection(
				(bond_start[0], bond_start[1]),
				(bond_start[0], bond_start[1] + 1.0),
				p1,
				p2,
			)
			if candidate is not None:
				return _closest_point_on_segment(candidate, p1, p2)
		intersection = _line_intersection(bond_start, hint, p1, p2)
		if intersection is not None:
			return _closest_point_on_segment(intersection, p1, p2)
		return _closest_point_on_segment(hint, p1, p2)
	raise ValueError(f"Unsupported attach target kind: {resolved_target.kind!r}")


#============================================
def _vertical_box_intersection(bond_start, attach_bbox, interior_hint):
	"""Return vertical-lock box boundary intersection, or None if unavailable."""
	x1, y1, x2, y2 = misc.normalize_coords(attach_bbox)
	start_x, start_y = bond_start
	if start_x < x1 or start_x > x2:
		return None
	hint_y = interior_hint[1]
	direction = hint_y - start_y
	candidates = [y1, y2]
	if abs(direction) <= 1e-12:
		candidates.sort(key=lambda value: abs(value - start_y))
	else:
		candidates.sort(
			key=lambda value: (
				((value - start_y) * direction) < 0.0,
				abs(value - start_y),
			)
		)
	return (start_x, candidates[0])


#============================================
def validate_attachment_paint(
		line_start,
		line_end,
		line_width,
		forbidden_regions,
		allowed_regions=None,
		epsilon=0.5):
	"""Return True when connector paint does not penetrate forbidden interiors."""
	if allowed_regions is None:
		allowed_regions = []
	half_width = max(0.0, float(line_width)) / 2.0
	# Fast analytic path: when no allowed carve-outs are active, validate paint
	# by continuous capsule-vs-target checks to avoid sampling false negatives.
	if not allowed_regions:
		for region in forbidden_regions:
			if _capsule_intersects_target(line_start, line_end, half_width, region, epsilon):
				return False
		return True
	# Fallback path with allowed carve-outs: keep explicit point checks so
	# forbidden-minus-allowed semantics stay identical to existing behavior.
	dx = line_end[0] - line_start[0]
	dy = line_end[1] - line_start[1]
	length = math.hypot(dx, dy)
	if length <= 1e-12:
		sample_points = [line_start]
	else:
		base_step = max(0.1, min(1.0, half_width * 0.5 if half_width > 0.0 else 0.25))
		steps = max(16, int(math.ceil(length / base_step)))
		sample_points = [
			(
				line_start[0] + (dx * (index / float(steps))),
				line_start[1] + (dy * (index / float(steps))),
			)
			for index in range(steps + 1)
		]
	offsets = [(0.0, 0.0)]
	if length > 1e-12 and half_width > 1e-12:
		nx = -dy / length
		ny = dx / length
		offsets.extend(
			[
				(nx * half_width, ny * half_width),
				(-nx * half_width, -ny * half_width),
			]
		)
	for base_point in sample_points:
		for ox, oy in offsets:
			point = (base_point[0] + ox, base_point[1] + oy)
			is_forbidden = any(
				_point_in_attach_target(point, region, epsilon=epsilon)
				for region in forbidden_regions
			)
			if not is_forbidden:
				continue
			is_allowed = any(
				_point_in_attach_target(point, region, epsilon=epsilon)
				for region in allowed_regions
			)
			if not is_allowed:
				return False
	return True


#============================================
def retreat_endpoint_until_legal(
		line_start,
		line_end,
		line_width,
		forbidden_regions,
		allowed_regions=None,
		epsilon=0.5,
		max_iterations=28):
	"""Retreat line_end toward line_start until attachment paint becomes legal."""
	if allowed_regions is None:
		allowed_regions = []
	if validate_attachment_paint(
			line_start=line_start,
			line_end=line_end,
			line_width=line_width,
			forbidden_regions=forbidden_regions,
			allowed_regions=allowed_regions,
			epsilon=epsilon):
		return line_end
	x_start, y_start = line_start
	x_end, y_end = line_end
	low = 0.0
	high = 1.0
	for _ in range(max(1, int(max_iterations))):
		mid = (low + high) * 0.5
		candidate = (
			x_start + ((x_end - x_start) * mid),
			y_start + ((y_end - y_start) * mid),
		)
		if validate_attachment_paint(
				line_start=line_start,
				line_end=candidate,
				line_width=line_width,
				forbidden_regions=forbidden_regions,
				allowed_regions=allowed_regions,
				epsilon=epsilon):
			low = mid
		else:
			high = mid
	if low <= 1e-12:
		return line_start
	safe_t = max(0.0, low - 1e-4)
	return (
		x_start + ((x_end - x_start) * safe_t),
		y_start + ((y_end - y_start) * safe_t),
	)


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
	bbox = label_target(
		vertex.x,
		vertex.y,
		text,
		label_anchor,
		font_size,
		font_name=font_name,
	).box
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
def _transform_target(target, transform_xy):
	"""Return one attachment target transformed by transform_xy."""
	resolved = _coerce_attach_target(target)
	if transform_xy is None:
		return resolved
	if resolved.kind == "box":
		return make_box_target(_transform_bbox(resolved.box, transform_xy))
	if resolved.kind == "circle":
		center = transform_xy(resolved.center[0], resolved.center[1])
		edge = transform_xy(resolved.center[0] + float(resolved.radius), resolved.center[1])
		radius = geometry.point_distance(center[0], center[1], edge[0], edge[1])
		return make_circle_target(center, radius)
	if resolved.kind == "segment":
		p1 = transform_xy(resolved.p1[0], resolved.p1[1])
		p2 = transform_xy(resolved.p2[0], resolved.p2[1])
		return make_segment_target(p1, p2)
	if resolved.kind == "composite":
		return make_composite_target([_transform_target(child, transform_xy) for child in (resolved.targets or ())])
	raise ValueError(f"Unsupported attach target kind: {resolved.kind!r}")


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
	label_targets = {}
	attach_targets = {}
	for vertex in shown_vertices:
		layout = _resolved_vertex_label_layout(
			vertex,
			show_hydrogens_on_hetero=bool(used_style["show_hydrogens_on_hetero"]),
			font_size=float(used_style["font_size"]),
			font_name=str(used_style["font_name"]),
		)
		if layout is None:
			continue
		label_target_obj = label_target(
			vertex.x,
			vertex.y,
			layout["text"],
			layout["anchor"],
			float(used_style["font_size"]),
			font_name=str(used_style["font_name"]),
		)
		label_target_obj = _transform_target(label_target_obj, transform_xy)
		label_targets[vertex] = label_target_obj
		if len(_tokenized_atom_spans(layout["text"])) <= 1:
			continue
		attach_mode = vertex.properties_.get("attach_atom", "first")
		attach_element = vertex.properties_.get("attach_element")
		attach_target_obj = label_attach_target(
			vertex.x,
			vertex.y,
			layout["text"],
			layout["anchor"],
			float(used_style["font_size"]),
			attach_atom=attach_mode,
			attach_element=attach_element,
			font_name=str(used_style["font_name"]),
		)
		attach_target_obj = _transform_target(attach_target_obj, transform_xy)
		attach_targets[vertex] = attach_target_obj
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
		label_targets=label_targets,
		attach_targets=attach_targets,
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
