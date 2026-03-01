"""Object menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.undo.commands

# minimum z-value floor to avoid overlapping paper/grid layers
_Z_FLOOR = -50


#============================================
def _get_selected_items(app) -> list:
	"""Collect all selected atom and bond QGraphicsItems.

	Args:
		app: The main application object.

	Returns:
		List of AtomItem and BondItem instances that are selected.
	"""
	atoms = app.document.selected_atoms
	bonds = app.document.selected_bonds
	items = list(atoms) + list(bonds)
	return items


#============================================
def _scene_z_range(app) -> tuple:
	"""Compute min and max z-values of interactive items in the scene.

	Skips items with z-values below _Z_FLOOR to exclude the paper
	background and grid overlay layers.

	Args:
		app: The main application object.

	Returns:
		Tuple of (min_z, max_z). Returns (0.0, 0.0) if no items exist.
	"""
	scene = app.document._scene
	if scene is None:
		return (0.0, 0.0)
	z_values = []
	for item in scene.items():
		z = item.zValue()
		# skip paper background and grid layers
		if z < _Z_FLOOR:
			continue
		z_values.append(z)
	if not z_values:
		return (0.0, 0.0)
	return (min(z_values), max(z_values))


#============================================
def handle_bring_to_front(app) -> None:
	"""Lift selected items to the top of the z-order stack.

	Finds the maximum z-value among all interactive scene items and
	sets each selected item one level above it.

	Args:
		app: The main application object.
	"""
	items = _get_selected_items(app)
	if not items:
		return
	_min_z, max_z = _scene_z_range(app)
	# place all selected items above the current max
	new_z = max_z + 1
	for item in items:
		item.setZValue(new_z)
	app.statusBar().showMessage("Brought to front", 2000)


#============================================
def handle_send_back(app) -> None:
	"""Lower selected items to the bottom of the z-order stack.

	Finds the minimum z-value among interactive scene items (above
	the paper/grid floor) and sets each selected item one level
	below it.

	Args:
		app: The main application object.
	"""
	items = _get_selected_items(app)
	if not items:
		return
	min_z, _max_z = _scene_z_range(app)
	# place all selected items below the current min but above floor
	new_z = max(min_z - 1, _Z_FLOOR)
	for item in items:
		item.setZValue(new_z)
	app.statusBar().showMessage("Sent to back", 2000)


#============================================
def handle_swap_on_stack(app) -> None:
	"""Reverse the z-order of selected items.

	Collects the z-values of all selected items, sorts them, then
	assigns them in reverse order so items swap their stacking
	positions.

	Args:
		app: The main application object.
	"""
	items = _get_selected_items(app)
	if len(items) < 2:
		app.statusBar().showMessage(
			"Select at least two items to swap", 3000
		)
		return
	# collect current z-values sorted ascending
	z_values = sorted(item.zValue() for item in items)
	# sort items by current z ascending
	items_sorted = sorted(items, key=lambda it: it.zValue())
	# assign z-values in reverse order
	for item, new_z in zip(items_sorted, reversed(z_values)):
		item.setZValue(new_z)
	app.statusBar().showMessage("Swapped on stack", 2000)


#============================================
def _compute_selection_center(atoms) -> tuple:
	"""Compute the centroid of selected atom positions.

	Args:
		atoms: List of AtomItem instances.

	Returns:
		Tuple of (center_x, center_y).
	"""
	sum_x = 0.0
	sum_y = 0.0
	for atom_item in atoms:
		sum_x += atom_item.atom_model.x
		sum_y += atom_item.atom_model.y
	n = len(atoms)
	center_x = sum_x / n
	center_y = sum_y / n
	return (center_x, center_y)


#============================================
def handle_vertical_mirror(app) -> None:
	"""Reflect selected atoms across their common vertical axis.

	Computes the horizontal center of the selection and mirrors
	each atom's x-coordinate across it. Creates an undoable
	MoveAtomsCommand for the transformation.

	Args:
		app: The main application object.
	"""
	atoms = app.document.selected_atoms
	if not atoms:
		app.statusBar().showMessage(
			"Select atoms to mirror", 3000
		)
		return
	center_x, _center_y = _compute_selection_center(atoms)
	# compute offsets and apply moves
	items_and_offsets = []
	for atom_item in atoms:
		model = atom_item.atom_model
		old_x = model.x
		new_x = 2 * center_x - old_x
		dx = new_x - old_x
		# apply the move immediately
		model.x = new_x
		items_and_offsets.append((atom_item, dx, 0.0))
	# push undoable command (first redo is skipped since already moved)
	cmd = bkchem_qt.undo.commands.MoveAtomsCommand(
		items_and_offsets, "Vertical Mirror"
	)
	app.document.undo_stack.push(cmd)
	app.statusBar().showMessage("Vertical mirror applied", 2000)


#============================================
def handle_horizontal_mirror(app) -> None:
	"""Reflect selected atoms across their common horizontal axis.

	Computes the vertical center of the selection and mirrors each
	atom's y-coordinate across it. Creates an undoable
	MoveAtomsCommand for the transformation.

	Args:
		app: The main application object.
	"""
	atoms = app.document.selected_atoms
	if not atoms:
		app.statusBar().showMessage(
			"Select atoms to mirror", 3000
		)
		return
	_center_x, center_y = _compute_selection_center(atoms)
	# compute offsets and apply moves
	items_and_offsets = []
	for atom_item in atoms:
		model = atom_item.atom_model
		old_y = model.y
		new_y = 2 * center_y - old_y
		dy = new_y - old_y
		# apply the move immediately
		model.y = new_y
		items_and_offsets.append((atom_item, 0.0, dy))
	# push undoable command (first redo is skipped since already moved)
	cmd = bkchem_qt.undo.commands.MoveAtomsCommand(
		items_and_offsets, "Horizontal Mirror"
	)
	app.document.undo_stack.push(cmd)
	app.statusBar().showMessage("Horizontal mirror applied", 2000)


#============================================
def handle_scale(app) -> None:
	"""Scale selected atom positions relative to the selection center.

	Opens the ScaleDialog to get X and Y scale factors. Each atom's
	position is scaled around the centroid of the selection. Creates
	an undoable MoveAtomsCommand for the transformation.

	Args:
		app: The main application object.
	"""
	atoms = app.document.selected_atoms
	if not atoms:
		app.statusBar().showMessage(
			"Select atoms to scale", 3000
		)
		return
	# show scale dialog
	import bkchem_qt.dialogs.scale_dialog
	result = bkchem_qt.dialogs.scale_dialog.ScaleDialog.get_scale_factors(
		app
	)
	if result is None:
		return
	scale_x, scale_y = result
	# avoid no-op scaling
	if scale_x == 1.0 and scale_y == 1.0:
		return
	center_x, center_y = _compute_selection_center(atoms)
	# compute offsets and apply moves
	items_and_offsets = []
	for atom_item in atoms:
		model = atom_item.atom_model
		old_x = model.x
		old_y = model.y
		new_x = center_x + (old_x - center_x) * scale_x
		new_y = center_y + (old_y - center_y) * scale_y
		dx = new_x - old_x
		dy = new_y - old_y
		# apply the move immediately
		model.x = new_x
		model.y = new_y
		items_and_offsets.append((atom_item, dx, dy))
	# push undoable command (first redo is skipped since already moved)
	cmd = bkchem_qt.undo.commands.MoveAtomsCommand(
		items_and_offsets, "Scale"
	)
	app.document.undo_stack.push(cmd)
	app.statusBar().showMessage("Scale applied", 2000)


#============================================
def handle_configure(app) -> None:
	"""Open the properties dialog for a single selected atom or bond.

	If exactly one atom is selected, opens AtomDialog. If exactly
	one bond is selected, opens BondDialog. Otherwise shows a
	status message explaining the selection requirement.

	Args:
		app: The main application object.
	"""
	atoms = app.document.selected_atoms
	bonds = app.document.selected_bonds
	# exactly one atom, no bonds
	if len(atoms) == 1 and len(bonds) == 0:
		import bkchem_qt.dialogs.atom_dialog
		bkchem_qt.dialogs.atom_dialog.AtomDialog.edit_atom(
			atoms[0].atom_model, app
		)
		return
	# exactly one bond, no atoms
	if len(bonds) == 1 and len(atoms) == 0:
		import bkchem_qt.dialogs.bond_dialog
		bkchem_qt.dialogs.bond_dialog.BondDialog.edit_bond(
			bonds[0].bond_model, app
		)
		return
	app.statusBar().showMessage(
		"Select a single atom or bond to configure", 3000
	)


#============================================
def register_object_actions(registry, app) -> None:
	"""Register all Object menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# predicate: true when the document has selected items
	def has_selection():
		return app.document.has_selection

	# scale selected objects
	registry.register(MenuAction(
		id='object.scale',
		label_key='Scale',
		help_key='Scale selected objects',
		accelerator=None,
		handler=lambda: handle_scale(app),
		enabled_when=has_selection,
	))

	# lift selected objects to the top of the stack
	registry.register(MenuAction(
		id='object.bring_to_front',
		label_key='Bring to front',
		help_key='Lift selected objects to the top of the stack',
		accelerator=None,
		handler=lambda: handle_bring_to_front(app),
		enabled_when=has_selection,
	))

	# lower selected objects to the bottom of the stack
	registry.register(MenuAction(
		id='object.send_back',
		label_key='Send back',
		help_key='Lower the selected objects to the bottom of the stack',
		accelerator=None,
		handler=lambda: handle_send_back(app),
		enabled_when=has_selection,
	))

	# reverse the ordering of selected objects on the stack
	registry.register(MenuAction(
		id='object.swap_on_stack',
		label_key='Swap on stack',
		help_key=(
			'Reverse the ordering of the selected objects on the stack'
		),
		accelerator=None,
		handler=lambda: handle_swap_on_stack(app),
		enabled_when=has_selection,
	))

	# create a vertical-axis reflection of selected objects
	registry.register(MenuAction(
		id='object.vertical_mirror',
		label_key='Vertical mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection'
			' axis is the common vertical axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: handle_vertical_mirror(app),
		enabled_when=has_selection,
	))

	# create a horizontal-axis reflection of selected objects
	registry.register(MenuAction(
		id='object.horizontal_mirror',
		label_key='Horizontal mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection'
			' axis is the common horizontal axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: handle_horizontal_mirror(app),
		enabled_when=has_selection,
	))

	# configure properties of the selected object
	registry.register(MenuAction(
		id='object.configure',
		label_key='Configure',
		help_key=(
			'Set the properties of the object, such as color,'
			' font size etc.'
		),
		accelerator=None,
		handler=lambda: handle_configure(app),
		enabled_when=has_selection,
	))
