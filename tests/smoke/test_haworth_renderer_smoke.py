"""Smoke tests for Haworth renderer ops and SVG serialization."""

# Standard Library
from xml.dom import minidom as xml_minidom

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

import oasa.dom_extensions as dom_extensions
import oasa.haworth_renderer as haworth_renderer
import oasa.haworth_spec as haworth_spec
import oasa.render_ops as render_ops
import oasa.sugar_code as sugar_code
import oasa.svg_out as svg_out


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
