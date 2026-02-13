"""Tests for measurelib.haworth_ring module."""

# Standard Library
import math
import os
import sys

# Third Party
import pytest

# Local
import conftest
_tools_dir = os.path.join(conftest.repo_root(), "tools")
if _tools_dir not in sys.path:
	sys.path.insert(0, _tools_dir)

from measurelib.haworth_ring import (
	canonical_cycle_key,
	clustered_endpoint_graph,
	cycle_node_pairs,
	detect_haworth_base_ring,
	detect_haworth_ring_from_line_cycles,
	detect_haworth_ring_from_primitives,
	empty_haworth_ring_detection,
	find_candidate_cycles,
)


# -- helpers --

def _hexagon_lines(cx=50.0, cy=50.0, r=20.0):
	"""Return 6 line dicts forming a regular hexagon."""
	vertices = [
		(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
		for a in range(0, 360, 60)
	]
	lines = [
		{
			"x1": vertices[i][0], "y1": vertices[i][1],
			"x2": vertices[(i + 1) % 6][0], "y2": vertices[(i + 1) % 6][1],
			"width": 1.0, "linecap": "round",
		}
		for i in range(6)
	]
	return lines, vertices


def _oxygen_label(cx=50.0, cy=50.0):
	"""Return a label dict with text 'O' near (cx, cy)."""
	return {"text": "O", "x": cx, "y": cy, "font_size": 12.0}


#============================================
def test_canonical_cycle_key_rotation_invariance():
	"""Rotations of the same cycle must produce the same key."""
	key_a = canonical_cycle_key([0, 1, 2, 3, 4])
	key_b = canonical_cycle_key([2, 3, 4, 0, 1])
	assert key_a == key_b


#============================================
def test_canonical_cycle_key_direction_invariance():
	"""Forward and reversed cycles must produce the same key."""
	key_forward = canonical_cycle_key([0, 1, 2, 3, 4])
	key_reverse = canonical_cycle_key([4, 3, 2, 1, 0])
	assert key_forward == key_reverse


#============================================
def test_canonical_cycle_key_distinct_cycles():
	"""Different cycles must produce different keys."""
	key_a = canonical_cycle_key([0, 1, 2, 3, 4])
	key_b = canonical_cycle_key([0, 1, 2, 4, 3])
	assert key_a != key_b


#============================================
def test_cycle_node_pairs_five_nodes():
	"""Five-node cycle returns normalized (min, max) pairs including wrap-around."""
	pairs = cycle_node_pairs((0, 1, 2, 3, 4))
	assert pairs == [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]


#============================================
def test_cycle_node_pairs_three_nodes():
	"""Three-node cycle returns three normalized pairs."""
	pairs = cycle_node_pairs((5, 3, 7))
	assert pairs == [(3, 5), (3, 7), (5, 7)]


#============================================
def test_clustered_endpoint_graph_triangle():
	"""Triangle of 3 lines produces 3 nodes and correct adjacency."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "width": 1.0},
		{"x1": 10.0, "y1": 0.0, "x2": 5.0, "y2": 8.66, "width": 1.0},
		{"x1": 5.0, "y1": 8.66, "x2": 0.0, "y2": 0.0, "width": 1.0},
	]
	nodes, line_to_nodes, adjacency, edge_to_lines = clustered_endpoint_graph(
		lines, list(range(3)), merge_tol=1.5
	)
	assert len(nodes) == 3
	# every node is adjacent to the other two
	for node_index in adjacency:
		assert len(adjacency[node_index]) == 2


#============================================
def test_find_candidate_cycles_pentagon():
	"""A 5-cycle adjacency returns exactly one cycle."""
	adjacency = {
		0: {1, 4},
		1: {0, 2},
		2: {1, 3},
		3: {2, 4},
		4: {3, 0},
	}
	cycles = find_candidate_cycles(adjacency, min_size=5, max_size=6)
	assert len(cycles) == 1
	assert len(cycles[0]) == 5


#============================================
def test_find_candidate_cycles_no_cycle_in_path():
	"""A simple path graph has no cycles."""
	adjacency = {
		0: {1},
		1: {0, 2},
		2: {1, 3},
		3: {2},
	}
	cycles = find_candidate_cycles(adjacency, min_size=5, max_size=6)
	assert cycles == []


#============================================
def test_find_candidate_cycles_hexagon():
	"""A 6-cycle adjacency returns exactly one cycle."""
	adjacency = {
		0: {1, 5},
		1: {0, 2},
		2: {1, 3},
		3: {2, 4},
		4: {3, 5},
		5: {4, 0},
	}
	cycles = find_candidate_cycles(adjacency, min_size=5, max_size=6)
	assert len(cycles) == 1
	assert len(cycles[0]) == 6


#============================================
def test_empty_haworth_ring_detection_keys():
	"""empty_haworth_ring_detection returns dict with all expected keys."""
	result = empty_haworth_ring_detection()
	assert result["detected"] is False
	expected_keys = {
		"detected", "line_indexes", "primitive_indexes",
		"node_count", "centroid", "radius", "score", "source",
	}
	assert set(result.keys()) == expected_keys
	assert result["line_indexes"] == []
	assert result["primitive_indexes"] == []
	assert result["centroid"] is None
	assert result["radius"] == 0.0
	assert result["score"] is None
	assert result["source"] is None


#============================================
def test_detect_haworth_ring_from_line_cycles_hexagon_with_oxygen():
	"""Regular hexagon with O label at center is detected as Haworth ring."""
	lines, vertices = _hexagon_lines()
	labels = [_oxygen_label()]
	result = detect_haworth_ring_from_line_cycles(lines, labels)
	assert result["detected"] is True
	assert result["source"] == "line_cycle"
	assert result["node_count"] in (5, 6)
	assert result["centroid"] is not None
	assert result["radius"] > 0.0
	assert len(result["line_indexes"]) >= 5


#============================================
def test_detect_haworth_ring_from_line_cycles_too_few_lines():
	"""Fewer than HAWORTH_RING_MIN_PRIMITIVES lines -> not detected."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "width": 1.0},
		{"x1": 10.0, "y1": 0.0, "x2": 5.0, "y2": 8.66, "width": 1.0},
	]
	labels = [_oxygen_label()]
	result = detect_haworth_ring_from_line_cycles(lines, labels)
	assert result["detected"] is False


#============================================
def test_detect_haworth_ring_from_primitives_hexagon():
	"""Six primitives arranged in a circle with O label are detected."""
	cx, cy, r = 50.0, 50.0, 15.0
	primitives = [
		{"centroid": (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))}
		for a in range(0, 360, 60)
	]
	labels = [_oxygen_label(cx, cy)]
	result = detect_haworth_ring_from_primitives(primitives, labels)
	assert result["detected"] is True
	assert result["source"] == "filled_primitive_cluster"
	assert result["centroid"] is not None
	assert result["radius"] == pytest.approx(r, abs=1.0)


#============================================
def test_detect_haworth_ring_from_primitives_too_few():
	"""Fewer than HAWORTH_RING_MIN_PRIMITIVES primitives -> not detected."""
	primitives = [
		{"centroid": (10.0, 10.0)},
		{"centroid": (20.0, 10.0)},
	]
	labels = [_oxygen_label()]
	result = detect_haworth_ring_from_primitives(primitives, labels)
	assert result["detected"] is False


#============================================
def test_detect_haworth_base_ring_both_not_detected():
	"""When neither heuristic detects a ring, result is empty detection."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.0, "width": 1.0},
	]
	labels = []
	primitives = []
	result = detect_haworth_base_ring(lines, labels, primitives)
	assert result["detected"] is False


#============================================
def test_detect_haworth_base_ring_line_only():
	"""When only line-cycle detects, that result is returned."""
	lines, _ = _hexagon_lines()
	labels = [_oxygen_label()]
	primitives = []
	result = detect_haworth_base_ring(lines, labels, primitives)
	assert result["detected"] is True
	assert result["source"] == "line_cycle"


#============================================
def test_detect_haworth_base_ring_primitive_only():
	"""When only primitive detects, that result is returned."""
	lines = [
		{"x1": 0.0, "y1": 0.0, "x2": 2.0, "y2": 0.0, "width": 1.0},
	]
	cx, cy, r = 50.0, 50.0, 15.0
	primitives = [
		{"centroid": (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))}
		for a in range(0, 360, 60)
	]
	labels = [_oxygen_label(cx, cy)]
	result = detect_haworth_base_ring(lines, labels, primitives)
	assert result["detected"] is True
	assert result["source"] == "filled_primitive_cluster"
