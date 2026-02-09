#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""CD-SVG codec: SVG rendering with embedded CDML metadata."""

# Standard Library
import io
import xml.dom.minidom as dom

# local repo modules
from .. import cdml
from .. import cdml_writer
from .. import render_out
from .. import safe_xml
from .. import svg_out


_CDML_NAMESPACE = cdml_writer.CDML_NAMESPACE
_FORBIDDEN_EXPORT_SNIPPETS = (
	"<script",
	" onload=",
	" onerror=",
	"<foreignobject",
	"url(http",
	"href=\"http://",
	"href=\"https://",
	"xlink:href=\"http://",
	"xlink:href=\"https://",
)


#============================================
def _first_element(node):
	for child in node.childNodes:
		if child.nodeType == child.ELEMENT_NODE:
			return child
	return None


#============================================
def _assert_safe_svg_export(svg_text):
	lower_text = svg_text.lower()
	for snippet in _FORBIDDEN_EXPORT_SNIPPETS:
		if snippet in lower_text:
			raise ValueError(f"Unsafe SVG content blocked during CD-SVG export: {snippet}")


#============================================
def _extract_cdml_element(svg_text):
	doc = safe_xml.parse_dom_from_string(svg_text)
	nodes = doc.getElementsByTagNameNS(_CDML_NAMESPACE, "cdml")
	if nodes:
		return nodes[0]
	# Backward compatibility: older BKChem CD-SVG files may have <cdml>
	# without a namespace, so fall back to non-namespaced lookup.
	for node in doc.getElementsByTagName("cdml"):
		return node
	return None


#============================================
def _build_cdsvg_text(mol, **kwargs):
	svg_buffer = io.StringIO()
	render_out.render_to_svg(mol, svg_buffer, **kwargs)
	svg_doc = safe_xml.parse_dom_from_string(svg_buffer.getvalue())
	root = _first_element(svg_doc)
	if root is None or root.tagName.lower() != "svg":
		raise ValueError("CD-SVG export failed to construct an SVG root node.")
	metadata = svg_doc.createElement("metadata")
	metadata.setAttribute("id", "bkchem_cdml")
	cdml_doc = safe_xml.parse_dom_from_string(cdml_writer.mol_to_text(mol))
	cdml_root = _first_element(cdml_doc)
	if cdml_root is None:
		raise ValueError("CD-SVG export failed to build CDML payload.")
	metadata.appendChild(svg_doc.importNode(cdml_root, True))
	root.appendChild(metadata)
	svg_text = svg_out.pretty_print_svg(svg_doc.toxml("utf-8"))
	_assert_safe_svg_export(svg_text)
	return svg_text


#============================================
def text_to_mol(text, **kwargs):
	"""Parse CD-SVG by extracting only the embedded CDML payload."""
	del kwargs
	cdml_element = _extract_cdml_element(text)
	if cdml_element is None:
		raise ValueError("CD-SVG import failed: no embedded CDML block found.")
	doc = dom.Document()
	doc.appendChild(doc.importNode(cdml_element, True))
	return cdml.text_to_mol(doc.toxml("utf-8"))


#============================================
def file_to_mol(file_obj, **kwargs):
	text = file_obj.read()
	if isinstance(text, bytes):
		text = text.decode("utf-8")
	return text_to_mol(text, **kwargs)


#============================================
def mol_to_text(mol, **kwargs):
	return _build_cdsvg_text(mol, **kwargs)


#============================================
def mol_to_file(mol, file_obj, **kwargs):
	text = _build_cdsvg_text(mol, **kwargs)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text)
	else:
		file_obj.write(text.encode("utf-8"))
