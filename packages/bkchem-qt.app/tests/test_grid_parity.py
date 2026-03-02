"""Grid visual parity tests for BKChem-Qt.

Verifies that the ChemScene grid overlay behaves correctly: visible by
default, togglable, snappable, populated with child items, and
resilient across theme changes.

Usage:
	source source_me.sh && QT_QPA_PLATFORM=offscreen python3 -m pytest \
		packages/bkchem-qt.app/tests/test_grid_parity.py -v
"""


#============================================
def test_grid_visible_by_default(main_window):
	"""Verify the grid is visible when the scene is first created."""
	scene = main_window.scene
	assert scene.grid_visible is True, (
		"grid should be visible by default on a fresh scene"
	)


#============================================
def test_grid_toggle(main_window):
	"""Toggle grid off and on, verifying visibility at each step."""
	scene = main_window.scene

	# hide the grid
	scene.set_grid_visible(False)
	assert scene.grid_visible is False, (
		"grid_visible should be False after set_grid_visible(False)"
	)

	# show the grid again
	scene.set_grid_visible(True)
	assert scene.grid_visible is True, (
		"grid_visible should be True after set_grid_visible(True)"
	)


#============================================
def test_grid_snap(main_window):
	"""Call snap_to_grid with arbitrary coords and verify the return type."""
	scene = main_window.scene

	# use arbitrary coordinates that are unlikely to land on a grid point
	result = scene.snap_to_grid(137.3, 248.9)
	assert isinstance(result, tuple), (
		f"snap_to_grid should return a tuple, got {type(result).__name__}"
	)
	assert len(result) == 2, (
		f"snap_to_grid should return a 2-tuple, got length {len(result)}"
	)
	# both elements should be numeric floats (or ints coercible to float)
	assert isinstance(result[0], (int, float)), (
		f"snapped x should be numeric, got {type(result[0]).__name__}"
	)
	assert isinstance(result[1], (int, float)), (
		f"snapped y should be numeric, got {type(result[1]).__name__}"
	)


#============================================
def test_grid_has_items(main_window):
	"""Verify the grid group contains child items when the grid is visible."""
	scene = main_window.scene

	# grid should be visible by default
	assert scene.grid_visible is True, "precondition: grid should be visible"

	# the grid group should exist
	grid_group = scene._grid_group
	assert grid_group is not None, "grid group should not be None"

	# the grid group should have child items (lines and dots)
	children = grid_group.childItems()
	assert len(children) > 0, (
		"grid group should contain child items when grid is visible"
	)


#============================================
def test_grid_theme_change_rebuilds(main_window):
	"""Apply dark then light themes and verify the grid survives rebuilds."""
	scene = main_window.scene

	# switch to dark theme
	scene.apply_theme("dark")

	# grid should still be visible after theme change
	assert scene.grid_visible is True, (
		"grid should remain visible after apply_theme('dark')"
	)

	# grid group should still have child items
	grid_group = scene._grid_group
	assert grid_group is not None, (
		"grid group should not be None after dark theme apply"
	)
	children = grid_group.childItems()
	assert len(children) > 0, (
		"grid group should contain items after dark theme apply"
	)

	# switch back to light theme to restore state
	scene.apply_theme("light")

	# grid should still be visible after restoring light theme
	assert scene.grid_visible is True, (
		"grid should remain visible after apply_theme('light')"
	)

	# grid group should still have child items
	grid_group_light = scene._grid_group
	assert grid_group_light is not None, (
		"grid group should not be None after light theme apply"
	)
	children_light = grid_group_light.childItems()
	assert len(children_light) > 0, (
		"grid group should contain items after light theme apply"
	)
