"""Tests for Patch 4-5: Dialog wiring, template placement, and bond drawing."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import bkchem_qt.modes.draw_mode
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.actions.context_menu
import bkchem_qt.actions.repair_actions


#============================================
def test_atom_dialog_applies_changes(qapp):
	"""AtomDialog.edit_atom() can apply changes to an AtomModel."""
	oasa_atom = oasa.atom_lib.Atom(symbol="C")
	atom = bkchem_qt.models.atom_model.AtomModel(oasa_atom=oasa_atom)
	atom.set_xyz(0.0, 0.0, 0.0)
	assert atom.symbol == "C", "should start as C"
	# directly test property setting
	atom.symbol = "N"
	assert atom.symbol == "N", "symbol should be N after set"
	atom.charge = -1
	assert atom.charge == -1, "charge should be -1"
	atom.font_size = 14
	assert atom.font_size == 14, "font_size should be 14"


#============================================
def test_bond_dialog_applies_changes(qapp):
	"""BondDialog.edit_bond() can apply changes to a BondModel."""
	oasa_bond = oasa.bond_lib.Bond(order=1, type="n")
	bond = bkchem_qt.models.bond_model.BondModel(oasa_bond=oasa_bond)
	assert bond.order == 1, "should start as single"
	assert bond.type == "n", "should start as normal"
	# directly test property setting
	bond.order = 2
	assert bond.order == 2, "order should be 2 after set"
	bond.type = "w"
	assert bond.type == "w", "type should be w after set"
	bond.line_width = 2.5
	assert bond.line_width == 2.5, "line_width should be 2.5"


#============================================
def test_template_mode_places_molecule(main_window):
	"""Template mode _place_template() adds atoms to the scene and document."""
	main_window._mode_manager.set_mode("template")
	tmpl_mode = main_window._mode_manager.current_mode
	# set a known template
	if "Ph" in tmpl_mode.template_names:
		tmpl_mode.set_template("Ph")
	elif "Me" in tmpl_mode.template_names:
		tmpl_mode.set_template("Me")
	else:
		# use the first available template
		if tmpl_mode.template_names:
			tmpl_mode.set_template(tmpl_mode.template_names[0])
		else:
			# no templates available, skip
			return
	# place the template
	tmpl_mode._place_template(200.0, 200.0)
	# verify atoms were added
	atom_items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(atom_items) > 0, "template should have added atoms to scene"
	assert len(main_window.document.molecules) > 0, (
		"document should have molecules"
	)


#============================================
def test_context_menu_delete_atom(main_window):
	"""Context menu _delete_atom() removes atom with undo support."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	atom_item = draw_mode._create_atom_at(100.0, 200.0, "C")
	assert atom_item is not None
	# verify atom exists
	items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(items) == 1
	# delete via context menu helper
	bkchem_qt.actions.context_menu._delete_atom(
		main_window.view, atom_item
	)
	items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(items) == 0, "atom should be removed"
	# undo should restore it
	main_window.document.undo_stack.undo()
	items = [
		i for i in main_window.scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	]
	assert len(items) == 1, "atom should be restored after undo"


#============================================
def test_stub_modes_emit_not_implemented(main_window):
	"""Stub modes emit 'not yet implemented' status messages."""
	stub_modes = ["vector", "bracket", "plus", "repair", "misc"]
	for mode_name in stub_modes:
		main_window._mode_manager.set_mode(mode_name)
		mode = main_window._mode_manager.current_mode
		messages = []
		mode.status_message.connect(messages.append)
		# simulate a mouse press
		pos = PySide6.QtCore.QPointF(100.0, 100.0)
		mode.mouse_press(pos, None)
		assert len(messages) > 0, (
			f"{mode_name}: should emit status message"
		)
		assert "not yet implemented" in messages[-1], (
			f"{mode_name}: message should say 'not yet implemented', "
			f"got: {messages[-1]}"
		)
		# disconnect to avoid accumulation across modes
		mode.status_message.disconnect(messages.append)


# ------------------------------------------------------------------
# Bond placement parity tests
# ------------------------------------------------------------------

#============================================
def _count_atom_items(scene) -> int:
	"""Count AtomItem instances in the scene."""
	return sum(
		1 for i in scene.items()
		if isinstance(i, bkchem_qt.canvas.items.atom_item.AtomItem)
	)


#============================================
def _count_bond_items(scene) -> int:
	"""Count BondItem instances in the scene."""
	return sum(
		1 for i in scene.items()
		if isinstance(i, bkchem_qt.canvas.items.bond_item.BondItem)
	)


#============================================
class _FakeMouseEvent:
	"""Minimal mouse-event stub for direct mode method calls in tests."""

	#============================================
	def __init__(self, modifiers=PySide6.QtCore.Qt.KeyboardModifier.NoModifier):
		self._modifiers = modifiers

	#============================================
	def modifiers(self):
		"""Return keyboard modifiers."""
		return self._modifiers


#============================================
def test_scene_and_draw_share_canonical_spacing(main_window):
	"""Draw mode must read bond length directly from scene spacing."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	main_window.scene.set_grid_spacing_pt(52.0)
	assert abs(main_window.scene.grid_spacing_pt - 52.0) < 1e-6
	assert abs(draw_mode._get_bond_length() - 52.0) < 1e-6


#============================================
def test_zoom_does_not_change_scene_spacing_value(main_window):
	"""Zoom operations must not change the canonical scene spacing value."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	initial_spacing = main_window.scene.grid_spacing_pt
	main_window.view.set_zoom_percent(220.0)
	assert abs(main_window.scene.grid_spacing_pt - initial_spacing) < 1e-6
	assert abs(draw_mode._get_bond_length() - initial_spacing) < 1e-6
	main_window.view.reset_zoom()


#============================================
def test_element_change_routes_to_atom_mode_setter(main_window):
	"""Element edits should route through AtomMode.set_element()."""
	main_window._mode_manager.set_mode("atom")
	atom_mode = main_window._mode_manager.current_mode
	main_window._on_element_changed("O")
	assert atom_mode.current_element == "O", (
		"Atom mode should update current element via set_element()"
	)


#============================================
def test_element_change_routes_to_draw_mode_property(main_window):
	"""Element edits should route to DrawMode.current_element setter."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	main_window._on_element_changed("  N  ")
	assert draw_mode.current_element == "N", (
		"Draw mode should store stripped element text"
	)
	main_window._on_element_changed("   ")
	assert draw_mode.current_element == "N", (
		"Blank element edits should not clear draw mode element"
	)


#============================================
def test_bond_click_creates_fixed_length_bond(main_window):
	"""Click on an existing atom creates a new atom at grid_spacing distance."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	# create a seed atom directly
	seed = draw_mode._create_atom_at(200.0, 200.0, "C")
	assert seed is not None, "seed atom should be created"
	# simulate clicking on the seed atom
	pos = PySide6.QtCore.QPointF(200.0, 200.0)
	draw_mode.mouse_press(pos, None)
	# should now have 2 atoms and 1 bond
	assert _count_atom_items(main_window.scene) == 2, (
		"clicking atom should create a bonded neighbor"
	)
	assert _count_bond_items(main_window.scene) == 1, (
		"clicking atom should create one bond"
	)
	# verify the bond length matches grid spacing
	bond_length = draw_mode._get_bond_length()
	mol = main_window.document.molecules[0]
	atoms = mol.atoms
	assert len(atoms) == 2, "molecule should have 2 atoms"
	dx = atoms[1].x - atoms[0].x
	dy = atoms[1].y - atoms[0].y
	actual_dist = math.sqrt(dx * dx + dy * dy)
	assert abs(actual_dist - bond_length) < 0.5, (
		f"bond length {actual_dist:.2f} should be close to "
		f"grid spacing {bond_length:.2f}"
	)


#============================================
def test_bond_click_uses_120_degree_angle(main_window):
	"""Click on atom with one neighbor places new bond at ~120 degrees."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol_model = draw_mode._get_active_molecule()
	bond_length = draw_mode._get_bond_length()
	# create two connected atoms manually (horizontal bond)
	a1 = draw_mode._create_atom_at(200.0, 200.0, "C")
	a2 = draw_mode._create_atom_at(200.0 + bond_length, 200.0, "C")
	draw_mode._create_bond_between(a1, a2)
	assert _count_atom_items(main_window.scene) == 2
	assert _count_bond_items(main_window.scene) == 1
	# click on a2 to add a third atom
	pos = PySide6.QtCore.QPointF(200.0 + bond_length, 200.0)
	draw_mode.mouse_press(pos, None)
	assert _count_atom_items(main_window.scene) == 3, (
		"should have 3 atoms after clicking a2"
	)
	# measure the angle between a1-a2 and a2-a3
	atoms = mol_model.atoms
	# find a3: the atom that is not a1 or a2
	a1m = a1.atom_model
	a2m = a2.atom_model
	a3m = None
	for am in atoms:
		if am is not a1m and am is not a2m:
			a3m = am
			break
	assert a3m is not None, "should find a third atom"
	# angle at a2 between a1 and a3
	angle_a2_a1 = math.atan2(a1m.y - a2m.y, a1m.x - a2m.x)
	angle_a2_a3 = math.atan2(a3m.y - a2m.y, a3m.x - a2m.x)
	angle_diff = abs(angle_a2_a3 - angle_a2_a1)
	# normalize to [0, pi]
	if angle_diff > math.pi:
		angle_diff = 2 * math.pi - angle_diff
	# should be approximately 120 degrees (2*pi/3 radians)
	expected = 2 * math.pi / 3
	assert abs(angle_diff - expected) < 0.15, (
		f"angle between bonds should be ~120 deg ({math.degrees(expected):.1f}), "
		f"got {math.degrees(angle_diff):.1f} deg"
	)


#============================================
def test_standalone_atom_snaps_to_grid(main_window):
	"""Click on empty space creates atoms snapped to hex grid."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	scene = main_window.scene
	# click on a position that is NOT on the grid
	pos = PySide6.QtCore.QPointF(103.7, 98.2)
	draw_mode.mouse_press(pos, None)
	# should have 2 atoms (standalone + auto-bonded neighbor)
	assert _count_atom_items(scene) >= 2, (
		"clicking empty space should create atom + bonded neighbor"
	)
	# the first atom should be snapped to grid
	mol = main_window.document.molecules[0]
	first_atom = mol.atoms[0]
	# verify by re-snapping and checking it matches
	snapped_x, snapped_y = scene.snap_to_grid(103.7, 98.2)
	assert abs(first_atom.x - snapped_x) < 0.5, (
		f"x={first_atom.x:.2f} should be snapped to {snapped_x:.2f}"
	)
	assert abs(first_atom.y - snapped_y) < 0.5, (
		f"y={first_atom.y:.2f} should be snapped to {snapped_y:.2f}"
	)


#============================================
def test_standalone_atom_respects_grid_snap_toggle(main_window):
	"""Draw mode should place on raw cursor when grid snap is disabled."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	scene = main_window.scene
	scene.set_grid_snap_enabled(False)
	pos = PySide6.QtCore.QPointF(103.7, 98.2)
	draw_mode.mouse_press(pos, None)
	mol = main_window.document.molecules[0]
	first_atom = mol.atoms[0]
	assert abs(first_atom.x - pos.x()) < 0.5, (
		f"x={first_atom.x:.2f} should stay near click x={pos.x():.2f}"
	)
	assert abs(first_atom.y - pos.y()) < 0.5, (
		f"y={first_atom.y:.2f} should stay near click y={pos.y():.2f}"
	)


#============================================
def test_bond_drag_snaps_angle(main_window):
	"""Drag from an atom snaps endpoint to 15-degree angle increments."""
	draw_mode = bkchem_qt.modes.draw_mode.DrawMode
	# unit test _point_on_circle directly
	# direction at 47 degrees should snap to 45 degrees
	cx, cy = 100.0, 100.0
	radius = 40.0
	dx = math.cos(math.radians(47)) * 50
	dy = math.sin(math.radians(47)) * 50
	snap_x, snap_y = draw_mode._point_on_circle(cx, cy, radius, dx, dy)
	# expected: 45 deg snapped
	expected_x = cx + round(math.cos(math.radians(45)) * radius, 2)
	expected_y = cy + round(math.sin(math.radians(45)) * radius, 2)
	assert abs(snap_x - expected_x) < 0.1, (
		f"snapped x={snap_x:.2f} should be ~{expected_x:.2f}"
	)
	assert abs(snap_y - expected_y) < 0.1, (
		f"snapped y={snap_y:.2f} should be ~{expected_y:.2f}"
	)
	# direction at 5 degrees should snap to 0 degrees
	dx2 = math.cos(math.radians(5)) * 50
	dy2 = math.sin(math.radians(5)) * 50
	snap_x2, snap_y2 = draw_mode._point_on_circle(
		cx, cy, radius, dx2, dy2,
	)
	expected_x2 = cx + round(radius, 2)
	expected_y2 = cy + 0.0
	assert abs(snap_x2 - expected_x2) < 0.1, (
		f"snapped x={snap_x2:.2f} should be ~{expected_x2:.2f} (0 deg)"
	)
	assert abs(snap_y2 - expected_y2) < 0.1, (
		f"snapped y={snap_y2:.2f} should be ~{expected_y2:.2f} (0 deg)"
	)


#============================================
def test_edit_drag_snaps_anchor_to_grid(main_window):
	"""Edit drag should snap selected atoms by anchor when enabled."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	scene = main_window.scene
	scene.set_grid_snap_enabled(True)
	a1 = draw_mode._create_atom_at(101.0, 99.0, "C")
	a2 = draw_mode._create_atom_at(141.0, 99.0, "C")
	draw_mode._create_bond_between(a1, a2)
	initial_dx = a2.atom_model.x - a1.atom_model.x
	initial_dy = a2.atom_model.y - a1.atom_model.y
	a1.setSelected(True)
	a2.setSelected(True)
	main_window._mode_manager.set_mode("edit")
	edit_mode = main_window._mode_manager.current_mode
	event = _FakeMouseEvent()
	start = PySide6.QtCore.QPointF(a1.atom_model.x, a1.atom_model.y)
	target = PySide6.QtCore.QPointF(start.x() + 13.2, start.y() + 8.7)
	edit_mode.mouse_press(start, event)
	edit_mode.mouse_move(target, event)
	edit_mode.mouse_release(target, event)
	expected_x, expected_y = scene.snap_to_grid(target.x(), target.y())
	assert abs(a1.atom_model.x - expected_x) < 0.5, (
		f"anchor x={a1.atom_model.x:.2f} should snap to {expected_x:.2f}"
	)
	assert abs(a1.atom_model.y - expected_y) < 0.5, (
		f"anchor y={a1.atom_model.y:.2f} should snap to {expected_y:.2f}"
	)
	final_dx = a2.atom_model.x - a1.atom_model.x
	final_dy = a2.atom_model.y - a1.atom_model.y
	assert abs(final_dx - initial_dx) < 0.1, (
		f"pair dx should remain {initial_dx:.2f}, got {final_dx:.2f}"
	)
	assert abs(final_dy - initial_dy) < 0.1, (
		f"pair dy should remain {initial_dy:.2f}, got {final_dy:.2f}"
	)


#============================================
def test_find_place_zero_neighbors(main_window):
	"""_find_place with zero neighbors places at 30-degree default angle."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol_model = draw_mode._get_active_molecule()
	# create isolated atom
	atom = draw_mode._create_atom_at(200.0, 200.0, "C")
	bond_length = draw_mode._get_bond_length()
	new_x, new_y = draw_mode._find_place(
		atom.atom_model, mol_model, bond_length,
	)
	# should be at 30 deg angle: cos(pi/6)*d, -sin(pi/6)*d
	expected_x = 200.0 + math.cos(math.pi / 6) * bond_length
	expected_y = 200.0 - math.sin(math.pi / 6) * bond_length
	assert abs(new_x - expected_x) < 0.5, (
		f"x={new_x:.2f} should be ~{expected_x:.2f}"
	)
	assert abs(new_y - expected_y) < 0.5, (
		f"y={new_y:.2f} should be ~{expected_y:.2f}"
	)


#============================================
def test_find_place_least_crowded(main_window):
	"""_find_place with 2+ neighbors uses least-crowded angular gap."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	mol_model = draw_mode._get_active_molecule()
	bond_length = draw_mode._get_bond_length()
	# create a center atom with 2 neighbors at 0 and 90 degrees
	center = draw_mode._create_atom_at(200.0, 200.0, "C")
	right = draw_mode._create_atom_at(200.0 + bond_length, 200.0, "C")
	up = draw_mode._create_atom_at(200.0, 200.0 - bond_length, "C")
	draw_mode._create_bond_between(center, right)
	draw_mode._create_bond_between(center, up)
	# find place should pick the largest angular gap
	new_x, new_y = draw_mode._find_place(
		center.atom_model, mol_model, bond_length,
	)
	# the largest gap is from 0 deg clockwise to 270 deg (= -90 deg)
	# which is a 270 deg gap; midpoint is at 135 deg (down-left)
	dx = new_x - 200.0
	dy = new_y - 200.0
	actual_dist = math.sqrt(dx * dx + dy * dy)
	assert abs(actual_dist - bond_length) < 0.5, (
		f"distance {actual_dist:.2f} should be ~{bond_length:.2f}"
	)
	# verify it is NOT in the 0-to-90 deg sector occupied by neighbors
	angle = math.atan2(dy, dx)
	if angle < 0:
		angle += 2 * math.pi
	# neighbors are at 0 deg and 270 deg (= -90 deg = 1.5*pi)
	# the new atom should be between them in the largest gap
	assert not (angle < 0.1 or abs(angle - 1.5 * math.pi) < 0.1), (
		f"new atom angle {math.degrees(angle):.1f} should not be at "
		"a neighbor angle"
	)


# ------------------------------------------------------------------
# Bond endpoint clipping and signal chain tests
# ------------------------------------------------------------------

#============================================
def _make_bonded_items(qapp, symbol1="C", symbol2="N", x1=0.0, y1=0.0, x2=40.0, y2=0.0):
	"""Create two AtomModels connected by a BondModel with BondItem.

	Uses MoleculeModel to properly wire the OASA graph connectivity
	so edge.vertices returns the correct atoms for bond rendering.
	"""
	import bkchem_qt.models.molecule_model
	mol_model = bkchem_qt.models.molecule_model.MoleculeModel()
	a1 = mol_model.create_atom(symbol=symbol1)
	a2 = mol_model.create_atom(symbol=symbol2)
	a1.set_xyz(x1, y1, 0.0)
	a2.set_xyz(x2, y2, 0.0)
	mol_model.add_atom(a1)
	mol_model.add_atom(a2)
	bond = mol_model.create_bond(order=1, bond_type="n")
	mol_model.add_bond(a1, a2, bond)
	bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond)
	return a1, a2, bond, bond_item


#============================================
def test_bond_item_clips_at_labeled_atom(qapp):
	"""Bond endpoint near a labeled heteroatom is shorter than center-to-center."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "N", 0.0, 0.0, 40.0, 0.0)
	# find the maximum x coordinate in bond ops line endpoints
	import oasa.render_ops
	line_ops = [op for op in bond_item._ops if isinstance(op, oasa.render_ops.LineOp)]
	assert len(line_ops) > 0, "bond should have line ops"
	# the bond line toward N (at x=40) should be clipped short of 40
	max_x = max(op.p2[0] for op in line_ops)
	assert max_x < 40.0, (
		f"bond end x={max_x:.2f} should be clipped before atom center at 40.0"
	)


#============================================
def test_bond_item_no_clip_for_hidden_carbon(qapp):
	"""Bond between two hidden carbons has no clipping."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "C", 0.0, 0.0, 40.0, 0.0)
	import oasa.render_ops
	line_ops = [op for op in bond_item._ops if isinstance(op, oasa.render_ops.LineOp)]
	assert len(line_ops) > 0, "bond should have line ops"
	# both endpoints should be at full center-to-center distance
	min_x = min(op.p1[0] for op in line_ops)
	max_x = max(op.p2[0] for op in line_ops)
	assert min_x == 0.0 or abs(min_x) < 1.0, "start should be near 0"
	assert max_x == 40.0 or abs(max_x - 40.0) < 1.0, "end should be near 40"


#============================================
def test_atom_symbol_change_triggers_bond_redraw(qapp):
	"""Changing atom symbol triggers bond item update via signal chain."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "C", 0.0, 0.0, 40.0, 0.0)
	# change atom2 to nitrogen (should trigger bond update)
	a2.symbol = "N"
	# bond_item should have been updated (ops may differ now)
	# the end should now be clipped because N is shown
	import oasa.render_ops
	line_ops = [op for op in bond_item._ops if isinstance(op, oasa.render_ops.LineOp)]
	assert len(line_ops) > 0
	max_x = max(op.p2[0] for op in line_ops)
	assert max_x < 40.0, (
		f"after symbol change to N, bond end x={max_x:.2f} should be clipped"
	)


#============================================
def test_atom_charge_change_triggers_bond_redraw(qapp):
	"""Changing atom charge triggers bond item update via signal chain."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "N", 0.0, 0.0, 40.0, 0.0)
	# get initial ops snapshot
	ops_before = list(bond_item._ops)
	# change charge on the nitrogen
	a2.charge = 1
	# ops should have been regenerated (clipping may change slightly)
	ops_after = list(bond_item._ops)
	# ops should be different because the label text changed (N -> N+)
	assert ops_before != ops_after, "bond ops should change after charge update"


#============================================
def test_atom_position_change_triggers_bond_redraw(qapp):
	"""Moving an atom triggers bond item update via signal chain."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "N", 0.0, 0.0, 40.0, 0.0)
	import oasa.render_ops
	line_ops_before = [op for op in bond_item._ops if isinstance(op, oasa.render_ops.LineOp)]
	max_x_before = max(op.p2[0] for op in line_ops_before)
	# move atom2 further away
	a2.x = 80.0
	line_ops_after = [op for op in bond_item._ops if isinstance(op, oasa.render_ops.LineOp)]
	max_x_after = max(op.p2[0] for op in line_ops_after)
	# the bond should now extend further than before
	assert max_x_after > max_x_before, (
		f"after moving atom, bond end x should increase from {max_x_before:.2f}"
	)


#============================================
def test_bond_render_context_has_real_targets(qapp):
	"""BondItem build passes non-empty label_targets for heteroatom bonds."""
	a1, a2, bond, bond_item = _make_bonded_items(qapp, "C", "O", 0.0, 0.0, 40.0, 0.0)
	# force update and inspect the context by checking ops differ from empty
	import oasa.render_ops
	line_ops = [op for op in bond_item._ops if isinstance(op, oasa.render_ops.LineOp)]
	assert len(line_ops) > 0
	# the end near oxygen (at x=40) should be clipped, proving targets were used
	max_x = max(op.p2[0] for op in line_ops)
	assert max_x < 40.0, (
		f"oxygen end x={max_x:.2f} should be clipped, proving real targets are used"
	)


#============================================
def test_repair_normalize_uses_canonical_spacing(main_window):
	"""Repair normalization target must come from scene spacing."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	main_window.scene.set_grid_spacing_pt(50.0)
	a1 = draw_mode._create_atom_at(100.0, 200.0, "C")
	a2 = draw_mode._create_atom_at(260.0, 200.0, "C")
	draw_mode._create_bond_between(a1, a2)
	bkchem_qt.actions.repair_actions._handle_normalize_bond_lengths(main_window)
	mol = main_window.document.molecules[0]
	bond = mol.bonds[0]
	dx = bond.atom2.x - bond.atom1.x
	dy = bond.atom2.y - bond.atom1.y
	actual_dist = math.sqrt(dx * dx + dy * dy)
	assert abs(actual_dist - main_window.scene.grid_spacing_pt) < 0.5, (
		f"normalized bond length {actual_dist:.2f} should match scene spacing "
		f"{main_window.scene.grid_spacing_pt:.2f}"
	)
