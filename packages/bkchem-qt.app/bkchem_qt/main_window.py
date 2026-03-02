"""Main application window for BKChem-Qt."""

# Standard Library
import pathlib

# PIP3 modules
import yaml
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.scene
import bkchem_qt.canvas.view
import bkchem_qt.config.geometry_units
import bkchem_qt.config.preferences
import bkchem_qt.widgets.status_bar
import bkchem_qt.widgets.mode_toolbar
import bkchem_qt.widgets.edit_ribbon
import bkchem_qt.widgets.zoom_controls
import bkchem_qt.widgets.submode_ribbon
import bkchem_qt.widgets.icon_loader
import bkchem_qt.modes.config
import bkchem_qt.modes.mode_manager
import bkchem_qt.modes.template_mode
import bkchem_qt.modes.biotemplate_mode
import bkchem_qt.modes.arrow_mode
import bkchem_qt.modes.text_mode
import bkchem_qt.modes.mark_mode
import bkchem_qt.modes.atom_mode
import bkchem_qt.modes.rotate_mode
import bkchem_qt.modes.bondalign_mode
import bkchem_qt.modes.bracket_mode
import bkchem_qt.modes.vector_mode
import bkchem_qt.modes.repair_mode
import bkchem_qt.modes.plus_mode
import bkchem_qt.modes.misc_mode
import bkchem_qt.modes.file_actions_mode
import bkchem_qt.actions.file_actions
import bkchem_qt.actions.context_menu
import bkchem_qt.io.cdml_io
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.dialogs.about_dialog
import bkchem_qt.dialogs.preferences_dialog
import bkchem_qt.dialogs.theme_chooser_dialog
import bkchem_qt.models.document
import bkchem_qt.io.export
import bkchem_qt.themes.palettes
import bkchem_qt.themes.theme_loader
import bkchem_qt.canvas.items.render_ops_painter

# path to modes.yaml in the shared bkchem_data directory
_MODES_YAML_PATH = (
	pathlib.Path(__file__).resolve().parent.parent
	/ "bkchem_data" / "modes.yaml"
)


#============================================
class MainWindow(PySide6.QtWidgets.QMainWindow):
	"""Main application window with menus, canvas, toolbar, and status bar.

	Args:
		theme_manager: ThemeManager instance for toggling themes.
	"""

	#============================================
	def __init__(self, theme_manager, parent: PySide6.QtWidgets.QWidget = None):
		"""Initialize the main window with all UI components.

		Args:
			theme_manager: ThemeManager instance for theme toggling.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self._theme_manager = theme_manager
		self._prefs = bkchem_qt.config.preferences.Preferences.instance()
		self._document = bkchem_qt.models.document.Document(self)

		self.setWindowTitle(self.tr("BKChem-Qt"))
		style = PySide6.QtWidgets.QApplication.style()
		window_icon = style.standardIcon(
			PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileIcon
		)
		if not window_icon.isNull():
			app = PySide6.QtWidgets.QApplication.instance()
			if app is not None:
				app.setWindowIcon(window_icon)
			self.setWindowIcon(window_icon)
		self.resize(1280, 800)

		# build the UI components
		self._setup_canvas()
		self._setup_mode_system()
		self._setup_menus()
		self._setup_toolbars()
		self._setup_status_bar()
		self._connect_signals()
		self._apply_geometry_preferences()
		self._apply_view_preferences()

	#============================================
	@property
	def document(self):
		"""The active document."""
		return self._document

	#============================================
	@property
	def scene(self):
		"""The active graphics scene."""
		return self._scene

	#============================================
	@property
	def view(self):
		"""The active graphics view."""
		return self._view

	#============================================
	def _setup_canvas(self) -> None:
		"""Create the scene, view, and tab widget for the central area."""
		theme = self._theme_manager.current_theme
		bond_length_pt = bkchem_qt.config.geometry_units.resolve_bond_length_pt(
			self._prefs
		)
		grid_snap_enabled = bool(self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_SNAP_ENABLED,
			True,
		))
		self._scene = bkchem_qt.canvas.scene.ChemScene(
			parent=self,
			theme_name=theme,
			grid_spacing_pt=bond_length_pt,
			grid_snap_enabled=grid_snap_enabled,
		)
		self._view = bkchem_qt.canvas.view.ChemView(self._scene, parent=self)
		# wire the document so modes can access undo stack and molecules
		self._view.set_document(self._document)
		# wire scene into document for selection query forwarding
		self._document.set_scene(self._scene)

		# set initial viewport background from YAML theme
		surround = bkchem_qt.themes.theme_loader.get_canvas_surround(theme)
		self._view.set_background_color(surround)

		# set default chemistry line color from YAML theme
		chem_colors = bkchem_qt.themes.theme_loader.get_chemistry_colors(theme)
		bkchem_qt.canvas.items.render_ops_painter.set_default_color(
			chem_colors["default_line"]
		)
		# set default area color for atom label background masking
		bkchem_qt.canvas.items.render_ops_painter.set_default_area_color(
			chem_colors["default_area"]
		)
		# set canvas interaction colors from YAML theme
		canvas_colors = bkchem_qt.themes.theme_loader.get_canvas_colors(theme)
		bkchem_qt.canvas.items.render_ops_painter.set_canvas_colors(canvas_colors)
		# set charge mark colors from YAML theme
		bkchem_qt.canvas.items.render_ops_painter.set_charge_colors({
			"plus": chem_colors["charge_plus"],
			"minus": chem_colors["charge_minus"],
		})
		# set the light theme sentinel for dark mode color remapping
		light_chem = bkchem_qt.themes.theme_loader.get_chemistry_colors("light")
		bkchem_qt.canvas.items.render_ops_painter.set_light_default_line(
			light_chem["default_line"]
		)

		# wrap the view in a tab widget for multi-document support
		self._tab_widget = PySide6.QtWidgets.QTabWidget(self)
		self._tab_widget.addTab(self._view, self.tr("Untitled"))
		self.setCentralWidget(self._tab_widget)

	#============================================
	def _setup_mode_system(self) -> None:
		"""Create and register all interaction modes."""
		self._mode_manager = bkchem_qt.modes.mode_manager.ModeManager(
			self._view, parent=self
		)
		# register file actions mode (before edit/draw in toolbar order)
		self._mode_manager.register_mode(
			"file_actions",
			bkchem_qt.modes.file_actions_mode.FileActionsMode(
				self._view, main_window=self
			),
		)
		# register additional modes beyond the default edit/draw
		self._mode_manager.register_mode(
			"template",
			bkchem_qt.modes.template_mode.TemplateMode(self._view),
		)
		self._mode_manager.register_mode(
			"biotemplate",
			bkchem_qt.modes.biotemplate_mode.BioTemplateMode(self._view),
		)
		self._mode_manager.register_mode(
			"arrow",
			bkchem_qt.modes.arrow_mode.ArrowMode(self._view),
		)
		self._mode_manager.register_mode(
			"text",
			bkchem_qt.modes.text_mode.TextMode(self._view),
		)
		self._mode_manager.register_mode(
			"rotate",
			bkchem_qt.modes.rotate_mode.RotateMode(self._view),
		)
		self._mode_manager.register_mode(
			"mark",
			bkchem_qt.modes.mark_mode.MarkMode(self._view),
		)
		self._mode_manager.register_mode(
			"atom",
			bkchem_qt.modes.atom_mode.AtomMode(self._view),
		)
		self._mode_manager.register_mode(
			"align",
			bkchem_qt.modes.bondalign_mode.BondAlignMode(self._view),
		)
		self._mode_manager.register_mode(
			"bracket",
			bkchem_qt.modes.bracket_mode.BracketMode(self._view),
		)
		self._mode_manager.register_mode(
			"vector",
			bkchem_qt.modes.vector_mode.VectorMode(self._view),
		)
		self._mode_manager.register_mode(
			"repair",
			bkchem_qt.modes.repair_mode.RepairMode(self._view),
		)
		self._mode_manager.register_mode(
			"plus",
			bkchem_qt.modes.plus_mode.PlusMode(self._view),
		)
		self._mode_manager.register_mode(
			"misc",
			bkchem_qt.modes.misc_mode.MiscMode(self._view),
		)
		# connect the mode manager to the view for event dispatch
		self._view.set_mode_manager(self._mode_manager)
		# inject YAML submode data into each registered mode
		self._inject_submodes_from_yaml()

	#============================================
	def _inject_submodes_from_yaml(self) -> None:
		"""Parse modes.yaml and inject submode data into registered modes.

		For each registered mode, looks up its definition in modes.yaml
		and parses the submodes section. The parsed data is set on the
		mode object's attributes so the SubModeRibbon can render them.
		"""
		if not _MODES_YAML_PATH.is_file():
			return
		with open(_MODES_YAML_PATH, "r") as fh:
			modes_config = yaml.safe_load(fh) or {}
		modes_defs = modes_config.get("modes", {})

		for mode_name in self._mode_manager.mode_names():
			mode = self._mode_manager._modes[mode_name]
			# find the YAML definition for this mode
			# try direct key match first, then alias lookup
			yaml_key = mode_name
			if yaml_key == "align":
				yaml_key = "bondalign"
			cfg = modes_defs.get(yaml_key, {})
			if not cfg:
				continue

			# set show_edit_pool from YAML
			mode.show_edit_pool = cfg.get('show_edit_pool', False)

			# dynamic modes populate their own submodes at init time;
			# skip YAML injection if the mode already has submode data
			if cfg.get('dynamic') and mode.submodes:
				continue

			# parse submode groups from YAML
			parsed = bkchem_qt.modes.config.load_submodes_from_yaml(cfg)
			(submodes, submodes_names, submode_defaults,
				icon_map, group_labels, group_layouts,
				tooltip_map, size_map) = parsed

			mode.submodes = submodes
			mode.submodes_names = submodes_names
			# initialize current submode indices from defaults
			mode.submode = list(submode_defaults)
			mode.icon_map = icon_map
			mode.group_labels = group_labels
			mode.group_layouts = group_layouts
			mode.tooltip_map = tooltip_map
			mode.size_map = size_map

	#============================================
	def _setup_menus(self) -> None:
		"""Create the menu bar from YAML menu structure and action registry."""
		from bkchem_qt.actions.action_registry import register_all_actions
		from bkchem_qt.actions.platform_menu import PlatformMenuAdapter
		from bkchem_qt.actions.menu_builder import MenuBuilder
		# register all per-menu action modules
		self._registry = register_all_actions(self)
		# create the Qt menu adapter wrapping QMenuBar
		self._adapter = PlatformMenuAdapter(self)
		# locate menus.yaml in the shared bkchem_data directory
		yaml_path = str(
			pathlib.Path(__file__).resolve().parent.parent
			/ "bkchem_data" / "menus.yaml"
		)
		# build all menus from YAML structure
		self._menu_builder = MenuBuilder(
			yaml_path, self._registry, self._adapter,
		)
		self._menu_builder.build_menus()
		# populate the Export cascade with export handlers
		export_cascade_label = "Export"
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export SVG...",
			"Export the current document as SVG",
			self._on_export_svg,
		)
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export PNG...",
			"Export the current document as PNG",
			self._on_export_png,
		)
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export PDF...",
			"Export the current document as PDF",
			self._on_export_pdf,
		)
		# backward compatibility aliases for existing code references
		self._action_save = self._adapter.get_action("File", "Save")
		self._action_open = self._adapter.get_action("File", "Open")
		self._action_new = self._adapter.get_action("File", "New")
		self._action_exit = self._adapter.get_action("File", "Quit")
		self._action_undo = self._adapter.get_action("Edit", "Undo")
		self._action_redo = self._adapter.get_action("Edit", "Redo")
		self._action_toggle_theme = self._adapter.get_action("Options", "Theme")
		self._action_about = self._adapter.get_action("Help", "About")
		# grid toggle is not in menus.yaml (it is a view feature)
		# create it as a standalone checkable action
		view_menu = self._adapter.get_menu_component("View")
		if view_menu is not None:
			view_menu.addSeparator()
			self._action_toggle_grid = view_menu.addAction(
				self.tr("Toggle &Grid")
			)
			self._action_toggle_grid.setCheckable(True)
			self._action_toggle_grid.setChecked(self._scene.grid_visible)
			self._action_toggle_grid.triggered.connect(self._on_toggle_grid)
			self._action_toggle_grid_snap = view_menu.addAction(
				self.tr("Snap To &Grid")
			)
			self._action_toggle_grid_snap.setCheckable(True)
			self._action_toggle_grid_snap.setChecked(
				self._scene.grid_snap_enabled
			)
			self._action_toggle_grid_snap.setShortcut(
				PySide6.QtGui.QKeySequence(self.tr("Shift+Ctrl+G"))
			)
			self._action_toggle_grid_snap.triggered.connect(
				self._on_toggle_grid_snap
			)

	#============================================
	def _setup_menus_legacy(self) -> None:
		"""Create the menu bar and all menu actions (legacy manual approach).

		Retained for reference. Use _setup_menus() for the YAML-driven version.
		"""
		menubar = self.menuBar()

		# -- File menu --
		file_menu = menubar.addMenu(self.tr("&File"))

		self._action_new = file_menu.addAction(self.tr("&New"))
		self._action_new.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.New)
		self._action_new.triggered.connect(self._on_new)

		self._action_open = file_menu.addAction(self.tr("&Open..."))
		self._action_open.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Open)
		self._action_open.triggered.connect(self._on_open)

		self._action_save = file_menu.addAction(self.tr("&Save"))
		self._action_save.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Save)
		self._action_save.triggered.connect(self._on_save)

		file_menu.addSeparator()

		# export submenu
		export_menu = file_menu.addMenu(self.tr("&Export"))
		self._action_export_svg = export_menu.addAction(self.tr("Export &SVG..."))
		self._action_export_svg.triggered.connect(self._on_export_svg)
		self._action_export_png = export_menu.addAction(self.tr("Export &PNG..."))
		self._action_export_png.triggered.connect(self._on_export_png)
		self._action_export_pdf = export_menu.addAction(self.tr("Export P&DF..."))
		self._action_export_pdf.triggered.connect(self._on_export_pdf)

		file_menu.addSeparator()

		self._action_exit = file_menu.addAction(self.tr("E&xit"))
		self._action_exit.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Quit)
		self._action_exit.triggered.connect(self.close)

		# -- Edit menu --
		edit_menu = menubar.addMenu(self.tr("&Edit"))

		self._action_undo = edit_menu.addAction(self.tr("&Undo"))
		self._action_undo.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Undo)
		self._action_undo.triggered.connect(self._document.undo_stack.undo)

		self._action_redo = edit_menu.addAction(self.tr("&Redo"))
		self._action_redo.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Redo)
		self._action_redo.triggered.connect(self._document.undo_stack.redo)

		edit_menu.addSeparator()

		self._action_preferences = edit_menu.addAction(self.tr("&Preferences..."))
		self._action_preferences.triggered.connect(self._on_preferences)

		# -- View menu --
		view_menu = menubar.addMenu(self.tr("&View"))

		self._action_toggle_grid = view_menu.addAction(self.tr("Toggle &Grid"))
		self._action_toggle_grid.setCheckable(True)
		self._action_toggle_grid.setChecked(self._scene.grid_visible)
		self._action_toggle_grid.triggered.connect(self._on_toggle_grid)
		self._action_toggle_grid_snap = view_menu.addAction(
			self.tr("Snap To &Grid")
		)
		self._action_toggle_grid_snap.setCheckable(True)
		self._action_toggle_grid_snap.setChecked(
			self._scene.grid_snap_enabled
		)
		self._action_toggle_grid_snap.setShortcut(
			PySide6.QtGui.QKeySequence(self.tr("Shift+Ctrl+G"))
		)
		self._action_toggle_grid_snap.triggered.connect(
			self._on_toggle_grid_snap
		)

		# theme toggle with text reflecting current state
		if self._theme_manager.current_theme == "dark":
			theme_label = self.tr("Switch to &Light Mode")
		else:
			theme_label = self.tr("Switch to &Dark Mode")
		self._action_toggle_theme = view_menu.addAction(theme_label)
		self._action_toggle_theme.triggered.connect(self._on_toggle_theme)

		view_menu.addSeparator()

		self._action_reset_zoom = view_menu.addAction(self.tr("&Reset Zoom"))
		self._action_reset_zoom.setShortcut(
			PySide6.QtGui.QKeySequence(self.tr("Ctrl+0"))
		)
		self._action_reset_zoom.triggered.connect(self._view.reset_zoom)

		# -- Insert menu (stub) --
		menubar.addMenu(self.tr("&Insert"))

		# -- Align menu (stub) --
		menubar.addMenu(self.tr("&Align"))

		# -- Object menu (stub) --
		menubar.addMenu(self.tr("&Object"))

		# -- Chemistry menu (stub) --
		menubar.addMenu(self.tr("C&hemistry"))

		# -- Options menu (stub) --
		menubar.addMenu(self.tr("&Options"))

		# -- Help menu --
		help_menu = menubar.addMenu(self.tr("&Help"))

		self._action_about = help_menu.addAction(self.tr("&About"))
		self._action_about.triggered.connect(self._on_about)

	#============================================
	def _setup_toolbars(self) -> None:
		"""Create the mode toolbar, submode ribbon, and edit ribbon.

		The mode toolbar is the topmost toolbar row, using the
		toolbar_order from modes.yaml for mode sequencing and
		separator placement. Icons are loaded from pixmaps via icon_loader.
		"""
		# validate icon data directory before loading any icons
		bkchem_qt.widgets.icon_loader.validate_icon_paths()
		# sync icon_loader with the current theme
		bkchem_qt.widgets.icon_loader.set_theme(self._theme_manager.current_theme)

		# load modes.yaml for toolbar_order and icon mappings
		if not _MODES_YAML_PATH.is_file():
			raise FileNotFoundError(
				f"modes.yaml not found: {_MODES_YAML_PATH}\n"
				"Check that the bkchem_data symlink is correct."
			)
		with open(_MODES_YAML_PATH, "r") as fh:
			modes_config = yaml.safe_load(fh) or {}

		toolbar_order = modes_config.get("toolbar_order", [])
		modes_defs = modes_config.get("modes", {})

		# mode selection toolbar - topmost horizontal toolbar row
		self._mode_toolbar = bkchem_qt.widgets.mode_toolbar.ModeToolbar(self)
		registered_modes = set(self._mode_manager.mode_names())

		for entry in toolbar_order:
			# separator marker in modes.yaml
			if entry == "---":
				self._mode_toolbar.add_separator_marker()
				continue
			# look up the mode definition for label and icon name
			mode_def = modes_defs.get(entry, {})
			label = mode_def.get("label", mode_def.get("name", entry))
			icon_name = mode_def.get("icon", entry)
			icon = bkchem_qt.widgets.icon_loader.get_icon(icon_name)
			tooltip = label.capitalize()
			# only add if the mode is registered in the mode manager
			# (some yaml modes like biotemplate/usertemplate may not be registered yet)
			if entry in registered_modes:
				self._mode_toolbar.add_mode(entry, label, tooltip=tooltip, icon=icon)
			elif entry == "bondalign" and "align" in registered_modes:
				# modes.yaml calls it bondalign, mode_manager registers it as align
				self._mode_toolbar.add_mode("align", label, tooltip=tooltip, icon=icon)

		self._mode_toolbar.set_active_mode("edit")

		# add separator then Undo/Redo action buttons
		self._mode_toolbar.add_separator_marker()
		self._undo_action = self._mode_toolbar.add_action_button(
			"undo", "Undo", tooltip="Undo last action",
			callback=self._document.undo_stack.undo,
		)
		self._undo_action.setEnabled(self._document.undo_stack.canUndo())
		self._redo_action = self._mode_toolbar.add_action_button(
			"redo", "Redo", tooltip="Redo last undone action",
			callback=self._document.undo_stack.redo,
		)
		self._redo_action.setEnabled(self._document.undo_stack.canRedo())

		# mode toolbar is the topmost toolbar row
		self.addToolBar(self._mode_toolbar)

		# submode ribbon on its own row below mode toolbar
		self.addToolBarBreak()
		self._submode_ribbon = (
			bkchem_qt.widgets.submode_ribbon.SubModeRibbon(self)
		)
		self._submode_toolbar = self.addToolBar(
			self.tr("Submode Ribbon")
		)
		self._submode_toolbar.addWidget(self._submode_ribbon)
		self._submode_toolbar.setMovable(False)

		# edit ribbon on its own row below submode ribbon
		self.addToolBarBreak()
		self._edit_ribbon = bkchem_qt.widgets.edit_ribbon.EditRibbon(self)
		self._edit_ribbon_toolbar = self.addToolBar(
			self.tr("Edit Ribbon")
		)
		self._edit_ribbon_toolbar.addWidget(self._edit_ribbon)
		self._edit_ribbon_toolbar.setMovable(False)

	#============================================
	def _setup_status_bar(self) -> None:
		"""Create and install the status bar with zoom controls."""
		self._status_bar = bkchem_qt.widgets.status_bar.StatusBar(self)
		self.setStatusBar(self._status_bar)
		# add zoom controls as a permanent widget on the right
		self._zoom_controls = bkchem_qt.widgets.zoom_controls.ZoomControls(self)
		self._status_bar.addPermanentWidget(self._zoom_controls)

	#============================================
	def _connect_signals(self) -> None:
		"""Wire all signals between components."""
		# view signals -> status bar
		self._view.mouse_moved.connect(self._status_bar.update_coords)

		# mode toolbar -> mode manager
		self._mode_toolbar.mode_selected.connect(self._mode_manager.set_mode)
		self._mode_manager.mode_changed.connect(self._mode_toolbar.set_active_mode)
		self._mode_manager.mode_changed.connect(self._status_bar.update_mode)
		# mode changes -> rebuild submode ribbon and show/hide edit ribbon
		self._mode_manager.mode_changed.connect(self._on_mode_changed)

		# submode ribbon -> active mode submode selection
		self._submode_ribbon.submode_selected.connect(
			self._on_submode_selected
		)

		# edit ribbon -> draw mode
		self._edit_ribbon.element_changed.connect(self._on_element_changed)
		self._edit_ribbon.bond_order_changed.connect(self._on_bond_order_changed)
		self._edit_ribbon.bond_type_changed.connect(self._on_bond_type_changed)

		# theme changes -> icon refresh and menu text update
		self._theme_manager.theme_changed.connect(self._on_theme_changed)

		# zoom controls -> handler methods
		self._zoom_controls.zoom_in_clicked.connect(self.on_zoom_in)
		self._zoom_controls.zoom_out_clicked.connect(self.on_zoom_out)
		self._zoom_controls.reset_zoom_clicked.connect(self.on_reset_zoom)
		self._zoom_controls.zoom_to_fit_clicked.connect(self.on_zoom_to_fit)
		self._zoom_controls.zoom_to_content_clicked.connect(
			self.on_zoom_to_content
		)
		self._zoom_controls.zoom_slider_changed.connect(
			lambda pct: self._view.set_zoom_percent(float(pct))
		)
		# view zoom -> zoom controls display
		self._view.zoom_changed.connect(
			self._zoom_controls.update_zoom_display
		)

		# selection and undo changes -> update menu enabled states
		self._document.selection_changed.connect(self._update_menu_predicates)
		self._document.undo_stack.canUndoChanged.connect(
			lambda _: self._update_menu_predicates()
		)
		self._document.undo_stack.canRedoChanged.connect(
			lambda _: self._update_menu_predicates()
		)
		# undo/redo toolbar button enabled states
		self._document.undo_stack.canUndoChanged.connect(
			self._undo_action.setEnabled
		)
		self._document.undo_stack.canRedoChanged.connect(
			self._redo_action.setEnabled
		)

		# trigger initial mode visibility (submode ribbon + edit ribbon)
		self._on_mode_changed("edit")

	# ------------------------------------------------------------------
	# Public action methods (used by menu action registrations)
	# ------------------------------------------------------------------

	#============================================
	def on_new(self) -> None:
		"""Public wrapper for toolbar New button."""
		self._on_new()

	#============================================
	def on_open(self) -> None:
		"""Public wrapper for toolbar Open button."""
		self._on_open()

	#============================================
	def on_save(self) -> None:
		"""Public wrapper for toolbar Save button."""
		self._on_save()

	#============================================
	def on_undo(self) -> None:
		"""Public wrapper for toolbar Undo button."""
		self._document.undo_stack.undo()

	#============================================
	def on_redo(self) -> None:
		"""Public wrapper for toolbar Redo button."""
		self._document.undo_stack.redo()

	#============================================
	def on_cut(self) -> None:
		"""Cut selected items: copy to clipboard then delete."""
		if not self._document.has_selection:
			return
		# copy first, then delete
		self.on_copy()
		self._delete_selected()

	#============================================
	def on_copy(self) -> None:
		"""Copy selected molecules to clipboard as CDML."""
		mols = self._document.selected_mols
		if not mols:
			self.statusBar().showMessage(
				self.tr("Nothing selected to copy"), 3000,
			)
			return
		# serialize selected molecules to CDML XML string
		cdml_text = self._selected_mols_to_cdml(mols)
		if not cdml_text:
			return
		# place on clipboard with custom MIME and plain text fallback
		clipboard = PySide6.QtWidgets.QApplication.clipboard()
		mime_data = PySide6.QtCore.QMimeData()
		mime_data.setData(
			"application/x-bkchem-cdml",
			PySide6.QtCore.QByteArray(cdml_text.encode("utf-8")),
		)
		mime_data.setText(cdml_text)
		clipboard.setMimeData(mime_data)
		self.statusBar().showMessage(
			self.tr("Copied %d molecule(s)") % len(mols), 3000,
		)

	#============================================
	def on_paste(self) -> None:
		"""Paste molecules from clipboard CDML data."""
		clipboard = PySide6.QtWidgets.QApplication.clipboard()
		mime_data = clipboard.mimeData()
		cdml_text = None
		# prefer custom MIME type
		if mime_data.hasFormat("application/x-bkchem-cdml"):
			raw = mime_data.data("application/x-bkchem-cdml")
			cdml_text = bytes(raw).decode("utf-8")
		elif mime_data.hasText():
			# try plain text as CDML fallback
			text = mime_data.text()
			if "<cdml" in text or "<molecule" in text:
				cdml_text = text
		if not cdml_text:
			self.statusBar().showMessage(
				self.tr("No CDML data on clipboard"), 3000,
			)
			return
		molecules = bkchem_qt.io.cdml_io.load_cdml_string(cdml_text)
		if not molecules:
			self.statusBar().showMessage(
				self.tr("Could not parse clipboard data"), 3000,
			)
			return
		# offset pasted molecules to avoid exact overlap
		for mol_model in molecules:
			for atom_model in mol_model.atoms:
				atom_model.x = atom_model.x + 20.0
				atom_model.y = atom_model.y + 20.0
		bkchem_qt.actions.file_actions._add_molecules_to_scene(
			self, molecules,
		)
		self.statusBar().showMessage(
			self.tr("Pasted %d molecule(s)") % len(molecules), 3000,
		)

	#============================================
	def on_select_all(self) -> None:
		"""Select all interactive items in the scene."""
		import bkchem_qt.canvas.items.atom_item
		import bkchem_qt.canvas.items.bond_item
		for item in self._scene.items():
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				item.setSelected(True)
			elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				item.setSelected(True)

	#============================================
	def _selected_mols_to_cdml(self, mols: list) -> str:
		"""Serialize a list of MoleculeModels to CDML XML string.

		Args:
			mols: List of MoleculeModel instances to serialize.

		Returns:
			CDML XML string, or empty string on failure.
		"""
		import xml.dom.minidom as dom
		import oasa.cdml_writer
		from bkchem_qt.io.cdml_io import _px_to_cm_text

		xml_doc = dom.Document()
		cdml_el = xml_doc.createElement("cdml")
		cdml_el.setAttribute(
			"version", str(oasa.cdml_writer.DEFAULT_CDML_VERSION),
		)
		cdml_el.setAttribute(
			"xmlns", str(oasa.cdml_writer.CDML_NAMESPACE),
		)
		for mol_model in mols:
			oasa_mol = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(
				mol_model,
			)
			mol_el = oasa.cdml_writer.write_cdml_molecule_element(
				oasa_mol, doc=xml_doc, coord_to_text=_px_to_cm_text,
			)
			cdml_el.appendChild(mol_el)
		xml_doc.appendChild(cdml_el)
		xml_text = xml_doc.toxml(encoding="utf-8").decode("utf-8")
		return xml_text

	#============================================
	def _delete_selected(self) -> None:
		"""Delete all selected atoms and bonds with undo support."""
		import bkchem_qt.canvas.items.atom_item
		import bkchem_qt.canvas.items.bond_item
		import bkchem_qt.undo.commands
		scene = self._scene
		undo_stack = self._document.undo_stack
		# begin undo macro for compound delete
		undo_stack.beginMacro("Cut")
		# delete selected bonds first
		for bond_item in list(self._document.selected_bonds):
			bond_model = bond_item.bond_model
			mol = self._document._find_molecule_for_bond(bond_model)
			if mol is not None:
				cmd = bkchem_qt.undo.commands.RemoveBondCommand(
					scene, mol, bond_model, bond_item,
				)
				undo_stack.push(cmd)
		# delete selected atoms and their remaining connected bonds
		for atom_item in list(self._document.selected_atoms):
			atom_model = atom_item.atom_model
			mol = self._document._find_molecule_for_atom(atom_model)
			if mol is None:
				continue
			# find connected bond items still in scene
			connected = []
			for item in scene.items():
				if isinstance(
					item, bkchem_qt.canvas.items.bond_item.BondItem
				):
					bm = item.bond_model
					if bm.atom1 is atom_model or bm.atom2 is atom_model:
						connected.append((bm, item))
			cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
				scene, mol, atom_model, atom_item, connected,
			)
			undo_stack.push(cmd)
		undo_stack.endMacro()

	#============================================
	def on_zoom_in(self) -> None:
		"""Zoom in on the canvas."""
		self._view.zoom_in()

	#============================================
	def on_zoom_out(self) -> None:
		"""Zoom out on the canvas."""
		self._view.zoom_out()

	#============================================
	def on_reset_zoom(self) -> None:
		"""Reset zoom to 100%."""
		self._view.reset_zoom()

	#============================================
	def on_zoom_to_fit(self) -> None:
		"""Zoom to fit the paper in the viewport."""
		self._view.zoom_to_fit()

	#============================================
	def on_zoom_to_content(self) -> None:
		"""Zoom to fit all drawn content."""
		self._view.zoom_to_content()

	#============================================
	def on_toggle_grid(self) -> None:
		"""Toggle grid visibility from toolbar."""
		current = self._scene.grid_visible
		self._on_toggle_grid(not current)
		# keep the menu action checkmark in sync
		self._action_toggle_grid.setChecked(not current)

	#============================================
	def on_toggle_grid_snap(self) -> None:
		"""Toggle snap-to-grid from toolbar or command."""
		current = self._scene.grid_snap_enabled
		self._on_toggle_grid_snap(not current)
		# keep the menu action checkmark in sync
		if hasattr(self, "_action_toggle_grid_snap"):
			self._action_toggle_grid_snap.setChecked(not current)

	# ------------------------------------------------------------------
	# Mode and submode switching
	# ------------------------------------------------------------------

	#============================================
	def _update_menu_predicates(self) -> None:
		"""Re-evaluate enabled_when predicates on all menu actions.

		Called when selection changes, undo/redo state changes, or
		tab switches to keep menu items in sync with document state.
		"""
		if hasattr(self, '_menu_builder') and self._menu_builder is not None:
			self._menu_builder.update_menu_states(self)

	#============================================
	def _on_mode_changed(self, mode_name: str) -> None:
		"""Handle a mode switch by rebuilding the submode ribbon.

		Shows or hides the edit ribbon based on the mode's
		show_edit_pool flag. Rebuilds the submode ribbon with
		the new mode's submode groups.

		Args:
			mode_name: Name of the newly active mode.
		"""
		mode = self._mode_manager.current_mode
		if mode is None:
			return
		# rebuild the submode ribbon for the new mode
		self._submode_ribbon.rebuild(mode_name)
		# keep submode toolbar always visible at a fixed minimum height
		# to prevent layout jumps when switching between modes
		self._submode_toolbar.setVisible(True)
		self._submode_toolbar.setMinimumHeight(32)
		# show/hide the edit ribbon based on mode's show_edit_pool flag
		show_edit = getattr(mode, 'show_edit_pool', False)
		self._edit_ribbon_toolbar.setVisible(show_edit)

	#============================================
	def _on_submode_selected(self, key: str) -> None:
		"""Forward a submode button click to the active mode.

		Args:
			key: The submode key string selected in the ribbon.
		"""
		mode = self._mode_manager.current_mode
		if mode is not None:
			mode.set_submode(key)

	# ------------------------------------------------------------------
	# Private action handlers
	# ------------------------------------------------------------------

	#============================================
	def _on_new(self) -> None:
		"""Create a new empty document, prompting to save if dirty."""
		# check for unsaved changes before clearing
		if self._document.dirty:
			reply = PySide6.QtWidgets.QMessageBox.question(
				self,
				self.tr("Unsaved Changes"),
				self.tr("Save changes before creating a new document?"),
				(PySide6.QtWidgets.QMessageBox.StandardButton.Save
					| PySide6.QtWidgets.QMessageBox.StandardButton.Discard
					| PySide6.QtWidgets.QMessageBox.StandardButton.Cancel),
				PySide6.QtWidgets.QMessageBox.StandardButton.Save,
			)
			if reply == PySide6.QtWidgets.QMessageBox.StandardButton.Cancel:
				return
			if reply == PySide6.QtWidgets.QMessageBox.StandardButton.Save:
				self._on_save()
		self._scene.clear()
		self._scene._build_paper()
		self._scene._build_grid()
		self._document = bkchem_qt.models.document.Document(self)
		# re-wire so modes access the new document
		self._view.set_document(self._document)
		self._document.set_scene(self._scene)
		# re-wire predicate signals for the new document
		self._document.selection_changed.connect(self._update_menu_predicates)
		self._document.undo_stack.canUndoChanged.connect(
			lambda _: self._update_menu_predicates()
		)
		self._document.undo_stack.canRedoChanged.connect(
			lambda _: self._update_menu_predicates()
		)
		self._tab_widget.setTabText(0, self.tr("Untitled"))

	#============================================
	def _on_open(self) -> None:
		"""Open a file via file dialog."""
		bkchem_qt.actions.file_actions.open_file(self)

	#============================================
	def _on_save(self) -> None:
		"""Save the current document to a CDML file.

		If the document has a file path, saves directly. Otherwise
		prompts for a save location via file dialog.
		"""
		file_path = self._document.file_path
		if not file_path:
			file_path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
				self, self.tr("Save CDML File"), "",
				self.tr("CDML Files (*.cdml);;All Files (*)"),
			)[0]
			if not file_path:
				return
		bkchem_qt.io.cdml_io.save_cdml_file(file_path, self._document)
		self._document.file_path = file_path
		self._document.dirty = False
		self._tab_widget.setTabText(0, self._document.title())
		self.statusBar().showMessage(
			self.tr("Saved: %s") % file_path, 3000,
		)

	#============================================
	def _on_save_as(self) -> None:
		"""Save the current document to a new file path.

		Always prompts for a save location, even if the document
		already has a file path.
		"""
		file_path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Save CDML File As"), "",
			self.tr("CDML Files (*.cdml);;All Files (*)"),
		)[0]
		if not file_path:
			return
		bkchem_qt.io.cdml_io.save_cdml_file(file_path, self._document)
		self._document.file_path = file_path
		self._document.dirty = False
		self._tab_widget.setTabText(0, self._document.title())
		self.statusBar().showMessage(
			self.tr("Saved: %s") % file_path, 3000,
		)

	#============================================
	def _on_export_svg(self) -> None:
		"""Export scene to SVG."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export SVG"), "", self.tr("SVG Files (*.svg)")
		)[0]
		if path:
			bkchem_qt.io.export.export_svg(self._scene, path)

	#============================================
	def _on_export_png(self) -> None:
		"""Export scene to PNG."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export PNG"), "", self.tr("PNG Files (*.png)")
		)[0]
		if path:
			bkchem_qt.io.export.export_png(self._scene, path)

	#============================================
	def _on_export_pdf(self) -> None:
		"""Export scene to PDF."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export PDF"), "", self.tr("PDF Files (*.pdf)")
		)[0]
		if path:
			bkchem_qt.io.export.export_pdf(self._scene, path)

	#============================================
	def _on_toggle_grid(self, checked: bool) -> None:
		"""Toggle the grid visibility on the scene.

		Args:
			checked: Whether the grid action is checked.
		"""
		self._scene.set_grid_visible(checked)
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE, checked
		)

	#============================================
	def _on_toggle_grid_snap(self, checked: bool) -> None:
		"""Toggle snap-to-grid behavior on the scene.

		Args:
			checked: Whether the snap action is checked.
		"""
		self._scene.set_grid_snap_enabled(checked)
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_SNAP_ENABLED,
			checked,
		)
		if checked:
			self.statusBar().showMessage(self.tr("Snap to grid enabled"), 2000)
		else:
			self.statusBar().showMessage(self.tr("Snap to grid disabled"), 2000)

	#============================================
	def _on_toggle_theme(self) -> None:
		"""Toggle between dark and light themes."""
		self._theme_manager.toggle_theme()

	#============================================
	def _on_choose_theme(self) -> None:
		"""Open the theme chooser dialog and apply the selected theme."""
		current = self._theme_manager.current_theme
		chosen = bkchem_qt.dialogs.theme_chooser_dialog.ThemeChooserDialog \
			.choose_theme(self, current)
		# apply only if user selected a different theme
		if chosen is not None and chosen != current:
			self._theme_manager.apply_theme(chosen)

	#============================================
	def _on_theme_changed(self, theme_name: str) -> None:
		"""Handle a theme change by refreshing icons and updating menu text.

		Args:
			theme_name: The new theme name ('dark' or 'light').
		"""
		# update icon_loader theme and clear cache
		bkchem_qt.widgets.icon_loader.set_theme(theme_name)
		bkchem_qt.widgets.icon_loader.reload_icons()

		# refresh mode toolbar icons
		modes_config = {}
		if _MODES_YAML_PATH.is_file():
			with open(_MODES_YAML_PATH, "r") as fh:
				modes_config = yaml.safe_load(fh) or {}
		modes_defs = modes_config.get("modes", {})
		for name, action in self._mode_toolbar._actions.items():
			# look up the icon name from modes.yaml
			mode_def = modes_defs.get(name, {})
			icon_name = mode_def.get("icon", name)
			icon = bkchem_qt.widgets.icon_loader.get_icon(icon_name)
			self._mode_toolbar.update_action_icon(name, icon)

		# update canvas viewport and paper/grid colors from YAML theme
		bkchem_qt.themes.theme_loader.clear_cache()
		surround = bkchem_qt.themes.theme_loader.get_canvas_surround(theme_name)
		self._view.set_background_color(surround)
		self._scene.apply_theme(theme_name)

		# update default chemistry line and area colors for new theme
		chem_colors = bkchem_qt.themes.theme_loader.get_chemistry_colors(theme_name)
		bkchem_qt.canvas.items.render_ops_painter.set_default_color(
			chem_colors["default_line"]
		)
		bkchem_qt.canvas.items.render_ops_painter.set_default_area_color(
			chem_colors["default_area"]
		)
		# update canvas interaction colors for new theme
		canvas_colors = bkchem_qt.themes.theme_loader.get_canvas_colors(theme_name)
		bkchem_qt.canvas.items.render_ops_painter.set_canvas_colors(canvas_colors)
		# update charge mark colors for new theme
		bkchem_qt.canvas.items.render_ops_painter.set_charge_colors({
			"plus": chem_colors["charge_plus"],
			"minus": chem_colors["charge_minus"],
		})

		# refresh submode ribbon icons for new theme
		mode = self._mode_manager.current_mode
		if mode is not None:
			mode_name = mode.name
			# find the registered name for rebuild
			for name in self._mode_manager.mode_names():
				if self._mode_manager._modes[name] is mode:
					mode_name = name
					break
			self._submode_ribbon.rebuild(mode_name)

	#============================================
	def _apply_geometry_preferences(self) -> None:
		"""Apply canonical geometry settings and remove legacy keys."""
		bond_length_pt = bkchem_qt.config.geometry_units.resolve_bond_length_pt(
			self._prefs
		)
		self._scene.set_grid_spacing_pt(bond_length_pt)
		self._prefs.remove_value(
			bkchem_qt.config.preferences.Preferences.KEY_BOND_LENGTH
		)

	#============================================
	def _apply_view_preferences(self) -> None:
		"""Apply persisted view toggles (grid visibility and snapping)."""
		grid_visible = bool(self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE,
			True,
		))
		grid_snap_enabled = bool(self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_SNAP_ENABLED,
			True,
		))
		self._scene.set_grid_visible(grid_visible)
		self._scene.set_grid_snap_enabled(grid_snap_enabled)
		if hasattr(self, "_action_toggle_grid"):
			self._action_toggle_grid.setChecked(grid_visible)
		if hasattr(self, "_action_toggle_grid_snap"):
			self._action_toggle_grid_snap.setChecked(grid_snap_enabled)

	#============================================
	def _on_preferences(self) -> None:
		"""Show the preferences dialog."""
		accepted = bkchem_qt.dialogs.preferences_dialog.PreferencesDialog \
			.show_preferences(self)
		if accepted:
			self._apply_geometry_preferences()
			self._apply_view_preferences()

	#============================================
	def _on_about(self) -> None:
		"""Show the About dialog."""
		bkchem_qt.dialogs.about_dialog.AboutDialog.show_about(self)

	#============================================
	def _on_element_changed(self, symbol: str) -> None:
		"""Forward element change from ribbon to active Draw/Atom mode.

		Args:
			symbol: New element symbol.
		"""
		symbol = str(symbol).strip()
		if not symbol:
			return
		mode = self._mode_manager.current_mode
		set_element = getattr(mode, "set_element", None)
		if callable(set_element):
			set_element(symbol)
			return
		if hasattr(mode, 'current_element'):
			try:
				mode.current_element = symbol
			except AttributeError:
				pass

	#============================================
	def _on_bond_order_changed(self, order: int) -> None:
		"""Forward bond order change from ribbon to draw mode.

		Args:
			order: New bond order.
		"""
		mode = self._mode_manager.current_mode
		if hasattr(mode, 'current_bond_order'):
			mode.current_bond_order = order

	#============================================
	def _on_bond_type_changed(self, bond_type: str) -> None:
		"""Forward bond type change from ribbon to draw mode.

		Args:
			bond_type: New bond type character.
		"""
		mode = self._mode_manager.current_mode
		if hasattr(mode, 'current_bond_type'):
			mode.current_bond_type = bond_type

	#============================================
	def restore_geometry(self) -> None:
		"""Restore window geometry from saved preferences.

		Only restores window size and position, not toolbar state,
		because toolbar layout changes between versions would conflict
		with stale saved state.
		"""
		geometry = self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_WINDOW_GEOMETRY
		)
		if geometry is not None:
			self.restoreGeometry(geometry)

	#============================================
	def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
		"""Save window geometry and state before closing.

		Args:
			event: The close event.
		"""
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_WINDOW_GEOMETRY,
			self.saveGeometry(),
		)
		super().closeEvent(event)
