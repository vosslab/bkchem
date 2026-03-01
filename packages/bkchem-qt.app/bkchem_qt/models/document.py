"""Document model holding molecules and providing undo support."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui

# local repo modules
import bkchem_qt.models.molecule_model


#============================================
class Document(PySide6.QtCore.QObject):
	"""Top-level document that holds molecules, file state, and undo stack.

	The Document is the single authority for the object stack (molecules
	and other drawable objects), undo history, and file state. Selection
	state lives in the QGraphicsScene but Document provides query helpers
	that give modes chemistry-aware access to the selection.

	Emits ``modified_changed`` whenever the dirty flag transitions so the
	window title can show an unsaved-changes indicator. Emits
	``selection_changed`` after selection queries detect a change.

	Args:
		parent: Optional parent QObject.
	"""

	# emitted when the dirty flag changes
	modified_changed = PySide6.QtCore.Signal(bool)
	# emitted when the selection changes (forwarded from scene)
	selection_changed = PySide6.QtCore.Signal()

	#============================================
	def __init__(self, parent: PySide6.QtCore.QObject = None):
		"""Initialize an empty document.

		Args:
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._molecules = []
		self._file_path = None
		self._dirty = False
		self._undo_stack = PySide6.QtGui.QUndoStack(self)
		# scene reference for selection queries (set by MainWindow)
		self._scene = None

	# ------------------------------------------------------------------
	# Properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def molecules(self) -> list:
		"""Return the list of MoleculeModel instances in this document.

		Returns:
			List of MoleculeModel objects.
		"""
		return list(self._molecules)

	#============================================
	@property
	def file_path(self):
		"""Absolute path to the saved file, or None if unsaved.

		Returns:
			str or None.
		"""
		return self._file_path

	#============================================
	@file_path.setter
	def file_path(self, value):
		self._file_path = value

	#============================================
	@property
	def dirty(self) -> bool:
		"""Whether the document has unsaved changes."""
		return self._dirty

	#============================================
	@dirty.setter
	def dirty(self, value: bool):
		new_value = bool(value)
		if new_value != self._dirty:
			self._dirty = new_value
			self.modified_changed.emit(self._dirty)

	#============================================
	@property
	def undo_stack(self) -> PySide6.QtGui.QUndoStack:
		"""The QUndoStack for undo/redo operations.

		Returns:
			QUndoStack instance owned by this document.
		"""
		return self._undo_stack

	# ------------------------------------------------------------------
	# Scene wiring
	# ------------------------------------------------------------------

	#============================================
	def set_scene(self, scene) -> None:
		"""Wire the scene for selection change forwarding.

		Connects the scene's selectionChanged signal so Document can
		re-emit it as ``selection_changed`` for menu predicates and
		mode state updates.

		Args:
			scene: QGraphicsScene instance (ChemScene).
		"""
		if self._scene is not None:
			# disconnect old scene
			self._scene.selectionChanged.disconnect(self._on_scene_selection_changed)
		self._scene = scene
		if scene is not None:
			scene.selectionChanged.connect(self._on_scene_selection_changed)

	#============================================
	def _on_scene_selection_changed(self) -> None:
		"""Forward scene selection changes as a Document signal."""
		self.selection_changed.emit()

	# ------------------------------------------------------------------
	# Selection queries
	# ------------------------------------------------------------------

	#============================================
	@property
	def selected_atoms(self) -> list:
		"""Return selected AtomItems from the scene.

		Returns:
			List of AtomItem instances currently selected.
		"""
		import bkchem_qt.canvas.items.atom_item
		if self._scene is None:
			return []
		return [item for item in self._scene.selectedItems()
				if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)]

	#============================================
	@property
	def selected_bonds(self) -> list:
		"""Return selected BondItems from the scene.

		Returns:
			List of BondItem instances currently selected.
		"""
		import bkchem_qt.canvas.items.bond_item
		if self._scene is None:
			return []
		return [item for item in self._scene.selectedItems()
				if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)]

	#============================================
	@property
	def selected_mols(self) -> list:
		"""Return MoleculeModels that have at least one selected atom.

		Deduplicates so each molecule appears at most once.

		Returns:
			List of MoleculeModel instances with selected content.
		"""
		seen = set()
		result = []
		for atom_item in self.selected_atoms:
			mol = self._find_molecule_for_atom(atom_item.atom_model)
			if mol is not None and id(mol) not in seen:
				seen.add(id(mol))
				result.append(mol)
		return result

	#============================================
	@property
	def has_selection(self) -> bool:
		"""Whether any interactive item is selected."""
		if self._scene is None:
			return False
		return bool(self._scene.selectedItems())

	#============================================
	def selected_to_unique_top_levels(self) -> tuple:
		"""Dedup selected items to their parent containers.

		Port of Tk paper_selection.selected_to_unique_top_levels().
		Maps atoms and bonds to their parent MoleculeModel, removing
		duplicates. Returns (unique_top_levels, is_unique) where
		is_unique is True when each container had at most one selected
		child.

		Returns:
			Tuple of (list of unique top-level objects, bool is_unique).
		"""
		filtrate = []
		unique = True
		seen_ids = set()
		for atom_item in self.selected_atoms:
			mol = self._find_molecule_for_atom(atom_item.atom_model)
			if mol is not None:
				if id(mol) not in seen_ids:
					seen_ids.add(id(mol))
					filtrate.append(mol)
				else:
					unique = False
		for bond_item in self.selected_bonds:
			mol = self._find_molecule_for_bond(bond_item.bond_model)
			if mol is not None:
				if id(mol) not in seen_ids:
					seen_ids.add(id(mol))
					filtrate.append(mol)
				else:
					unique = False
		return (filtrate, unique)

	#============================================
	@property
	def one_mol_selected(self) -> bool:
		"""Whether exactly one molecule has selected content."""
		return len(self.selected_mols) == 1

	#============================================
	def bonds_to_update(self) -> list:
		"""Return bonds adjacent to selected atoms that need redraw.

		Port of Tk paper_selection.bonds_to_update(). Finds bonds
		connected to any selected atom, excluding bonds that are
		themselves selected.

		Returns:
			List of BondModel instances needing update.
		"""
		import bkchem_qt.canvas.items.bond_item
		if self._scene is None:
			return []
		# collect selected atom models
		selected_atom_models = set()
		for atom_item in self.selected_atoms:
			selected_atom_models.add(id(atom_item.atom_model))
		# collect selected bond models to exclude
		selected_bond_models = set()
		for bond_item in self.selected_bonds:
			selected_bond_models.add(id(bond_item.bond_model))
		# find bonds connected to selected atoms but not themselves selected
		result = []
		for item in self._scene.items():
			if not isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				continue
			bm = item.bond_model
			if id(bm) in selected_bond_models:
				continue
			if bm.atom1 is not None and id(bm.atom1) in selected_atom_models:
				result.append(bm)
			elif bm.atom2 is not None and id(bm.atom2) in selected_atom_models:
				result.append(bm)
		return result

	#============================================
	def atoms_to_update(self) -> list:
		"""Return atoms adjacent to selected bonds that need redraw.

		Port of Tk paper_selection.atoms_to_update(). Finds atoms
		connected to any selected bond, excluding atoms that are
		themselves selected.

		Returns:
			List of AtomModel instances needing update.
		"""
		# collect selected atom models to exclude
		selected_atom_models = set()
		for atom_item in self.selected_atoms:
			selected_atom_models.add(id(atom_item.atom_model))
		# find atoms connected to selected bonds but not themselves selected
		seen = set()
		result = []
		for bond_item in self.selected_bonds:
			bm = bond_item.bond_model
			for atom_model in (bm.atom1, bm.atom2):
				if atom_model is None:
					continue
				if id(atom_model) in selected_atom_models:
					continue
				if id(atom_model) not in seen:
					seen.add(id(atom_model))
					result.append(atom_model)
		return result

	#============================================
	def _find_molecule_for_atom(self, atom_model):
		"""Find the MoleculeModel containing a given AtomModel.

		Args:
			atom_model: AtomModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		for mol_model in self._molecules:
			if atom_model in mol_model.atoms:
				return mol_model
		return None

	#============================================
	def _find_molecule_for_bond(self, bond_model):
		"""Find the MoleculeModel containing a given BondModel.

		Args:
			bond_model: BondModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		for mol_model in self._molecules:
			if bond_model in mol_model.bonds:
				return mol_model
		return None

	# ------------------------------------------------------------------
	# Mutation
	# ------------------------------------------------------------------

	#============================================
	def add_molecule(self, mol_model: bkchem_qt.models.molecule_model.MoleculeModel):
		"""Add a molecule to the document.

		Args:
			mol_model: MoleculeModel to add.
		"""
		self._molecules.append(mol_model)
		self.dirty = True

	#============================================
	def remove_molecule(self, mol_model: bkchem_qt.models.molecule_model.MoleculeModel):
		"""Remove a molecule from the document.

		Args:
			mol_model: MoleculeModel to remove.

		Raises:
			ValueError: If the molecule is not in the document.
		"""
		self._molecules.remove(mol_model)
		self.dirty = True

	#============================================
	def clear(self):
		"""Remove all molecules and reset the document to empty state."""
		self._molecules.clear()
		self._undo_stack.clear()
		self.dirty = False

	# ------------------------------------------------------------------
	# File info
	# ------------------------------------------------------------------

	#============================================
	def title(self) -> str:
		"""Return a display title for the document.

		Uses the filename from ``file_path`` if available, otherwise
		returns 'Untitled'.

		Returns:
			Title string.
		"""
		if self._file_path:
			basename = os.path.basename(self._file_path)
			return basename
		return "Untitled"

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		n_mols = len(self._molecules)
		title = self.title()
		return f"Document('{title}', {n_mols} molecules)"
