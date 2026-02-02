# SPDX-License-Identifier: LGPL-3.0-or-later
"""Test Fischer projection explicit hydrogen rendering."""

# Standard Library
# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
from oasa import render_ops
from oasa import selftest_sheet


#============================================
def test_fischer_explicit_hydrogens():
	"""Test that Fischer shows H labels when show_explicit_hydrogens=True."""
	default_ops = selftest_sheet._build_fischer_ops(show_explicit_hydrogens=False)
	explicit_ops = selftest_sheet._build_fischer_ops(show_explicit_hydrogens=True)

	def _collect_text(ops):
		return [op.text for op in ops if isinstance(op, render_ops.TextOp)]

	default_text = _collect_text(default_ops)
	explicit_text = _collect_text(explicit_ops)

	default_h = [value for value in default_text if value == "H"]
	explicit_h = [value for value in explicit_text if value == "H"]
	assert len(explicit_h) > len(default_h)
