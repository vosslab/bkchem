"""Bracket insertion mode for drawing brackets around molecule fragments."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item

# bracket rendering constants
_BRACKET_LINE_WIDTH = 2.0
_BRACKET_MARGIN = 6.0
_BRACKET_HOOK_LENGTH = 8.0


#============================================
class BracketMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for inserting brackets around selected items.

	Click to place square brackets around all currently selected items.
	If nothing is selected, click-drag to define a rectangular bracket
	region manually. Commonly used for polymer repeat units and
	complex ions.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the bracket mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Bracket"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		# drag state for manual bracket placement
		self._drag_start = None
		self._preview_rect = None

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return bracket mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		return "Click to bracket selection | Drag to draw bracket region"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Start bracket placement.

		If items are selected, immediately places brackets around them.
		Otherwise begins a drag to define a bracket region.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._env.scene
		if scene is None:
			return
		# check for selected items first
		selected = scene.selectedItems()
		atom_items = [
			item for item in selected
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		if atom_items:
			# bracket around selected atoms
			_place_brackets_around_items(scene, atom_items)
			self.status_message.emit("Brackets placed around selection")
			return
		# start drag for manual bracket region
		self._drag_start = scene_pos

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Update the bracket preview rectangle during drag.

		Args:
			scene_pos: Current position in scene coordinates.
			event: The mouse event.
		"""
		if self._drag_start is None:
			return
		scene = self._env.scene
		if scene is None:
			return
		# remove previous preview
		if self._preview_rect is not None:
			scene.removeItem(self._preview_rect)
			self._preview_rect = None
		# draw preview rectangle
		rect = _make_rect(self._drag_start, scene_pos)
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(100, 100, 100, 128))
		pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
		pen.setWidthF(1.0)
		self._preview_rect = scene.addRect(rect, pen)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Finalize bracket placement from drag region.

		Args:
			scene_pos: End position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._env.scene
		if scene is None:
			self._drag_start = None
			return
		# remove preview
		if self._preview_rect is not None:
			scene.removeItem(self._preview_rect)
			self._preview_rect = None
		if self._drag_start is not None:
			rect = _make_rect(self._drag_start, scene_pos)
			# only create brackets if the drag region is large enough
			if rect.width() > 10.0 and rect.height() > 10.0:
				_place_bracket_pair(scene, rect)
				self.status_message.emit("Brackets placed")
		self._drag_start = None

	#============================================
	def deactivate(self) -> None:
		"""Clean up preview when leaving bracket mode."""
		if self._preview_rect is not None:
			scene = self._env.scene
			if scene is not None:
				scene.removeItem(self._preview_rect)
			self._preview_rect = None
		self._drag_start = None
		super().deactivate()


#============================================
def _make_rect(
		p1: PySide6.QtCore.QPointF,
		p2: PySide6.QtCore.QPointF) -> PySide6.QtCore.QRectF:
	"""Build a QRectF from two corner points.

	Args:
		p1: First corner point.
		p2: Second corner point.

	Returns:
		Normalized QRectF enclosing both points.
	"""
	x1 = min(p1.x(), p2.x())
	y1 = min(p1.y(), p2.y())
	x2 = max(p1.x(), p2.x())
	y2 = max(p1.y(), p2.y())
	return PySide6.QtCore.QRectF(x1, y1, x2 - x1, y2 - y1)


#============================================
def _place_brackets_around_items(scene, items: list) -> None:
	"""Place bracket pair around the bounding box of given items.

	Args:
		scene: The QGraphicsScene.
		items: List of QGraphicsItems to bracket.
	"""
	if not items:
		return
	# compute bounding rect of all items
	first_rect = items[0].sceneBoundingRect()
	union_rect = PySide6.QtCore.QRectF(first_rect)
	for item in items[1:]:
		union_rect = union_rect.united(item.sceneBoundingRect())
	# expand by margin
	union_rect.adjust(
		-_BRACKET_MARGIN, -_BRACKET_MARGIN,
		_BRACKET_MARGIN, _BRACKET_MARGIN,
	)
	_place_bracket_pair(scene, union_rect)


#============================================
def _place_bracket_pair(scene, rect: PySide6.QtCore.QRectF) -> None:
	"""Draw left and right square brackets around a rectangle.

	Args:
		scene: The QGraphicsScene to add bracket items to.
		rect: The rectangle to bracket.
	"""
	pen = PySide6.QtGui.QPen(PySide6.QtCore.Qt.GlobalColor.black)
	pen.setWidthF(_BRACKET_LINE_WIDTH)
	pen.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.SquareCap)
	# left bracket: [ shape
	left_path = PySide6.QtGui.QPainterPath()
	left_path.moveTo(rect.left() + _BRACKET_HOOK_LENGTH, rect.top())
	left_path.lineTo(rect.left(), rect.top())
	left_path.lineTo(rect.left(), rect.bottom())
	left_path.lineTo(rect.left() + _BRACKET_HOOK_LENGTH, rect.bottom())
	left_item = scene.addPath(left_path, pen)
	left_item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
		True,
	)
	left_item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
		True,
	)
	# right bracket: ] shape
	right_path = PySide6.QtGui.QPainterPath()
	right_path.moveTo(rect.right() - _BRACKET_HOOK_LENGTH, rect.top())
	right_path.lineTo(rect.right(), rect.top())
	right_path.lineTo(rect.right(), rect.bottom())
	right_path.lineTo(rect.right() - _BRACKET_HOOK_LENGTH, rect.bottom())
	right_item = scene.addPath(right_path, pen)
	right_item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
		True,
	)
	right_item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
		True,
	)
