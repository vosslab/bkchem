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

RING_SLOT_SEQUENCE = {
	"pyranose": ("MR", "BR", "BL", "ML", "TL"),
	"furanose": ("MR", "BR", "BL", "ML"),
}

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

RING_RENDER_CONFIG = {
	"pyranose": {
		"ring_size": 6,
		"slot_index": PYRANOSE_SLOT_INDEX,
		"slot_label_cfg": PYRANOSE_SLOT_LABEL_CONFIG,
		"front_edge_index": PYRANOSE_FRONT_EDGE_INDEX,
		"oxygen_index": haworth.PYRANOSE_O_INDEX,
	},
	"furanose": {
		"ring_size": 5,
		"slot_index": FURANOSE_SLOT_INDEX,
		"slot_label_cfg": FURANOSE_SLOT_LABEL_CONFIG,
		"front_edge_index": FURANOSE_FRONT_EDGE_INDEX,
		"oxygen_index": haworth.FURANOSE_O_INDEX,
	},
}

CARBON_NUMBER_VERTEX_WEIGHT = 0.68
OXYGEN_COLOR = "#8b0000"
HYDROXYL_GLYPH_WIDTH_FACTOR = 0.60
HYDROXYL_O_X_CENTER_FACTOR = 0.30
HYDROXYL_O_Y_CENTER_FROM_BASELINE = 0.52
HYDROXYL_O_RADIUS_FACTOR = 0.30
LEADING_C_X_CENTER_FACTOR = 0.24
HYDROXYL_LAYOUT_CANDIDATE_FACTORS = (1.00, 1.18, 1.34)
HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS = (0.88, 1.00, 1.12, 1.26, 1.42)
HYDROXYL_LAYOUT_MIN_GAP_FACTOR = 0.18
HYDROXYL_RING_COLLISION_PENALTY = 1000000.0
INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD = 0.50
INTERNAL_PAIR_LABEL_SCALE = 0.90
INTERNAL_PAIR_LANE_Y_TOLERANCE_FACTOR = 0.12
INTERNAL_PAIR_MIN_H_GAP_FACTOR = 0.75
FURANOSE_TOP_UP_CLEARANCE_FACTOR = 0.08
FURANOSE_TOP_RIGHT_HYDROXYL_EXTRA_CLEARANCE_FACTOR = 0.12
VALID_DIRECTIONS = ("up", "down")
VALID_ANCHORS = ("start", "middle", "end")
REQUIRED_SIMPLE_JOB_KEYS = (
	"carbon",
	"direction",
	"vertex",
	"dx",
	"dy",
	"length",
	"label",
	"connector_width",
	"font_size",
	"font_name",
	"anchor",
	"line_color",
	"label_color",
)


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

	coords = haworth._ring_template(ring_size, bond_length=bond_length)
	ops = []
	front_thickness = bond_length * 0.15
	back_thickness = bond_length * 0.04
	front_vertices = {front_edge_index, (front_edge_index + 1) % ring_size}
	adjacent = {(front_edge_index - 1) % ring_size, (front_edge_index + 1) % ring_size}
	ring_block_polygons = []

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
			gradient_polygons = _add_gradient_edge_ops(
				ops, p1, p2, t1, t2, edge_index,
				o_end=(start_index == o_index),
				oxygen_color=oxygen_color,
				line_color=line_color,
			)
			for polygon in gradient_polygons:
				ring_block_polygons.append(tuple(polygon))
		else:
			polygon = _edge_polygon(p1, p2, t1, t2)
			ring_block_polygons.append(tuple(polygon))
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
	slot_to_carbon = {slot: int(carbon_key[1:]) for carbon_key, slot in slot_map.items()}
	left_top_carbon = slot_to_carbon.get("ML")
	left_top_up_label = "H"
	if left_top_carbon is not None:
		left_top_up_label = spec.substituents.get(f"C{left_top_carbon}_up", "H")
	left_top_is_chain_like = _is_chain_like_label(left_top_up_label)
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
			dx, dy = _normalize_vector(raw_dx, raw_dy)
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
					and str(label) == "CH(OH)CH2OH"
					and slot in ("ML", "MR")
			):
				_add_furanose_two_carbon_tail_ops(
					ops=ops,
					carbon=carbon,
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
			chain_labels = _chain_labels(label)
			if chain_labels:
				_add_chain_ops(
					ops=ops,
					carbon=carbon,
					direction=direction,
					vertex=vertex,
					dx=dx,
					dy=dy,
					segment_length=effective_length,
					labels=chain_labels,
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

	for job in _resolve_hydroxyl_layout_jobs(simple_jobs, blocked_polygons=ring_block_polygons):
		_add_simple_label_ops(
			ops=ops,
			carbon=job["carbon"],
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
def _validate_simple_job(job: dict) -> None:
	"""Validate one simple-label layout job for deterministic processing."""
	missing = [key for key in REQUIRED_SIMPLE_JOB_KEYS if key not in job]
	if missing:
		raise ValueError("Simple label job missing required keys: %s" % ", ".join(missing))
	if job["direction"] not in VALID_DIRECTIONS:
		raise ValueError("Simple label job has invalid direction '%s'" % job["direction"])
	if job["anchor"] not in VALID_ANCHORS:
		raise ValueError("Simple label job has invalid anchor '%s'" % job["anchor"])
	if "ring_type" in job or "slot" in job:
		if "ring_type" not in job or "slot" not in job:
			raise ValueError("Simple label job must include both ring_type and slot together")
		ring_type = job["ring_type"]
		slot = job["slot"]
		slot_sequence = _ring_slot_sequence(ring_type)
		if slot not in slot_sequence:
			raise ValueError(
				"Simple label job has slot '%s' not valid for ring_type '%s'" % (slot, ring_type)
			)


def _resolve_hydroxyl_layout_jobs(
		jobs: list[dict],
		blocked_polygons: list[tuple[tuple[float, float], ...]] | None = None) -> list[dict]:
	"""Two-pass placement for OH/HO labels using a tiny candidate slot set."""
	if not jobs:
		return []
	for job in jobs:
		_validate_simple_job(job)
	min_gap = jobs[0]["font_size"] * HYDROXYL_LAYOUT_MIN_GAP_FACTOR
	blocked = list(blocked_polygons or [])
	occupied = []
	resolved = []
	internal_hydroxyl_up_indices = []

	for job in jobs:
		if _job_is_hydroxyl(job):
			continue
		occupied.append(_job_text_bbox(job, job["length"]))

	for job in jobs:
		if not _job_is_hydroxyl(job):
			resolved.append(job)
			continue
		best_job = dict(job)
		best_penalty = _hydroxyl_job_penalty(best_job, occupied, blocked, min_gap)
		for candidate_job in _hydroxyl_candidate_jobs(
				job,
				allow_anchor_flip=_job_can_flip_internal_anchor(job),
		):
			penalty = _hydroxyl_job_penalty(candidate_job, occupied, blocked, min_gap)
			if penalty <= 0.0:
				best_job = candidate_job
				best_penalty = penalty
				break
			if penalty < best_penalty:
				best_job = candidate_job
				best_penalty = penalty
		resolved.append(best_job)
		if _job_is_internal_hydroxyl(best_job) and best_job["direction"] == "up":
			internal_hydroxyl_up_indices.append(len(resolved) - 1)
		occupied.append(_job_text_bbox(best_job, best_job["length"]))

	if len(internal_hydroxyl_up_indices) >= 2:
		internal_index_set = set(internal_hydroxyl_up_indices)
		fixed_occupied = []
		for index, fixed_job in enumerate(resolved):
			if index in internal_index_set:
				continue
			fixed_occupied.append(_job_text_bbox(fixed_job, fixed_job["length"]))
		internal_jobs = [resolved[index] for index in internal_hydroxyl_up_indices]
		equal_length = _best_equal_internal_hydroxyl_length(
			internal_jobs=internal_jobs,
			occupied=fixed_occupied,
			blocked_polygons=blocked,
			min_gap=min_gap,
		)
		for index in internal_hydroxyl_up_indices:
			resolved[index]["length"] = equal_length
	_resolve_internal_hydroxyl_pair_overlap(resolved)
	return resolved


#============================================
def _job_is_hydroxyl(job: dict) -> bool:
	"""Return True when one simple-label job renders as OH/HO."""
	text = _format_label_text(job["label"], anchor=job["anchor"])
	return text in ("OH", "HO")


#============================================
def _job_is_internal_hydroxyl(job: dict) -> bool:
	"""Return True for hydroxyl labels drawn into the ring interior."""
	if job.get("direction") != "up":
		return False
	ring_type = job.get("ring_type")
	slot = job.get("slot")
	if ring_type == "pyranose":
		return slot in ("BR", "BL")
	if ring_type == "furanose":
		return slot in ("BR", "BL")
	return False


#============================================
def _job_can_flip_internal_anchor(job: dict) -> bool:
	"""Return True when internal hydroxyl candidates may flip HO/OH anchor side."""
	if not _job_is_internal_hydroxyl(job):
		return False
	return job.get("ring_type") == "furanose"


#============================================
def _best_equal_internal_hydroxyl_length(
		internal_jobs: list[dict],
		occupied: list[tuple[float, float, float, float]],
		blocked_polygons: list[tuple[tuple[float, float], ...]],
		min_gap: float) -> float:
	"""Select one shared internal hydroxyl length with minimal overlap penalty."""
	base_lengths = [job["length"] for job in internal_jobs]
	candidate_lengths = set(base_lengths)
	base_max = max(base_lengths)
	for factor in HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS:
		candidate_lengths.add(base_max * factor)
	ordered_candidates = sorted(candidate_lengths)
	best_length = ordered_candidates[0]
	best_penalty = float("inf")
	for length in ordered_candidates:
		candidate_occupied = list(occupied)
		total_penalty = 0.0
		for job in internal_jobs:
			candidate = dict(job)
			candidate["length"] = length
			total_penalty += _hydroxyl_job_penalty(
				candidate,
				candidate_occupied,
				blocked_polygons,
				min_gap,
			)
			candidate_occupied.append(_job_text_bbox(candidate, candidate["length"]))
		if total_penalty < best_penalty:
			best_penalty = total_penalty
			best_length = length
		if total_penalty <= 0.0:
			break
	return best_length


#============================================
def _hydroxyl_candidate_jobs(job: dict, allow_anchor_flip: bool = False) -> list[dict]:
	"""Build a tiny candidate set for hydroxyl placement search."""
	candidates = []
	anchor_candidates = [job["anchor"]]
	if allow_anchor_flip:
		if job["anchor"] == "start":
			anchor_candidates.append("end")
		elif job["anchor"] == "end":
			anchor_candidates.append("start")
	if allow_anchor_flip:
		factors = HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS
	else:
		factors = HYDROXYL_LAYOUT_CANDIDATE_FACTORS
	for anchor in anchor_candidates:
		for factor in factors:
			candidate = dict(job)
			candidate["anchor"] = anchor
			candidate["length"] = job["length"] * factor
			candidates.append(candidate)
	return candidates


#============================================
def _job_end_point(job: dict, length: float | None = None) -> tuple[float, float]:
	"""Return connector endpoint for one job."""
	if length is None:
		length = job["length"]
	return (
		job["vertex"][0] + (job["dx"] * length),
		job["vertex"][1] + (job["dy"] * length),
	)


#============================================
def _internal_pair_overlap_area(left_job: dict, right_job: dict) -> float:
	"""Compute overlap area between two internal hydroxyl label boxes."""
	left_box = _job_text_bbox(left_job, left_job["length"])
	right_box = _job_text_bbox(right_job, right_job["length"])
	return _intersection_area(left_box, right_box, gap=0.0)


#============================================
def _internal_pair_horizontal_gap(left_job: dict, right_job: dict) -> float:
	"""Return horizontal box gap between left/right internal pair labels."""
	left_box = _job_text_bbox(left_job, left_job["length"])
	right_box = _job_text_bbox(right_job, right_job["length"])
	return right_box[0] - left_box[2]


#============================================
def _resolve_internal_hydroxyl_pair_overlap(jobs: list[dict]) -> None:
	"""Apply one deterministic local fix for overlapping internal OH/HO pairs."""
	internal_indices = [
		index
		for index, job in enumerate(jobs)
		if _job_is_internal_hydroxyl(job) and _job_is_hydroxyl(job)
	]
	if len(internal_indices) < 2:
		return
	lane_tolerance = jobs[internal_indices[0]]["font_size"] * INTERNAL_PAIR_LANE_Y_TOLERANCE_FACTOR
	sorted_indices = sorted(
		internal_indices,
		key=lambda index: _job_end_point(jobs[index])[1],
	)
	groups = []
	current_group = []
	current_lane = None
	for index in sorted_indices:
		lane_y = _job_end_point(jobs[index])[1]
		if not current_group:
			current_group = [index]
			current_lane = lane_y
			continue
		if abs(lane_y - current_lane) <= lane_tolerance:
			current_group.append(index)
			continue
		groups.append(current_group)
		current_group = [index]
		current_lane = lane_y
	if current_group:
		groups.append(current_group)
	for group in groups:
		if len(group) != 2:
			continue
		left_index, right_index = sorted(
			group,
			key=lambda index: _job_end_point(jobs[index])[0],
		)
		left_job = dict(jobs[left_index])
		right_job = dict(jobs[right_index])
		ring_type = left_job.get("ring_type")
		if ring_type == "pyranose" and right_job.get("ring_type") == "pyranose":
			# Keep interior pyranose hydroxyls center-facing: OH ... HO.
			left_job["anchor"] = "start"
			right_job["anchor"] = "end"
		elif ring_type == "furanose" and right_job.get("ring_type") == "furanose":
			# Keep classic interior reading order (OH ... HO) and use
			# small local label scaling instead of widening the pair.
			left_job["anchor"] = "start"
			right_job["anchor"] = "end"
			left_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
			right_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
		else:
			left_job["anchor"] = "end"
			right_job["anchor"] = "start"
		if ring_type != "furanose" or right_job.get("ring_type") != "furanose":
			overlap = _internal_pair_overlap_area(left_job, right_job)
			min_gap = left_job["font_size"] * INTERNAL_PAIR_MIN_H_GAP_FACTOR
			h_gap = _internal_pair_horizontal_gap(left_job, right_job)
			if overlap > INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD or h_gap < min_gap:
				left_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
				right_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
		jobs[left_index] = left_job
		jobs[right_index] = right_job


#============================================
def _job_text_bbox(job: dict, length: float) -> tuple[float, float, float, float]:
	"""Approximate text bbox for one simple-label placement job."""
	end_x, end_y = _job_end_point(job, length)
	text = _format_label_text(job["label"], anchor=job["anchor"])
	layout_font_size = job["font_size"]
	draw_font_size = layout_font_size * float(job.get("text_scale", 1.0))
	text_x = end_x + _anchor_x_offset(text, job["anchor"], layout_font_size)
	text_y = end_y + _baseline_shift(job["direction"], layout_font_size, text)
	return _text_bbox(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=job["anchor"],
		font_size=draw_font_size,
	)


#============================================
def _text_bbox(
		text_x: float,
		text_y: float,
		text: str,
		anchor: str,
		font_size: float) -> tuple[float, float, float, float]:
	"""Approximate text bounding box from text geometry fields."""
	visible = _visible_text_length(text)
	width = visible * font_size * 0.60
	height = font_size
	if anchor == "middle":
		x_left = text_x - (width / 2.0)
	elif anchor == "end":
		x_left = text_x - width
	else:
		x_left = text_x
	return (x_left, text_y - height, x_left + width, text_y)


#============================================
def _overlap_penalty(
		box: tuple[float, float, float, float],
		occupied_boxes: list[tuple[float, float, float, float]],
		gap: float) -> float:
	"""Return summed overlap area against occupied boxes with required minimum gap."""
	total = 0.0
	for other in occupied_boxes:
		area = _intersection_area(box, other, gap)
		if area > 0.0:
			total += area
	return total


#============================================
def _hydroxyl_job_penalty(
		job: dict,
		occupied: list[tuple[float, float, float, float]],
		blocked_polygons: list[tuple[tuple[float, float], ...]],
		min_gap: float) -> float:
	"""Return overlap penalty for one hydroxyl job against occupied boxes."""
	box = _job_text_bbox(job, job["length"])
	penalty = _overlap_penalty(box, occupied, min_gap)
	if _job_is_internal_hydroxyl(job):
		for polygon in blocked_polygons:
			if _box_overlaps_polygon(box, polygon):
				penalty += HYDROXYL_RING_COLLISION_PENALTY
	return penalty


#============================================
def _intersection_area(
		box_a: tuple[float, float, float, float],
		box_b: tuple[float, float, float, float],
		gap: float = 0.0) -> float:
	"""Return intersection area after expanding each box by half the required gap."""
	half_gap = gap / 2.0
	ax0 = box_a[0] - half_gap
	ay0 = box_a[1] - half_gap
	ax1 = box_a[2] + half_gap
	ay1 = box_a[3] + half_gap
	bx0 = box_b[0] - half_gap
	by0 = box_b[1] - half_gap
	bx1 = box_b[2] + half_gap
	by1 = box_b[3] + half_gap
	overlap_w = min(ax1, bx1) - max(ax0, bx0)
	overlap_h = min(ay1, by1) - max(ay0, by0)
	if overlap_w <= 0.0 or overlap_h <= 0.0:
		return 0.0
	return overlap_w * overlap_h


#============================================
def _point_in_box(
		point: tuple[float, float],
		box: tuple[float, float, float, float]) -> bool:
	"""Return True when one point lies inside one bbox."""
	return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


#============================================
def _rect_corners(box: tuple[float, float, float, float]) -> list[tuple[float, float]]:
	"""Return rectangle corners in clockwise order."""
	return [
		(box[0], box[1]),
		(box[2], box[1]),
		(box[2], box[3]),
		(box[0], box[3]),
	]


#============================================
def _point_in_polygon(
		point: tuple[float, float],
		polygon: tuple[tuple[float, float], ...]) -> bool:
	"""Return True when point is inside polygon using ray-casting."""
	x_value, y_value = point
	inside = False
	count = len(polygon)
	for index in range(count):
		x1, y1 = polygon[index]
		x2, y2 = polygon[(index + 1) % count]
		intersects = ((y1 > y_value) != (y2 > y_value))
		if not intersects:
			continue
		denominator = y2 - y1
		if abs(denominator) < 1e-9:
			continue
		x_intersect = x1 + ((y_value - y1) * (x2 - x1) / denominator)
		if x_intersect >= x_value:
			inside = not inside
	return inside


#============================================
def _segments_intersect(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float]) -> bool:
	"""Return True when two closed line segments intersect."""
	def _cross(p1, p2, p3):
		return ((p2[0] - p1[0]) * (p3[1] - p1[1])) - ((p2[1] - p1[1]) * (p3[0] - p1[0]))

	def _on_segment(p1, p2, p3):
		return (
			min(p1[0], p2[0]) - 1e-9 <= p3[0] <= max(p1[0], p2[0]) + 1e-9
			and min(p1[1], p2[1]) - 1e-9 <= p3[1] <= max(p1[1], p2[1]) + 1e-9
		)

	d1 = _cross(a1, a2, b1)
	d2 = _cross(a1, a2, b2)
	d3 = _cross(b1, b2, a1)
	d4 = _cross(b1, b2, a2)
	if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
		return True
	if abs(d1) < 1e-9 and _on_segment(a1, a2, b1):
		return True
	if abs(d2) < 1e-9 and _on_segment(a1, a2, b2):
		return True
	if abs(d3) < 1e-9 and _on_segment(b1, b2, a1):
		return True
	if abs(d4) < 1e-9 and _on_segment(b1, b2, a2):
		return True
	return False


#============================================
def _box_overlaps_polygon(
		box: tuple[float, float, float, float],
		polygon: tuple[tuple[float, float], ...]) -> bool:
	"""Return True when one bbox intersects one polygon."""
	for point in polygon:
		if _point_in_box(point, box):
			return True
	for corner in _rect_corners(box):
		if _point_in_polygon(corner, polygon):
			return True
	rect_points = _rect_corners(box)
	rect_edges = [
		(rect_points[0], rect_points[1]),
		(rect_points[1], rect_points[2]),
		(rect_points[2], rect_points[3]),
		(rect_points[3], rect_points[0]),
	]
	for index in range(len(polygon)):
		edge_start = polygon[index]
		edge_end = polygon[(index + 1) % len(polygon)]
		for rect_start, rect_end in rect_edges:
			if _segments_intersect(edge_start, edge_end, rect_start, rect_end):
				return True
	return False


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
		text_scale: float,
		font_name: str,
		anchor: str,
		line_color: str,
		label_color: str) -> None:
	"""Add one connector line + one label."""
	end_point = (vertex[0] + dx * length, vertex[1] + dy * length)
	text = _format_label_text(label, anchor=anchor)
	anchor_x = _anchor_x_offset(text, anchor, font_size)
	text_x = end_point[0] + anchor_x
	text_y = end_point[1] + _baseline_shift(direction, font_size, text)
	draw_font_size = font_size * text_scale
	connector_end = end_point
	c_center = _leading_carbon_center(text, anchor, text_x, text_y, draw_font_size)
	if direction == "down" and c_center is not None:
		# For downward CH* labels, keep x centered on the leading carbon but
		# stop just above the top glyph boundary so the bond cap touches the text
		# without running through the "C" character.
		label_top = text_y - draw_font_size
		max_tip_y = label_top - (draw_font_size * 0.10)
		connector_end = (c_center[0], min(c_center[1], max_tip_y))
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
		text = _format_chain_label_text(raw_label, anchor=anchor)
		anchor_x = _anchor_x_offset(text, anchor, font_size)
		text_x = end[0] + anchor_x
		text_y = end[1] + _baseline_shift(direction, font_size, text)
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
	lateral = -1.0 if anchor == "end" else 1.0
	ho_dx, ho_dy = _normalize_vector(lateral, -0.55)
	ch2_dx, ch2_dy = _normalize_vector(lateral, 0.72)
	ho_length = segment_length * 0.78
	ch2_length = segment_length * 0.95
	ho_end = (
		branch_point[0] + (ho_dx * ho_length),
		branch_point[1] + (ho_dy * ho_length),
	)
	ch2_end = (
		branch_point[0] + (ch2_dx * ch2_length),
		branch_point[1] + (ch2_dy * ch2_length),
	)
	ops.append(
		render_ops.LineOp(
			p1=branch_point,
			p2=ho_end,
			width=connector_width,
			cap="round",
			color=line_color,
			z=4,
			op_id=f"C{carbon}_{direction}_chain1_oh_connector",
		)
	)
	ops.append(
		render_ops.LineOp(
			p1=branch_point,
			p2=ch2_end,
			width=connector_width,
			cap="round",
			color=line_color,
			z=4,
			op_id=f"C{carbon}_{direction}_chain2_connector",
		)
	)
	ho_text = _format_label_text("OH", anchor=anchor)
	ho_x = ho_end[0] + _anchor_x_offset(ho_text, anchor, font_size)
	ho_y = ho_end[1] + _baseline_shift("up", font_size, ho_text)
	ops.append(
		render_ops.TextOp(
			x=ho_x,
			y=ho_y,
			text=ho_text,
			font_size=font_size,
			font_name=font_name,
			anchor=anchor,
			weight="normal",
			color=label_color,
			z=5,
			op_id=f"C{carbon}_{direction}_chain1_oh_label",
		)
	)
	ch2_text = _format_chain_label_text("CH2OH", anchor=anchor)
	ch2_x = ch2_end[0] + _anchor_x_offset(ch2_text, anchor, font_size)
	ch2_y = ch2_end[1] + _baseline_shift("down", font_size, ch2_text)
	ops.append(
		render_ops.TextOp(
			x=ch2_x,
			y=ch2_y,
			text=ch2_text,
			font_size=font_size,
			font_name=font_name,
			anchor=anchor,
			weight="normal",
			color=label_color,
			z=5,
			op_id=f"C{carbon}_{direction}_chain2_label",
		)
	)


#============================================
def _baseline_shift(direction: str, font_size: float, text: str = "") -> float:
	"""Compute vertical baseline correction for label text.

	For downward labels the text baseline needs to shift down so the top
	of the glyphs aligns with the connector endpoint.  For upward labels
	the baseline shift is near zero (text hangs below the endpoint).
	"""
	if text in ("OH", "HO"):
		# Keep connector endpoints clear of hydroxyl oxygen glyphs.
		if direction == "down":
			return font_size * 0.90
		return -font_size * 0.10
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
		line_color: str) -> list[tuple[tuple[float, float], ...]]:
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
	return [tuple(poly_o), tuple(poly_c)]


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
def _is_chain_like_label(label: str) -> bool:
	"""Return True for compact CH* labels that render as chain-like substituents."""
	text = str(label or "")
	if text.startswith("CH"):
		return True
	return _chain_labels(text) is not None


#============================================
def _format_label_text(label: str, anchor: str = "middle") -> str:
	"""Convert plain labels to display text with side-aware hydroxyl ordering."""
	text = str(label)
	if text == "OH" and anchor == "end":
		text = "HO"
	text = _apply_subscript_markup(text)
	return text


#============================================
def _format_chain_label_text(label: str, anchor: str = "middle") -> str:
	"""Format exocyclic-chain segment labels with side-aware left-end flipping."""
	text = str(label)
	if anchor == "end":
		if text == "CH2OH":
			text = "HOH2C"
		elif text == "CHOH":
			text = "HOHC"
	text = _apply_subscript_markup(text)
	return text


#============================================
def _apply_subscript_markup(text: str) -> str:
	"""Apply subscript markup for compact numeric label fragments."""
	text = text.replace("CH2OH", "CH<sub>2</sub>OH")
	text = text.replace("HOH2C", "HOH<sub>2</sub>C")
	return text


#============================================
def _anchor_x_offset(text: str, anchor: str, font_size: float) -> float:
	"""Shift text so hydroxyl connectors terminate at oxygen glyph center."""
	if text == "OH":
		if anchor == "start":
			return -font_size * 0.30
		if anchor == "end":
			return font_size * 0.90
	if text == "HO":
		if anchor == "start":
			return -font_size * 0.90
		if anchor == "end":
			return font_size * 0.30
	carbon_offset = _leading_carbon_anchor_offset(text, anchor, font_size)
	if carbon_offset is not None:
		return carbon_offset
	trailing_carbon_offset = _trailing_carbon_anchor_offset(text, anchor, font_size)
	if trailing_carbon_offset is not None:
		return trailing_carbon_offset
	if anchor == "start":
		return font_size * 0.12
	if anchor == "end":
		return -font_size * 0.12
	return 0.0


#============================================
def _leading_carbon_anchor_offset(text: str, anchor: str, font_size: float) -> float | None:
	"""Return text-x offset for labels that should connect at leading-carbon center."""
	visible = re.sub(r"<[^>]+>", "", text or "")
	if not visible.startswith("C"):
		return None
	text_width = len(visible) * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	c_center = font_size * LEADING_C_X_CENTER_FACTOR
	if anchor == "start":
		return -c_center
	if anchor == "middle":
		return (text_width / 2.0) - c_center
	if anchor == "end":
		return text_width - c_center
	return None


#============================================
def _trailing_carbon_anchor_offset(text: str, anchor: str, font_size: float) -> float | None:
	"""Return text-x offset for labels that connect at trailing-carbon center."""
	visible = re.sub(r"<[^>]+>", "", text or "")
	if not visible.endswith("C"):
		return None
	text_width = len(visible) * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	c_center = font_size * LEADING_C_X_CENTER_FACTOR
	if anchor == "start":
		return -(text_width - c_center)
	if anchor == "middle":
		return -((text_width / 2.0) - c_center)
	if anchor == "end":
		return c_center
	return None


#============================================
def _hydroxyl_oxygen_radius(font_size: float) -> float:
	"""Approximate oxygen glyph radius for OH/HO overlap checks."""
	return font_size * HYDROXYL_O_RADIUS_FACTOR


#============================================
def _leading_carbon_center(
		text: str,
		anchor: str,
		text_x: float,
		text_y: float,
		font_size: float) -> tuple[float, float] | None:
	"""Approximate leading-carbon glyph center for C* labels."""
	visible = re.sub(r"<[^>]+>", "", text or "")
	if not visible.startswith("C"):
		return None
	text_width = len(visible) * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	if anchor == "start":
		start_x = text_x
	elif anchor == "end":
		start_x = text_x - text_width
	elif anchor == "middle":
		start_x = text_x - (text_width / 2.0)
	else:
		start_x = text_x
	c_center_x = start_x + (font_size * LEADING_C_X_CENTER_FACTOR)
	c_center_y = text_y - (font_size * HYDROXYL_O_Y_CENTER_FROM_BASELINE)
	return (c_center_x, c_center_y)


#============================================
def _hydroxyl_oxygen_center(
		text: str,
		anchor: str,
		text_x: float,
		text_y: float,
		font_size: float) -> tuple[float, float] | None:
	"""Approximate oxygen glyph center in OH/HO label coordinates."""
	if text not in ("OH", "HO"):
		return None
	visible = _visible_text_length(text)
	text_width = visible * font_size * HYDROXYL_GLYPH_WIDTH_FACTOR
	if anchor == "start":
		start_x = text_x
	elif anchor == "end":
		start_x = text_x - text_width
	elif anchor == "middle":
		start_x = text_x - (text_width / 2.0)
	else:
		start_x = text_x
	o_index = text.find("O")
	if o_index < 0:
		return None
	o_center_x = start_x + ((o_index * HYDROXYL_GLYPH_WIDTH_FACTOR) + HYDROXYL_O_X_CENTER_FACTOR) * font_size
	o_center_y = text_y - (font_size * HYDROXYL_O_Y_CENTER_FROM_BASELINE)
	return (o_center_x, o_center_y)


#============================================
def _visible_text_length(text: str) -> int:
	"""Count visible characters, ignoring HTML-like tags."""
	return len(re.sub(r"<[^>]+>", "", text or ""))
