"""Edit menu action registrations for BKChem-Qt."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtSvg
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _selected_to_svg(app) -> None:
	"""Copy selected items as SVG to the system clipboard.

	Renders only the selected AtomItem and BondItem graphics to an
	SVG string via QSvgGenerator, then places the SVG data on the
	clipboard as image/svg+xml MIME type.

	Args:
		app: MainWindow instance.
	"""
	scene = app._scene
	selected = scene.selectedItems()
	if not selected:
		app.statusBar().showMessage("Nothing selected", 3000)
		return
	# compute bounding rect of selected items with padding
	bounds = PySide6.QtCore.QRectF()
	for item in selected:
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			bounds = bounds.united(item.sceneBoundingRect())
		elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			bounds = bounds.united(item.sceneBoundingRect())
	if bounds.isEmpty():
		app.statusBar().showMessage("Selection bounds empty", 3000)
		return
	# add padding
	padding = 10.0
	bounds.adjust(-padding, -padding, padding, padding)
	# render to SVG buffer
	svg_buffer = PySide6.QtCore.QBuffer()
	svg_buffer.open(PySide6.QtCore.QIODevice.OpenModeFlag.WriteOnly)
	generator = PySide6.QtSvg.QSvgGenerator()
	generator.setOutputDevice(svg_buffer)
	generator.setSize(PySide6.QtCore.QSize(
		int(bounds.width()), int(bounds.height()),
	))
	generator.setViewBox(bounds)
	generator.setTitle("BKChem-Qt Selection")
	# temporarily hide non-selected items
	hidden_items = []
	for item in scene.items():
		if item not in selected and item.isVisible():
			item.setVisible(False)
			hidden_items.append(item)
	# render the scene (only visible/selected items)
	from PySide6.QtGui import QPainter
	painter = QPainter(generator)
	scene.render(painter, source=bounds)
	painter.end()
	svg_buffer.close()
	# restore hidden items
	for item in hidden_items:
		item.setVisible(True)
	# place SVG on clipboard
	svg_bytes = svg_buffer.data()
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	mime_data = PySide6.QtCore.QMimeData()
	mime_data.setData("image/svg+xml", svg_bytes)
	mime_data.setText(bytes(svg_bytes).decode("utf-8"))
	clipboard.setMimeData(mime_data)
	app.statusBar().showMessage("Selection copied as SVG", 3000)


#============================================
def register_edit_actions(registry, app) -> None:
	"""Register all Edit menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# undo last change
	registry.register(MenuAction(
		id='edit.undo',
		label_key='Undo',
		help_key='Revert the last change made',
		accelerator='(C-z)',
		handler=app.on_undo,
		enabled_when=None,
	))

	# redo last undo
	registry.register(MenuAction(
		id='edit.redo',
		label_key='Redo',
		help_key='Revert the last undo action',
		accelerator='(C-S-z)',
		handler=app.on_redo,
		enabled_when=None,
	))

	# predicate: true when the document has selected items
	def has_selection():
		return app.document.has_selection

	# predicate: true when the undo stack can undo
	def can_undo():
		import shiboken6
		stack = app.document.undo_stack
		if not shiboken6.isValid(stack):
			return False
		return stack.canUndo()

	# predicate: true when the undo stack can redo
	def can_redo():
		import shiboken6
		stack = app.document.undo_stack
		if not shiboken6.isValid(stack):
			return False
		return stack.canRedo()

	# update undo/redo predicates
	registry.get('edit.undo').enabled_when = can_undo
	registry.get('edit.redo').enabled_when = can_redo

	# cut selected objects to clipboard
	registry.register(MenuAction(
		id='edit.cut',
		label_key='Cut',
		help_key='Copy the selected objects to clipboard and delete them',
		accelerator='(C-k)',
		handler=app.on_cut,
		enabled_when=has_selection,
	))

	# copy selected objects to clipboard
	registry.register(MenuAction(
		id='edit.copy',
		label_key='Copy',
		help_key='Copy the selected objects to clipboard',
		accelerator='(C-c)',
		handler=app.on_copy,
		enabled_when=has_selection,
	))

	# paste clipboard contents onto paper
	registry.register(MenuAction(
		id='edit.paste',
		label_key='Paste',
		help_key='Paste the content of clipboard to current paper',
		accelerator='(C-v)',
		handler=app.on_paste,
		enabled_when=None,
	))

	# copy selection as SVG to system clipboard
	registry.register(MenuAction(
		id='edit.selected_to_svg',
		label_key='Copy as SVG',
		help_key='Create SVG for the selected objects and place it to the system clipboard',
		accelerator=None,
		handler=lambda: _selected_to_svg(app),
		enabled_when=has_selection,
	))

	# select all objects on the paper
	registry.register(MenuAction(
		id='edit.select_all',
		label_key='Select All',
		help_key='Select everything on the paper',
		accelerator='(C-S-a)',
		handler=app.on_select_all,
		enabled_when=None,
	))
