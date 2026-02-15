"""Standalone PDF alignment analysis using the same pipeline as SVG analysis."""

# Standard Library
import pathlib

from measurelib.pdf_parse import (
	collect_pdf_labels,
	collect_pdf_lines,
	collect_pdf_ring_primitives,
	collect_pdf_wedge_bonds,
	open_pdf_page,
)
from measurelib.glyph_model import (
	label_svg_estimated_box,
	label_svg_estimated_primitives,
	label_text_path,
)
from measurelib.haworth_ring import detect_haworth_base_ring
from measurelib.hatch_detect import (
	detect_double_bond_pairs,
	detect_hashed_carrier_map,
	overlap_origin,
	quadrant_label,
	ring_region_label,
)
from measurelib.violations import (
	count_bond_bond_overlaps,
	count_bond_glyph_overlaps,
	count_glyph_glyph_overlaps,
	count_hatched_thin_conflicts,
	count_lattice_angle_violations,
)
from measurelib.constants import (
	BOND_GLYPH_GAP_TOLERANCE,
	CANONICAL_LATTICE_ANGLES,
	LATTICE_ANGLE_TOLERANCE_DEGREES,
)
from measurelib.util import (
	group_length_append,
	length_stats,
	line_length,
	line_midpoint,
)


#============================================
def analyze_pdf_file(
		pdf_path: pathlib.Path,
		exclude_haworth_base_ring: bool = True,
		bond_glyph_gap_tolerance: float = BOND_GLYPH_GAP_TOLERANCE) -> dict:
	"""Analyze one PDF file and return geometry and alignment metrics.

	Opens the PDF, extracts primitives via pdf_parse, enriches labels
	with glyph geometry, and runs the same structural checks as
	analysis.analyze_svg_file.

	Args:
		pdf_path: path to the PDF file.
		exclude_haworth_base_ring: whether to exclude Haworth ring lines.
		bond_glyph_gap_tolerance: gap tolerance for bond/glyph overlap checks.

	Returns:
		dict with the same top-level keys as analyze_svg_file, with
		'pdf' key instead of 'svg'.
	"""
	page, pdf_obj = open_pdf_page(str(pdf_path))
	lines = collect_pdf_lines(page)
	labels = collect_pdf_labels(page)
	ring_primitives = collect_pdf_ring_primitives(page)
	wedge_bonds = collect_pdf_wedge_bonds(page)
	pdf_obj.close()
	# enrich labels with glyph geometry (same as analysis.py lines 79-83)
	for label in labels:
		label["svg_text_path"] = label_text_path(label)
		label["svg_estimated_primitives"] = label_svg_estimated_primitives(label)
		label["svg_estimated_box"] = label_svg_estimated_box(label)
		label["_source_svg_path"] = str(pdf_path)
	measurement_label_indexes = [
		index for index, label in enumerate(labels) if label["is_measurement_label"]
	]
	# haworth ring detection
	haworth_base_ring = detect_haworth_base_ring(lines, labels, ring_primitives)
	excluded_line_indexes = set()
	if exclude_haworth_base_ring and haworth_base_ring["detected"]:
		excluded_line_indexes = set(haworth_base_ring["line_indexes"])
	checked_line_indexes = [
		index for index in range(len(lines)) if index not in excluded_line_indexes
	]
	# hatch and double bond detection
	pre_hashed_carrier_map = detect_hashed_carrier_map(lines, checked_line_indexes)
	pre_decorative_hatched_stroke_index_set = {
		stroke_index
		for stroke_indexes in pre_hashed_carrier_map.values()
		for stroke_index in stroke_indexes
	}
	pre_hashed_carrier_index_set = set(pre_hashed_carrier_map.keys())
	double_bond_pairs = detect_double_bond_pairs(
		lines, checked_line_indexes,
		excluded_indexes=pre_decorative_hatched_stroke_index_set | pre_hashed_carrier_index_set,
	)
	double_bond_secondary_indexes = set()
	for _primary_idx, secondary_idx in double_bond_pairs:
		double_bond_secondary_indexes.add(secondary_idx)
	# line lengths and bond classification
	line_lengths_all = [line_length(line) for line in lines]
	checked_label_indexes = list(range(len(labels)))
	# violations
	lattice_angle_violation_count, lattice_angle_violations = count_lattice_angle_violations(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	glyph_glyph_overlap_count, glyph_glyph_overlaps = count_glyph_glyph_overlaps(
		labels=labels,
		checked_label_indexes=checked_label_indexes,
	)
	bond_bond_overlap_count, bond_bond_overlaps = count_bond_bond_overlaps(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	hatched_thin_conflict_count, hatched_thin_conflicts, hashed_carrier_map = count_hatched_thin_conflicts(
		lines=lines,
		checked_line_indexes=checked_line_indexes,
		haworth_base_ring=haworth_base_ring,
	)
	decorative_hatched_stroke_indexes = sorted(
		{
			stroke_index
			for stroke_indexes in hashed_carrier_map.values()
			for stroke_index in stroke_indexes
		}
	)
	decorative_hatched_stroke_index_set = set(decorative_hatched_stroke_indexes)
	checked_bond_line_indexes = [
		index for index in checked_line_indexes
		if index not in decorative_hatched_stroke_index_set
		and index not in double_bond_secondary_indexes
	]
	# bond/glyph overlaps
	bond_glyph_overlap_count, bond_glyph_overlaps = count_bond_glyph_overlaps(
		lines=lines,
		labels=labels,
		checked_line_indexes=checked_line_indexes,
		checked_label_indexes=checked_label_indexes,
		aligned_connector_pairs=set(),
		haworth_base_ring=haworth_base_ring,
		gap_tolerance=float(bond_glyph_gap_tolerance),
		wedge_bonds=wedge_bonds,
	)
	# bond length statistics
	location_origin = overlap_origin(lines, haworth_base_ring)
	checked_bond_lengths_by_quadrant: dict[str, list[float]] = {}
	checked_bond_lengths_by_ring_region: dict[str, list[float]] = {}
	checked_bond_lengths_by_quadrant_ring_region: dict[str, list[float]] = {}
	for line_index in checked_bond_line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		length = line_lengths_all[line_index]
		midpoint = line_midpoint(line)
		quadrant = quadrant_label(midpoint, origin=location_origin)
		ring_region_val = ring_region_label(midpoint, haworth_base_ring=haworth_base_ring)
		group_length_append(checked_bond_lengths_by_quadrant, quadrant, length)
		group_length_append(checked_bond_lengths_by_ring_region, ring_region_val, length)
		group_length_append(
			checked_bond_lengths_by_quadrant_ring_region,
			f"{quadrant} | {ring_region_val}",
			length,
		)
	line_lengths_checked = [
		line_lengths_all[index]
		for index in checked_bond_line_indexes
		if 0 <= index < len(line_lengths_all)
	]
	excluded_line_lengths = [
		line_lengths_all[index]
		for index in sorted(excluded_line_indexes)
		if 0 <= index < len(line_lengths_all)
	]
	return {
		"pdf": str(pdf_path),
		"text_labels_total": len(labels),
		"text_label_values": [str(label.get("text", "")) for label in labels],
		"labels_analyzed": len(measurement_label_indexes),
		"aligned_count": 0,
		"missed_count": 0,
		"no_connector_count": 0,
		"alignment_outside_tolerance_count": 0,
		"labels": [],
		"lattice_angle_violation_count": lattice_angle_violation_count,
		"glyph_glyph_overlap_count": glyph_glyph_overlap_count,
		"bond_bond_overlap_count": bond_bond_overlap_count,
		"hatched_thin_conflict_count": hatched_thin_conflict_count,
		"bond_glyph_overlap_count": bond_glyph_overlap_count,
		"wedge_bond_count": len(wedge_bonds),
		"geometry_checks": {
			"canonical_angles_degrees": list(CANONICAL_LATTICE_ANGLES),
			"angle_tolerance_degrees": LATTICE_ANGLE_TOLERANCE_DEGREES,
			"bond_glyph_gap_tolerance": float(bond_glyph_gap_tolerance),
			"lattice_angle_violations": lattice_angle_violations,
			"glyph_glyph_overlaps": glyph_glyph_overlaps,
			"bond_bond_overlaps": bond_bond_overlaps,
			"hatched_thin_conflicts": hatched_thin_conflicts,
			"hashed_carrier_map": {
				str(line_index): stroke_indexes
				for line_index, stroke_indexes in sorted(hashed_carrier_map.items())
			},
			"bond_glyph_overlaps": bond_glyph_overlaps,
		},
		"haworth_base_ring": {
			"detected": bool(haworth_base_ring["detected"]),
			"excluded": bool(exclude_haworth_base_ring and haworth_base_ring["detected"]),
			"line_indexes": sorted(set(haworth_base_ring["line_indexes"])),
			"line_count": len(set(haworth_base_ring["line_indexes"])),
			"primitive_indexes": sorted(set(haworth_base_ring.get("primitive_indexes", []))),
			"primitive_count": len(set(haworth_base_ring.get("primitive_indexes", []))),
			"node_count": int(haworth_base_ring["node_count"]),
			"centroid": haworth_base_ring["centroid"],
			"radius": float(haworth_base_ring["radius"]),
			"source": haworth_base_ring.get("source"),
		},
		"checked_line_indexes": checked_line_indexes,
		"checked_bond_line_indexes": checked_bond_line_indexes,
		"excluded_line_indexes": sorted(excluded_line_indexes),
		"decorative_hatched_stroke_indexes": decorative_hatched_stroke_indexes,
		"decorative_hatched_stroke_count": len(decorative_hatched_stroke_indexes),
		"decorative_double_bond_offset_indexes": sorted(double_bond_secondary_indexes),
		"decorative_double_bond_offset_count": len(double_bond_secondary_indexes),
		"double_bond_pairs": [
			{"primary": p, "secondary": s} for p, s in double_bond_pairs
		],
		"line_lengths": {
			"all_lines": line_lengths_all,
			"checked_lines": line_lengths_checked,
			"connector_lines": [],
			"non_connector_lines": line_lengths_checked,
			"excluded_haworth_base_ring_lines": excluded_line_lengths,
		},
		"line_length_stats": {
			"all_lines": length_stats(line_lengths_all),
			"checked_lines": length_stats(line_lengths_checked),
		},
	}
