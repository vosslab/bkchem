"""Cross-renderer parity comparison for SVG and PDF primitive sets."""

# Standard Library
import math

from measurelib.util import length_stats, point_distance_sq


#============================================
def _line_midpoint(line: dict) -> tuple[float, float]:
	"""Return midpoint of one line dict."""
	return (
		(line["x1"] + line["x2"]) * 0.5,
		(line["y1"] + line["y2"]) * 0.5,
	)


#============================================
def _line_length(line: dict) -> float:
	"""Return Euclidean length for one line dict."""
	return math.hypot(line["x2"] - line["x1"], line["y2"] - line["y1"])


#============================================
def match_lines(
		svg_lines: list[dict],
		pdf_lines: list[dict],
		tolerance: float = 2.0) -> list[dict]:
	"""Match SVG and PDF line primitives by midpoint proximity.

	Uses nearest-neighbor matching by midpoint position.
	Each SVG line is matched to the closest unmatched PDF line.

	Args:
		svg_lines: lines extracted from SVG.
		pdf_lines: lines extracted from PDF.
		tolerance: max midpoint distance for a valid match.

	Returns:
		list of match dicts with keys: svg_index, pdf_index,
		midpoint_delta, length_delta, width_delta, matched.
	"""
	results = []
	used_pdf_indexes = set()
	# precompute PDF midpoints
	pdf_midpoints = [_line_midpoint(line) for line in pdf_lines]
	for svg_idx, svg_line in enumerate(svg_lines):
		svg_mid = _line_midpoint(svg_line)
		svg_len = _line_length(svg_line)
		best_pdf_idx = None
		best_dist = float("inf")
		# find nearest unmatched PDF line
		for pdf_idx, pdf_mid in enumerate(pdf_midpoints):
			if pdf_idx in used_pdf_indexes:
				continue
			dist = math.sqrt(point_distance_sq(svg_mid, pdf_mid))
			if dist < best_dist:
				best_dist = dist
				best_pdf_idx = pdf_idx
		if best_pdf_idx is not None and best_dist <= tolerance:
			used_pdf_indexes.add(best_pdf_idx)
			pdf_line = pdf_lines[best_pdf_idx]
			pdf_len = _line_length(pdf_line)
			results.append({
				"svg_index": svg_idx,
				"pdf_index": best_pdf_idx,
				"midpoint_delta": best_dist,
				"length_delta": abs(svg_len - pdf_len),
				"width_delta": abs(float(svg_line.get("width", 1.0)) - float(pdf_line.get("width", 1.0))),
				"matched": True,
			})
		else:
			results.append({
				"svg_index": svg_idx,
				"pdf_index": None,
				"midpoint_delta": best_dist if best_pdf_idx is not None else None,
				"length_delta": None,
				"width_delta": None,
				"matched": False,
			})
	# add unmatched PDF lines
	for pdf_idx in range(len(pdf_lines)):
		if pdf_idx not in used_pdf_indexes:
			results.append({
				"svg_index": None,
				"pdf_index": pdf_idx,
				"midpoint_delta": None,
				"length_delta": None,
				"width_delta": None,
				"matched": False,
			})
	return results


#============================================
def match_labels(
		svg_labels: list[dict],
		pdf_labels: list[dict],
		tolerance: float = 5.0) -> list[dict]:
	"""Match SVG and PDF text labels by content then position proximity.

	First matches by canonical text content, then refines by position
	for labels with identical text.

	Args:
		svg_labels: labels extracted from SVG.
		pdf_labels: labels extracted from PDF.
		tolerance: max position distance for a valid match.

	Returns:
		list of match dicts with keys: text, svg_index, pdf_index,
		x_delta, y_delta, font_size_delta, matched.
	"""
	results = []
	used_pdf_indexes = set()
	# build text-to-index map for PDF labels
	pdf_text_map: dict[str, list[int]] = {}
	for idx, label in enumerate(pdf_labels):
		text_key = str(label.get("canonical_text", label.get("text", "")))
		if text_key not in pdf_text_map:
			pdf_text_map[text_key] = []
		pdf_text_map[text_key].append(idx)
	for svg_idx, svg_label in enumerate(svg_labels):
		svg_text = str(svg_label.get("canonical_text", svg_label.get("text", "")))
		svg_x = float(svg_label.get("x", 0.0))
		svg_y = float(svg_label.get("y", 0.0))
		svg_fs = float(svg_label.get("font_size", 12.0))
		# look for matching text in PDF
		candidates = pdf_text_map.get(svg_text, [])
		best_pdf_idx = None
		best_dist = float("inf")
		for pdf_idx in candidates:
			if pdf_idx in used_pdf_indexes:
				continue
			pdf_label = pdf_labels[pdf_idx]
			pdf_x = float(pdf_label.get("x", 0.0))
			pdf_y = float(pdf_label.get("y", 0.0))
			dist = math.hypot(svg_x - pdf_x, svg_y - pdf_y)
			if dist < best_dist:
				best_dist = dist
				best_pdf_idx = pdf_idx
		if best_pdf_idx is not None and best_dist <= tolerance:
			used_pdf_indexes.add(best_pdf_idx)
			pdf_label = pdf_labels[best_pdf_idx]
			pdf_x = float(pdf_label.get("x", 0.0))
			pdf_y = float(pdf_label.get("y", 0.0))
			pdf_fs = float(pdf_label.get("font_size", 12.0))
			results.append({
				"text": svg_text,
				"svg_index": svg_idx,
				"pdf_index": best_pdf_idx,
				"x_delta": abs(svg_x - pdf_x),
				"y_delta": abs(svg_y - pdf_y),
				"font_size_delta": abs(svg_fs - pdf_fs),
				"matched": True,
			})
		else:
			results.append({
				"text": svg_text,
				"svg_index": svg_idx,
				"pdf_index": None,
				"x_delta": None,
				"y_delta": None,
				"font_size_delta": None,
				"matched": False,
			})
	# add unmatched PDF labels
	for pdf_idx in range(len(pdf_labels)):
		if pdf_idx not in used_pdf_indexes:
			pdf_label = pdf_labels[pdf_idx]
			pdf_text = str(pdf_label.get("canonical_text", pdf_label.get("text", "")))
			results.append({
				"text": pdf_text,
				"svg_index": None,
				"pdf_index": pdf_idx,
				"x_delta": None,
				"y_delta": None,
				"font_size_delta": None,
				"matched": False,
			})
	return results


#============================================
def match_ring_primitives(
		svg_rings: list[dict],
		pdf_rings: list[dict],
		tolerance: float = 5.0) -> list[dict]:
	"""Match SVG and PDF ring primitives by centroid proximity.

	Args:
		svg_rings: ring primitives from SVG.
		pdf_rings: ring primitives from PDF.
		tolerance: max centroid distance for a valid match.

	Returns:
		list of match dicts with keys: svg_index, pdf_index,
		centroid_delta, matched.
	"""
	results = []
	used_pdf_indexes = set()
	for svg_idx, svg_ring in enumerate(svg_rings):
		svg_centroid = svg_ring.get("centroid", (0.0, 0.0))
		best_pdf_idx = None
		best_dist = float("inf")
		for pdf_idx, pdf_ring in enumerate(pdf_rings):
			if pdf_idx in used_pdf_indexes:
				continue
			pdf_centroid = pdf_ring.get("centroid", (0.0, 0.0))
			dist = math.sqrt(point_distance_sq(svg_centroid, pdf_centroid))
			if dist < best_dist:
				best_dist = dist
				best_pdf_idx = pdf_idx
		if best_pdf_idx is not None and best_dist <= tolerance:
			used_pdf_indexes.add(best_pdf_idx)
			results.append({
				"svg_index": svg_idx,
				"pdf_index": best_pdf_idx,
				"centroid_delta": best_dist,
				"matched": True,
			})
		else:
			results.append({
				"svg_index": svg_idx,
				"pdf_index": None,
				"centroid_delta": best_dist if best_pdf_idx is not None else None,
				"matched": False,
			})
	# add unmatched PDF rings
	for pdf_idx in range(len(pdf_rings)):
		if pdf_idx not in used_pdf_indexes:
			results.append({
				"svg_index": None,
				"pdf_index": pdf_idx,
				"centroid_delta": None,
				"matched": False,
			})
	return results


#============================================
def match_wedge_bonds(
		svg_wedges: list[dict],
		pdf_wedges: list[dict],
		tolerance: float = 5.0) -> list[dict]:
	"""Match SVG and PDF wedge bonds by spine midpoint proximity.

	Args:
		svg_wedges: wedge bonds from SVG.
		pdf_wedges: wedge bonds from PDF.
		tolerance: max spine midpoint distance for a valid match.

	Returns:
		list of match dicts with keys: svg_index, pdf_index,
		spine_midpoint_delta, matched.
	"""
	results = []
	used_pdf_indexes = set()
	# helper to compute spine midpoint
	def _spine_mid(wedge: dict) -> tuple[float, float]:
		s = wedge.get("spine_start", (0.0, 0.0))
		e = wedge.get("spine_end", (0.0, 0.0))
		return ((s[0] + e[0]) * 0.5, (s[1] + e[1]) * 0.5)
	for svg_idx, svg_wedge in enumerate(svg_wedges):
		svg_mid = _spine_mid(svg_wedge)
		best_pdf_idx = None
		best_dist = float("inf")
		for pdf_idx, pdf_wedge in enumerate(pdf_wedges):
			if pdf_idx in used_pdf_indexes:
				continue
			pdf_mid = _spine_mid(pdf_wedge)
			dist = math.sqrt(point_distance_sq(svg_mid, pdf_mid))
			if dist < best_dist:
				best_dist = dist
				best_pdf_idx = pdf_idx
		if best_pdf_idx is not None and best_dist <= tolerance:
			used_pdf_indexes.add(best_pdf_idx)
			results.append({
				"svg_index": svg_idx,
				"pdf_index": best_pdf_idx,
				"spine_midpoint_delta": best_dist,
				"matched": True,
			})
		else:
			results.append({
				"svg_index": svg_idx,
				"pdf_index": None,
				"spine_midpoint_delta": best_dist if best_pdf_idx is not None else None,
				"matched": False,
			})
	# add unmatched PDF wedges
	for pdf_idx in range(len(pdf_wedges)):
		if pdf_idx not in used_pdf_indexes:
			results.append({
				"svg_index": None,
				"pdf_index": pdf_idx,
				"spine_midpoint_delta": None,
				"matched": False,
			})
	return results


#============================================
def parity_summary(
		line_matches: list[dict],
		label_matches: list[dict],
		ring_matches: list[dict],
		wedge_matches: list[dict]) -> dict:
	"""Compute aggregate parity statistics from match results.

	Args:
		line_matches: results from match_lines().
		label_matches: results from match_labels().
		ring_matches: results from match_ring_primitives().
		wedge_matches: results from match_wedge_bonds().

	Returns:
		dict with summary statistics: total_matched, total_unmatched,
		max/mean/median deltas, overall parity_score.
	"""
	# count matches per category
	line_matched = sum(1 for m in line_matches if m["matched"])
	label_matched = sum(1 for m in label_matches if m["matched"])
	ring_matched = sum(1 for m in ring_matches if m["matched"])
	wedge_matched = sum(1 for m in wedge_matches if m["matched"])
	line_unmatched = len(line_matches) - line_matched
	label_unmatched = len(label_matches) - label_matched
	ring_unmatched = len(ring_matches) - ring_matched
	wedge_unmatched = len(wedge_matches) - wedge_matched
	total_matched = line_matched + label_matched + ring_matched + wedge_matched
	total_unmatched = line_unmatched + label_unmatched + ring_unmatched + wedge_unmatched
	total_primitives = total_matched + total_unmatched
	# collect delta values for matched lines
	line_midpoint_deltas = [
		float(m["midpoint_delta"]) for m in line_matches
		if m["matched"] and m["midpoint_delta"] is not None
	]
	line_length_deltas = [
		float(m["length_delta"]) for m in line_matches
		if m["matched"] and m["length_delta"] is not None
	]
	# collect delta values for matched labels
	label_x_deltas = [
		float(m["x_delta"]) for m in label_matches
		if m["matched"] and m["x_delta"] is not None
	]
	label_y_deltas = [
		float(m["y_delta"]) for m in label_matches
		if m["matched"] and m["y_delta"] is not None
	]
	# parity score: fraction of total primitives that are matched
	parity_score = 0.0
	if total_primitives > 0:
		parity_score = total_matched / float(total_primitives)
	return {
		"total_matched": total_matched,
		"total_unmatched": total_unmatched,
		"total_primitives": total_primitives,
		"parity_score": parity_score,
		"lines": {
			"matched": line_matched,
			"unmatched": line_unmatched,
			"midpoint_delta_stats": length_stats(line_midpoint_deltas),
			"length_delta_stats": length_stats(line_length_deltas),
		},
		"labels": {
			"matched": label_matched,
			"unmatched": label_unmatched,
			"x_delta_stats": length_stats(label_x_deltas),
			"y_delta_stats": length_stats(label_y_deltas),
		},
		"rings": {
			"matched": ring_matched,
			"unmatched": ring_unmatched,
		},
		"wedges": {
			"matched": wedge_matched,
			"unmatched": wedge_unmatched,
		},
	}
