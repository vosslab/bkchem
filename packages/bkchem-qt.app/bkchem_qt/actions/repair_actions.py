"""Repair menu action registrations for BKChem-Qt."""

# Standard Library
import math

# local repo modules
from oasa import coords_generator
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.config.geometry_units
import bkchem_qt.undo.commands
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _resolve_target_bond_length_pt(app) -> float:
	"""Resolve canonical target bond length in scene-space points."""
	scene = getattr(app, "_scene", None)
	if scene is not None and hasattr(scene, "grid_spacing_pt"):
		return float(scene.grid_spacing_pt)
	return bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT


#============================================
def _get_target_mols_and_items(app) -> list:
	"""Get molecules to operate on and their AtomItem mappings.

	Uses selected molecules if any, otherwise all molecules in the
	document. Builds a mapping from AtomModel identity to the
	corresponding AtomItem in the scene for each molecule.

	Args:
		app: The main BKChem-Qt application object.

	Returns:
		List of (MoleculeModel, {AtomModel_id: AtomItem}) pairs.
		Empty list when no molecules are available.
	"""
	mols = app.document.selected_mols
	if not mols:
		mols = app.document.molecules
	if not mols:
		return []
	# build AtomModel id -> AtomItem mapping from scene
	atom_item_map = {}
	for item in app._scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			atom_item_map[id(item.atom_model)] = item
	result = []
	for mol in mols:
		mol_items = {}
		for am in mol.atoms:
			ai = atom_item_map.get(id(am))
			if ai is not None:
				mol_items[id(am)] = ai
		result.append((mol, mol_items))
	return result


#============================================
def _build_adjacency(mol_model) -> dict:
	"""Build an adjacency dict from bond endpoint pairs.

	Maps each AtomModel id to a list of neighbor AtomModels connected
	by bonds in the molecule.

	Args:
		mol_model: MoleculeModel to extract adjacency from.

	Returns:
		Dict mapping AtomModel id -> list of neighbor AtomModel objects.
	"""
	adj = {}
	for am in mol_model.atoms:
		adj[id(am)] = []
	for bm in mol_model.bonds:
		a1 = bm.atom1
		a2 = bm.atom2
		if a1 is None or a2 is None:
			continue
		adj.setdefault(id(a1), []).append(a2)
		adj.setdefault(id(a2), []).append(a1)
	return adj


#============================================
def _apply_moves_with_undo(app, items_and_offsets, description) -> None:
	"""Push a MoveAtomsCommand to the undo stack for a batch of atom moves.

	The atoms have already been moved in-place before this call. The
	command records the offsets so undo can reverse them.

	Args:
		app: The main BKChem-Qt application object.
		items_and_offsets: List of (AtomItem, dx, dy) tuples.
		description: Text label for the undo history entry.
	"""
	if not items_and_offsets:
		return
	cmd = bkchem_qt.undo.commands.MoveAtomsCommand(
		items_and_offsets, text=description,
	)
	# first redo is skipped because atoms are already at new positions
	app.document.undo_stack.push(cmd)


#============================================
def _handle_clean_geometry(app) -> None:
	"""Full coordinate regeneration via OASA for target molecules.

	Converts each molecule to an OASA molecule, calls the OASA
	coordinate generator to recompute 2D layout, then maps the
	fresh coordinates back to the existing AtomModels.

	Args:
		app: The main BKChem-Qt application object.
	"""
	targets = _get_target_mols_and_items(app)
	if not targets:
		app.statusBar().showMessage("No molecules to clean", 3000)
		return
	all_offsets = []
	target_bond_length_pt = _resolve_target_bond_length_pt(app)
	for mol_model, mol_items in targets:
		if not mol_model.atoms:
			continue
		# convert to OASA molecule
		try:
			oasa_mol = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(
				mol_model
			)
			# regenerate coordinates with force=1
			coords_generator.calculate_coords(
				oasa_mol, bond_length=1.0, force=1
			)
		except Exception as exc:
			app.statusBar().showMessage(
				f"Clean geometry failed: {exc}", 5000
			)
			return
		# convert back to get fresh coordinates with proper scaling
		temp_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
			oasa_mol, bond_length_pt=target_bond_length_pt,
		)
		# map fresh coords back by atom index (vertex order preserved)
		orig_atoms = mol_model.atoms
		temp_atoms = temp_model.atoms
		count = min(len(orig_atoms), len(temp_atoms))
		for i in range(count):
			orig_am = orig_atoms[i]
			temp_am = temp_atoms[i]
			old_x = orig_am.x
			old_y = orig_am.y
			new_x = temp_am.x
			new_y = temp_am.y
			dx = new_x - old_x
			dy = new_y - old_y
			# apply the move in-place
			orig_am.x = new_x
			orig_am.y = new_y
			# record offset for undo
			atom_item = mol_items.get(id(orig_am))
			if atom_item is not None:
				all_offsets.append((atom_item, dx, dy))
	_apply_moves_with_undo(app, all_offsets, "Clean up geometry")
	n_atoms = len(all_offsets)
	app.statusBar().showMessage(
		f"Regenerated coordinates for {n_atoms} atoms", 3000
	)


#============================================
def _handle_normalize_bond_lengths(app) -> None:
	"""Scale each molecule so its average bond length matches the target.

	Computes the current average bond length, determines a uniform
	scale factor, and repositions every atom relative to the molecule
	centroid.

	Args:
		app: The main BKChem-Qt application object.
	"""
	targets = _get_target_mols_and_items(app)
	if not targets:
		app.statusBar().showMessage("No molecules to normalize", 3000)
		return
	all_offsets = []
	target_bond_length_pt = _resolve_target_bond_length_pt(app)
	for mol_model, mol_items in targets:
		bonds = mol_model.bonds
		atoms = mol_model.atoms
		if not bonds or not atoms:
			continue
		# compute current average bond length
		lengths = []
		for bm in bonds:
			a1 = bm.atom1
			a2 = bm.atom2
			if a1 is None or a2 is None:
				continue
			dx = a1.x - a2.x
			dy = a1.y - a2.y
			length = math.sqrt(dx * dx + dy * dy)
			lengths.append(length)
		if not lengths:
			continue
		avg_length = sum(lengths) / len(lengths)
		# skip if already close to target
		if avg_length < 1e-6:
			continue
		scale = target_bond_length_pt / avg_length
		# skip if scale is trivially close to 1.0
		if abs(scale - 1.0) < 0.001:
			continue
		# compute centroid
		cx = sum(am.x for am in atoms) / len(atoms)
		cy = sum(am.y for am in atoms) / len(atoms)
		# scale each atom position relative to centroid
		for am in atoms:
			old_x = am.x
			old_y = am.y
			new_x = cx + (old_x - cx) * scale
			new_y = cy + (old_y - cy) * scale
			dx = new_x - old_x
			dy = new_y - old_y
			am.x = new_x
			am.y = new_y
			atom_item = mol_items.get(id(am))
			if atom_item is not None:
				all_offsets.append((atom_item, dx, dy))
	_apply_moves_with_undo(app, all_offsets, "Normalize bond lengths")
	n_atoms = len(all_offsets)
	app.statusBar().showMessage(
		f"Normalized bond lengths for {n_atoms} atoms", 3000
	)


#============================================
def _handle_snap_to_hex_grid(app) -> None:
	"""Move every atom in target molecules to the nearest hex grid point.

	Uses the scene's ``snap_to_grid()`` method to find the closest
	hex grid vertex for each atom position.

	Args:
		app: The main BKChem-Qt application object.
	"""
	targets = _get_target_mols_and_items(app)
	if not targets:
		app.statusBar().showMessage("No molecules to snap", 3000)
		return
	all_offsets = []
	for mol_model, mol_items in targets:
		for am in mol_model.atoms:
			old_x = am.x
			old_y = am.y
			snapped_x, snapped_y = app._scene.snap_to_grid(old_x, old_y)
			dx = snapped_x - old_x
			dy = snapped_y - old_y
			# skip atoms already on the grid
			if abs(dx) < 0.01 and abs(dy) < 0.01:
				continue
			am.x = snapped_x
			am.y = snapped_y
			atom_item = mol_items.get(id(am))
			if atom_item is not None:
				all_offsets.append((atom_item, dx, dy))
	_apply_moves_with_undo(app, all_offsets, "Snap to hex grid")
	n_atoms = len(all_offsets)
	app.statusBar().showMessage(
		f"Snapped {n_atoms} atoms to hex grid", 3000
	)


#============================================
def _snap_angle_to_multiple(angle_rad, step_deg) -> float:
	"""Snap an angle in radians to the nearest multiple of step_deg.

	Args:
		angle_rad: Angle in radians.
		step_deg: Step size in degrees to snap to.

	Returns:
		Snapped angle in radians.
	"""
	step_rad = math.radians(step_deg)
	snapped = round(angle_rad / step_rad) * step_rad
	return snapped


#============================================
def _handle_normalize_bond_angles(app) -> None:
	"""Snap each bond angle to the nearest 30-degree multiple.

	For every bond, computes the angle from atom1 to atom2, snaps
	it to the nearest 30-degree direction, and adjusts atom2's
	position to match while preserving the original bond length.

	Args:
		app: The main BKChem-Qt application object.
	"""
	targets = _get_target_mols_and_items(app)
	if not targets:
		app.statusBar().showMessage("No molecules to normalize", 3000)
		return
	all_offsets = []
	# track which atoms have already been moved to avoid double-moves
	moved_atoms = set()
	for mol_model, mol_items in targets:
		adj = _build_adjacency(mol_model)
		# process atoms with more neighbors first (ring junctions, etc.)
		atoms_by_degree = sorted(
			mol_model.atoms,
			key=lambda am: len(adj.get(id(am), [])),
			reverse=True,
		)
		for am in atoms_by_degree:
			neighbors = adj.get(id(am), [])
			if len(neighbors) < 1:
				continue
			for nbr in neighbors:
				# only move the neighbor if it has not been pinned
				if id(nbr) in moved_atoms:
					continue
				dx = nbr.x - am.x
				dy = nbr.y - am.y
				length = math.sqrt(dx * dx + dy * dy)
				if length < 1e-6:
					continue
				# compute current angle and snap to 30-degree
				angle = math.atan2(dy, dx)
				snapped_angle = _snap_angle_to_multiple(angle, 30.0)
				# compute new neighbor position
				new_x = am.x + length * math.cos(snapped_angle)
				new_y = am.y + length * math.sin(snapped_angle)
				offset_x = new_x - nbr.x
				offset_y = new_y - nbr.y
				# skip if already close
				if abs(offset_x) < 0.01 and abs(offset_y) < 0.01:
					continue
				nbr.x = new_x
				nbr.y = new_y
				atom_item = mol_items.get(id(nbr))
				if atom_item is not None:
					all_offsets.append((atom_item, offset_x, offset_y))
			# mark this atom as anchored so it is not moved later
			moved_atoms.add(id(am))
	_apply_moves_with_undo(app, all_offsets, "Normalize bond angles")
	n_atoms = len(all_offsets)
	app.statusBar().showMessage(
		f"Normalized bond angles for {n_atoms} atoms", 3000
	)


#============================================
def _handle_normalize_rings(app) -> None:
	"""Reshape each ring in target molecules to a regular polygon.

	Uses OASA cycle detection to find rings, then computes regular
	polygon positions centered at the ring centroid and maps the ring
	atoms to the nearest polygon vertex to minimize total displacement.

	Args:
		app: The main BKChem-Qt application object.
	"""
	targets = _get_target_mols_and_items(app)
	if not targets:
		app.statusBar().showMessage("No molecules to normalize", 3000)
		return
	all_offsets = []
	for mol_model, mol_items in targets:
		if not mol_model.contains_cycle():
			continue
		# get OASA cycles (lists of OASA vertex objects)
		oasa_cycles = mol_model.get_smallest_independent_cycles()
		if not oasa_cycles:
			continue
		# build OASA vertex id -> AtomModel mapping
		oasa_to_am = {}
		for am in mol_model.atoms:
			oasa_to_am[id(am._chem_atom)] = am
		# process each ring cycle
		for cycle_verts in oasa_cycles:
			# map OASA vertices to AtomModels
			ring_atoms = []
			for v in cycle_verts:
				am = oasa_to_am.get(id(v))
				if am is not None:
					ring_atoms.append(am)
			n = len(ring_atoms)
			if n < 3:
				continue
			# compute centroid of current ring positions
			cx = sum(am.x for am in ring_atoms) / n
			cy = sum(am.y for am in ring_atoms) / n
			# compute average radius from centroid
			radii = []
			for am in ring_atoms:
				dx = am.x - cx
				dy = am.y - cy
				radii.append(math.sqrt(dx * dx + dy * dy))
			avg_radius = sum(radii) / len(radii)
			if avg_radius < 1e-6:
				continue
			# compute the starting angle from centroid to first atom
			# to preserve overall ring orientation
			start_angle = math.atan2(
				ring_atoms[0].y - cy, ring_atoms[0].x - cx
			)
			# generate regular polygon vertices
			polygon_pts = []
			for i in range(n):
				angle = start_angle + (2.0 * math.pi * i) / n
				px = cx + avg_radius * math.cos(angle)
				py = cy + avg_radius * math.sin(angle)
				polygon_pts.append((px, py))
			# assign ring atoms to polygon points in order
			# (ring atoms from OASA are already in cycle traversal order)
			for i, am in enumerate(ring_atoms):
				new_x, new_y = polygon_pts[i]
				dx = new_x - am.x
				dy = new_y - am.y
				if abs(dx) < 0.01 and abs(dy) < 0.01:
					continue
				am.x = new_x
				am.y = new_y
				atom_item = mol_items.get(id(am))
				if atom_item is not None:
					all_offsets.append((atom_item, dx, dy))
	_apply_moves_with_undo(app, all_offsets, "Normalize ring structures")
	n_atoms = len(all_offsets)
	app.statusBar().showMessage(
		f"Normalized rings for {n_atoms} atoms", 3000
	)


#============================================
def _handle_straighten_bonds(app) -> None:
	"""Snap terminal bonds to the nearest 30-degree direction.

	For each terminal atom (degree 1), computes the angle from its
	single neighbor to the terminal atom, snaps to the nearest
	30-degree multiple, and repositions the terminal atom while
	preserving bond length.

	Args:
		app: The main BKChem-Qt application object.
	"""
	targets = _get_target_mols_and_items(app)
	if not targets:
		app.statusBar().showMessage("No molecules to straighten", 3000)
		return
	all_offsets = []
	for mol_model, mol_items in targets:
		adj = _build_adjacency(mol_model)
		for am in mol_model.atoms:
			neighbors = adj.get(id(am), [])
			# only process terminal atoms (degree 1)
			if len(neighbors) != 1:
				continue
			anchor = neighbors[0]
			# compute vector from anchor to terminal atom
			dx = am.x - anchor.x
			dy = am.y - anchor.y
			length = math.sqrt(dx * dx + dy * dy)
			if length < 1e-6:
				continue
			# compute angle and snap to 30-degree
			angle = math.atan2(dy, dx)
			snapped_angle = _snap_angle_to_multiple(angle, 30.0)
			# compute new terminal atom position
			new_x = anchor.x + length * math.cos(snapped_angle)
			new_y = anchor.y + length * math.sin(snapped_angle)
			offset_x = new_x - am.x
			offset_y = new_y - am.y
			# skip if already aligned
			if abs(offset_x) < 0.01 and abs(offset_y) < 0.01:
				continue
			am.x = new_x
			am.y = new_y
			atom_item = mol_items.get(id(am))
			if atom_item is not None:
				all_offsets.append((atom_item, offset_x, offset_y))
	_apply_moves_with_undo(app, all_offsets, "Straighten bonds")
	n_atoms = len(all_offsets)
	app.statusBar().showMessage(
		f"Straightened {n_atoms} terminal bonds", 3000
	)


#============================================
def register_repair_actions(registry, app) -> None:
	"""Register all Repair menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# predicate: true when the document has any molecules to repair
	def has_molecules():
		"""Check whether the document contains any molecules."""
		return bool(app.document.molecules)

	# set all bonds to the standard bond length
	registry.register(MenuAction(
		id='repair.normalize_bond_lengths',
		label_key='Normalize bond lengths',
		help_key='Set all bonds to the standard bond length',
		accelerator=None,
		handler=lambda: _handle_normalize_bond_lengths(app),
		enabled_when=has_molecules,
	))

	# move every atom to the nearest hex grid point
	registry.register(MenuAction(
		id='repair.snap_to_hex_grid',
		label_key='Snap to hex grid',
		help_key='Move every atom to the nearest hex grid point',
		accelerator=None,
		handler=lambda: _handle_snap_to_hex_grid(app),
		enabled_when=has_molecules,
	))

	# round bond angles to nearest 60-degree multiple
	registry.register(MenuAction(
		id='repair.normalize_bond_angles',
		label_key='Normalize bond angles',
		help_key='Round bond angles to nearest 30-degree multiple',
		accelerator=None,
		handler=lambda: _handle_normalize_bond_angles(app),
		enabled_when=has_molecules,
	))

	# reshape each ring to a regular polygon
	registry.register(MenuAction(
		id='repair.normalize_rings',
		label_key='Normalize ring structures',
		help_key='Reshape each ring to a regular polygon',
		accelerator=None,
		handler=lambda: _handle_normalize_rings(app),
		enabled_when=has_molecules,
	))

	# snap terminal bonds to nearest 30-degree direction
	registry.register(MenuAction(
		id='repair.straighten_bonds',
		label_key='Straighten bonds',
		help_key='Snap terminal bonds to nearest 30-degree direction',
		accelerator=None,
		handler=lambda: _handle_straighten_bonds(app),
		enabled_when=has_molecules,
	))

	# full coordinate regeneration for selected or all molecules
	registry.register(MenuAction(
		id='repair.clean_geometry',
		label_key='Clean up geometry',
		help_key='Full coordinate regeneration for selected or all molecules',
		accelerator=None,
		handler=lambda: _handle_clean_geometry(app),
		enabled_when=has_molecules,
	))
