#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Schematic Haworth renderer producing shared render_ops primitives."""

# Standard Library
import math
import re

# local repo modules
from . import _ring_template
from .. import geometry
from .. import render_ops
from .. import render_geometry as _render_geometry
from .spec import HaworthSpec
from . import renderer_geometry as _geom
from . import renderer_text as _text
from . import renderer_layout as _layout
from .renderer_config import (
	RING_SLOT_SEQUENCE,
	RING_RENDER_CONFIG,
	CARBON_NUMBER_VERTEX_WEIGHT,
OXYGEN_COLOR,
FURANOSE_TOP_UP_CLEARANCE_FACTOR,
FURANOSE_TOP_RIGHT_HYDROXYL_EXTRA_CLEARANCE_FACTOR,
)

# Use a tight epsilon for retreat binary-search convergence. The strict
# overlap acceptance gate remains 0.5 px in validate_attachment_paint.
RETREAT_SOLVER_EPSILON = 1e-3


#============================================
def _ring_slot_sequence(ring_type: str) -> tuple[str, ...]:
	"""Return canonical carbon-slot order for one ring type."""
	try:
		return RING_SLOT_SEQUENCE[ring_type]
	except KeyError as error:
		raise ValueError("Unsupported ring_type '%s'" % ring_type) from error


#============================================
def _ring_render_config(ring_type: str) -> dict:
	"""Return renderer geometry config for one ring type."""
	try:
		return RING_RENDER_CONFIG[ring_type]
	except KeyError as error:
		raise ValueError("Unsupported ring_type '%s'" % ring_type) from error


#============================================
def carbon_slot_map(spec: HaworthSpec) -> dict[str, str]:
	"""Map ring carbons from HaworthSpec to stable slot identifiers."""
	carbons = _ring_carbons(spec)
	anomeric = min(carbons)
	slot_sequence = _ring_slot_sequence(spec.ring_type)
	if len(carbons) != len(slot_sequence):
		raise ValueError(
			"HaworthSpec carbon count mismatch for ring_type=%s: expected %d, got %d"
			% (spec.ring_type, len(slot_sequence), len(carbons))
		)
	expected = list(range(anomeric, anomeric + len(slot_sequence)))
	if carbons != expected:
		raise ValueError(
			"HaworthSpec carbons must be contiguous from anomeric center; got %s"
			% (carbons,)
		)
	return {f"C{carbon}": slot_sequence[index] for index, carbon in enumerate(carbons)}


#============================================
def render(
		spec: HaworthSpec,
		bond_length: float = 30.0,
		font_size: float = 12.0,
		font_name: str = "sans-serif",
		show_carbon_numbers: bool = False,
		show_hydrogens: bool = True,
		line_color: str = "#000",
		label_color: str = "#000",
		bg_color: str = "#fff",
		oxygen_color: str = OXYGEN_COLOR) -> list:
	"""Render HaworthSpec into ring/substituent ops."""
	ring_cfg = _ring_render_config(spec.ring_type)
	ring_size = ring_cfg["ring_size"]
	slot_index = ring_cfg["slot_index"]
	slot_label_cfg = ring_cfg["slot_label_cfg"]
	front_edge_index = ring_cfg["front_edge_index"]
	o_index = ring_cfg["oxygen_index"]

	coords = _ring_template(ring_size, bond_length=bond_length)
	ops = []
	front_thickness = bond_length * 0.15
	back_thickness = bond_length * 0.04
	front_vertices = {front_edge_index, (front_edge_index + 1) % ring_size}
	adjacent = {(front_edge_index - 1) % ring_size, (front_edge_index + 1) % ring_size}
	ring_block_polygons = []
	ox, oy = coords[o_index]
	oxygen_text_y = oy + (font_size * 0.35)
	oxygen_label_target = _render_geometry.label_target_from_text_origin(
		text_x=ox,
		text_y=oxygen_text_y,
		text="O",
		anchor="middle",
		font_size=font_size,
		font_name=font_name,
	)
	oxygen_exclusion_center = (
		(oxygen_label_target.box[0] + oxygen_label_target.box[2]) * 0.5,
		(oxygen_label_target.box[1] + oxygen_label_target.box[3]) * 0.5,
	)

	for edge_index in range(ring_size):
		start_index = edge_index
		end_index = (edge_index + 1) % ring_size
		p1 = coords[start_index]
		p2 = coords[end_index]
		if edge_index == front_edge_index:
			t1 = front_thickness
			t2 = front_thickness
		elif edge_index in adjacent:
			t1 = back_thickness
			t2 = back_thickness
			if start_index in front_vertices:
				t1 = front_thickness
			elif end_index in front_vertices:
				t2 = front_thickness
		else:
			t1 = back_thickness
			t2 = back_thickness
		touches_oxygen = (start_index == o_index or end_index == o_index)
		if touches_oxygen:
			if start_index == o_index:
				exclusion_radius = _oxygen_exclusion_radius(
					oxygen_label_target=oxygen_label_target,
					oxygen_side_thickness=t1,
					font_size=font_size,
				)
				p1 = _render_geometry.resolve_attach_endpoint(
					bond_start=p2,
					target=_render_geometry.make_circle_target(
						oxygen_exclusion_center,
						exclusion_radius,
					),
					interior_hint=p1,
					constraints=_render_geometry.AttachConstraints(direction_policy="line"),
				)
			else:
				exclusion_radius = _oxygen_exclusion_radius(
					oxygen_label_target=oxygen_label_target,
					oxygen_side_thickness=t2,
					font_size=font_size,
				)
				p2 = _render_geometry.resolve_attach_endpoint(
					bond_start=p1,
					target=_render_geometry.make_circle_target(
						oxygen_exclusion_center,
						exclusion_radius,
					),
					interior_hint=p2,
					constraints=_render_geometry.AttachConstraints(direction_policy="line"),
				)
		if touches_oxygen and oxygen_color != line_color:
			gradient_polygons = _add_gradient_edge_ops(
				ops, p1, p2, t1, t2, edge_index,
				o_end=(start_index == o_index),
				oxygen_color=oxygen_color,
				line_color=line_color,
			)
			for polygon in gradient_polygons:
				ring_block_polygons.append(tuple(polygon))
		else:
			polygon = _geom.edge_polygon(p1, p2, t1, t2)
			ring_block_polygons.append(tuple(polygon))
			if edge_index in adjacent:
				path_op = _rounded_side_edge_path_op(
					p1=p1,
					p2=p2,
					t1=t1,
					t2=t2,
					color=line_color,
					edge_index=edge_index,
				)
				if path_op is None:
					ops.append(
						render_ops.PolygonOp(
							points=tuple(polygon),
							fill=line_color,
							stroke=None,
							stroke_width=0.0,
							z=1,
							op_id=f"ring_edge_{edge_index}",
						)
					)
				else:
					ops.append(path_op)
			else:
				ops.append(
					render_ops.PolygonOp(
						points=tuple(polygon),
						fill=line_color,
						stroke=None,
						stroke_width=0.0,
						z=1,
						op_id=f"ring_edge_{edge_index}",
					)
				)
	ops.append(
		render_ops.TextOp(
			x=ox,
			y=oxygen_text_y,
			text="O",
			font_size=font_size,
			font_name=font_name,
			anchor="middle",
			weight="bold",
			color=oxygen_color,
			z=3,
			op_id="oxygen_label",
		)
	)

	slot_map = carbon_slot_map(spec)
	slot_to_carbon = {slot: int(carbon_key[1:]) for carbon_key, slot in slot_map.items()}
	left_top_carbon = slot_to_carbon.get("ML")
	left_top_up_label = "H"
	if left_top_carbon is not None:
		left_top_up_label = spec.substituents.get(f"C{left_top_carbon}_up", "H")
	left_top_is_chain_like = _text.is_chain_like_label(left_top_up_label)
	default_sub_length = bond_length * 0.45
	connector_width = back_thickness
	simple_jobs = []

	for carbon in sorted(_ring_carbons(spec)):
		carbon_key = f"C{carbon}"
		slot = slot_map[carbon_key]
		vertex = coords[slot_index[slot]]
		up_label = spec.substituents.get(f"{carbon_key}_up", "H")
		down_label = spec.substituents.get(f"{carbon_key}_down", "H")
		multiplier = 1.3 if up_label != "H" and down_label != "H" else 1.0
		sub_length = default_sub_length * multiplier
		for direction, label in (("up", up_label), ("down", down_label)):
			if label == "H" and not show_hydrogens:
				continue
			dir_key = "up_dir" if direction == "up" else "down_dir"
			raw_dx, raw_dy = slot_label_cfg[slot][dir_key]
			dx, dy = _geom.normalize_vector(raw_dx, raw_dy)
			anchor = slot_label_cfg[slot]["anchor"]
			if (
					spec.ring_type == "pyranose"
					and direction == "up"
					and str(label) == "OH"
					and slot in ("BL", "BR")
			):
				# Interior pyranose hydroxyl labels should face ring center.
				anchor = "start" if slot == "BL" else "end"
			effective_length = sub_length
			if spec.ring_type == "furanose" and direction == "up" and slot in ("ML", "MR"):
				oxygen_top = oy - (font_size * 0.65)
				target_y = oxygen_top - (font_size * FURANOSE_TOP_UP_CLEARANCE_FACTOR)
				if (
						slot == "MR"
						and left_top_is_chain_like
						and str(label) == "OH"
						and down_label == "H"
				):
					# Keep right-top OH visually separate from left CH2OH
					# by nudging it down toward ring center (not on one header line).
					target_y += font_size * FURANOSE_TOP_RIGHT_HYDROXYL_EXTRA_CLEARANCE_FACTOR
				min_length = max(0.0, vertex[1] - target_y)
				if min_length > effective_length:
					effective_length = min_length
			if (
					spec.ring_type == "furanose"
					and _text.is_two_carbon_tail_label(label)
					and slot in ("ML", "MR")
			):
				_add_furanose_two_carbon_tail_ops(
					ops=ops,
					carbon=carbon,
					slot=slot,
					direction=direction,
					vertex=vertex,
					dx=dx,
					dy=dy,
					segment_length=effective_length,
					connector_width=connector_width,
					font_size=font_size,
					font_name=font_name,
					anchor=anchor,
					line_color=line_color,
					label_color=label_color,
				)
				continue
			chain_label_list = _text.chain_labels(label)
			if chain_label_list:
				_add_chain_ops(
					ops=ops,
					carbon=carbon,
					direction=direction,
					vertex=vertex,
					dx=dx,
					dy=dy,
					segment_length=effective_length,
					labels=chain_label_list,
					connector_width=connector_width,
					font_size=font_size,
					font_name=font_name,
					anchor=anchor,
					line_color=line_color,
					label_color=label_color,
				)
				continue
			simple_jobs.append(
				{
					"carbon": carbon,
					"ring_type": spec.ring_type,
					"slot": slot,
					"direction": direction,
					"vertex": vertex,
					"dx": dx,
					"dy": dy,
					"length": effective_length,
					"label": label,
					"connector_width": connector_width,
					"font_size": font_size,
					"font_name": font_name,
					"anchor": anchor,
					"text_scale": 1.0,
					"line_color": line_color,
					"label_color": label_color,
				}
			)

	for job in _layout.resolve_hydroxyl_layout_jobs(simple_jobs, blocked_polygons=ring_block_polygons):
		_add_simple_label_ops(
			ops=ops,
			carbon=job["carbon"],
			ring_type=job["ring_type"],
			slot=job["slot"],
			direction=job["direction"],
			vertex=job["vertex"],
			dx=job["dx"],
			dy=job["dy"],
			length=job["length"],
			label=job["label"],
			connector_width=job["connector_width"],
			font_size=job["font_size"],
			text_scale=job.get("text_scale", 1.0),
			font_name=job["font_name"],
			anchor=job["anchor"],
			attach_atom=job.get("attach_atom"),
			line_color=job["line_color"],
			label_color=job["label_color"],
		)

	if show_carbon_numbers:
		center_x = sum(point[0] for point in coords) / len(coords)
		center_y = sum(point[1] for point in coords) / len(coords)
		for carbon in sorted(_ring_carbons(spec)):
			slot = slot_map[f"C{carbon}"]
			vx, vy = coords[slot_index[slot]]
			text_x = (
				(vx * CARBON_NUMBER_VERTEX_WEIGHT)
				+ (center_x * (1.0 - CARBON_NUMBER_VERTEX_WEIGHT))
			)
			text_y = (
				(vy * CARBON_NUMBER_VERTEX_WEIGHT)
				+ (center_y * (1.0 - CARBON_NUMBER_VERTEX_WEIGHT))
			)
			ops.append(
				render_ops.TextOp(
					x=text_x,
					y=text_y,
					text=str(carbon),
					font_size=font_size * 0.65,
					font_name=font_name,
					anchor="middle",
					weight="normal",
					color=label_color,
					z=6,
					op_id=f"C{carbon}_number",
				)
			)
	return render_ops.sort_ops(ops)


#============================================
def _ring_carbons(spec: HaworthSpec) -> list[int]:
	"""Extract sorted ring-carbon indices from Cn_up/Cn_down keys."""
	carbons = set()
	for key in spec.substituents:
		match = re.match(r"^C(\d+)_(up|down)$", key)
		if not match:
			continue
		carbons.add(int(match.group(1)))
	if not carbons:
		raise ValueError("HaworthSpec has no Cn_up/Cn_down substituent keys")
	return sorted(carbons)


#============================================
def _add_simple_label_ops(
		ops: list,
		carbon: int,
		ring_type: str,
		slot: str,
		direction: str,
		vertex: tuple[float, float],
		dx: float,
		dy: float,
		length: float,
		label: str,
		connector_width: float,
		font_size: float,
		text_scale: float,
		font_name: str,
		anchor: str,
		attach_atom: str | None,
		line_color: str,
		label_color: str) -> None:
	"""Add one connector line + one label."""
	end_point = (vertex[0] + dx * length, vertex[1] + dy * length)
	text = _text.format_label_text(label, anchor=anchor)
	anchor_x = _text.anchor_x_offset(text, anchor, font_size)
	text_x = end_point[0] + anchor_x
	text_y = end_point[1] + _text.baseline_shift(direction, font_size, text)
	draw_font_size = font_size * text_scale
	first_attach_target = _render_geometry.label_attach_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=draw_font_size,
		attach_atom="first",
		font_name=font_name,
	)
	last_attach_target = _render_geometry.label_attach_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=draw_font_size,
		attach_atom="last",
		font_name=font_name,
	)
	full_target = _render_geometry.label_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=draw_font_size,
		font_name=font_name,
	)
	target = full_target
	is_hydroxyl_label = _text.is_hydroxyl_render_text(text)
	target_hint = None
	oxygen_center = None
	connector_end = None

	def _resolve_oxygen_circle_endpoint(local_text_x: float, local_text_y: float) -> tuple[
			tuple[float, float] | None,
			tuple[float, float] | None]:
		local_oxygen_center = _text.hydroxyl_oxygen_center(
			text=text,
			anchor=anchor,
			text_x=local_text_x,
			text_y=local_text_y,
			font_size=draw_font_size,
		)
		if local_oxygen_center is None:
			return (None, None)
		local_oxygen_radius = _hydroxyl_connector_radius(draw_font_size, connector_width)
		local_connector_end = _render_geometry.resolve_attach_endpoint(
			bond_start=vertex,
			target=_render_geometry.make_circle_target(local_oxygen_center, local_oxygen_radius),
			interior_hint=local_oxygen_center,
			constraints=_render_geometry.AttachConstraints(
				vertical_lock=slot in ("BR", "BL", "TL"),
				direction_policy="line",
			),
		)
		return (local_oxygen_center, local_connector_end)

	if is_hydroxyl_label:
		oxygen_center, connector_end = _resolve_oxygen_circle_endpoint(text_x, text_y)
		if oxygen_center is None or connector_end is None:
			target = _render_geometry.label_attach_target_from_text_origin(
				text_x=text_x,
				text_y=text_y,
				text=text,
				anchor=anchor,
				font_size=draw_font_size,
				attach_atom=attach_atom or "first",
				attach_element="O",
				font_name=font_name,
			)
			target_hint = target.centroid()
			connector_end = None
	else:
		if first_attach_target.box != last_attach_target.box:
			attach_mode = attach_atom or "first"
			target = _render_geometry.label_attach_target_from_text_origin(
				text_x=text_x,
				text_y=text_y,
				text=text,
				anchor=anchor,
				font_size=draw_font_size,
				attach_atom=attach_mode,
				font_name=font_name,
			)
	if is_hydroxyl_label and oxygen_center is not None and connector_end is not None:
		# Upward hydroxyl labels need a deterministic escape hatch:
		# nudge label placement and recompute connector endpoint until the
		# connector paint no longer penetrates its own label interior.
		if (
				ring_type == "furanose"
				and direction == "up"
				and slot not in ("BL", "BR")
		):
			best_text_x = text_x
			best_text_y = text_y
			best_target = full_target
			best_center = oxygen_center
			initial_end = connector_end
			best_end = _render_geometry.retreat_endpoint_until_legal(
				line_start=vertex,
				line_end=initial_end,
				line_width=connector_width,
				forbidden_regions=[full_target],
				epsilon=RETREAT_SOLVER_EPSILON,
			)
			best_retreat = geometry.point_distance(
				initial_end[0], initial_end[1], best_end[0], best_end[1]
			)
			for offset_x, offset_y in _upward_hydroxyl_nudge_offsets(
					anchor=anchor,
					font_size=draw_font_size,
					connector_end=initial_end,
					oxygen_center=best_center):
				candidate_text_x = text_x + offset_x
				candidate_text_y = text_y + offset_y
				candidate_target = _render_geometry.label_target_from_text_origin(
					text_x=candidate_text_x,
					text_y=candidate_text_y,
					text=text,
					anchor=anchor,
					font_size=draw_font_size,
					font_name=font_name,
				)
				candidate_center, candidate_end = _resolve_oxygen_circle_endpoint(
					candidate_text_x,
					candidate_text_y,
				)
				if candidate_center is None or candidate_end is None:
					continue
				raw_candidate_end = candidate_end
				candidate_end = _render_geometry.retreat_endpoint_until_legal(
					line_start=vertex,
					line_end=candidate_end,
					line_width=connector_width,
					forbidden_regions=[candidate_target],
					epsilon=RETREAT_SOLVER_EPSILON,
				)
				candidate_retreat = geometry.point_distance(
					raw_candidate_end[0],
					raw_candidate_end[1],
					candidate_end[0],
					candidate_end[1],
				)
				if candidate_retreat < best_retreat:
					best_text_x = candidate_text_x
					best_text_y = candidate_text_y
					best_target = candidate_target
					best_center = candidate_center
					best_end = candidate_end
					best_retreat = candidate_retreat
				if candidate_retreat <= 1e-9:
					break
			text_x = best_text_x
			text_y = best_text_y
			full_target = best_target
			target = best_target
			oxygen_center = best_center
			connector_end = best_end
		if ring_type != "furanose" and direction == "up":
			connector_end = _render_geometry.retreat_endpoint_until_legal(
				line_start=vertex,
				line_end=connector_end,
				line_width=connector_width,
				forbidden_regions=[full_target],
				epsilon=RETREAT_SOLVER_EPSILON,
			)
		if ring_type == "furanose" and direction == "up" and slot in ("BL", "BR"):
			connector_end = _render_geometry.retreat_endpoint_until_legal(
				line_start=vertex,
				line_end=connector_end,
				line_width=connector_width,
				forbidden_regions=[full_target],
				epsilon=RETREAT_SOLVER_EPSILON,
			)
	if connector_end is None:
		if target_hint is None:
			target_hint = _text.leading_carbon_center(
				text=text,
				anchor=anchor,
				text_x=text_x,
				text_y=text_y,
				font_size=draw_font_size,
			)
			if target_hint is None:
				target_hint = target.centroid()
			x1, y1, x2, y2 = target.box
			is_inside = x1 <= target_hint[0] <= x2 and y1 <= target_hint[1] <= y2
			if not is_inside:
				target_hint = target.centroid()
		connector_end = _render_geometry.resolve_attach_endpoint(
			bond_start=vertex,
			target=target,
			interior_hint=target_hint,
			constraints=_render_geometry.AttachConstraints(direction_policy="auto"),
		)
	ops.append(
		render_ops.LineOp(
			p1=vertex,
			p2=connector_end,
			width=connector_width,
			cap="round",
			color=line_color,
			z=4,
			op_id=f"C{carbon}_{direction}_connector",
		)
	)
	ops.append(
		render_ops.TextOp(
			x=text_x,
			y=text_y,
			text=text,
			font_size=draw_font_size,
			font_name=font_name,
			anchor=anchor,
			weight="normal",
			color=label_color,
			z=5,
			op_id=f"C{carbon}_{direction}_label",
		)
	)


#============================================
def _oxygen_exclusion_radius(
		oxygen_label_target: _render_geometry.AttachTarget,
		oxygen_side_thickness: float,
		font_size: float) -> float:
	"""Return clipping radius for oxygen-adjacent ring-edge paint."""
	label_box = oxygen_label_target.box
	label_w = max(0.0, label_box[2] - label_box[0])
	label_h = max(0.0, label_box[3] - label_box[1])
	label_radius = max(label_w, label_h) * 0.5
	safety_margin = max(0.25, font_size * 0.05)
	return label_radius + (max(0.0, oxygen_side_thickness) * 0.5) + safety_margin


#============================================
def _hydroxyl_connector_radius(font_size: float, connector_width: float) -> float:
	"""Return clearance radius with explicit safety margin for glyph separation."""
	base_radius = _text.hydroxyl_oxygen_radius(font_size) + (connector_width * 0.5)
	clearance_margin = max(0.25, font_size * 0.05)
	return base_radius + clearance_margin


#============================================
def _upward_hydroxyl_nudge_offsets(
		anchor: str,
		font_size: float,
		connector_end: tuple[float, float],
		oxygen_center: tuple[float, float]) -> list[tuple[float, float]]:
	"""Deterministic candidate offsets for upward hydroxyl labels."""
	step_x = max(0.5, font_size * 0.35)
	step_y = max(0.25, font_size * 0.08)
	if oxygen_center[0] < connector_end[0]:
		horizontal_sign = -1.0
	elif oxygen_center[0] > connector_end[0]:
		horizontal_sign = 1.0
	elif anchor == "end":
		horizontal_sign = -1.0
	else:
		horizontal_sign = 1.0
	offsets = [(0.0, 0.0)]
	for scale in (1.0, 1.25, 1.5, 1.75, 2.0, 2.25):
		x_shift = horizontal_sign * step_x * scale
		offsets.append((x_shift, 0.0))
		offsets.append((x_shift, -step_y))
	return offsets


#============================================
def _add_chain_ops(
		ops: list,
		carbon: int,
		direction: str,
		vertex: tuple[float, float],
		dx: float,
		dy: float,
		segment_length: float,
		labels: list[str],
		connector_width: float,
		font_size: float,
		font_name: str,
		anchor: str,
		line_color: str,
		label_color: str) -> None:
	"""Add multi-segment exocyclic-chain connector + labels."""
	start = vertex
	for index, raw_label in enumerate(labels, start=1):
		end = (start[0] + dx * segment_length, start[1] + dy * segment_length)
		ops.append(
			render_ops.LineOp(
				p1=start,
				p2=end,
				width=connector_width,
				cap="round",
				color=line_color,
				z=4,
				op_id=f"C{carbon}_{direction}_chain{index}_connector",
			)
		)
		text = _text.format_chain_label_text(raw_label, anchor=anchor)
		anchor_x = _text.anchor_x_offset(text, anchor, font_size)
		text_x = end[0] + anchor_x
		text_y = end[1] + _text.baseline_shift(direction, font_size, text)
		ops.append(
			render_ops.TextOp(
				x=text_x,
				y=text_y,
				text=text,
				font_size=font_size,
				font_name=font_name,
				anchor=anchor,
				weight="normal",
				color=label_color,
				z=5,
				op_id=f"C{carbon}_{direction}_chain{index}_label",
			)
		)
		start = end


#============================================
def _add_furanose_two_carbon_tail_ops(
		ops: list,
		carbon: int,
		slot: str,
		direction: str,
		vertex: tuple[float, float],
		dx: float,
		dy: float,
		segment_length: float,
		connector_width: float,
		font_size: float,
		font_name: str,
		anchor: str,
		line_color: str,
		label_color: str) -> None:
	"""Render CH(OH)CH2OH as a branched furanose sidechain."""
	branch_point = (vertex[0] + dx * segment_length, vertex[1] + dy * segment_length)
	ops.append(
		render_ops.LineOp(
			p1=vertex,
			p2=branch_point,
			width=connector_width,
			cap="round",
			color=line_color,
			z=4,
			op_id=f"C{carbon}_{direction}_chain1_connector",
		)
	)
	template = _furanose_two_carbon_tail_template(slot=slot, direction=direction)
	ho_dx, ho_dy = _geom.normalize_vector(template["ho_vector"][0], template["ho_vector"][1])
	ch2_dx, ch2_dy = _geom.normalize_vector(template["ch2_vector"][0], template["ch2_vector"][1])
	ho_length = segment_length * template["ho_length_factor"]
	ch2_length = segment_length * template["ch2_length_factor"]
	ho_anchor = template["ho_anchor"]
	ch2_anchor = template["ch2_anchor"]
	ho_direction = template["ho_text_direction"]
	ch2_direction = template["ch2_text_direction"]
	ch2_canonical_text = bool(template.get("ch2_canonical_text", False))
	ho_end = (
		branch_point[0] + (ho_dx * ho_length),
		branch_point[1] + (ho_dy * ho_length),
	)
	ch2_end = (
		branch_point[0] + (ch2_dx * ch2_length),
		branch_point[1] + (ch2_dy * ch2_length),
	)
	ho_text = _text.format_label_text("OH", anchor=ho_anchor)
	ho_x = ho_end[0] + _text.anchor_x_offset(ho_text, ho_anchor, font_size)
	ho_y = ho_end[1] + _text.baseline_shift(ho_direction, font_size, ho_text)
	ho_label_target = _render_geometry.label_target_from_text_origin(
		text_x=ho_x,
		text_y=ho_y,
		text=ho_text,
		anchor=ho_anchor,
		font_size=font_size,
		font_name=font_name,
	)
	if ch2_canonical_text:
		ch2_text = _text.apply_subscript_markup("CH2OH")
	else:
		ch2_text = _text.format_chain_label_text("CH2OH", anchor=ch2_anchor)
	ch2_x = ch2_end[0] + _text.anchor_x_offset(ch2_text, ch2_anchor, font_size)
	ch2_y = ch2_end[1] + _text.baseline_shift(ch2_direction, font_size, ch2_text)
	ho_attach_target = _render_geometry.label_attach_target_from_text_origin(
		text_x=ho_x,
		text_y=ho_y,
		text=ho_text,
		anchor=ho_anchor,
		font_size=font_size,
		attach_atom="first",
		attach_element="O",
		font_name=font_name,
	)
	ho_connector_end = _render_geometry.resolve_attach_endpoint(
		bond_start=branch_point,
		target=ho_attach_target,
		interior_hint=ho_attach_target.centroid(),
		constraints=_render_geometry.AttachConstraints(direction_policy="auto"),
	)
	ho_connector_end = _render_geometry.retreat_endpoint_until_legal(
		line_start=branch_point,
		line_end=ho_connector_end,
		line_width=connector_width,
		forbidden_regions=[ho_label_target],
		epsilon=RETREAT_SOLVER_EPSILON,
	)
	ch2_attach_target = _render_geometry.label_attach_target_from_text_origin(
		text_x=ch2_x,
		text_y=ch2_y,
		text=ch2_text,
		anchor=ch2_anchor,
		font_size=font_size,
		attach_atom="first",
		attach_element="C",
		font_name=font_name,
	)
	ch2_connector_end = _render_geometry.resolve_attach_endpoint(
		bond_start=branch_point,
		target=ch2_attach_target,
		interior_hint=ch2_attach_target.centroid(),
		constraints=_render_geometry.AttachConstraints(direction_policy="auto"),
	)
	ch2_label_target = _render_geometry.label_target_from_text_origin(
		text_x=ch2_x,
		text_y=ch2_y,
		text=ch2_text,
		anchor=ch2_anchor,
		font_size=font_size,
		font_name=font_name,
	)
	ch2_connector_end = _render_geometry.retreat_endpoint_until_legal(
		line_start=branch_point,
		line_end=ch2_connector_end,
		line_width=connector_width,
		forbidden_regions=[ch2_label_target],
		epsilon=RETREAT_SOLVER_EPSILON,
	)
	_append_branch_connector_ops(
		ops=ops,
		start=branch_point,
		end=ch2_connector_end,
		connector_width=connector_width,
		font_size=font_size,
		color=line_color,
		op_id=f"C{carbon}_{direction}_chain2_connector",
		style="hashed" if template["hashed_branch"] == "ch2" else "solid",
	)
	_append_branch_connector_ops(
		ops=ops,
		start=branch_point,
		end=ho_connector_end,
		connector_width=connector_width,
		font_size=font_size,
		color=line_color,
		op_id=f"C{carbon}_{direction}_chain1_oh_connector",
		style="hashed" if template["hashed_branch"] == "ho" else "solid",
	)
	ops.append(
		render_ops.TextOp(
			x=ho_x,
			y=ho_y,
			text=ho_text,
			font_size=font_size,
			font_name=font_name,
			anchor=ho_anchor,
			weight="normal",
			color=label_color,
			z=5,
			op_id=f"C{carbon}_{direction}_chain1_oh_label",
		)
	)
	ops.append(
		render_ops.TextOp(
			x=ch2_x,
			y=ch2_y,
			text=ch2_text,
			font_size=font_size,
			font_name=font_name,
			anchor=ch2_anchor,
			weight="normal",
			color=label_color,
			z=5,
			op_id=f"C{carbon}_{direction}_chain2_label",
		)
	)


#============================================
def _furanose_two_carbon_tail_template(slot: str, direction: str) -> dict:
	"""Return deterministic branch geometry/text placement for one two-carbon tail."""
	left_template = {
		"ho_vector": (-1.0, -0.55),
		"ch2_vector": (-1.0, 0.72),
		"ho_length_factor": 0.78,
		"ch2_length_factor": 0.95,
		"ho_anchor": "end",
		"ch2_anchor": "end",
		"ho_text_direction": "up",
		"ch2_text_direction": "down",
		"hashed_branch": "ho",
	}
	right_template = {
		"ho_vector": (-1.0, -0.50),
		"ch2_vector": (1.0, -0.95),
		"ho_length_factor": 0.72,
		"ch2_length_factor": 1.08,
		"ho_anchor": "end",
		"ch2_anchor": "start",
		"ho_text_direction": "up",
		"ch2_text_direction": "up",
		"ch2_canonical_text": True,
		"hashed_branch": "ch2",
	}
	if slot == "ML":
		if direction == "up":
			return right_template
		if direction == "down":
			return left_template
	if slot == "MR":
		# Right-side two-carbon tails keep canonical right-branch template.
		return right_template
	raise ValueError(f"Unsupported furanose two-carbon-tail slot/direction: {slot}/{direction}")


#============================================
def _append_branch_connector_ops(
		ops: list,
		start: tuple[float, float],
		end: tuple[float, float],
		connector_width: float,
		font_size: float,
		color: str,
		op_id: str,
		style: str) -> None:
	"""Add one branch connector as solid or hashed without doubling the bond."""
	if style == "solid":
		ops.append(
			render_ops.LineOp(
				p1=start,
				p2=end,
				width=connector_width,
				cap="round",
				color=color,
				z=4,
				op_id=op_id,
			)
		)
		return
	if style != "hashed":
		raise ValueError(f"Unsupported branch connector style '{style}'")
	dx, dy = _geom.normalize_vector(end[0] - start[0], end[1] - start[1])
	length = math.hypot(end[0] - start[0], end[1] - start[1])
	if length <= 1e-9:
		return
	ops.append(
		render_ops.LineOp(
			p1=start,
			p2=end,
			width=max(0.18, connector_width * 0.22),
			cap="butt",
			color=color,
			z=4,
			op_id=op_id,
		)
	)
	line_width = max(0.8, connector_width * 0.72)
	wedge_width = max(line_width * 2.8, font_size * 0.24)
	hashed_ops = _render_geometry._hashed_ops(
		start=start,
		end=end,
		line_width=line_width,
		wedge_width=wedge_width,
		color1=color,
		color2=color,
		gradient=False,
	)
	if not hashed_ops:
		return
	kept = []
	for hashed in hashed_ops:
		mid_x = (hashed.p1[0] + hashed.p2[0]) * 0.5
		mid_y = (hashed.p1[1] + hashed.p2[1]) * 0.5
		along = ((mid_x - start[0]) * dx) + ((mid_y - start[1]) * dy)
		if along < (0.03 * length):
			continue
		if along > (0.97 * length):
			continue
		kept.append(hashed)
	nearest_along = length
	if kept:
		nearest_along = min(
			(((line.p1[0] + line.p2[0]) * 0.5 - start[0]) * dx)
			+ (((line.p1[1] + line.p2[1]) * 0.5 - start[1]) * dy)
			for line in kept
		)
	if nearest_along > (0.10 * length):
		origin_along = 0.04 * length
		origin_center = (start[0] + (dx * origin_along), start[1] + (dy * origin_along))
		perp_x, perp_y = -dy, dx
		half_span = max(connector_width * 0.35, font_size * 0.06)
		if kept:
			template = kept[0]
			stroke_width = template.width
			stroke_cap = template.cap
		else:
			stroke_width = line_width
			stroke_cap = "round"
		kept.append(
			render_ops.LineOp(
				p1=(
					origin_center[0] + (perp_x * half_span),
					origin_center[1] + (perp_y * half_span),
				),
				p2=(
					origin_center[0] - (perp_x * half_span),
					origin_center[1] - (perp_y * half_span),
				),
				width=stroke_width,
				cap=stroke_cap,
				color=color,
				z=4,
			)
		)
	farthest_along = 0.0
	if kept:
		farthest_along = max(
			(((line.p1[0] + line.p2[0]) * 0.5 - start[0]) * dx)
			+ (((line.p1[1] + line.p2[1]) * 0.5 - start[1]) * dy)
			for line in kept
		)
	if farthest_along < (0.85 * length):
		terminal_along = min(0.92 * length, max(0.88 * length, farthest_along))
		center = (start[0] + (dx * terminal_along), start[1] + (dy * terminal_along))
		perp_x, perp_y = -dy, dx
		half_span = max(connector_width * 0.45, font_size * 0.08)
		if kept:
			template = kept[-1]
			stroke_width = template.width
			stroke_cap = template.cap
		else:
			stroke_width = line_width
			stroke_cap = "round"
		kept.append(
			render_ops.LineOp(
				p1=(center[0] + (perp_x * half_span), center[1] + (perp_y * half_span)),
				p2=(center[0] - (perp_x * half_span), center[1] - (perp_y * half_span)),
				width=stroke_width,
				cap=stroke_cap,
				color=color,
				z=4,
			)
		)
	for index, hashed in enumerate(kept, start=1):
		ops.append(
			render_ops.LineOp(
				p1=hashed.p1,
				p2=hashed.p2,
				width=hashed.width,
				cap=hashed.cap,
				color=color,
				z=4,
				op_id=f"{op_id}_hatch{index}",
			)
		)


#============================================
def _add_gradient_edge_ops(
		ops: list,
		p1: tuple[float, float],
		p2: tuple[float, float],
		t1: float,
		t2: float,
		edge_index: int,
		o_end: bool,
		oxygen_color: str,
		line_color: str) -> list[tuple[tuple[float, float], ...]]:
	"""Split one ring edge into two colored halves (gradient near oxygen)."""
	mx = (p1[0] + p2[0]) / 2.0
	my = (p1[1] + p2[1]) / 2.0
	tm = (t1 + t2) / 2.0
	if o_end:
		# p1 is the oxygen end
		poly_o = _geom.edge_polygon(p1, (mx, my), t1, tm)
		poly_c = _geom.edge_polygon((mx, my), p2, tm, t2)
	else:
		# p2 is the oxygen end
		poly_c = _geom.edge_polygon(p1, (mx, my), t1, tm)
		poly_o = _geom.edge_polygon((mx, my), p2, tm, t2)
	ops.append(
		render_ops.PolygonOp(
			points=tuple(poly_o),
			fill=oxygen_color,
			stroke=None,
			stroke_width=0.0,
			z=1,
			op_id=f"ring_edge_{edge_index}_o",
		)
	)
	ops.append(
		render_ops.PolygonOp(
			points=tuple(poly_c),
			fill=line_color,
			stroke=None,
			stroke_width=0.0,
			z=1,
			op_id=f"ring_edge_{edge_index}_c",
		)
	)
	return [tuple(poly_o), tuple(poly_c)]


#============================================
def _rounded_side_edge_path_op(
		p1: tuple[float, float],
		p2: tuple[float, float],
		t1: float,
		t2: float,
		color: str,
		edge_index: int) -> render_ops.PathOp | None:
	"""Build rounded side-edge wedge path, wide at front-adjacent endpoint."""
	narrow_width = min(t1, t2)
	wide_width = max(t1, t2)
	if narrow_width <= 1e-9 or wide_width <= 1e-9:
		return None
	if t1 <= t2:
		tip_point = p1
		base_point = p2
	else:
		tip_point = p2
		base_point = p1
	path_ops = _render_geometry._rounded_wedge_ops(
		start=tip_point,
		end=base_point,
		line_width=narrow_width,
		wedge_width=wide_width,
		color=color,
	)
	if not path_ops:
		return None
	path_op = path_ops[0]
	return render_ops.PathOp(
		commands=path_op.commands,
		fill=color,
		stroke=None,
		stroke_width=0.0,
		cap=path_op.cap,
		join=path_op.join,
		z=1,
		op_id=f"ring_edge_{edge_index}",
	)
