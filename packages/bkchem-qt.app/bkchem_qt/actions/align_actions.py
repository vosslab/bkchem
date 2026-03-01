"""Align menu action registrations for BKChem-Qt."""

# local repo modules
import bkchem_qt.undo.commands
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _align_selection(app, direction: str) -> None:
	"""Align selected atoms grouped by parent molecule.

	Groups selected atoms by their parent MoleculeModel, computes the
	bounding box for each group, determines the alignment target from
	the aggregate bounds, then moves each group so its bounding-box
	edge (or center) matches the target. Pushes a MoveAtomsCommand
	onto the undo stack so the operation is reversible.

	Args:
		app: The main BKChem-Qt application object.
		direction: One of 'top', 'bottom', 'left', 'right',
			'center_h', or 'center_v'.
	"""
	atoms = app.document.selected_atoms
	if len(atoms) < 2:
		app.statusBar().showMessage(
			"Select at least 2 atoms to align", 3000
		)
		return

	# group selected atom items by parent molecule
	groups = {}
	for atom_item in atoms:
		mol = app.document._find_molecule_for_atom(atom_item.atom_model)
		# use molecule identity as key, fall back to atom identity
		mol_key = id(mol) if mol is not None else id(atom_item)
		if mol_key not in groups:
			groups[mol_key] = []
		groups[mol_key].append(atom_item)

	if len(groups) < 2:
		app.statusBar().showMessage(
			"Select items from at least 2 molecules to align", 3000
		)
		return

	# compute bounding box for each molecule group
	group_bounds = {}
	for mol_key, group_atoms in groups.items():
		xs = [a.atom_model.x for a in group_atoms]
		ys = [a.atom_model.y for a in group_atoms]
		group_bounds[mol_key] = {
			'top': min(ys),
			'bottom': max(ys),
			'left': min(xs),
			'right': max(xs),
			'center_x': (min(xs) + max(xs)) / 2.0,
			'center_y': (min(ys) + max(ys)) / 2.0,
		}

	# compute alignment target from aggregate bounds
	if direction == 'top':
		target = min(b['top'] for b in group_bounds.values())
	elif direction == 'bottom':
		target = max(b['bottom'] for b in group_bounds.values())
	elif direction == 'left':
		target = min(b['left'] for b in group_bounds.values())
	elif direction == 'right':
		target = max(b['right'] for b in group_bounds.values())
	elif direction == 'center_h':
		centers = [b['center_x'] for b in group_bounds.values()]
		target = sum(centers) / len(centers)
	elif direction == 'center_v':
		centers = [b['center_y'] for b in group_bounds.values()]
		target = sum(centers) / len(centers)
	else:
		app.statusBar().showMessage(
			f"Unknown align direction: {direction}", 3000
		)
		return

	# compute per-group offsets and apply immediately
	items_and_offsets = []
	for mol_key, group_atoms in groups.items():
		bounds = group_bounds[mol_key]
		dx = 0.0
		dy = 0.0
		if direction == 'top':
			dy = target - bounds['top']
		elif direction == 'bottom':
			dy = target - bounds['bottom']
		elif direction == 'left':
			dx = target - bounds['left']
		elif direction == 'right':
			dx = target - bounds['right']
		elif direction == 'center_h':
			dx = target - bounds['center_x']
		elif direction == 'center_v':
			dy = target - bounds['center_y']

		# skip groups that are already aligned
		if abs(dx) < 0.001 and abs(dy) < 0.001:
			continue

		# move each atom in the group
		for atom_item in group_atoms:
			atom_item.atom_model.x += dx
			atom_item.atom_model.y += dy
			items_and_offsets.append((atom_item, dx, dy))

	if not items_and_offsets:
		app.statusBar().showMessage("Items already aligned", 3000)
		return

	# push undo command (first redo is skipped because items moved above)
	cmd = bkchem_qt.undo.commands.MoveAtomsCommand(
		items_and_offsets, text=f"Align {direction}",
	)
	app.document.undo_stack.push(cmd)
	app.statusBar().showMessage(f"Aligned {direction}", 2000)


#============================================
def register_align_actions(registry, app) -> None:
	"""Register all Align menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# predicate: true when the document has selected items
	def has_selection():
		return app.document.has_selection

	# align the tops of selected objects
	registry.register(MenuAction(
		id='align.top',
		label_key='Top',
		help_key='Align the tops of selected objects',
		accelerator=None,
		handler=lambda: _align_selection(app, 'top'),
		enabled_when=has_selection,
	))

	# align the bottoms of selected objects
	registry.register(MenuAction(
		id='align.bottom',
		label_key='Bottom',
		help_key='Align the bottoms of selected objects',
		accelerator=None,
		handler=lambda: _align_selection(app, 'bottom'),
		enabled_when=has_selection,
	))

	# align the left sides of selected objects
	registry.register(MenuAction(
		id='align.left',
		label_key='Left',
		help_key='Align the left sides of selected objects',
		accelerator=None,
		handler=lambda: _align_selection(app, 'left'),
		enabled_when=has_selection,
	))

	# align the right sides of selected objects
	registry.register(MenuAction(
		id='align.right',
		label_key='Right',
		help_key='Align the right sides of selected objects',
		accelerator=None,
		handler=lambda: _align_selection(app, 'right'),
		enabled_when=has_selection,
	))

	# align the horizontal centers of selected objects
	registry.register(MenuAction(
		id='align.center_h',
		label_key='Center horizontally',
		help_key='Align the horizontal centers of selected objects',
		accelerator=None,
		handler=lambda: _align_selection(app, 'center_h'),
		enabled_when=has_selection,
	))

	# align the vertical centers of selected objects
	registry.register(MenuAction(
		id='align.center_v',
		label_key='Center vertically',
		help_key='Align the vertical centers of selected objects',
		accelerator=None,
		handler=lambda: _align_selection(app, 'center_v'),
		enabled_when=has_selection,
	))
