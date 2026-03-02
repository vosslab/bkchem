"""Dockable property panel for editing atom and bond properties."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item


# bond type codes and their human-readable labels
_BOND_TYPE_CODES = ["n", "w", "h", "b", "d", "q"]
_BOND_TYPE_LABELS = [
	"n (normal)",
	"w (wedge)",
	"h (hatch)",
	"b (bold)",
	"d (dash)",
	"q (wavy)",
]


#============================================
class PropertyDock(PySide6.QtWidgets.QDockWidget):
	"""Dock widget showing editable properties for the selected scene item.

	Displays atom fields (symbol, charge, show label) when an AtomItem is
	selected, bond fields (order, type) when a BondItem is selected, or a
	brief document summary when nothing is selected. Uses a QStackedWidget
	to switch between the three panels.

	Args:
		document: The Document model for counting molecules and atoms.
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, document, parent: PySide6.QtWidgets.QWidget = None):
		"""Initialize the property dock with atom, bond, and info panels.

		Args:
			document: Document model for document info display.
			parent: Optional parent widget.
		"""
		super().__init__("Properties", parent)
		self._document = document
		# prevent the dock from being closed by the user
		self.setFeatures(
			PySide6.QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
			| PySide6.QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
		)
		# track the currently displayed item to avoid redundant updates
		self._current_item = None
		# guard flag to suppress feedback loops during programmatic updates
		self._updating = False
		# build all three panel pages
		self._stack = PySide6.QtWidgets.QStackedWidget()
		self._build_info_panel()
		self._build_atom_panel()
		self._build_bond_panel()
		self.setWidget(self._stack)
		# set a reasonable fixed width so the dock does not consume too much space
		self.setMinimumWidth(200)
		self.setMaximumWidth(300)

	# ------------------------------------------------------------------
	# Panel construction
	# ------------------------------------------------------------------

	#============================================
	def _build_info_panel(self) -> None:
		"""Build the document info panel shown when nothing is selected."""
		panel = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QVBoxLayout(panel)
		layout.setContentsMargins(8, 8, 8, 8)
		# document summary label
		self._info_label = PySide6.QtWidgets.QLabel("No selection")
		self._info_label.setWordWrap(True)
		self._info_label.setAlignment(PySide6.QtCore.Qt.AlignmentFlag.AlignTop)
		layout.addWidget(self._info_label)
		layout.addStretch()
		# page index 0
		self._stack.addWidget(panel)

	#============================================
	def _build_atom_panel(self) -> None:
		"""Build the atom property editing panel."""
		panel = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QFormLayout(panel)
		layout.setContentsMargins(8, 8, 8, 8)
		# section heading
		heading = PySide6.QtWidgets.QLabel("Atom Properties")
		heading.setStyleSheet("font-weight: bold;")
		layout.addRow(heading)
		# symbol field
		self._atom_symbol_edit = PySide6.QtWidgets.QLineEdit()
		self._atom_symbol_edit.setMaxLength(3)
		self._atom_symbol_edit.setToolTip("Element symbol (e.g. C, N, O)")
		self._atom_symbol_edit.editingFinished.connect(self._on_atom_symbol_changed)
		layout.addRow("Symbol:", self._atom_symbol_edit)
		# charge spin box
		self._atom_charge_spin = PySide6.QtWidgets.QSpinBox()
		self._atom_charge_spin.setRange(-9, 9)
		self._atom_charge_spin.setToolTip("Formal charge")
		self._atom_charge_spin.valueChanged.connect(self._on_atom_charge_changed)
		layout.addRow("Charge:", self._atom_charge_spin)
		# show label checkbox
		self._atom_show_check = PySide6.QtWidgets.QCheckBox("Show label")
		self._atom_show_check.setToolTip("Show or hide the atom symbol on the canvas")
		self._atom_show_check.stateChanged.connect(self._on_atom_show_changed)
		layout.addRow(self._atom_show_check)
		# page index 1
		self._stack.addWidget(panel)

	#============================================
	def _build_bond_panel(self) -> None:
		"""Build the bond property editing panel."""
		panel = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QFormLayout(panel)
		layout.setContentsMargins(8, 8, 8, 8)
		# section heading
		heading = PySide6.QtWidgets.QLabel("Bond Properties")
		heading.setStyleSheet("font-weight: bold;")
		layout.addRow(heading)
		# order combo box
		self._bond_order_combo = PySide6.QtWidgets.QComboBox()
		self._bond_order_combo.addItem("1 (single)", 1)
		self._bond_order_combo.addItem("2 (double)", 2)
		self._bond_order_combo.addItem("3 (triple)", 3)
		self._bond_order_combo.setToolTip("Bond order")
		self._bond_order_combo.currentIndexChanged.connect(
			self._on_bond_order_changed
		)
		layout.addRow("Order:", self._bond_order_combo)
		# type combo box
		self._bond_type_combo = PySide6.QtWidgets.QComboBox()
		for i, label in enumerate(_BOND_TYPE_LABELS):
			self._bond_type_combo.addItem(label, _BOND_TYPE_CODES[i])
		self._bond_type_combo.setToolTip("Bond type")
		self._bond_type_combo.currentIndexChanged.connect(
			self._on_bond_type_changed
		)
		layout.addRow("Type:", self._bond_type_combo)
		# page index 2
		self._stack.addWidget(panel)

	# ------------------------------------------------------------------
	# Public update slot
	# ------------------------------------------------------------------

	#============================================
	def update_from_selection(self) -> None:
		"""Update the dock contents based on the current scene selection.

		Reads the scene's selectedItems list and shows the appropriate
		panel. When a single AtomItem or BondItem is selected, its
		properties are loaded into the editing widgets. Otherwise,
		the info panel is displayed with a document summary.
		"""
		scene = self._document._scene
		if scene is None:
			self._show_info_panel()
			return
		selected = scene.selectedItems()
		# filter to atoms and bonds only
		atoms = [
			item for item in selected
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		bonds = [
			item for item in selected
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
		]
		# single atom selected
		if len(atoms) == 1 and len(bonds) == 0:
			self._show_atom_panel(atoms[0])
			return
		# single bond selected
		if len(bonds) == 1 and len(atoms) == 0:
			self._show_bond_panel(bonds[0])
			return
		# nothing selected or multi-selection: show document info
		self._current_item = None
		self._show_info_panel()

	# ------------------------------------------------------------------
	# Panel switching helpers
	# ------------------------------------------------------------------

	#============================================
	def _show_info_panel(self) -> None:
		"""Switch to the document info panel and update the summary text."""
		self._current_item = None
		# count molecules and total atoms across the document
		molecules = self._document.molecules
		n_molecules = len(molecules)
		n_atoms = sum(len(mol.atoms) for mol in molecules)
		if n_molecules == 0:
			text = "Empty document"
		else:
			text = f"{n_molecules} molecule(s), {n_atoms} atom(s)"
		self._info_label.setText(text)
		self._stack.setCurrentIndex(0)

	#============================================
	def _show_atom_panel(self, atom_item) -> None:
		"""Switch to the atom panel and populate fields from the AtomItem.

		Args:
			atom_item: The selected AtomItem whose model drives the fields.
		"""
		self._current_item = atom_item
		model = atom_item.atom_model
		# set guard flag to suppress change callbacks during population
		self._updating = True
		self._atom_symbol_edit.setText(model.symbol)
		self._atom_charge_spin.setValue(model.charge)
		self._atom_show_check.setChecked(model.show)
		self._updating = False
		self._stack.setCurrentIndex(1)

	#============================================
	def _show_bond_panel(self, bond_item) -> None:
		"""Switch to the bond panel and populate fields from the BondItem.

		Args:
			bond_item: The selected BondItem whose model drives the fields.
		"""
		self._current_item = bond_item
		model = bond_item.bond_model
		# set guard flag to suppress change callbacks during population
		self._updating = True
		# find the combo index matching the current bond order
		order_index = self._bond_order_combo.findData(model.order)
		if order_index >= 0:
			self._bond_order_combo.setCurrentIndex(order_index)
		# find the combo index matching the current bond type
		type_index = self._bond_type_combo.findData(model.type)
		if type_index >= 0:
			self._bond_type_combo.setCurrentIndex(type_index)
		self._updating = False
		self._stack.setCurrentIndex(2)

	# ------------------------------------------------------------------
	# Widget change callbacks
	# ------------------------------------------------------------------

	#============================================
	def _on_atom_symbol_changed(self) -> None:
		"""Apply the edited symbol to the selected atom model."""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.atom_item.AtomItem,
		):
			return
		new_symbol = self._atom_symbol_edit.text().strip()
		if not new_symbol:
			return
		self._current_item.atom_model.symbol = new_symbol

	#============================================
	def _on_atom_charge_changed(self, value: int) -> None:
		"""Apply the edited charge to the selected atom model.

		Args:
			value: New charge value from the spin box.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.atom_item.AtomItem,
		):
			return
		self._current_item.atom_model.charge = value

	#============================================
	def _on_atom_show_changed(self, state: int) -> None:
		"""Apply the show/hide toggle to the selected atom model.

		Args:
			state: Qt check state integer.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.atom_item.AtomItem,
		):
			return
		checked = state == PySide6.QtCore.Qt.CheckState.Checked.value
		self._current_item.atom_model.show = checked

	#============================================
	def _on_bond_order_changed(self, index: int) -> None:
		"""Apply the edited order to the selected bond model.

		Args:
			index: New combo box index.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.bond_item.BondItem,
		):
			return
		order = self._bond_order_combo.itemData(index)
		if order is not None:
			self._current_item.bond_model.order = order

	#============================================
	def _on_bond_type_changed(self, index: int) -> None:
		"""Apply the edited type to the selected bond model.

		Args:
			index: New combo box index.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.bond_item.BondItem,
		):
			return
		bond_type = self._bond_type_combo.itemData(index)
		if bond_type is not None:
			self._current_item.bond_model.type = bond_type
