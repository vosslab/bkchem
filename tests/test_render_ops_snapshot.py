"""Golden snapshot for render ops serialization."""

# Standard Library
import json
import os

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

# local repo modules
import oasa
from oasa import render_geometry
from oasa import render_ops


SNAPSHOT_PATH = conftest.tests_path("fixtures", "render_ops_snapshot.json")


#============================================
def _build_ops():
	mol = oasa.molecule()
	context = render_geometry.BondRenderContext(
		molecule=mol,
		line_width=2.0,
		bond_width=6.0,
		wedge_width=6.0,
		bold_line_width_multiplier=1.2,
		bond_second_line_shortening=0.0,
		color_bonds=False,
		atom_colors=None,
		shown_vertices=set(),
		bond_coords=None,
		point_for_atom=None,
	)
	ops = []
	bonds = [
		(0.0, 0.0, 30.0, 0.0, "n", "#000000"),
		(0.0, 10.0, 30.0, 10.0, "b", "#000000"),
		(0.0, 20.0, 30.0, 20.0, "w", "#d94a2d"),
		(0.0, 30.0, 30.0, 30.0, "h", "#239e2d"),
		(0.0, 40.0, 30.0, 40.0, "q", "#000000"),
		(0.0, 50.0, 30.0, 50.0, "s", "#2d5fd9"),
	]
	for x1, y1, x2, y2, bond_type, color in bonds:
		a1 = oasa.atom(symbol="C")
		a2 = oasa.atom(symbol="C")
		a1.x = x1
		a1.y = y1
		a2.x = x2
		a2.y = y2
		mol.add_vertex(a1)
		mol.add_vertex(a2)
		bond = oasa.bond(order=1, type=bond_type)
		if bond_type == "s":
			bond.wavy_style = "triangle"
			bond.properties_["wavy_style"] = "triangle"
		bond.line_color = color
		bond.properties_["line_color"] = color
		bond.vertices = (a1, a2)
		mol.add_edge(a1, a2, bond)
		ops.extend(render_geometry.build_bond_ops(bond, (x1, y1), (x2, y2), context))
	ops.append(
		render_ops.PathOp(
			commands=(
				("M", (0.0, 0.0)),
				("ARC", (0.0, 0.0, 4.0, 0.0, 1.5708)),
				("Z", None),
			),
			fill="#000000",
		)
	)
	return ops


#============================================
def test_render_ops_snapshot():
	if not os.path.isfile(SNAPSHOT_PATH):
		raise AssertionError("Missing snapshot file: %s" % SNAPSHOT_PATH)
	with open(SNAPSHOT_PATH, "r", encoding="utf-8") as handle:
		expected = json.load(handle)
	actual = render_ops.ops_to_json_dict(_build_ops(), round_digits=3)
	assert actual == expected
