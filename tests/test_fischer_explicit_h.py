#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Test Fischer projection explicit hydrogen rendering."""

import os
import sys

# Add packages directory to path
packages_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'packages')
if packages_dir not in sys.path:
    sys.path.insert(0, packages_dir)

# Import selftest_sheet directly
sys.path.insert(0, os.path.join(packages_dir, 'oasa'))
import selftest_sheet


def test_fischer_explicit_hydrogens():
    """Test that Fischer shows H labels when show_explicit_hydrogens=True."""

    # Build Fischer without explicit H
    ops_default, labels_default = selftest_sheet._build_fischer_ops(show_explicit_hydrogens=False)

    # Build Fischer with explicit H
    ops_explicit, labels_explicit = selftest_sheet._build_fischer_ops(show_explicit_hydrogens=True)

    # Count H labels
    h_labels_default = [l for l in labels_default if l[2] == 'H']
    h_labels_explicit = [l for l in labels_explicit if l[2] == 'H']

    print(f"Default mode: {len(h_labels_default)} H labels")
    print(f"Explicit mode: {len(h_labels_explicit)} H labels")

    # With explicit H, we should have more H labels
    # D-glucose has 4 stereocenters (C2-C5), each with 2 positions
    # Some positions have OH, some should get H labels
    assert len(h_labels_explicit) > len(h_labels_default), \
        f"Expected more H labels with explicit H ({len(h_labels_explicit)}) than default ({len(h_labels_default)})"

    # Verify labels have correct format (x, y, text, font_size, anchor)
    for label in h_labels_explicit:
        assert len(label) == 5, f"Label should have 5 elements: {label}"
        x, y, text, font_size, anchor = label
        if text == 'H':
            assert font_size == 9, "H labels should use font size 9"
            assert anchor in ['start', 'end'], "H labels should be left/right anchored"

    print("✓ Fischer explicit hydrogens test passed")
    return True


if __name__ == '__main__':
    test_fischer_explicit_hydrogens()
