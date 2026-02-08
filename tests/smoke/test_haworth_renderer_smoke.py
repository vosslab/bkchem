"""Smoke tests for Haworth renderer ops and SVG serialization."""

# Standard Library
import math
import sys
from xml.dom import minidom as xml_minidom

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()
sys.path.insert(0, conftest.tests_path("fixtures"))

import oasa.dom_extensions as dom_extensions
import oasa.haworth_renderer as haworth_renderer
import oasa.haworth_spec as haworth_spec
import oasa.render_ops as render_ops
import oasa.sugar_code as sugar_code
import oasa.svg_out as svg_out
from neurotiker_archive_mapping import all_mappable_entries


#============================================
def _build_ops(code: str, ring_type: str, anomeric: str, **render_kwargs) -> list:
	parsed = sugar_code.parse(code)
	spec = haworth_spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)
	return haworth_renderer.render(spec, **render_kwargs)


#============================================
def _ops_to_svg_text(ops: list, width: int = 220, height: int = 220) -> str:
	try:
		impl = xml_minidom.getDOMImplementation()
		doc = impl.createDocument(None, None, None)
	except Exception:
		doc = xml_minidom.Document()
	svg = dom_extensions.elementUnder(
		doc,
		"svg",
		attributes=(
			("xmlns", "http://www.w3.org/2000/svg"),
			("version", "1.1"),
			("width", str(width)),
			("height", str(height)),
			("viewBox", f"0 0 {width} {height}"),
		),
	)
	render_ops.ops_to_svg(svg, ops)
	return svg_out.pretty_print_svg(doc.toxml("utf-8"))


#============================================
def _assert_ops_well_formed(ops: list, context: str) -> None:
	"""Validate basic render-op invariants for stability."""
	op_ids = [op.op_id for op in ops if getattr(op, "op_id", None)]
	assert len(op_ids) == len(set(op_ids)), f"Duplicate op_id values in {context}"
	for op in ops:
		if isinstance(op, render_ops.TextOp):
			assert op.text, f"Empty text op in {context}"
			assert op.font_size > 0.0, f"Non-positive text size in {context}"
			points = [(op.x, op.y)]
		elif isinstance(op, render_ops.LineOp):
			dx = op.p2[0] - op.p1[0]
			dy = op.p2[1] - op.p1[1]
			assert math.hypot(dx, dy) > 0.0, f"Zero-length line in {context}: {op.op_id}"
			points = [op.p1, op.p2]
		elif isinstance(op, render_ops.PolygonOp):
			assert len(op.points) >= 3, f"Degenerate polygon in {context}: {op.op_id}"
			points = list(op.points)
		else:
			points = []
		for x, y in points:
			assert math.isfinite(x) and math.isfinite(y), f"Non-finite point in {context}: {op.op_id}"


#============================================
def test_haworth_renderer_smoke_matrix(tmp_path):
	cases = [
		("ARLRDM", "pyranose"),
		("ARLRDM", "furanose"),
		("ARRDM", "pyranose"),
		("ARRDM", "furanose"),
		("ARDM", "furanose"),
		("MKLRDM", "pyranose"),
		("MKLRDM", "furanose"),
		("AdRDM", "furanose"),
	]
	for code, ring_type in cases:
		for anomeric in ("alpha", "beta"):
			ops = _build_ops(code, ring_type, anomeric)
			_assert_ops_well_formed(ops, f"{code}_{ring_type}_{anomeric}")
			assert any(isinstance(op, render_ops.PolygonOp) for op in ops)
			assert any(isinstance(op, render_ops.TextOp) for op in ops)
			svg_text = _ops_to_svg_text(ops)
			output_path = tmp_path / f"{code}_{ring_type}_{anomeric}.svg"
			with open(output_path, "w", encoding="utf-8") as handle:
				handle.write(svg_text)
			assert output_path.is_file()
			assert output_path.stat().st_size > 0
			with open(output_path, "r", encoding="utf-8") as handle:
				file_text = handle.read()
			assert "<svg" in file_text

	ops = _build_ops("ARLRDM", "pyranose", "alpha", bg_color="#f0f0f0")
	_assert_ops_well_formed(ops, "ARLRDM_pyranose_alpha_bg")
	assert any(isinstance(op, render_ops.PolygonOp) for op in ops)
	assert any(isinstance(op, render_ops.TextOp) for op in ops)
	svg_text = _ops_to_svg_text(ops)
	output_path = tmp_path / "ARLRDM_pyranose_alpha_bg.svg"
	with open(output_path, "w", encoding="utf-8") as handle:
		handle.write(svg_text)
	assert output_path.is_file()
	assert output_path.stat().st_size > 0
	with open(output_path, "r", encoding="utf-8") as handle:
		file_text = handle.read()
	assert "<svg" in file_text


#============================================
# Full archive matrix: all 78 mappable sugars from NEUROtiker archive
#============================================

_ARCHIVE_CASES = [
	(code, ring_type, anomeric, filename)
	for code, ring_type, anomeric, filename, _name in all_mappable_entries()
]

_ARCHIVE_IDS = [
	f"{code}_{ring_type}_{anomeric}"
	for code, ring_type, anomeric, _filename, _name in all_mappable_entries()
]


@pytest.mark.parametrize(
	"code,ring_type,anomeric,archive_filename",
	_ARCHIVE_CASES,
	ids=_ARCHIVE_IDS,
)
def test_archive_full_matrix(tmp_path, code, ring_type, anomeric, archive_filename):
	"""Render every mappable sugar from the NEUROtiker archive and verify output."""
	ops = _build_ops(code, ring_type, anomeric)
	_assert_ops_well_formed(ops, f"{code}_{ring_type}_{anomeric}")
	assert any(isinstance(op, render_ops.PolygonOp) for op in ops), (
		f"No PolygonOps for {code} {ring_type} {anomeric}"
	)
	assert any(isinstance(op, render_ops.TextOp) for op in ops), (
		f"No TextOps for {code} {ring_type} {anomeric}"
	)
	svg_text = _ops_to_svg_text(ops)
	output_path = tmp_path / f"{code}_{ring_type}_{anomeric}.svg"
	with open(output_path, "w", encoding="utf-8") as handle:
		handle.write(svg_text)
	assert output_path.is_file()
	assert output_path.stat().st_size > 0
	with open(output_path, "r", encoding="utf-8") as handle:
		file_text = handle.read()
	assert "<svg" in file_text
