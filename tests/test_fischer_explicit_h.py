# SPDX-License-Identifier: LGPL-3.0-or-later
"""Test Fischer projection explicit hydrogen rendering."""

# Standard Library
# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
from oasa import selftest_sheet


#============================================
def test_fischer_explicit_hydrogens():
	"""Test that Fischer shows H labels when show_explicit_hydrogens=True."""
	default_svg = selftest_sheet._build_fischer_svg(show_explicit_hydrogens=False)
	explicit_svg = selftest_sheet._build_fischer_svg(show_explicit_hydrogens=True)

	def _collect_text(svg_doc):
		text_nodes = svg_doc.getElementsByTagName("text")
		values = []
		for node in text_nodes:
			if node.firstChild:
				values.append(node.firstChild.nodeValue)
		return values

	default_text = _collect_text(default_svg)
	explicit_text = _collect_text(explicit_svg)

	default_h = [value for value in default_text if value == "H"]
	explicit_h = [value for value in explicit_text if value == "H"]
	assert len(explicit_h) > len(default_h)
