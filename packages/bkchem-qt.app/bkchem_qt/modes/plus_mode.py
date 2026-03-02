"""Plus symbol mode for placing + between molecules in reaction schemes."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode

# default font for the plus symbol
_PLUS_FONT_FAMILY = "Arial"
_PLUS_FONT_SIZE = 18


#============================================
class PlusMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for placing plus symbols between molecules.

	Click on the canvas to insert a + symbol at the clicked
	position, commonly used in reaction scheme diagrams.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the plus symbol mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Plus"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return plus mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		return "Click to place + symbol"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Place a plus symbol at the click position.

		Creates a QGraphicsTextItem with a centered + character
		at the scene position. The item is selectable and movable.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._env.scene
		if scene is None:
			return
		# create a text item with the plus character
		font = PySide6.QtGui.QFont(_PLUS_FONT_FAMILY, _PLUS_FONT_SIZE)
		font.setBold(True)
		text_item = scene.addText("+", font)
		# center the text on the click position
		bounding = text_item.boundingRect()
		offset_x = bounding.width() / 2.0
		offset_y = bounding.height() / 2.0
		text_item.setPos(
			scene_pos.x() - offset_x,
			scene_pos.y() - offset_y,
		)
		# make selectable and movable
		text_item.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
			True,
		)
		text_item.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
			True,
		)
		text_item.setDefaultTextColor(PySide6.QtCore.Qt.GlobalColor.black)
		self.status_message.emit("Placed + symbol")
