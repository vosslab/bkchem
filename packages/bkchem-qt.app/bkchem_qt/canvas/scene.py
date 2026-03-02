"""Chemistry scene for the BKChem Qt canvas."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import oasa.hex_grid
import bkchem_qt.config.geometry_units
import bkchem_qt.themes.theme_loader

# -- default scene dimensions in pixels --
DEFAULT_SCENE_WIDTH = 4000
DEFAULT_SCENE_HEIGHT = 3000

# -- paper defaults --
PAPER_WIDTH = 2000
PAPER_HEIGHT = 1500
PAPER_Z_VALUE = -200

# -- grid defaults (scene-space points) --
DEFAULT_GRID_SPACING_PT = bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT
GRID_Z_VALUE = -100


#============================================
class ChemScene(PySide6.QtWidgets.QGraphicsScene):
	"""QGraphicsScene subclass for 2D chemistry drawing.

	Provides a paper rectangle on a transparent background,
	an optional snap grid overlay constrained to the paper area,
	and coordinate snapping helpers. Colors are loaded from the
	shared YAML theme files in bkchem_data/themes/.

	Args:
		parent: Optional parent QObject.
		theme_name: Initial theme name ('dark' or 'light').
	"""

	#============================================
	def __init__(self, parent: PySide6.QtCore.QObject = None,
			theme_name: str = "dark", grid_spacing_pt: float = DEFAULT_GRID_SPACING_PT,
			grid_snap_enabled: bool = True):
		"""Initialize the scene with default rect, paper, and grid.

		Args:
			parent: Optional parent QObject.
			theme_name: Theme name for initial colors.
			grid_spacing_pt: Hex-grid spacing in scene-space points.
			grid_snap_enabled: Whether point snapping is enabled.
		"""
		super().__init__(parent)
		self._theme_name = theme_name
		# set scene rectangle
		self.setSceneRect(0, 0, DEFAULT_SCENE_WIDTH, DEFAULT_SCENE_HEIGHT)
		# leave background transparent so the QGraphicsView dark viewport shows through

		# paper state
		self._paper_item: PySide6.QtWidgets.QGraphicsRectItem = None

		# grid state
		self._grid_spacing_pt: float = float(grid_spacing_pt)
		self._grid_visible: bool = True
		self._grid_snap_enabled: bool = bool(grid_snap_enabled)
		self._grid_group: PySide6.QtWidgets.QGraphicsItemGroup = None

		# build the paper rectangle centered in the scene
		self._build_paper()
		# build the grid constrained to the paper area
		self._build_grid()

	#============================================
	def _build_paper(self) -> None:
		"""Create the paper rectangle centered in the scene.

		The paper sits at PAPER_Z_VALUE (-200), below the grid at -100,
		so grid lines render on top of the paper surface. Color comes
		from the active YAML theme file.
		"""
		# center the paper within the scene rect
		scene_rect = self.sceneRect()
		paper_x = (scene_rect.width() - PAPER_WIDTH) / 2.0
		paper_y = (scene_rect.height() - PAPER_HEIGHT) / 2.0

		# get paper color and outline from YAML theme
		paper_color = bkchem_qt.themes.theme_loader.get_paper_color(self._theme_name)
		outline_color = bkchem_qt.themes.theme_loader.get_paper_outline(self._theme_name)

		# outline pen from YAML theme (visible paper border)
		paper_pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(outline_color))
		paper_pen.setWidthF(1.5)

		self._paper_item = self.addRect(
			paper_x, paper_y, PAPER_WIDTH, PAPER_HEIGHT,
			paper_pen,
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(paper_color)),
		)
		self._paper_item.setZValue(PAPER_Z_VALUE)

	#============================================
	def _build_grid(self) -> None:
		"""Create hex grid honeycomb lines and dots constrained to the paper rect.

		Uses oasa.hex_grid to generate pointy-top hexagonal grid lines
		and vertex dots matching the Tk version. Colors come from the
		active YAML theme file. Items are collected into a group that
		can be shown or hidden as a unit.
		"""
		self._grid_group = self.createItemGroup([])
		self._grid_group.setZValue(GRID_Z_VALUE)
		self._grid_group.setVisible(self._grid_visible)

		# get grid colors from YAML theme
		grid_colors = bkchem_qt.themes.theme_loader.get_grid_colors(self._theme_name)

		# constrain grid to the paper rect boundaries
		p_rect = self._paper_item.rect()
		left = p_rect.left()
		top = p_rect.top()
		right = p_rect.right()
		bottom = p_rect.bottom()

		# draw honeycomb line segments
		line_pen = PySide6.QtGui.QPen(
			PySide6.QtGui.QColor(grid_colors["line"])
		)
		line_pen.setWidthF(0.375)

		edges = oasa.hex_grid.generate_hex_honeycomb_edges(
			left, top, right, bottom, self._grid_spacing_pt,
		)
		if edges is not None:
			for (x1, y1), (x2, y2) in edges:
				line = self.addLine(x1, y1, x2, y2, line_pen)
				self._grid_group.addToGroup(line)

		# draw dots at hex grid vertices
		dot_pen = PySide6.QtGui.QPen(
			PySide6.QtGui.QColor(grid_colors["dot_outline"])
		)
		dot_pen.setWidthF(0.375)
		dot_brush = PySide6.QtGui.QBrush(
			PySide6.QtGui.QColor(grid_colors["dot_fill"])
		)
		dot_radius = 1.0

		points = oasa.hex_grid.generate_hex_grid_points(
			left, top, right, bottom, self._grid_spacing_pt,
		)
		if points is not None:
			for px, py in points:
				dot = self.addEllipse(
					px - dot_radius, py - dot_radius,
					dot_radius * 2, dot_radius * 2,
					dot_pen, dot_brush,
				)
				self._grid_group.addToGroup(dot)

	#============================================
	def apply_theme(self, theme_name: str) -> None:
		"""Update paper and grid colors from the named YAML theme.

		Recolors existing grid items in place instead of destroying
		and rebuilding ~10,400 items, which avoids multi-second hangs.

		Args:
			theme_name: 'dark' or 'light'.
		"""
		self._theme_name = theme_name
		# update paper color and outline
		paper_color = bkchem_qt.themes.theme_loader.get_paper_color(theme_name)
		outline_color = bkchem_qt.themes.theme_loader.get_paper_outline(theme_name)
		self._paper_item.setBrush(
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(paper_color))
		)
		paper_pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(outline_color))
		paper_pen.setWidthF(1.5)
		self._paper_item.setPen(paper_pen)
		# recolor grid items in place (no destroy+rebuild)
		self._recolor_grid(theme_name)

	#============================================
	def _recolor_grid(self, theme_name: str) -> None:
		"""Recolor existing grid items to match the named theme.

		Updates pen and brush on existing grid line and dot items
		instead of destroying and rebuilding ~10,400 items.

		Args:
			theme_name: 'dark' or 'light'.
		"""
		if self._grid_group is None:
			return
		grid_colors = bkchem_qt.themes.theme_loader.get_grid_colors(theme_name)
		# build new pens and brushes once
		line_pen = PySide6.QtGui.QPen(
			PySide6.QtGui.QColor(grid_colors["line"])
		)
		line_pen.setWidthF(0.375)
		dot_pen = PySide6.QtGui.QPen(
			PySide6.QtGui.QColor(grid_colors["dot_outline"])
		)
		dot_pen.setWidthF(0.375)
		dot_brush = PySide6.QtGui.QBrush(
			PySide6.QtGui.QColor(grid_colors["dot_fill"])
		)
		# update each child item
		for child in self._grid_group.childItems():
			if hasattr(child, "line"):
				# QGraphicsLineItem
				child.setPen(line_pen)
			else:
				# QGraphicsEllipseItem (dot)
				child.setPen(dot_pen)
				child.setBrush(dot_brush)

	#============================================
	@property
	def paper_rect(self) -> PySide6.QtCore.QRectF:
		"""Return the paper rectangle in scene coordinates.

		Returns:
			QRectF describing the paper area.
		"""
		return self._paper_item.rect()

	#============================================
	def set_paper_color(self, color: str) -> None:
		"""Change the paper fill color.

		Args:
			color: CSS hex color string (e.g. '#ffffff').
		"""
		self._paper_item.setBrush(
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(color))
		)

	#============================================
	@property
	def grid_visible(self) -> bool:
		"""Whether the grid overlay is currently visible."""
		return self._grid_visible

	#============================================
	def set_grid_visible(self, visible: bool) -> None:
		"""Show or hide the grid overlay.

		Args:
			visible: True to show grid lines, False to hide.
		"""
		self._grid_visible = visible
		if self._grid_group is not None:
			self._grid_group.setVisible(visible)

	#============================================
	@property
	def grid_snap_enabled(self) -> bool:
		"""Whether snapping to the hex grid is currently enabled."""
		return self._grid_snap_enabled

	#============================================
	def set_grid_snap_enabled(self, enabled: bool) -> None:
		"""Enable or disable snapping to the hex grid."""
		self._grid_snap_enabled = bool(enabled)

	#============================================
	@property
	def grid_spacing_pt(self) -> float:
		"""Current hex-grid spacing in scene-space points."""
		return self._grid_spacing_pt

	#============================================
	def set_grid_spacing_pt(self, value: float) -> None:
		"""Set grid spacing and rebuild the grid overlay.

		Args:
			value: New spacing in scene-space points.
		"""
		new_spacing = float(value)
		if new_spacing <= 0.0:
			return
		if abs(new_spacing - self._grid_spacing_pt) < 1e-6:
			return
		self._grid_spacing_pt = new_spacing
		# spacing changes are infrequent; rebuild ensures geometry correctness.
		if self._grid_group is not None:
			try:
				children = list(self._grid_group.childItems())
			except RuntimeError:
				# group may already be deleted when scene was cleared.
				self._grid_group = None
			else:
				for child in children:
					self.removeItem(child)
				try:
					self.removeItem(self._grid_group)
				except RuntimeError:
					# object lifetime already ended on C++ side.
					pass
				self._grid_group = None
		self._build_grid()

	#============================================
	def snap_to_grid(self, x: float, y: float) -> tuple:
		"""Snap coordinates to the nearest hex grid point.

		Args:
			x: Scene x coordinate.
			y: Scene y coordinate.

		Returns:
			Tuple of (snapped_x, snapped_y) on the hex grid.
		"""
		snapped = oasa.hex_grid.snap_to_hex_grid(
			x, y, self._grid_spacing_pt,
		)
		return snapped
