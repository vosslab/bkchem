# SPDX-License-Identifier: LGPL-3.0-or-later
"""Test Fischer projection explicit hydrogen rendering."""

# Standard Library
import os
import sys

PACKAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "packages")
if PACKAGES_DIR not in sys.path:
	sys.path.insert(0, PACKAGES_DIR)

# local repo modules
from oasa import selftest_sheet


#============================================
def test_fischer_explicit_hydrogens():
	"""Test that Fischer shows H labels when show_explicit_hydrogens=True."""
	ops_default, labels_default = selftest_sheet._build_fischer_ops(show_explicit_hydrogens=False)
	ops_explicit, labels_explicit = selftest_sheet._build_fischer_ops(show_explicit_hydrogens=True)

	h_labels_default = [label for label in labels_default if label[2] == "H"]
	h_labels_explicit = [label for label in labels_explicit if label[2] == "H"]

	assert len(h_labels_explicit) > len(h_labels_default)

	for label in h_labels_explicit:
		assert len(label) == 5
		x, y, text, font_size, anchor = label
		if text == "H":
			assert font_size == 9
			assert anchor in ["start", "end"]
