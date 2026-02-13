"""Haworth ring detection for glyph-bond alignment measurement."""

# Standard Library
import math

from measurelib.constants import HAWORTH_RING_MIN_PRIMITIVES, HAWORTH_RING_SEARCH_RADIUS
from measurelib.util import length_stats, line_endpoints, line_length
from measurelib.geometry import points_close


#============================================
def canonical_cycle_key(node_indexes: list[int]) -> tuple[int, ...]:
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
def cycle_node_pairs(node_cycle: tuple[int, ...]) -> list[tuple[int, int]]:
	"""Return normalized node-pairs for one closed cycle."""
	pairs = []
	for index, node_value in enumerate(node_cycle):
		next_node = node_cycle[(index + 1) % len(node_cycle)]
		pairs.append((min(node_value, next_node), max(node_value, next_node)))
	return pairs


#============================================
def clustered_endpoint_graph(
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
		p1, p2 = line_endpoints(line)
		node_indexes = []
		for point in (p1, p2):
			matched_node = None
			for node_index, node_point in enumerate(nodes):
				if points_close(point, node_point, tol=merge_tol):
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
def find_candidate_cycles(adjacency: dict[int, set[int]], min_size: int = 5, max_size: int = 6) -> list[tuple[int, ...]]:
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
					cycle = canonical_cycle_key(path[:])
					cycles.add(cycle)
					continue
				if neighbor in path:
					continue
				if len(path) >= max_size:
					continue
				stack.append((neighbor, path + [neighbor]))
	return sorted(cycles)


#============================================
def empty_haworth_ring_detection() -> dict:
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
def detect_haworth_ring_from_line_cycles(lines: list[dict], labels: list[dict]) -> dict:
	"""Detect Haworth-like base ring cycle from line geometry."""
	line_indexes = list(range(len(lines)))
	if len(line_indexes) < HAWORTH_RING_MIN_PRIMITIVES:
		return empty_haworth_ring_detection()
	nodes, _, adjacency, edge_to_lines = clustered_endpoint_graph(lines, line_indexes, merge_tol=1.5)
	cycles = find_candidate_cycles(adjacency, min_size=5, max_size=6)
	best = None
	for cycle in cycles:
		node_pairs = cycle_node_pairs(cycle)
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
		radius_stats = length_stats(radii)
		if radius_stats["mean"] <= 4.0 or radius_stats["mean"] > HAWORTH_RING_SEARCH_RADIUS:
			continue
		if radius_stats["coefficient_of_variation"] > 0.55:
			continue
		cycle_lengths = [line_length(lines[line_index]) for line_index in cycle_line_indexes]
		cycle_length_stats = length_stats(cycle_lengths)
		if cycle_length_stats["mean"] <= 2.0 or cycle_length_stats["coefficient_of_variation"] > 0.7:
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
			+ cycle_length_stats["coefficient_of_variation"]
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
	return empty_haworth_ring_detection()


#============================================
def detect_haworth_ring_from_primitives(primitives: list[dict], labels: list[dict]) -> dict:
	"""Detect Haworth-like base ring from filled polygon/path primitive clusters."""
	if len(primitives) < HAWORTH_RING_MIN_PRIMITIVES:
		return empty_haworth_ring_detection()
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
		radius_stats = length_stats(radii)
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
	return empty_haworth_ring_detection()


#============================================
def detect_haworth_base_ring(lines: list[dict], labels: list[dict], ring_primitives: list[dict]) -> dict:
	"""Detect Haworth base ring using line-cycle and filled-primitive heuristics."""
	line_detection = detect_haworth_ring_from_line_cycles(lines, labels)
	primitive_detection = detect_haworth_ring_from_primitives(ring_primitives, labels)
	if not line_detection["detected"] and not primitive_detection["detected"]:
		return empty_haworth_ring_detection()
	if line_detection["detected"] and not primitive_detection["detected"]:
		return line_detection
	if primitive_detection["detected"] and not line_detection["detected"]:
		return primitive_detection
	if primitive_detection["score"] <= line_detection["score"]:
		return primitive_detection
	return line_detection
