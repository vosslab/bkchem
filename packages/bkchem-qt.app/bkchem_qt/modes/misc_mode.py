"""Miscellaneous mode for atom numbering and special annotations."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item

# font for numbering labels
_NUMBER_FONT_FAMILY = "Arial"
_NUMBER_FONT_SIZE = 9
_NUMBER_OFFSET_X = 8.0
_NUMBER_OFFSET_Y = -12.0


#============================================
class MiscMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for miscellaneous operations like atom numbering.

	Provides access to less common drawing operations. The active
	submode determines the operation:
	- number: click atoms in sequence to assign numbers
	- clear-numbers: click to clear numbering from atoms

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the miscellaneous mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Misc"
		self._cursor = PySide6.QtCore.Qt.CursorShape.PointingHandCursor
		# active operation (from submode selection)
		self._operation = "number"
		# running counter for atom numbering
		self._next_number = 1

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return misc mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		if self._operation == "number":
			return f"Click atoms to number them (next: {self._next_number})"
		if self._operation == "clear-numbers":
			return "Click an atom to clear its number"
		return "Click to apply operation"

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Switch the active operation when a submode is selected.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		self._operation = name
		# reset counter when switching to number mode
		if name == "number":
			self._next_number = 1
		self.status_message.emit(self.status_hint)

	#============================================
	def activate(self) -> None:
		"""Reset numbering counter on mode activation."""
		self._next_number = 1
		super().activate()

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Apply the active operation at the click position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		item = self._item_at(scene_pos)
		if self._operation == "number":
			self._number_atom(item, scene_pos)
		elif self._operation == "clear-numbers":
			self._clear_number(item)

	#============================================
	def _number_atom(self, item, scene_pos) -> None:
		"""Assign a sequential number to the clicked atom.

		If an AtomItem is under the cursor, attaches a small number
		label as a child item. If clicking empty space, does nothing.

		Args:
			item: The item at the click position (or None).
			scene_pos: The click position in scene coordinates.
		"""
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		# remove any existing number label on this atom
		_remove_number_label(item)
		# create a number label as a child of the atom item
		number_text = str(self._next_number)
		font = PySide6.QtGui.QFont(_NUMBER_FONT_FAMILY, _NUMBER_FONT_SIZE)
		label = PySide6.QtWidgets.QGraphicsSimpleTextItem(number_text, item)
		label.setFont(font)
		label.setBrush(PySide6.QtGui.QBrush(
			PySide6.QtGui.QColor(0, 0, 200)
		))
		label.setPos(_NUMBER_OFFSET_X, _NUMBER_OFFSET_Y)
		# tag the label for later identification
		label.setData(0, "atom_number_label")
		self._next_number += 1
		self.status_message.emit(self.status_hint)

	#============================================
	def _clear_number(self, item) -> None:
		"""Remove the number label from the clicked atom.

		Args:
			item: The item at the click position (or None).
		"""
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		removed = _remove_number_label(item)
		if removed:
			self.status_message.emit("Number cleared")
		else:
			self.status_message.emit("No number to clear")


#============================================
def _remove_number_label(atom_item) -> bool:
	"""Remove any atom_number_label child from an atom item.

	Args:
		atom_item: The AtomItem to clean.

	Returns:
		True if a label was removed, False otherwise.
	"""
	for child in atom_item.childItems():
		if child.data(0) == "atom_number_label":
			scene = child.scene()
			if scene is not None:
				scene.removeItem(child)
			return True
	return False
