#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Schematic Haworth renderer producing shared render_ops primitives."""

# Standard Library
import math
import re

# local repo modules
from . import haworth
from . import render_ops
from .haworth_spec import HaworthSpec


#============================================
PYRANOSE_SLOTS = ("ML", "TL", "TO", "MR", "BR", "BL")
FURANOSE_SLOTS = ("ML", "BL", "BR", "MR", "TO")

PYRANOSE_SLOT_INDEX = {
	"ML": 0,
	"TL": 1,
	"TO": 2,
	"MR": 3,
	"BR": 4,
	"BL": 5,
}

FURANOSE_SLOT_INDEX = {
	"ML": 0,
	"BL": 1,
	"BR": 2,
	"MR": 3,
	"TO": 4,
}

PYRANOSE_FRONT_EDGE_SLOT = "BR"
FURANOSE_FRONT_EDGE_SLOT = "BL"

PYRANOSE_FRONT_EDGE_INDEX = PYRANOSE_SLOT_INDEX[PYRANOSE_FRONT_EDGE_SLOT]
FURANOSE_FRONT_EDGE_INDEX = FURANOSE_SLOT_INDEX[FURANOSE_FRONT_EDGE_SLOT]

PYRANOSE_SLOT_LABEL_CONFIG = {
	"MR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BL": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
	"ML": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
	"TL": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "middle"},
}

FURANOSE_SLOT_LABEL_CONFIG = {
	"MR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BL": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
	"ML": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
}

CARBON_NUMBER_VERTEX_WEIGHT = 0.68
OXYGEN_COLOR = "#8b0000"


#============================================
def carbon_slot_map(spec: HaworthSpec) -> dict[str, str]:
	"""Map ring carbons from HaworthSpec to stable slot identifiers."""
	carbons = _ring_carbons(spec)
	anomeric = min(carbons)
	if spec.ring_type == "pyranose":
		slot_sequence = ("MR", "BR", "BL", "ML", "TL")
	elif spec.ring_type == "furanose":
		slot_sequence = ("MR", "BR", "BL", "ML")
	else:
		raise ValueError("Unsupported ring_type '%s'" % spec.ring_type)
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
	if spec.ring_type == "pyranose":
		ring_size = 6
		slot_index = PYRANOSE_SLOT_INDEX
		slot_label_cfg = PYRANOSE_SLOT_LABEL_CONFIG
		front_edge_index = PYRANOSE_FRONT_EDGE_INDEX
		o_index = haworth.PYRANOSE_O_INDEX
	elif spec.ring_type == "furanose":
		ring_size = 5
		slot_index = FURANOSE_SLOT_INDEX
		slot_label_cfg = FURANOSE_SLOT_LABEL_CONFIG
		front_edge_index = FURANOSE_FRONT_EDGE_INDEX
		o_index = haworth.FURANOSE_O_INDEX
	else:
		raise ValueError("Unsupported ring_type '%s'" % spec.ring_type)

	coords = haworth._ring_template(ring_size, bond_length=bond_length)
	ops = []
	front_thickness = bond_length * 0.15
	back_thickness = bond_length * 0.04
	front_vertices = {front_edge_index, (front_edge_index + 1) % ring_size}
	adjacent = {(front_edge_index - 1) % ring_size, (front_edge_index + 1) % ring_size}

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
		if touches_oxygen and oxygen_color != line_color:
			_add_gradient_edge_ops(
				ops, p1, p2, t1, t2, edge_index,
				o_end=(start_index == o_index),
				oxygen_color=oxygen_color,
				line_color=line_color,
			)
		else:
			polygon = _edge_polygon(p1, p2, t1, t2)
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

	ox, oy = coords[o_index]
	mask_half_w = font_size * 0.60
	mask_half_h = font_size * 0.55
	mask_points = (
		(ox - mask_half_w, oy - mask_half_h),
		(ox + mask_half_w, oy - mask_half_h),
		(ox + mask_half_w, oy + mask_half_h),
		(ox - mask_half_w, oy + mask_half_h),
	)
	ops.append(
		render_ops.PolygonOp(
			points=mask_points,
			fill=bg_color,
			stroke=None,
			stroke_width=0.0,
			z=2,
			op_id="oxygen_mask",
		)
	)
	ops.append(
		render_ops.TextOp(
			x=ox,
			y=oy + (font_size * 0.35),
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
	default_sub_length = bond_length * 0.45
	connector_width = back_thickness

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
			dx, dy = _normalize_vector(raw_dx, raw_dy)
			anchor = slot_label_cfg[slot]["anchor"]
			chain_labels = _chain_labels(label)
			if chain_labels:
				_add_chain_ops(
					ops=ops,
					carbon=carbon,
					direction=direction,
					vertex=vertex,
					dx=dx,
					dy=dy,
					segment_length=sub_length,
					labels=chain_labels,
					connector_width=connector_width,
					font_size=font_size,
					font_name=font_name,
					anchor=anchor,
					line_color=line_color,
					label_color=label_color,
				)
				continue
			_add_simple_label_ops(
				ops=ops,
				carbon=carbon,
				direction=direction,
				vertex=vertex,
				dx=dx,
				dy=dy,
				length=sub_length,
				label=label,
				connector_width=connector_width,
				font_size=font_size,
				font_name=font_name,
				anchor=anchor,
				line_color=line_color,
				label_color=label_color,
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
def _normalize_vector(dx: float, dy: float) -> tuple[float, float]:
	"""Normalize one direction vector."""
	magnitude = math.hypot(dx, dy)
	if magnitude == 0:
		return (0.0, 0.0)
	return (dx / magnitude, dy / magnitude)


#============================================
def _edge_polygon(
		p1: tuple[float, float],
		p2: tuple[float, float],
		thickness_at_p1: float,
		thickness_at_p2: float) -> tuple[tuple[float, float], ...]:
	"""Compute a 4-point polygon for one edge with optional taper."""
	x1, y1 = p1
	x2, y2 = p2
	length = math.hypot(x2 - x1, y2 - y1)
	if length == 0:
		return (p1, p1, p1, p1)
	nx = -(y2 - y1) / length
	ny = (x2 - x1) / length
	half1 = thickness_at_p1 / 2.0
	half2 = thickness_at_p2 / 2.0
	return (
		(x1 + nx * half1, y1 + ny * half1),
		(x1 - nx * half1, y1 - ny * half1),
		(x2 - nx * half2, y2 - ny * half2),
		(x2 + nx * half2, y2 + ny * half2),
	)


#============================================
def _add_simple_label_ops(
		ops: list,
		carbon: int,
		direction: str,
		vertex: tuple[float, float],
		dx: float,
		dy: float,
		length: float,
		label: str,
		connector_width: float,
		font_size: float,
		font_name: str,
		anchor: str,
		line_color: str,
		label_color: str) -> None:
	"""Add one connector line + one label."""
	end_point = (vertex[0] + dx * length, vertex[1] + dy * length)
	ops.append(
		render_ops.LineOp(
			p1=vertex,
			p2=end_point,
			width=connector_width,
			cap="round",
			color=line_color,
			z=4,
			op_id=f"C{carbon}_{direction}_connector",
		)
	)
	text = _format_label_text(label, anchor=anchor)
	anchor_x = _anchor_x_offset(anchor, font_size)
	text_x = end_point[0] + anchor_x
	text_y = end_point[1] + _baseline_shift(direction, font_size)
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
			op_id=f"C{carbon}_{direction}_label",
		)
	)


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
	anchor_x = _anchor_x_offset(anchor, font_size)
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
		text_x = end[0] + anchor_x
		text_y = end[1] + _baseline_shift(direction, font_size)
		ops.append(
			render_ops.TextOp(
				x=text_x,
				y=text_y,
				text=_format_label_text(raw_label, anchor=anchor),
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
def _baseline_shift(direction: str, font_size: float) -> float:
	"""Compute vertical baseline correction for label text.

	For downward labels the text baseline needs to shift down so the top
	of the glyphs aligns with the connector endpoint.  For upward labels
	the baseline shift is near zero (text hangs below the endpoint).
	"""
	if direction == "down":
		return font_size * 0.35
	return -font_size * 0.10


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
		line_color: str) -> None:
	"""Split one ring edge into two colored halves (gradient near oxygen)."""
	mx = (p1[0] + p2[0]) / 2.0
	my = (p1[1] + p2[1]) / 2.0
	tm = (t1 + t2) / 2.0
	if o_end:
		# p1 is the oxygen end
		poly_o = _edge_polygon(p1, (mx, my), t1, tm)
		poly_c = _edge_polygon((mx, my), p2, tm, t2)
	else:
		# p2 is the oxygen end
		poly_c = _edge_polygon(p1, (mx, my), t1, tm)
		poly_o = _edge_polygon((mx, my), p2, tm, t2)
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


#============================================
def _chain_labels(label: str) -> list[str] | None:
	"""Convert compact exocyclic label markers to rendered segment labels."""
	if label == "CH(OH)CH2OH":
		return ["CHOH", "CH2OH"]
	match = re.match(r"^CHAIN(\d+)$", label or "")
	if not match:
		return None
	count = int(match.group(1))
	if count < 2:
		return None
	labels = []
	for _ in range(count - 1):
		labels.append("CHOH")
	labels.append("CH2OH")
	return labels


#============================================
def _format_label_text(label: str, anchor: str = "middle") -> str:
	"""Convert plain labels to display text with side-aware hydroxyl ordering."""
	text = str(label)
	if text == "OH" and anchor == "end":
		text = "HO"
	text = text.replace("CH2OH", "CH<sub>2</sub>OH")
	return text


#============================================
def _anchor_x_offset(anchor: str, font_size: float) -> float:
	"""Shift text slightly away from vertical connector ends."""
	if anchor == "start":
		return font_size * 0.12
	if anchor == "end":
		return -font_size * 0.12
	return 0.0


#============================================
def _visible_text_length(text: str) -> int:
	"""Count visible characters, ignoring HTML-like tags."""
	return len(re.sub(r"<[^>]+>", "", text or ""))
