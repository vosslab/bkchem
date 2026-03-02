"""Vector graphics mode for rectangles, ovals, and lines."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode

# line width for vector shapes
_DEFAULT_LINE_WIDTH = 1.5
# preview pen style
_PREVIEW_STYLE = PySide6.QtCore.Qt.PenStyle.DashLine


#============================================
class VectorMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for drawing vector graphics shapes.

	Supports drawing rectangles, ovals, and lines on the canvas.
	Click to start a shape, drag to size it, release to finalize.
	The shape type can be switched via submodes.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the vector graphics mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Vector"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		# current shape type: "rectangle", "oval", or "line"
		self._shape_type = "rectangle"
		# drag state
		self._drag_start = None
		self._preview_item = None

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return vector mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		return f"Drag to draw {self._shape_type}"

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Switch the active shape type when a submode is selected.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		# map submode keys to shape types
		shape_map = {
			"rectangle": "rectangle",
			"oval": "oval",
			"line": "line",
		}
		shape = shape_map.get(name, name)
		self._shape_type = shape
		self.status_message.emit(f"Vector: {shape}")

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Start drawing a shape at the click position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self._drag_start = scene_pos

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Update the shape preview during drag.

		Args:
			scene_pos: Current position in scene coordinates.
			event: The mouse event.
		"""
		if self._drag_start is None:
			return
		scene = self._env.scene
		if scene is None:
			return
		# remove old preview
		if self._preview_item is not None:
			scene.removeItem(self._preview_item)
			self._preview_item = None
		# build preview pen
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(80, 80, 80, 150))
		pen.setWidthF(1.0)
		pen.setStyle(_PREVIEW_STYLE)
		# create shape preview
		if self._shape_type == "line":
			self._preview_item = scene.addLine(
				self._drag_start.x(), self._drag_start.y(),
				scene_pos.x(), scene_pos.y(), pen,
			)
		else:
			rect = _make_rect(self._drag_start, scene_pos)
			if self._shape_type == "oval":
				self._preview_item = scene.addEllipse(rect, pen)
			else:
				self._preview_item = scene.addRect(rect, pen)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Finalize the shape and add it to the scene.

		Args:
			scene_pos: End position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._env.scene
		if scene is None:
			self._drag_start = None
			return
		# remove preview
		if self._preview_item is not None:
			scene.removeItem(self._preview_item)
			self._preview_item = None
		if self._drag_start is None:
			return
		# build the final shape pen
		pen = PySide6.QtGui.QPen(PySide6.QtCore.Qt.GlobalColor.black)
		pen.setWidthF(_DEFAULT_LINE_WIDTH)
		# minimum drag distance
		dx = abs(scene_pos.x() - self._drag_start.x())
		dy = abs(scene_pos.y() - self._drag_start.y())
		if dx < 5.0 and dy < 5.0:
			self._drag_start = None
			return
		# create the final shape item
		item = None
		if self._shape_type == "line":
			item = scene.addLine(
				self._drag_start.x(), self._drag_start.y(),
				scene_pos.x(), scene_pos.y(), pen,
			)
		else:
			rect = _make_rect(self._drag_start, scene_pos)
			if self._shape_type == "oval":
				item = scene.addEllipse(rect, pen)
			else:
				item = scene.addRect(rect, pen)
		# make the item selectable and movable
		if item is not None:
			item.setFlag(
				PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
				True,
			)
			item.setFlag(
				PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
				True,
			)
		self._drag_start = None
		self.status_message.emit(f"Placed {self._shape_type}")

	#============================================
	def deactivate(self) -> None:
		"""Clean up preview when leaving vector mode."""
		if self._preview_item is not None:
			scene = self._env.scene
			if scene is not None:
				scene.removeItem(self._preview_item)
			self._preview_item = None
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
