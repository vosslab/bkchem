# SPDX-License-Identifier: LGPL-3.0-or-later
"""Integration tests for Haworth selftest builders."""

# Standard Library
import os
import sys

# Third Party
import pytest

# Local repo modules
import conftest


repo_root = conftest.repo_root()
tools_dir = os.path.join(repo_root, "tools")
if tools_dir not in sys.path:
	sys.path.insert(0, tools_dir)

conftest.add_oasa_to_sys_path()

# local repo modules
from oasa import render_ops
import selftest_sheet


#============================================
@pytest.mark.parametrize(
	"builder_name",
	[
		"_build_alpha_d_glucopyranose_ops",
		"_build_beta_d_fructofuranose_ops",
	],
)
def test_selftest_haworth_builders_have_expected_ops(builder_name):
	"""Ensure selftest Haworth builders emit drawable render_ops content."""
	builder = getattr(selftest_sheet, builder_name)
	ops = builder()
	assert ops
	assert any(isinstance(op, render_ops.PolygonOp) for op in ops)
	assert any(isinstance(op, render_ops.TextOp) for op in ops)
	minx, miny, maxx, maxy = selftest_sheet.ops_bbox(ops)
	assert maxx > minx
	assert maxy > miny
