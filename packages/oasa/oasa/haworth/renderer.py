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
from .. import sugar_code as _sugar_code
from .. import render_ops
from .. import render_geometry as _render_geometry
from . import spec as _spec
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
STRICT_OVERLAP_EPSILON = 0.5


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
def render_from_code(
		code: str,
		ring_type: str,
		anomeric: str,
		bond_length: float = 30.0,
		font_size: float = 12.0,
		font_name: str = "sans-serif",
		show_carbon_numbers: bool = False,
		show_hydrogens: bool = True,
		debug_attach_overlay: bool = False,
		line_color: str = "#000",
		label_color: str = "#000",
		bg_color: str = "#fff",
		oxygen_color: str = OXYGEN_COLOR) -> list:
	"""Render Haworth ops directly from sugar-code API inputs."""
	parsed = _sugar_code.parse(code)
	spec = _spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)
	return render(
		spec,
		bond_length=bond_length,
		font_size=font_size,
		font_name=font_name,
		show_carbon_numbers=show_carbon_numbers,
		show_hydrogens=show_hydrogens,
		debug_attach_overlay=debug_attach_overlay,
		line_color=line_color,
		label_color=label_color,
		bg_color=bg_color,
		oxygen_color=oxygen_color,
	)


#============================================
def label_target_for_text_op(label_op: render_ops.TextOp) -> _render_geometry.AttachTarget:
	"""Build full label target for one TextOp using renderer-owned policy."""
	return _render_geometry.label_target_from_text_origin(
		text_x=label_op.x,
		text_y=label_op.y,
		text=label_op.text,
		anchor=label_op.anchor,
		font_size=label_op.font_size,
		font_name=label_op.font_name,
	)


#============================================
def attach_target_for_text_op(
		label_op: render_ops.TextOp,
		chain_attach_site: str = "core_center") -> _render_geometry.AttachTarget:
	"""Build attach target for one TextOp using shared runtime policy."""
	text = str(label_op.text or "")
	if _text.is_chain_like_render_text(text):
		return _render_geometry.label_attach_target_from_text_origin(
			text_x=label_op.x,
			text_y=label_op.y,
			text=text,
			anchor=label_op.anchor,
			font_size=label_op.font_size,
			attach_atom="first",
			attach_element="C",
			attach_site=chain_attach_site,
			font_name=label_op.font_name,
		)
	if text == "OH":
		return _render_geometry.label_attach_target_from_text_origin(
			text_x=label_op.x,
			text_y=label_op.y,
			text=text,
			anchor=label_op.anchor,
			font_size=label_op.font_size,
			attach_atom="first",
			attach_element="O",
			font_name=label_op.font_name,
		)
	if text == "HO":
		return _render_geometry.label_attach_target_from_text_origin(
			text_x=label_op.x,
			text_y=label_op.y,
			text=text,
			anchor=label_op.anchor,
			font_size=label_op.font_size,
			attach_atom="last",
			attach_element="O",
			font_name=label_op.font_name,
		)
	return _render_geometry.label_attach_target_from_text_origin(
		text_x=label_op.x,
		text_y=label_op.y,
		text=text,
		anchor=label_op.anchor,
		font_size=label_op.font_size,
		attach_atom="first",
		font_name=label_op.font_name,
	)


#============================================
def _endpoint_near_label(
		label: render_ops.TextOp,
		connector: render_ops.LineOp) -> tuple[float, float]:
	"""Return connector endpoint closest to the label anchor point."""
	d1 = geometry.point_distance(connector.p1[0], connector.p1[1], label.x, label.y)
	d2 = geometry.point_distance(connector.p2[0], connector.p2[1], label.x, label.y)
	return connector.p1 if d1 <= d2 else connector.p2


#============================================
def _select_chain_attach_site_for_connector(
		label: render_ops.TextOp,
		connector: render_ops.LineOp) -> str:
	"""Resolve chain attach site from connector endpoint to enforce endpoint contract."""
	core_target = attach_target_for_text_op(label, chain_attach_site="core_center")
	stem_target = attach_target_for_text_op(label, chain_attach_site="stem_centerline")
	endpoint = _endpoint_near_label(label, connector)
	core_contains = _geom.point_in_box(endpoint, core_target.box)
	stem_contains = _geom.point_in_box(endpoint, stem_target.box)
	if core_contains and not stem_contains:
		return "core_center"
	if stem_contains and not core_contains:
		return "stem_centerline"
	core_x, core_y = core_target.centroid()
	stem_x, stem_y = stem_target.centroid()
	core_distance = geometry.point_distance(endpoint[0], endpoint[1], core_x, core_y)
	stem_distance = geometry.point_distance(endpoint[0], endpoint[1], stem_x, stem_y)
	return "core_center" if core_distance <= stem_distance else "stem_centerline"


#============================================
def _point_in_target_closed(
		point: tuple[float, float],
		target: _render_geometry.AttachTarget,
		tol: float = 1e-6) -> bool:
	"""Return True when point is inside target using closed-boundary semantics."""
	resolved = target
	if resolved.kind == "box":
		x1, y1, x2, y2 = resolved.box
		return (x1 - tol) <= point[0] <= (x2 + tol) and (y1 - tol) <= point[1] <= (y2 + tol)
	if resolved.kind == "circle":
		cx, cy = resolved.center
		distance = geometry.point_distance(point[0], point[1], cx, cy)
		return distance <= (float(resolved.radius) + tol)
	if resolved.kind == "segment":
		return False
	if resolved.kind == "composite":
		return any(_point_in_target_closed(point, child, tol=tol) for child in (resolved.targets or ()))
	raise ValueError(f"Unsupported attach target kind: {resolved.kind!r}")


#============================================
def _line_uses_label_attach_region(
		label: render_ops.TextOp,
		line: render_ops.LineOp,
		attach_target: _render_geometry.AttachTarget,
		epsilon: float) -> bool:
	"""Return True when line interacts with the label's attach region."""
	endpoint = _endpoint_near_label(label, line)
	if _point_in_target_closed(endpoint, attach_target):
		return True
	return not _render_geometry.validate_attachment_paint(
		line_start=line.p1,
		line_end=line.p2,
		line_width=float(getattr(line, "width", 0.0) or 0.0),
		forbidden_regions=[attach_target],
		allowed_regions=[],
		epsilon=epsilon,
	)


#============================================
def _allowed_regions_for_line_label_pair(
		label: render_ops.TextOp,
		line: render_ops.LineOp,
		epsilon: float) -> list[_render_geometry.AttachTarget]:
	"""Return shared attach carve-out regions for one line-vs-label strict check."""
	attach_target = _attach_target_for_connector(label, line)
	if _line_uses_label_attach_region(label, line, attach_target, epsilon=epsilon):
		return [attach_target]
	return []


#============================================
def _resolve_legal_attach_endpoint(
		bond_start: tuple[float, float],
		attach_target: _render_geometry.AttachTarget,
		interior_hint: tuple[float, float] | None,
		constraints: _render_geometry.AttachConstraints,
		line_width: float,
		forbidden_regions: list[_render_geometry.AttachTarget] | None = None,
		allowed_regions: list[_render_geometry.AttachTarget] | None = None,
		epsilon: float = STRICT_OVERLAP_EPSILON) -> tuple[float, float]:
	"""Resolve connector endpoint through shared resolver and legality retreat."""
	if allowed_regions is None:
		allowed_regions = []
	if forbidden_regions is None:
		forbidden_regions = []
	endpoint = _render_geometry.resolve_attach_endpoint(
		bond_start=bond_start,
		target=attach_target,
		interior_hint=interior_hint if interior_hint is not None else attach_target.centroid(),
		constraints=constraints,
	)
	return _render_geometry.retreat_endpoint_until_legal(
		line_start=bond_start,
		line_end=endpoint,
		line_width=line_width,
		forbidden_regions=forbidden_regions,
		allowed_regions=allowed_regions,
		epsilon=epsilon,
	)


#============================================
def strict_validate_ops(
		ops: list,
		context: str,
		epsilon: float = STRICT_OVERLAP_EPSILON) -> None:
	"""Raise RuntimeError when strict overlap checks fail for one ops list."""
	labels = [op for op in ops if isinstance(op, render_ops.TextOp)]
	lines = [op for op in ops if isinstance(op, render_ops.LineOp)]
	label_targets = {label: label_target_for_text_op(label) for label in labels}

	for left_index, left_label in enumerate(labels):
		left_box = label_targets[left_label].box
		left_id = left_label.op_id or f"label[{left_index}]"
		for right_index in range(left_index + 1, len(labels)):
			right_label = labels[right_index]
			right_box = label_targets[right_label].box
			overlap_area = _geom.intersection_area(left_box, right_box, gap=0.0)
			if overlap_area > epsilon:
				right_id = right_label.op_id or f"label[{right_index}]"
				raise RuntimeError(
					f"Strict overlap failure in {context}: label/label {left_id} vs {right_id}"
				)

	for label in labels:
		label_id = label.op_id or "<no-label-id>"
		full_target = label_targets[label]
		for line in lines:
			line_id = line.op_id or "<no-line-id>"
			allowed_regions = _allowed_regions_for_line_label_pair(label, line, epsilon=epsilon)
			is_legal = _render_geometry.validate_attachment_paint(
				line_start=line.p1,
				line_end=line.p2,
				line_width=float(getattr(line, "width", 0.0) or 0.0),
				forbidden_regions=[full_target],
				allowed_regions=allowed_regions,
				epsilon=epsilon,
			)
			if not is_legal:
				raise RuntimeError(
					f"Strict overlap failure in {context}: bond/label line={line_id} label={label_id}"
				)


#============================================
def _attach_target_for_connector(
		label: render_ops.TextOp,
		connector: render_ops.LineOp | None) -> _render_geometry.AttachTarget:
	"""Resolve one connector-specific attach target from shared policy."""
	if connector is not None and _text.is_chain_like_render_text(str(label.text or "")):
		site = _select_chain_attach_site_for_connector(label, connector)
		return attach_target_for_text_op(label, chain_attach_site=site)
	return attach_target_for_text_op(label)


#============================================
def _endpoint_for_target(
		line: render_ops.LineOp,
		target: _render_geometry.AttachTarget) -> tuple[float, float]:
	"""Return line endpoint inside target when available, otherwise nearest end."""
	x1, y1, x2, y2 = target.box
	p1_inside = x1 <= line.p1[0] <= x2 and y1 <= line.p1[1] <= y2
	p2_inside = x1 <= line.p2[0] <= x2 and y1 <= line.p2[1] <= y2
	if p1_inside and not p2_inside:
		return line.p1
	if p2_inside and not p1_inside:
		return line.p2
	if p1_inside and p2_inside:
		center_x, center_y = target.centroid()
		d1 = geometry.point_distance(line.p1[0], line.p1[1], center_x, center_y)
		d2 = geometry.point_distance(line.p2[0], line.p2[1], center_x, center_y)
		return line.p1 if d1 <= d2 else line.p2
	center_x, center_y = target.centroid()
	d1 = geometry.point_distance(line.p1[0], line.p1[1], center_x, center_y)
	d2 = geometry.point_distance(line.p2[0], line.p2[1], center_x, center_y)
	return line.p1 if d1 <= d2 else line.p2


#============================================
def _append_attach_debug_overlay_ops(ops: list) -> None:
	"""Append debug overlay primitives for attach target, centerline, and endpoint."""
	lines = {op.op_id: op for op in ops if isinstance(op, render_ops.LineOp) and op.op_id}
	for label in [op for op in ops if isinstance(op, render_ops.TextOp)]:
		label_id = label.op_id or ""
		if not label_id.endswith("_label"):
			continue
		connector = lines.get(label_id.replace("_label", "_connector"))
		if connector is None:
			continue
		target = _attach_target_for_connector(label, connector)
		x1, y1, x2, y2 = target.box
		ops.append(
			render_ops.PolygonOp(
				points=((x1, y1), (x2, y1), (x2, y2), (x1, y2)),
				fill="none",
				stroke="#0aa",
				stroke_width=0.45,
				z=90,
				op_id=f"{label_id}_debug_target",
			)
		)
		center_x, _center_y = target.centroid()
		ops.append(
			render_ops.LineOp(
				p1=(center_x, y1),
				p2=(center_x, y2),
				width=0.45,
				cap="round",
				color="#07a",
				z=91,
				op_id=f"{label_id}_debug_centerline",
			)
		)
		endpoint = _endpoint_for_target(connector, target)
		ops.append(
			render_ops.CircleOp(
				center=endpoint,
				radius=0.9,
				fill="#d12",
				stroke="none",
				stroke_width=0.0,
				z=92,
				op_id=f"{label_id}_debug_endpoint",
			)
		)


#============================================
def render(
		spec: HaworthSpec,
		bond_length: float = 30.0,
		font_size: float = 12.0,
		font_name: str = "sans-serif",
		show_carbon_numbers: bool = False,
		show_hydrogens: bool = True,
		debug_attach_overlay: bool = False,
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
	ring_center = (
		sum(point[0] for point in coords) / float(len(coords)),
		sum(point[1] for point in coords) / float(len(coords)),
	)
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
				p1 = _resolve_legal_attach_endpoint(
					bond_start=p2,
					attach_target=_render_geometry.make_circle_target(
						oxygen_exclusion_center,
						exclusion_radius,
					),
					interior_hint=p1,
					constraints=_render_geometry.AttachConstraints(direction_policy="line"),
					line_width=0.0,
				)
			else:
				exclusion_radius = _oxygen_exclusion_radius(
					oxygen_label_target=oxygen_label_target,
					oxygen_side_thickness=t2,
					font_size=font_size,
				)
				p2 = _resolve_legal_attach_endpoint(
					bond_start=p1,
					attach_target=_render_geometry.make_circle_target(
						oxygen_exclusion_center,
						exclusion_radius,
					),
					interior_hint=p2,
					constraints=_render_geometry.AttachConstraints(direction_policy="line"),
					line_width=0.0,
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
					ring_center=ring_center,
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
					"ring_center": ring_center,
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
	if debug_attach_overlay:
		_append_attach_debug_overlay_ops(ops)
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
	is_chain_like_label = _text.is_chain_like_label(str(label))
	draw_font_size = font_size * text_scale
	anchor_x = _text.anchor_x_offset(text, anchor, font_size)
	text_x = end_point[0] + anchor_x
	text_y = end_point[1] + _text.baseline_shift(direction, font_size, text)
	text, text_x, text_y, draw_font_size = _resolve_methyl_label_collision(
		ops=ops,
		end_point=end_point,
		direction=direction,
		anchor=anchor,
		font_name=font_name,
		text=text,
		text_x=text_x,
		text_y=text_y,
		layout_font_size=font_size,
		draw_font_size=draw_font_size,
	)
	force_vertical_chain = (
		ring_type == "furanose"
		and direction == "up"
		and slot == "ML"
		and is_chain_like_label
	)
	if force_vertical_chain:
		# Align vertical chain-like carbon connectors to the stem centerline.
		core_target = _render_geometry.label_attach_target_from_text_origin(
			text_x=text_x,
			text_y=text_y,
			text=text,
			anchor=anchor,
			font_size=draw_font_size,
			attach_atom=attach_atom or "first",
			attach_element="C",
			attach_site="stem_centerline",
			font_name=font_name,
		)
		core_center_x, _core_center_y = core_target.centroid()
		text_x += vertex[0] - core_center_x
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

	def _resolve_oxygen_circle_endpoint(
			local_text_x: float,
			local_text_y: float,
			forbidden_regions: list[_render_geometry.AttachTarget] | None = None) -> tuple[
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
		local_circle_target = _render_geometry.make_circle_target(local_oxygen_center, local_oxygen_radius)
		local_connector_end = _resolve_legal_attach_endpoint(
			bond_start=vertex,
			attach_target=local_circle_target,
			interior_hint=local_oxygen_center,
			constraints=_render_geometry.AttachConstraints(
				vertical_lock=slot in ("BR", "BL", "TL"),
				direction_policy="line",
			),
			line_width=connector_width,
			forbidden_regions=forbidden_regions,
			epsilon=RETREAT_SOLVER_EPSILON,
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
				attach_element="C" if is_chain_like_label else None,
				attach_site="stem_centerline" if (is_chain_like_label and force_vertical_chain) else "core_center",
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
			best_end = _resolve_oxygen_circle_endpoint(
				best_text_x,
				best_text_y,
				forbidden_regions=[full_target],
			)[1]
			if best_end is None:
				best_end = initial_end
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
				_raw_candidate_center, raw_candidate_end = _resolve_oxygen_circle_endpoint(
					candidate_text_x,
					candidate_text_y,
				)
				if raw_candidate_end is None:
					continue
				candidate_center, candidate_end = _resolve_oxygen_circle_endpoint(
					candidate_text_x,
					candidate_text_y,
					forbidden_regions=[candidate_target],
				)
				if candidate_center is None or candidate_end is None:
					continue
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
			recomputed_end = _resolve_oxygen_circle_endpoint(
				text_x,
				text_y,
				forbidden_regions=[full_target],
			)[1]
			if recomputed_end is not None:
				connector_end = recomputed_end
		if ring_type == "furanose" and direction == "up" and slot in ("BL", "BR"):
			recomputed_end = _resolve_oxygen_circle_endpoint(
				text_x,
				text_y,
				forbidden_regions=[full_target],
			)[1]
			if recomputed_end is not None:
				connector_end = recomputed_end
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
		force_vertical = (
			ring_type == "furanose"
			and direction == "up"
			and slot == "ML"
			and is_chain_like_label
		)
		connector_end = _resolve_legal_attach_endpoint(
			bond_start=vertex,
			attach_target=target,
			interior_hint=target_hint,
			constraints=_render_geometry.AttachConstraints(
				direction_policy="line" if force_vertical else "auto",
				vertical_lock=force_vertical,
			),
			line_width=connector_width,
			forbidden_regions=[full_target] if ((not is_hydroxyl_label) and is_chain_like_label) else [],
			allowed_regions=[target] if ((not is_hydroxyl_label) and is_chain_like_label) else [],
			epsilon=STRICT_OVERLAP_EPSILON,
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
def _box_overlap_area(
		box_a: tuple[float, float, float, float],
		box_b: tuple[float, float, float, float]) -> float:
	"""Return overlap area for two axis-aligned boxes."""
	ax1, ay1, ax2, ay2 = box_a
	bx1, by1, bx2, by2 = box_b
	overlap_w = min(ax2, bx2) - max(ax1, bx1)
	overlap_h = min(ay2, by2) - max(ay1, by1)
	if overlap_w <= 0.0 or overlap_h <= 0.0:
		return 0.0
	return overlap_w * overlap_h


#============================================
def _label_overlap_area_against_existing(
		ops: list,
		text_x: float,
		text_y: float,
		text: str,
		anchor: str,
		font_size: float,
		font_name: str) -> float:
	"""Return max overlap area between candidate label and existing labels."""
	candidate_target = _render_geometry.label_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		font_name=font_name,
	)
	max_area = 0.0
	for op in ops:
		if not isinstance(op, render_ops.TextOp):
			continue
		existing_target = _render_geometry.label_target_from_text_origin(
			text_x=op.x,
			text_y=op.y,
			text=op.text,
			anchor=op.anchor,
			font_size=op.font_size,
			font_name=op.font_name,
		)
		max_area = max(max_area, _box_overlap_area(candidate_target.box, existing_target.box))
	return max_area


#============================================
def _resolve_methyl_label_collision(
		ops: list,
		end_point: tuple[float, float],
		direction: str,
		anchor: str,
		font_name: str,
		text: str,
		text_x: float,
		text_y: float,
		layout_font_size: float,
		draw_font_size: float) -> tuple[str, float, float, float]:
	"""Resolve CH3-vs-neighbor label overlap with deterministic local fallbacks."""
	canonical_ch3 = _text.apply_subscript_markup("CH3")
	canonical_h3c = _text.apply_subscript_markup("H3C")
	if text != canonical_ch3:
		return (text, text_x, text_y, draw_font_size)
	base_font_size = draw_font_size
	# Mid-lane methyl labels are easier to read at 90% while preserving CH3
	# ordering; keep this deterministic and avoid shrinking below 90%.
	if anchor == "middle":
		min_methyl_size = layout_font_size * 0.90
		if draw_font_size > min_methyl_size:
			base_font_size = min_methyl_size
			text_x = end_point[0] + _text.anchor_x_offset(canonical_ch3, anchor, base_font_size)
			text_y = end_point[1] + _text.baseline_shift(direction, base_font_size, canonical_ch3)
			draw_font_size = base_font_size
	current_overlap = _label_overlap_area_against_existing(
		ops=ops,
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=draw_font_size,
		font_name=font_name,
	)
	if current_overlap <= STRICT_OVERLAP_EPSILON:
		return (text, text_x, text_y, draw_font_size)
	min_font_size = base_font_size
	candidates = [
		(canonical_ch3, max(min_font_size, draw_font_size * 0.90)),
		(canonical_h3c, max(min_font_size, draw_font_size)),
		(canonical_h3c, max(min_font_size, draw_font_size * 0.90)),
	]
	best = (text, text_x, text_y, draw_font_size, current_overlap)
	for candidate_text, candidate_font_size in candidates:
		candidate_x = end_point[0] + _text.anchor_x_offset(candidate_text, anchor, candidate_font_size)
		candidate_y = end_point[1] + _text.baseline_shift(direction, candidate_font_size, candidate_text)
		overlap_area = _label_overlap_area_against_existing(
			ops=ops,
			text_x=candidate_x,
			text_y=candidate_y,
			text=candidate_text,
			anchor=anchor,
			font_size=candidate_font_size,
			font_name=font_name,
		)
		if overlap_area < best[4]:
			best = (candidate_text, candidate_x, candidate_y, candidate_font_size, overlap_area)
		if overlap_area <= STRICT_OVERLAP_EPSILON:
			return (candidate_text, candidate_x, candidate_y, candidate_font_size)
	return (best[0], best[1], best[2], best[3])


#============================================
def _chain2_label_offset_candidates(
		connector_unit: tuple[float, float],
		font_size: float) -> list[tuple[float, float]]:
	"""Return connector-frame candidate offsets for chain2 label placement."""
	unit_x, unit_y = _geom.normalize_vector(connector_unit[0], connector_unit[1])
	perp_x, perp_y = (-unit_y, unit_x)
	step_along = max(0.5, font_size * 0.20)
	step_perp = max(0.5, font_size * 0.18)

	def _offset(along_scale: float, perp_scale: float) -> tuple[float, float]:
		return (
			(unit_x * step_along * along_scale) + (perp_x * step_perp * perp_scale),
			(unit_y * step_along * along_scale) + (perp_y * step_perp * perp_scale),
		)

	# Keep ordering deterministic: no motion first, then push label outward
	# along connector, then controlled perpendicular fan-out.
	return [
		(0.0, 0.0),
		_offset(1.0, 0.0),
		_offset(1.6, 0.0),
		_offset(1.0, 1.0),
		_offset(1.0, -1.0),
		_offset(1.8, 1.0),
		_offset(1.8, -1.0),
		_offset(0.8, 1.8),
		_offset(0.8, -1.8),
	]


#============================================
def _solve_chain2_label_with_resolver(
		ops: list,
		branch_point: tuple[float, float],
		preferred_endpoint: tuple[float, float],
		connector_width: float,
		text: str,
		anchor: str,
		label_direction: str,
		font_size: float,
		font_name: str,
		peer_label_target: _render_geometry.AttachTarget) -> tuple[
			float,
			float,
			_render_geometry.AttachTarget,
			_render_geometry.AttachTarget,
			tuple[float, float]]:
	"""Place chain2 label with resolver-owned endpoint targeting."""
	base_text_x = preferred_endpoint[0] + _text.anchor_x_offset(text, anchor, font_size)
	base_text_y = preferred_endpoint[1] + _text.baseline_shift(label_direction, font_size, text)
	base_attach_target = _render_geometry.label_attach_target_from_text_origin(
		text_x=base_text_x,
		text_y=base_text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		attach_atom="first",
		attach_element="C",
		attach_site="core_center",
		font_name=font_name,
	)
	base_center_x, _base_center_y = base_attach_target.centroid()
	aligned_base_x = base_text_x + (preferred_endpoint[0] - base_center_x)
	aligned_base_y = base_text_y + (preferred_endpoint[1] - _base_center_y)
	existing_label_boxes = [peer_label_target.box]
	for op in ops:
		if not isinstance(op, render_ops.TextOp):
			continue
		box = _render_geometry.label_target_from_text_origin(
			text_x=op.x,
			text_y=op.y,
			text=op.text,
			anchor=op.anchor,
			font_size=op.font_size,
			font_name=op.font_name,
		).box
		existing_label_boxes.append(box)
	best = None
	connector_unit = _geom.normalize_vector(
		preferred_endpoint[0] - branch_point[0],
		preferred_endpoint[1] - branch_point[1],
	)
	for offset_x, offset_y in _chain2_label_offset_candidates(
			connector_unit=connector_unit,
			font_size=font_size):
		candidate_x = aligned_base_x + offset_x
		candidate_y = aligned_base_y + offset_y
		candidate_attach = _render_geometry.label_attach_target_from_text_origin(
			text_x=candidate_x,
			text_y=candidate_y,
			text=text,
			anchor=anchor,
			font_size=font_size,
			attach_atom="first",
			attach_element="C",
			attach_site="core_center",
			font_name=font_name,
		)
		candidate_full = _render_geometry.label_target_from_text_origin(
			text_x=candidate_x,
			text_y=candidate_y,
			text=text,
			anchor=anchor,
			font_size=font_size,
			font_name=font_name,
		)
		candidate_endpoint = _resolve_legal_attach_endpoint(
			bond_start=branch_point,
			attach_target=candidate_attach,
			interior_hint=candidate_attach.centroid(),
			constraints=_render_geometry.AttachConstraints(direction_policy="auto"),
			line_width=connector_width,
			forbidden_regions=[candidate_full],
			allowed_regions=[candidate_attach],
			epsilon=STRICT_OVERLAP_EPSILON,
		)
		if not _point_in_target_closed(candidate_endpoint, candidate_attach):
			continue
		max_overlap = 0.0
		for existing_box in existing_label_boxes:
			max_overlap = max(max_overlap, _box_overlap_area(candidate_full.box, existing_box))
		attach_center_x, _attach_center_y = candidate_attach.centroid()
		center_x_distance = abs(attach_center_x - candidate_endpoint[0])
		preferred_delta = geometry.point_distance(
			candidate_endpoint[0],
			candidate_endpoint[1],
			preferred_endpoint[0],
			preferred_endpoint[1],
		)
		score = (max_overlap, preferred_delta, center_x_distance, abs(offset_x) + abs(offset_y))
		if best is None or score < best["score"]:
			best = {
				"score": score,
				"text_x": candidate_x,
				"text_y": candidate_y,
				"attach": candidate_attach,
				"full": candidate_full,
				"endpoint": candidate_endpoint,
			}
		if max_overlap <= STRICT_OVERLAP_EPSILON and preferred_delta <= 1e-6:
			break
	if best is None:
		raise RuntimeError(
			"No legal chain2 label placement with resolver-owned endpoint "
			f"branch={branch_point} preferred_end={preferred_endpoint} text={text!r} anchor={anchor!r}"
		)
	return (best["text_x"], best["text_y"], best["attach"], best["full"], best["endpoint"])


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
		nominal_end = (start[0] + dx * segment_length, start[1] + dy * segment_length)
		text = _text.format_chain_label_text(raw_label, anchor=anchor)
		anchor_x = _text.anchor_x_offset(text, anchor, font_size)
		text_x = nominal_end[0] + anchor_x
		text_y = nominal_end[1] + _text.baseline_shift(direction, font_size, text)
		label_target = _render_geometry.label_target_from_text_origin(
			text_x=text_x,
			text_y=text_y,
			text=text,
			anchor=anchor,
			font_size=font_size,
			font_name=font_name,
		)
		attach_target = _render_geometry.label_attach_target_from_text_origin(
			text_x=text_x,
			text_y=text_y,
			text=text,
			anchor=anchor,
			font_size=font_size,
			attach_atom="first",
			attach_element="C",
			attach_site="core_center",
			font_name=font_name,
		)
		connector_end = _resolve_legal_attach_endpoint(
			bond_start=start,
			attach_target=attach_target,
			interior_hint=attach_target.centroid(),
			constraints=_render_geometry.AttachConstraints(direction_policy="auto"),
			line_width=connector_width,
			forbidden_regions=[label_target],
			allowed_regions=[attach_target],
			epsilon=STRICT_OVERLAP_EPSILON,
		)
		ops.append(
			render_ops.LineOp(
				p1=start,
				p2=connector_end,
				width=connector_width,
				cap="round",
				color=line_color,
				z=4,
				op_id=f"C{carbon}_{direction}_chain{index}_connector",
			)
		)
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
		start = connector_end


#============================================
def _add_furanose_two_carbon_tail_ops(
		ops: list,
		carbon: int,
		slot: str,
		direction: str,
		vertex: tuple[float, float],
		ring_center: tuple[float, float],
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
	del slot
	# Keep branched tails at a readable distance from ring edges. Down-class
	# tails can otherwise look cramped and over-tuned when inherited length is
	# short from generic slot layout.
	min_standoff_factor = 1.75 if direction == "up" else 1.35
	branch_standoff = max(segment_length, font_size * min_standoff_factor)
	branch_point = (vertex[0] + dx * branch_standoff, vertex[1] + dy * branch_standoff)
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
	tail_profile = _furanose_two_carbon_tail_profile(
		direction=direction,
		vertex=vertex,
		ring_center=ring_center,
		dx=dx,
		dy=dy,
	)
	ho_dx, ho_dy = tail_profile["ho_vector"]
	ch2_dx, ch2_dy = tail_profile["ch2_vector"]
	ho_length = branch_standoff * tail_profile["ho_length_factor"]
	ch2_length = branch_standoff * tail_profile["ch2_length_factor"]
	ho_anchor = tail_profile["ho_anchor"]
	ch2_anchor = tail_profile["ch2_anchor"]
	ho_direction = tail_profile["ho_text_direction"]
	ch2_direction = tail_profile["ch2_text_direction"]
	ch2_canonical_text = bool(tail_profile.get("ch2_canonical_text", False))
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
	ho_attach_mode = "first" if ho_text == "OH" else "last"
	ho_attach_target = _render_geometry.label_attach_target_from_text_origin(
		text_x=ho_x,
		text_y=ho_y,
		text=ho_text,
		anchor=ho_anchor,
		font_size=font_size,
		attach_atom=ho_attach_mode,
		attach_element="O",
		font_name=font_name,
	)
	ho_connector_end = _resolve_legal_attach_endpoint(
		bond_start=branch_point,
		attach_target=ho_attach_target,
		interior_hint=ho_attach_target.centroid(),
		constraints=_render_geometry.AttachConstraints(direction_policy="auto"),
		line_width=connector_width,
		forbidden_regions=[ho_label_target],
		allowed_regions=[ho_attach_target],
		epsilon=STRICT_OVERLAP_EPSILON,
	)
	ch2_x, ch2_y, ch2_attach_target, ch2_label_target, ch2_connector_end = _solve_chain2_label_with_resolver(
		ops=ops,
		branch_point=branch_point,
		preferred_endpoint=ch2_end,
		connector_width=connector_width,
		text=ch2_text,
		anchor=ch2_anchor,
		label_direction=ch2_direction,
		font_size=font_size,
		font_name=font_name,
		peer_label_target=ho_label_target,
	)
	_append_branch_connector_ops(
		ops=ops,
		start=branch_point,
		end=ch2_connector_end,
		connector_width=connector_width,
		font_size=font_size,
		color=line_color,
		op_id=f"C{carbon}_{direction}_chain2_connector",
		style="hashed" if tail_profile["hashed_branch"] == "ch2" else "solid",
		forbidden_regions=[ch2_label_target],
		allowed_regions=[ch2_attach_target],
	)
	_append_branch_connector_ops(
		ops=ops,
		start=branch_point,
		end=ho_connector_end,
		connector_width=connector_width,
		font_size=font_size,
		color=line_color,
		op_id=f"C{carbon}_{direction}_chain1_oh_connector",
		style="hashed" if tail_profile["hashed_branch"] == "ho" else "solid",
		forbidden_regions=[ho_label_target],
		allowed_regions=[ho_attach_target],
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
def _furanose_two_carbon_tail_profile(
		direction: str,
		vertex: tuple[float, float],
		ring_center: tuple[float, float],
		dx: float,
		dy: float) -> dict:
	"""Build branched-tail geometry from one ring-local frame and face rule."""
	if direction not in ("up", "down"):
		raise ValueError(f"Unsupported two-carbon-tail direction: {direction!r}")
	trunk_dx, trunk_dy = _geom.normalize_vector(dx, dy)
	if abs(trunk_dx) <= 1e-9 and abs(trunk_dy) <= 1e-9:
		center_dx = vertex[0] - ring_center[0]
		center_dy = vertex[1] - ring_center[1]
		trunk_dx, trunk_dy = _geom.normalize_vector(center_dx, center_dy)
	tangent_dx, tangent_dy = (-trunk_dy, trunk_dx)
	# Stereochemical face rule for two-carbon tails:
	# "up" face keeps CH2 branch on the positive tangent side and hashes CH2;
	# "down" face keeps both branches on the negative x-facing side and hashes HO.
	if direction == "up":
		ho_tangent = -1.0
		ho_trunk = 0.50
		ch2_tangent = 1.0
		ch2_trunk = 0.95
		profile = {
			"ho_length_factor": 0.72,
			"ch2_length_factor": 1.08,
			"ho_anchor": "end",
			"ch2_anchor": "start",
			"ho_text_direction": "up",
			"ch2_text_direction": "up",
			"ch2_canonical_text": True,
			"hashed_branch": "ch2",
		}
	else:
		ho_tangent = 1.0
		ho_trunk = -0.55
		ch2_tangent = 1.0
		ch2_trunk = 0.72
		profile = {
			"ho_length_factor": 1.20,
			"ch2_length_factor": 0.95,
			"ho_anchor": "end",
			"ch2_anchor": "end",
			"ho_text_direction": "up",
			"ch2_text_direction": "down",
			"hashed_branch": "ho",
		}
	ho_vector = _geom.normalize_vector(
		(ho_tangent * tangent_dx) + (ho_trunk * trunk_dx),
		(ho_tangent * tangent_dy) + (ho_trunk * trunk_dy),
	)
	ch2_vector = _geom.normalize_vector(
		(ch2_tangent * tangent_dx) + (ch2_trunk * trunk_dx),
		(ch2_tangent * tangent_dy) + (ch2_trunk * trunk_dy),
	)
	profile["ho_vector"] = ho_vector
	profile["ch2_vector"] = ch2_vector
	return profile


#============================================
def _append_branch_connector_ops(
		ops: list,
		start: tuple[float, float],
		end: tuple[float, float],
		connector_width: float,
		font_size: float,
		color: str,
		op_id: str,
		style: str,
		forbidden_regions: list | None = None,
		allowed_regions: list | None = None) -> None:
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
	def _is_hatch_legal(hatch_line: render_ops.LineOp) -> bool:
		if not forbidden_regions:
			return True
		return _render_geometry.validate_attachment_paint(
			line_start=hatch_line.p1,
			line_end=hatch_line.p2,
			line_width=hatch_line.width,
			forbidden_regions=forbidden_regions,
			allowed_regions=allowed_regions,
			epsilon=STRICT_OVERLAP_EPSILON,
		)
	if forbidden_regions:
		kept = [line for line in kept if _is_hatch_legal(line)]
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
		origin_hatch = render_ops.LineOp(
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
		if _is_hatch_legal(origin_hatch):
			kept.append(origin_hatch)
	farthest_along = 0.0
	if kept:
		farthest_along = max(
			(((line.p1[0] + line.p2[0]) * 0.5 - start[0]) * dx)
			+ (((line.p1[1] + line.p2[1]) * 0.5 - start[1]) * dy)
			for line in kept
		)
	if farthest_along < (0.85 * length):
		perp_x, perp_y = -dy, dx
		half_span = max(connector_width * 0.45, font_size * 0.08)
		if kept:
			template = kept[-1]
			stroke_width = template.width
			stroke_cap = template.cap
		else:
			stroke_width = line_width
			stroke_cap = "round"
		terminal_added = False
		for percent in (0.92, 0.90, 0.88, 0.86, 0.85):
			terminal_along = percent * length
			if terminal_along <= farthest_along:
				continue
			center = (start[0] + (dx * terminal_along), start[1] + (dy * terminal_along))
			terminal_hatch = render_ops.LineOp(
				p1=(center[0] + (perp_x * half_span), center[1] + (perp_y * half_span)),
				p2=(center[0] - (perp_x * half_span), center[1] - (perp_y * half_span)),
				width=stroke_width,
				cap=stroke_cap,
				color=color,
				z=4,
			)
			if not _is_hatch_legal(terminal_hatch):
				continue
			kept.append(terminal_hatch)
			terminal_added = True
			break
		if not terminal_added:
			for percent in (0.84, 0.82):
				terminal_along = percent * length
				if terminal_along <= farthest_along:
					continue
				center = (start[0] + (dx * terminal_along), start[1] + (dy * terminal_along))
				terminal_hatch = render_ops.LineOp(
					p1=(center[0] + (perp_x * half_span), center[1] + (perp_y * half_span)),
					p2=(center[0] - (perp_x * half_span), center[1] - (perp_y * half_span)),
					width=stroke_width,
					cap=stroke_cap,
					color=color,
					z=4,
				)
				if _is_hatch_legal(terminal_hatch):
					kept.append(terminal_hatch)
					break
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
