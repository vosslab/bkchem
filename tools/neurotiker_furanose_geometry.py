#!/usr/bin/env python3
"""Estimate furanose ring template coordinates from NEUROtiker archive SVGs."""

# Standard Library
import math
import pathlib
import re
import subprocess

# Third Party
import defusedxml.ElementTree as ET


#============================================
def get_repo_root() -> pathlib.Path:
	"""Return repo root path from git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		check=False,
		capture_output=True,
		text=True,
	)
	if result.returncode != 0:
		raise RuntimeError("Could not resolve repo root from git")
	return pathlib.Path(result.stdout.strip())


#============================================
def parse_path_points(path_d: str) -> list[tuple[float, float]]:
	"""Parse numeric XY pairs from simple SVG path strings."""
	numbers = [float(item) for item in re.findall(r"-?\d+(?:\.\d+)?", path_d or "")]
	points = []
	for index in range(0, len(numbers) - 1, 2):
		points.append((numbers[index], numbers[index + 1]))
	return points


#============================================
def dedupe_closed_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
	"""Drop duplicated closing coordinate from path point lists."""
	if len(points) >= 2 and points[0] == points[-1]:
		return points[:-1]
	return points


#============================================
def cluster_points(points: list[tuple[float, float]], threshold: float = 10.0) -> list[tuple[float, float]]:
	"""Cluster nearby points and return cluster centers."""
	clusters: list[list[tuple[float, float]]] = []
	for point in points:
		assigned = False
		for cluster in clusters:
			center_x = sum(item[0] for item in cluster) / len(cluster)
			center_y = sum(item[1] for item in cluster) / len(cluster)
			if math.hypot(point[0] - center_x, point[1] - center_y) <= threshold:
				cluster.append(point)
				assigned = True
				break
		if not assigned:
			clusters.append([point])
	centers = []
	for cluster in clusters:
		center_x = sum(item[0] for item in cluster) / len(cluster)
		center_y = sum(item[1] for item in cluster) / len(cluster)
		centers.append((center_x, center_y))
	return centers


#============================================
def point_counts(path_points_by_id: dict[str, list[tuple[float, float]]]) -> dict[tuple[float, float], int]:
	"""Count in how many path IDs each coordinate appears."""
	counts: dict[tuple[float, float], int] = {}
	for points in path_points_by_id.values():
		for point in set(points):
			counts[point] = counts.get(point, 0) + 1
	return counts


#============================================
def average_points(points: list[tuple[float, float]]) -> tuple[float, float]:
	"""Return arithmetic mean of XY points."""
	if not points:
		raise ValueError("Cannot average empty point list")
	x_value = sum(point[0] for point in points) / len(points)
	y_value = sum(point[1] for point in points) / len(points)
	return (x_value, y_value)


#============================================
def top_endpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
	"""Estimate the top endpoint of one top-edge polygon (polygon9 or polygon15)."""
	if len(points) < 2:
		raise ValueError("Need at least two points for top endpoint")
	top_two = sorted(points, key=lambda item: (item[1], item[0]))[:2]
	return average_points(top_two)


#============================================
def order_furanose_vertices(vertices: list[tuple[float, float]]) -> dict[str, tuple[float, float]]:
	"""Map clustered ring vertices to ML/BL/BR/MR/TO labels."""
	if len(vertices) != 5:
		raise ValueError(f"Expected 5 ring vertices, got {len(vertices)}")
	to_vertex = min(vertices, key=lambda point: point[1])
	remaining = [point for point in vertices if point != to_vertex]
	left = sorted([point for point in remaining if point[0] < to_vertex[0]], key=lambda point: point[1])
	right = sorted([point for point in remaining if point[0] >= to_vertex[0]], key=lambda point: point[1])
	if len(left) != 2 or len(right) != 2:
		raise ValueError("Could not split vertices into left/right pairs")
	return {
		"ML": left[0],
		"BL": left[1],
		"BR": right[1],
		"MR": right[0],
		"TO": to_vertex,
	}


#============================================
def normalize_vertices(vertices_by_slot: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
	"""Center and scale ring vertices by average edge length."""
	slot_order = ["ML", "BL", "BR", "MR", "TO"]
	coords = [vertices_by_slot[slot] for slot in slot_order]
	center_x = sum(point[0] for point in coords) / len(coords)
	center_y = sum(point[1] for point in coords) / len(coords)
	centered = [(point[0] - center_x, point[1] - center_y) for point in coords]
	edge_lengths = []
	for index in range(len(centered)):
		x1, y1 = centered[index]
		x2, y2 = centered[(index + 1) % len(centered)]
		edge_lengths.append(math.hypot(x2 - x1, y2 - y1))
	scale = sum(edge_lengths) / len(edge_lengths)
	return {
		slot: (centered[index][0] / scale, centered[index][1] / scale)
		for index, slot in enumerate(slot_order)
	}


#============================================
def extract_ring_vertices(svg_path: pathlib.Path) -> dict[str, tuple[float, float]]:
	"""Extract approximate furanose ring vertices from one reference SVG file."""
	root = ET.parse(svg_path).getroot()
	path_points_by_id = {}
	for element in root.iter():
		tag = element.tag.split("}", 1)[-1]
		if tag != "path":
			continue
		path_id = element.attrib.get("id", "")
		if not path_id.startswith("polygon"):
			continue
		path_points_by_id[path_id] = dedupe_closed_points(
			parse_path_points(element.attrib.get("d", ""))
		)

	required_ids = ["polygon3", "polygon5", "polygon7", "polygon9", "polygon15"]
	missing = [path_id for path_id in required_ids if path_id not in path_points_by_id]
	if missing:
		raise ValueError(f"{svg_path.name}: missing {','.join(missing)}")

	required_points = {path_id: path_points_by_id[path_id] for path_id in required_ids}
	counts = point_counts(required_points)
	shared_points = []
	for path_id in required_ids:
		for point in required_points[path_id]:
			if counts.get(point, 0) >= 2:
				shared_points.append(point)

	clustered_side_vertices = cluster_points(shared_points, threshold=4.0)
	if len(clustered_side_vertices) != 4:
		raise ValueError(
			f"{svg_path.name}: expected 4 side-vertex clusters, got {len(clustered_side_vertices)}"
		)

	top_left = top_endpoint(required_points["polygon9"])
	top_right = top_endpoint(required_points["polygon15"])
	top_vertex = (
		(top_left[0] + top_right[0]) / 2.0,
		(top_left[1] + top_right[1]) / 2.0,
	)

	vertices = list(clustered_side_vertices)
	vertices.append(top_vertex)
	ordered = order_furanose_vertices(vertices)
	return normalize_vertices(ordered)


#============================================
def mean_template(slot_maps: list[dict[str, tuple[float, float]]]) -> dict[str, tuple[float, float]]:
	"""Average normalized vertices across files."""
	slots = ["ML", "BL", "BR", "MR", "TO"]
	result = {}
	for slot in slots:
		x_value = sum(item[slot][0] for item in slot_maps) / len(slot_maps)
		y_value = sum(item[slot][1] for item in slot_maps) / len(slot_maps)
		result[slot] = (x_value, y_value)
	return result


#============================================
def edge_lengths(slot_map: dict[str, tuple[float, float]]) -> dict[str, float]:
	"""Return normalized edge lengths for one ordered slot map."""
	slot_order = ["ML", "BL", "BR", "MR", "TO"]
	lengths = {}
	for index, slot in enumerate(slot_order):
		next_slot = slot_order[(index + 1) % len(slot_order)]
		x1, y1 = slot_map[slot]
		x2, y2 = slot_map[next_slot]
		lengths[f"{slot}-{next_slot}"] = math.hypot(x2 - x1, y2 - y1)
	return lengths


#============================================
def vertex_angles(slot_map: dict[str, tuple[float, float]]) -> dict[str, float]:
	"""Return internal ring angles in degrees for each vertex slot."""
	slot_order = ["ML", "BL", "BR", "MR", "TO"]
	angles = {}
	for index, slot in enumerate(slot_order):
		prev_slot = slot_order[(index - 1) % len(slot_order)]
		next_slot = slot_order[(index + 1) % len(slot_order)]
		px, py = slot_map[prev_slot]
		vx, vy = slot_map[slot]
		nx, ny = slot_map[next_slot]
		ax = px - vx
		ay = py - vy
		bx = nx - vx
		by = ny - vy
		a_len = math.hypot(ax, ay)
		b_len = math.hypot(bx, by)
		if a_len == 0.0 or b_len == 0.0:
			angles[slot] = 0.0
			continue
		dot = (ax * bx) + (ay * by)
		cos_theta = max(-1.0, min(1.0, dot / (a_len * b_len)))
		angles[slot] = math.degrees(math.acos(cos_theta))
	return angles


#============================================
def mean_values(records: list[dict[str, float]]) -> dict[str, float]:
	"""Average values from dict records with matching keys."""
	if not records:
		raise ValueError("Cannot average empty records")
	keys = sorted(records[0].keys())
	result = {}
	for key in keys:
		result[key] = sum(record[key] for record in records) / len(records)
	return result


#============================================
def main() -> None:
	"""Compute and print a suggested furanose template from references."""
	repo_root = get_repo_root()
	archive_dir = repo_root / "neurotiker_haworth_archive"
	furanose_files = sorted(archive_dir.glob("*furanose.svg"))
	if not furanose_files:
		raise FileNotFoundError("No furanose SVG files found in neurotiker_haworth_archive")

	slot_maps = []
	processed = 0
	for svg_path in furanose_files:
		try:
			slot_maps.append(extract_ring_vertices(svg_path))
			processed += 1
		except Exception as error:
			print(f"SKIP {svg_path.name}: {error}")

	if not slot_maps:
		raise RuntimeError("No furanose files parsed successfully")

	mean_slots = mean_template(slot_maps)
	mean_edges = mean_values([edge_lengths(item) for item in slot_maps])
	mean_angles = mean_values([vertex_angles(item) for item in slot_maps])

	print(f"Processed furanose references: {processed}")
	print("Mean normalized slot coordinates:")
	for slot in ("ML", "BL", "BR", "MR", "TO"):
		x_value, y_value = mean_slots[slot]
		print(f"  {slot}: ({x_value:.4f}, {y_value:.4f})")

	print("\nMean normalized edge lengths:")
	for edge in ("ML-BL", "BL-BR", "BR-MR", "MR-TO", "TO-ML"):
		print(f"  {edge}: {mean_edges[edge]:.4f}")

	print("\nMean internal angles (degrees):")
	for slot in ("ML", "BL", "BR", "MR", "TO"):
		print(f"  {slot}: {mean_angles[slot]:.2f}")

	print("\nSuggested FURANOSE_TEMPLATE order [ML, BL, BR, MR, TO]:")
	print("[")
	for slot in ("ML", "BL", "BR", "MR", "TO"):
		x_value, y_value = mean_slots[slot]
		print(f"\t({x_value:.4f}, {y_value:.4f}),")
	print("]")


#============================================
if __name__ == "__main__":
	main()
