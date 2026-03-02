"""Draw mode for creating new atoms and bonds.

Implements Tk-parity click-to-place bond drawing: clicking an atom
immediately adds a new bonded atom at a fixed bond length and smart
angle (120 deg zigzag, transoid placement, least-crowded for 2+
neighbors). Dragging from an atom snaps to 15-degree angle increments.
"""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.config.geometry_units
from bkchem_qt.canvas.items import render_ops_painter
import bkchem_qt.undo.commands

# snap radius: if release is within this distance of an atom, snap to it
_SNAP_RADIUS = 15.0
# minimum drag distance before treating as a drag rather than a click
_DRAG_THRESHOLD = 5.0
# angle resolution for drag snapping (degrees)
_ANGLE_RESOLUTION = 15
# overlap merge threshold: atoms closer than this are merged (Tk uses 4px)
_OVERLAP_THRESHOLD = 4.0


#============================================
class DrawMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for drawing new atoms and bonds via click-to-place.

	Click on an existing atom to add a new bonded atom at a smart angle
	and fixed bond length. Click on empty space to create a standalone
	atom with a bonded neighbor. Drag from an atom to place a new atom
	at a snapped angle. Drag between two atoms to bond them.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the draw mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Draw"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		# current drawing settings
		self._current_element = "C"
		self._current_bond_order = 1
		self._current_bond_type = "n"
		# drag state
		self._preview_line = None
		self._start_atom = None
		self._dragging = False
		self._press_pos = None
		# alternating sign for transoid bond placement (Tk parity)
		self._sign = 1
		# last atom used for placement (for transoid alternation)
		self._last_used_atom = None

	# ------------------------------------------------------------------
	# Drawing settings
	# ------------------------------------------------------------------

	#============================================
	@property
	def current_element(self) -> str:
		"""The element symbol used for new atoms."""
		return self._current_element

	#============================================
	@current_element.setter
	def current_element(self, symbol: str):
		self._current_element = str(symbol)

	#============================================
	@property
	def current_bond_order(self) -> int:
		"""The bond order used for new bonds (1, 2, or 3)."""
		return self._current_bond_order

	#============================================
	@current_bond_order.setter
	def current_bond_order(self, order: int):
		self._current_bond_order = int(order)

	#============================================
	@property
	def current_bond_type(self) -> str:
		"""The bond type character used for new bonds."""
		return self._current_bond_type

	#============================================
	@current_bond_type.setter
	def current_bond_type(self, bond_type: str):
		self._current_bond_type = str(bond_type)

	# ------------------------------------------------------------------
	# Lifecycle
	# ------------------------------------------------------------------

	#============================================
	def deactivate(self) -> None:
		"""Remove any preview line and reset drag state."""
		self._remove_preview_line()
		self._start_atom = None
		self._dragging = False
		self._press_pos = None
		super().deactivate()

	# ------------------------------------------------------------------
	# Bond length from grid spacing
	# ------------------------------------------------------------------

	#============================================
	def _get_bond_length(self) -> float:
		"""Return the bond length from the scene grid spacing.

		Returns:
			Bond length in scene units.
		"""
		scene = self._view.scene()
		if scene is not None and hasattr(scene, "grid_spacing_pt"):
			return scene.grid_spacing_pt
		return bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT

	#============================================
	@staticmethod
	def _grid_snap_enabled(scene) -> bool:
		"""Return whether scene-level grid snapping is enabled."""
		if scene is None or not hasattr(scene, "grid_snap_enabled"):
			return True
		return bool(scene.grid_snap_enabled)

	# ------------------------------------------------------------------
	# Geometry helpers (ported from Tk molecule_lib)
	# ------------------------------------------------------------------

	#============================================
	@staticmethod
	def _get_angle(a1_model, a2_model) -> float:
		"""Compute the angle from a1 to a2 relative to the horizontal.

		Mirrors Tk molecule_lib.get_angle().

		Args:
			a1_model: Source AtomModel.
			a2_model: Target AtomModel.

		Returns:
			Angle in radians.
		"""
		dx = a2_model.x - a1_model.x
		dy = a2_model.y - a1_model.y
		return math.atan2(dy, dx)

	#============================================
	def _find_place(self, atom_model, mol_model, bond_length: float,
					added_order: int = 1) -> tuple:
		"""Compute position for a new atom bonded to atom_model.

		Port of Tk molecule_lib.find_place(). Uses neighbor count to
		determine smart placement:
		- 0 neighbors: 30 deg angle (down-right, matching Tk default)
		- 1 neighbor (non-triple): 120 deg offset with transoid alternation
		- 1 neighbor (triple): 180 deg linear extension
		- 2+ neighbors: least crowded gap

		Args:
			atom_model: The AtomModel to bond from.
			mol_model: The MoleculeModel containing the atom.
			bond_length: Distance for the new bond.
			added_order: Bond order being added (affects triple logic).

		Returns:
			Tuple of (x, y) for the new atom position.
		"""
		# get OASA neighbors through the chem_atom
		oasa_atom = atom_model._chem_atom
		oasa_neighbors = oasa_atom.neighbors
		if len(oasa_neighbors) == 0:
			# no neighbors: place at 30 degrees (down-right, Tk default)
			x = atom_model.x + math.cos(math.pi / 6) * bond_length
			y = atom_model.y - math.sin(math.pi / 6) * bond_length
			return (x, y)
		if len(oasa_neighbors) == 1:
			# one neighbor: place at 120 deg offset or linear for triple
			oasa_neigh = oasa_neighbors[0]
			# look up the AtomModel for the neighbor
			neigh_model = mol_model._atom_models.get(id(oasa_neigh))
			if neigh_model is None:
				# fallback: place at default angle
				x = atom_model.x + math.cos(math.pi / 6) * bond_length
				y = atom_model.y - math.sin(math.pi / 6) * bond_length
				return (x, y)
			# check if existing bond is triple or we are adding triple
			oasa_edge = oasa_atom.get_edge_leading_to(oasa_neigh)
			existing_order = oasa_edge.order if oasa_edge else 1
			if existing_order == 3 or added_order == 3:
				# triple bond: extend linearly (180 deg from neighbor)
				angle = self._get_angle(atom_model, neigh_model) + math.pi
				x = atom_model.x + math.cos(angle) * bond_length
				y = atom_model.y + math.sin(angle) * bond_length
				return (x, y)
			# normal bond: 120 deg offset with transoid alternation
			if atom_model is self._last_used_atom or len(oasa_neigh.neighbors) != 2:
				# alternate side or no transoid reference available
				self._sign = -self._sign
				angle = self._get_angle(atom_model, neigh_model)
				angle += self._sign * 2 * math.pi / 3
				x = atom_model.x + math.cos(angle) * bond_length
				y = atom_model.y + math.sin(angle) * bond_length
			else:
				# try transoid placement relative to neighbor's other bond
				oasa_neighs2 = oasa_neigh.neighbors
				# find the neighbor's other neighbor (not atom_model)
				oasa_neigh2 = None
				for n2 in oasa_neighs2:
					if n2 is not oasa_atom:
						oasa_neigh2 = n2
						break
				angle = self._get_angle(atom_model, neigh_model)
				angle += self._sign * 2 * math.pi / 3
				x = atom_model.x + math.cos(angle) * bond_length
				y = atom_model.y + math.sin(angle) * bond_length
				# check if new atom is on the same side as neigh2
				if oasa_neigh2 is not None:
					neigh2_model = mol_model._atom_models.get(id(oasa_neigh2))
					if neigh2_model is not None:
						side_new = self._on_which_side(
							neigh_model, atom_model, x, y,
						)
						side_n2 = self._on_which_side(
							neigh_model, atom_model,
							neigh2_model.x, neigh2_model.y,
						)
						if side_new == side_n2 and side_new != 0:
							# same side: flip to achieve transoid
							self._sign = -self._sign
							angle = self._get_angle(atom_model, neigh_model)
							angle += self._sign * 2 * math.pi / 3
							x = atom_model.x + math.cos(angle) * bond_length
							y = atom_model.y + math.sin(angle) * bond_length
			self._last_used_atom = atom_model
			return (x, y)
		# 2+ neighbors: find the least crowded angular gap
		return self._find_least_crowded_place(
			atom_model, mol_model, bond_length,
		)

	#============================================
	@staticmethod
	def _on_which_side(a_model, b_model, px: float, py: float) -> int:
		"""Determine which side of line a->b the point (px, py) is on.

		Returns 1 or -1 for each side, 0 if on the line.

		Args:
			a_model: First endpoint AtomModel of the line.
			b_model: Second endpoint AtomModel of the line.
			px: Point x coordinate.
			py: Point y coordinate.

		Returns:
			1, -1, or 0.
		"""
		# cross product of (b-a) x (p-a)
		cross = ((b_model.x - a_model.x) * (py - a_model.y)
					- (b_model.y - a_model.y) * (px - a_model.x))
		if abs(cross) < 1e-6:
			return 0
		return 1 if cross > 0 else -1

	#============================================
	@staticmethod
	def _find_least_crowded_place(atom_model, mol_model,
									distance: float) -> tuple:
		"""Find the least crowded direction around an atom.

		Collects angles to all neighbors, finds the largest angular gap,
		and places the new atom in the middle of that gap. Port of Tk
		molecule_lib.find_least_crowded_place_around_atom().

		Args:
			atom_model: The center AtomModel.
			mol_model: The MoleculeModel containing the atom.
			distance: Bond length for the new atom.

		Returns:
			Tuple of (x, y) for the new atom position.
		"""
		oasa_atom = atom_model._chem_atom
		oasa_neighbors = oasa_atom.neighbors
		if not oasa_neighbors:
			# isolated atom: place to the right
			return (atom_model.x + distance, atom_model.y)
		# collect angles to all neighbors
		angles = []
		for oasa_neigh in oasa_neighbors:
			neigh_model = mol_model._atom_models.get(id(oasa_neigh))
			if neigh_model is None:
				continue
			dx = neigh_model.x - atom_model.x
			dy = neigh_model.y - atom_model.y
			# clockwise angle from east (0 to 2*pi)
			angle = math.atan2(dy, dx)
			if angle < 0:
				angle += 2 * math.pi
			angles.append(angle)
		if not angles:
			return (atom_model.x + distance, atom_model.y)
		# sort angles and find the largest gap
		angles.sort()
		# add wrap-around gap
		angles.append(angles[0] + 2 * math.pi)
		# compute differences between consecutive angles
		max_diff = 0.0
		max_idx = 0
		for i in range(len(angles) - 1):
			diff = angles[i + 1] - angles[i]
			if diff > max_diff:
				max_diff = diff
				max_idx = i
		# place in the middle of the largest gap
		best_angle = (angles[max_idx] + angles[max_idx + 1]) / 2.0
		x = atom_model.x + distance * math.cos(best_angle)
		y = atom_model.y + distance * math.sin(best_angle)
		return (x, y)

	#============================================
	@staticmethod
	def _point_on_circle(cx: float, cy: float, radius: float,
							dx: float, dy: float,
							resolution: int = _ANGLE_RESOLUTION) -> tuple:
		"""Compute a point on a circle in a direction, snapped to resolution.

		Port of oasa.geometry.point_on_circle(). The direction vector
		(dx, dy) is snapped to the nearest resolution-degree increment.

		Args:
			cx: Center x coordinate.
			cy: Center y coordinate.
			radius: Circle radius (bond length).
			dx: Direction x component.
			dy: Direction y component.
			resolution: Angle snap resolution in degrees.

		Returns:
			Tuple of (x, y) on the circle.
		"""
		if resolution:
			# snap angle to nearest resolution-degree increment
			res_rad = math.pi * resolution / 180.0
			angle = round(math.atan2(dy, dx) / res_rad) * res_rad
		else:
			angle = math.atan2(dy, dx)
		x = cx + round(math.cos(angle) * radius, 2)
		y = cy + round(math.sin(angle) * radius, 2)
		return (x, y)

	# ------------------------------------------------------------------
	# Mouse event handlers
	# ------------------------------------------------------------------

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press for click-to-place bond drawing.

		Click on an existing bond: toggle bond type/order/style via
		_toggle_bond_type() (port of Tk bond_type_control.toggle_type).

		Click on an existing atom: immediately add a new bonded atom at
		a smart angle via _find_place(). The clicked atom becomes the
		focus for the next click.

		Click on empty space: snap to grid, create a standalone atom,
		then immediately add a bonded neighbor via _find_place().

		Also records state for potential drag operations.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self._press_pos = scene_pos
		self._dragging = False
		# check for atom first (atoms take priority over bonds at endpoints)
		existing_atom = self._find_atom_at(scene_pos)
		if existing_atom is None:
			# no atom: check for bond click (toggle bond type/order)
			bond_item = self._find_bond_at(scene_pos)
			if bond_item is not None:
				self._toggle_bond_type(bond_item)
				return
		bond_length = self._get_bond_length()
		if existing_atom is not None:
			# click on existing atom: immediately place a bonded atom
			self._start_atom = existing_atom
			mol_model = self._get_active_molecule()
			if mol_model is not None:
				new_x, new_y = self._find_place(
					existing_atom.atom_model, mol_model, bond_length,
					added_order=self._current_bond_order,
				)
				new_atom_item = self._create_atom_at(new_x, new_y)
				if new_atom_item is not None:
					self._create_bond_between(existing_atom, new_atom_item)
					# new atom becomes the focused atom for next click
					self._start_atom = new_atom_item
			self._handle_overlap()
			self.status_message.emit("Added bond (drag to override angle)")
		else:
			# click on empty space: snap to grid, create atom + neighbor
			self._start_atom = None
			scene = self._view.scene()
			sx, sy = scene_pos.x(), scene_pos.y()
			if (
				scene is not None
				and hasattr(scene, "snap_to_grid")
				and self._grid_snap_enabled(scene)
			):
				sx, sy = scene.snap_to_grid(sx, sy)
			# create the first standalone atom
			first_atom = self._create_atom_at(sx, sy)
			if first_atom is not None:
				mol_model = self._get_active_molecule()
				if mol_model is not None:
					# add a bonded neighbor via find_place
					new_x, new_y = self._find_place(
						first_atom.atom_model, mol_model, bond_length,
					)
					second_atom = self._create_atom_at(new_x, new_y)
					if second_atom is not None:
						self._create_bond_between(first_atom, second_atom)
						# second atom is the focus for next click
						self._start_atom = second_atom
			self._handle_overlap()
			self.status_message.emit("Created new bond")

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse move for drag preview with angle snapping.

		Shows a preview line from the start atom to the snapped endpoint.
		The endpoint is snapped to 15-degree angle increments at the
		fixed bond length distance.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._start_atom is None or self._press_pos is None:
			return
		# check if we have moved far enough to be dragging
		dx = scene_pos.x() - self._press_pos.x()
		dy = scene_pos.y() - self._press_pos.y()
		dist = math.sqrt(dx * dx + dy * dy)
		if dist < _DRAG_THRESHOLD:
			return
		self._dragging = True
		# compute snapped endpoint
		start_model = self._start_atom.atom_model
		start_x = start_model.x
		start_y = start_model.y
		bond_length = self._get_bond_length()
		dir_dx = scene_pos.x() - start_x
		dir_dy = scene_pos.y() - start_y
		snap_x, snap_y = self._point_on_circle(
			start_x, start_y, bond_length, dir_dx, dir_dy,
		)
		scene = self._view.scene()
		if scene is not None and self._grid_snap_enabled(scene):
			snap_x, snap_y = scene.snap_to_grid(snap_x, snap_y)
		# draw or update the preview line
		if scene is None:
			return
		if self._preview_line is None:
			preview_color = render_ops_painter.get_canvas_color("preview")
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(preview_color))
			pen.setWidthF(1.5)
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			self._preview_line = scene.addLine(
				start_x, start_y, snap_x, snap_y, pen,
			)
		else:
			self._preview_line.setLine(
				start_x, start_y, snap_x, snap_y,
			)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse release for drag placement.

		If this was a drag: undo the auto-placed atom from mouse_press
		and place a new atom at the drag endpoint instead (angle-snapped
		or bonded to an existing atom). If not a drag: the click already
		handled placement in mouse_press, so just clean up.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self._remove_preview_line()
		if self._dragging and self._start_atom is not None:
			# drag completed: undo the auto-placed atom from mouse_press
			# and place at the drag endpoint instead
			undo_stack = self._find_undo_stack()
			if undo_stack is not None and undo_stack.canUndo():
				# undo the bond from mouse_press
				undo_stack.undo()
				if undo_stack.canUndo():
					# undo the auto-placed atom from mouse_press
					undo_stack.undo()
			# now place at the drag endpoint
			start_model = self._start_atom.atom_model
			end_atom = self._find_atom_at(scene_pos)
			if end_atom is not None and end_atom is not self._start_atom:
				# dragged onto an existing atom: bond to it
				self._create_bond_between(self._start_atom, end_atom)
			else:
				# compute snapped position and create atom there
				scene = self._view.scene()
				bond_length = self._get_bond_length()
				dir_dx = scene_pos.x() - start_model.x
				dir_dy = scene_pos.y() - start_model.y
				snap_x, snap_y = self._point_on_circle(
					start_model.x, start_model.y, bond_length,
					dir_dx, dir_dy,
				)
				if scene is not None and self._grid_snap_enabled(scene):
					snap_x, snap_y = scene.snap_to_grid(snap_x, snap_y)
				new_atom_item = self._create_atom_at(snap_x, snap_y)
				if new_atom_item is not None:
					self._create_bond_between(
						self._start_atom, new_atom_item,
					)
		# post-processing: merge overlapping atoms
		self._handle_overlap()
		# reset drag state (keep _start_atom as focus for next click)
		self._dragging = False
		self._press_pos = None

	# ------------------------------------------------------------------
	# Creation helpers
	# ------------------------------------------------------------------

	#============================================
	def _create_atom_at(self, x: float, y: float, symbol: str = None):
		"""Create a new atom at a scene position with undo support.

		Creates an AtomModel and AtomItem, adds the atom to the active
		molecule (creating one if needed), and pushes an AddAtomCommand.

		Args:
			x: X coordinate in scene units.
			y: Y coordinate in scene units.
			symbol: Element symbol (defaults to current_element).

		Returns:
			The created AtomItem, or None if creation failed.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		element = symbol or self._current_element
		# get or create the active molecule
		mol_model = self._get_active_molecule()
		if mol_model is None:
			return None
		# create the atom model
		atom_model = mol_model.create_atom(symbol=element)
		atom_model.x = x
		atom_model.y = y
		# create the visual item
		atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom_model)
		# push undo command
		undo_stack = self._find_undo_stack()
		if undo_stack is not None:
			cmd = bkchem_qt.undo.commands.AddAtomCommand(
				scene, mol_model, atom_model, atom_item,
			)
			undo_stack.push(cmd)
		else:
			# no undo stack: add directly
			mol_model.add_atom(atom_model)
			scene.addItem(atom_item)
		self.status_message.emit(f"Added {element} atom")
		return atom_item

	#============================================
	def _create_bond_between(self, atom1_item, atom2_item):
		"""Create a bond between two atom items with undo support.

		Adds the bond to the molecule graph first so the BondItem
		constructor can compute render ops from atom positions, then
		pushes an AddBondCommand for undo support.

		Args:
			atom1_item: First endpoint AtomItem.
			atom2_item: Second endpoint AtomItem.

		Returns:
			The created BondItem, or None if creation failed.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		mol_model = self._get_active_molecule()
		if mol_model is None:
			return None
		# create the bond model
		bond_model = mol_model.create_bond(
			order=self._current_bond_order,
			bond_type=self._current_bond_type,
		)
		# add bond to molecule graph first so BondItem can access vertices
		atom1_model = atom1_item.atom_model
		atom2_model = atom2_item.atom_model
		mol_model.add_bond(atom1_model, atom2_model, bond_model)
		# create the visual item (needs bond in graph for render ops)
		bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
		scene.addItem(bond_item)
		# push undo command (bond already added, skip first redo)
		undo_stack = self._find_undo_stack()
		if undo_stack is not None:
			cmd = bkchem_qt.undo.commands.AddBondCommand(
				scene, mol_model, bond_model, bond_item,
			)
			cmd._first_redo = True
			undo_stack.push(cmd)
		order_name = {1: "single", 2: "double", 3: "triple"}.get(
			self._current_bond_order, str(self._current_bond_order),
		)
		self.status_message.emit(f"Added {order_name} bond")
		return bond_item

	#============================================
	def _find_atom_at(self, scene_pos: PySide6.QtCore.QPointF):
		"""Find an AtomItem near a scene position within snap radius.

		Searches for AtomItems and returns the closest one within
		``_SNAP_RADIUS``, or None if none are close enough.

		Args:
			scene_pos: Position in scene coordinates.

		Returns:
			AtomItem or None.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		# check items in a rectangle around the position
		snap_rect = PySide6.QtCore.QRectF(
			scene_pos.x() - _SNAP_RADIUS,
			scene_pos.y() - _SNAP_RADIUS,
			_SNAP_RADIUS * 2,
			_SNAP_RADIUS * 2,
		)
		candidates = scene.items(snap_rect)
		best_item = None
		best_dist = _SNAP_RADIUS
		for item in candidates:
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				continue
			model = item.atom_model
			dx = model.x - scene_pos.x()
			dy = model.y - scene_pos.y()
			dist = math.sqrt(dx * dx + dy * dy)
			if dist < best_dist:
				best_dist = dist
				best_item = item
		return best_item

	# ------------------------------------------------------------------
	# Bond toggle helpers
	# ------------------------------------------------------------------

	#============================================
	def _find_bond_at(self, scene_pos: PySide6.QtCore.QPointF):
		"""Find a BondItem at a scene position.

		Args:
			scene_pos: Position in scene coordinates.

		Returns:
			BondItem or None.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		items = scene.items(scene_pos)
		for item in items:
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				return item
		return None

	#============================================
	def _toggle_bond_type(self, bond_item) -> None:
		"""Toggle bond type/order/style on click.

		Port of Tk bond_type_control.toggle_type(). Behavior depends on
		the current draw mode settings (bond_type, bond_order) vs the
		clicked bond's current state:
		- Different type: switch to the new type and order.
		- Same type, order 1 with normal/dotted type: cycle 1 -> 2 -> 3 -> 1.
		- Same type, different order: switch to new order.
		- Same type and order: cycle display variants (centering, width sign,
		  equithick, atom swap for wedge/hash/wavy).

		Changes are wrapped in an undo macro.

		Args:
			bond_item: The BondItem to toggle.
		"""
		model = bond_item.bond_model
		to_type = self._current_bond_type
		to_order = self._current_bond_order
		undo_stack = self._find_undo_stack()
		if undo_stack is None:
			return
		# snapshot for undo
		old_order = model.order
		old_type = model.type
		old_center = model.center
		old_bond_width = model.bond_width
		old_auto_sign = model.auto_bond_sign
		old_atom1 = model.atom1
		old_atom2 = model.atom2
		# apply the toggle logic
		if to_type != model.type:
			# switch to new type and order
			model.type = to_type
			model.order = to_order
		elif to_order == 1 and to_type in ('n', 'd'):
			# cycle order: 1 -> 2 -> 3 -> 1
			new_order = (model.order % 3) + 1
			model.order = new_order
		elif to_order != model.order:
			# switch to new order
			model.order = to_order
		else:
			# same type and order: cycle display variants
			if to_type in ('h', 'a'):
				# wedge/hash: swap endpoints
				model.atom1, model.atom2 = model.atom2, model.atom1
			elif to_type == 'w':
				# wavy: swap endpoints, negate bond_width
				model.atom1, model.atom2 = model.atom2, model.atom1
				if not model.center:
					model.bond_width = -model.bond_width
			elif to_order == 2:
				# double bond: cycle centering and width sign
				if model.center:
					model.bond_width = -model.bond_width
					model.auto_bond_sign = -model.auto_bond_sign
					model.center = False
				elif model.bond_width > 0:
					model.bond_width = -model.bond_width
					model.auto_bond_sign = -model.auto_bond_sign
				else:
					model.center = True
		# push undo for all changed properties
		undo_stack.beginMacro("Toggle Bond")
		for prop_name, old_val in [
			("order", old_order), ("type", old_type),
			("center", old_center), ("bond_width", old_bond_width),
			("auto_bond_sign", old_auto_sign),
		]:
			new_val = getattr(model, prop_name)
			if new_val != old_val:
				# revert so redo applies new value
				setattr(model, prop_name, old_val)
				cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
					model, prop_name, old_val, new_val,
					text=f"Toggle {prop_name}",
				)
				undo_stack.push(cmd)
		# handle atom swap undo if endpoints changed
		if model.atom1 is not old_atom1 or model.atom2 is not old_atom2:
			# swap back for undo, then push command to swap
			model.atom1, model.atom2 = old_atom1, old_atom2
			cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
				model, "atom1", old_atom1, old_atom2,
				text="Swap bond endpoints",
			)
			undo_stack.push(cmd)
			cmd2 = bkchem_qt.undo.commands.ChangePropertyCommand(
				model, "atom2", old_atom2, old_atom1,
				text="Swap bond endpoints",
			)
			undo_stack.push(cmd2)
		undo_stack.endMacro()
		self.status_message.emit(f"Toggled bond: order={model.order} type={model.type}")

	# ------------------------------------------------------------------
	# Overlap merge
	# ------------------------------------------------------------------

	#============================================
	def _handle_overlap(self) -> None:
		"""Merge overlapping atoms after drawing.

		Port of Tk paper_layout.handle_overlap() and molecule_lib.handle_overlap().
		Scans all atom pairs in the scene; when two atoms from the same or
		different molecules are within _OVERLAP_THRESHOLD pixels, redirects
		bonds from the duplicate to the survivor and removes the duplicate.
		Molecule merging (eat_molecule) is not yet implemented; only
		same-molecule overlap is handled.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		# collect all atom items
		atom_items = [
			item for item in scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		if len(atom_items) < 2:
			return
		# find overlapping pairs
		to_remove = set()
		for i in range(len(atom_items)):
			if id(atom_items[i]) in to_remove:
				continue
			a1 = atom_items[i]
			m1 = a1.atom_model
			for j in range(i + 1, len(atom_items)):
				if id(atom_items[j]) in to_remove:
					continue
				a2 = atom_items[j]
				m2 = a2.atom_model
				dx = abs(m1.x - m2.x)
				dy = abs(m1.y - m2.y)
				if dx < _OVERLAP_THRESHOLD and dy < _OVERLAP_THRESHOLD:
					# merge a2 into a1: redirect bonds from a2 to a1
					self._merge_atoms(a1, a2)
					to_remove.add(id(a2))

	#============================================
	def _merge_atoms(self, survivor_item, duplicate_item) -> None:
		"""Merge duplicate atom into survivor by redirecting bonds.

		Finds all bonds connected to duplicate_item, changes their
		endpoint to survivor_item, then removes the duplicate atom
		from its molecule and from the scene. Uses undo macro.

		Args:
			survivor_item: AtomItem that stays.
			duplicate_item: AtomItem to be removed.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		undo_stack = self._find_undo_stack()
		if undo_stack is None:
			return
		survivor_model = survivor_item.atom_model
		duplicate_model = duplicate_item.atom_model
		# find bonds connected to the duplicate
		bond_items_in_scene = [
			item for item in scene.items()
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
		]
		undo_stack.beginMacro("Merge Overlapping Atoms")
		for bond_item in bond_items_in_scene:
			bm = bond_item.bond_model
			if bm.atom1 is duplicate_model:
				# skip if this would create a self-bond
				if bm.atom2 is survivor_model:
					continue
				cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
					bm, "atom1", duplicate_model, survivor_model,
					text="Merge atom endpoint",
				)
				undo_stack.push(cmd)
			elif bm.atom2 is duplicate_model:
				if bm.atom1 is survivor_model:
					continue
				cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
					bm, "atom2", duplicate_model, survivor_model,
					text="Merge atom endpoint",
				)
				undo_stack.push(cmd)
		# remove the duplicate atom from its molecule
		view = self._view
		if hasattr(view, "document") and view.document is not None:
			for mol_model in view.document.molecules:
				if duplicate_model in mol_model.atoms:
					cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
						scene, mol_model, duplicate_model,
						duplicate_item, [],
					)
					undo_stack.push(cmd)
					break
		undo_stack.endMacro()

	# ------------------------------------------------------------------
	# Preview line helpers
	# ------------------------------------------------------------------

	#============================================
	def _remove_preview_line(self) -> None:
		"""Remove the bond preview line from the scene."""
		if self._preview_line is not None:
			scene = self._view.scene()
			if scene is not None:
				scene.removeItem(self._preview_line)
			self._preview_line = None

	# ------------------------------------------------------------------
	# Lookup helpers
	# ------------------------------------------------------------------

	#============================================
	def _find_undo_stack(self):
		"""Locate the document's QUndoStack through the view.

		Returns:
			QUndoStack or None if not accessible.
		"""
		view = self._view
		if hasattr(view, "document") and view.document is not None:
			return view.document.undo_stack
		return None

	#============================================
	def _get_active_molecule(self):
		"""Get or create the active MoleculeModel for drawing.

		If the document has molecules, returns the first one. Otherwise
		creates a new molecule and adds it to the document.

		Returns:
			MoleculeModel or None if no document is available.
		"""
		view = self._view
		if not hasattr(view, "document") or view.document is None:
			return None
		doc = view.document
		if doc.molecules:
			return doc.molecules[0]
		# create a new molecule for the document
		import bkchem_qt.models.molecule_model
		mol_model = bkchem_qt.models.molecule_model.MoleculeModel()
		doc.add_molecule(mol_model)
		return mol_model
