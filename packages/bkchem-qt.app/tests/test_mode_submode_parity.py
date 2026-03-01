"""Tests for mode submode parity: template, draw, and biotemplate modes."""


#============================================
def test_template_mode_has_submodes(main_window):
	"""Switch to template mode and verify submodes is non-empty."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("template")
	mode = mode_manager.current_mode
	assert mode is not None, "template mode should be active"
	assert isinstance(mode.submodes, list), "submodes should be a list"
	assert len(mode.submodes) > 0, "template mode should have submodes"
	# the first group should contain template names
	assert len(mode.submodes[0]) > 0, (
		"template mode group 0 should have entries"
	)


#============================================
def test_template_submode_sets_template(main_window):
	"""Switch to template mode and verify on_submode_switch changes template."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("template")
	mode = mode_manager.current_mode
	assert mode is not None, "template mode should be active"
	# need at least two templates to test switching
	if len(mode.submodes[0]) < 2:
		return
	# record initial template
	initial_template = mode._current_template
	# switch to the second template
	second_name = mode.submodes[0][1]
	mode.on_submode_switch(0, second_name)
	assert mode._current_template == second_name, (
		f"expected _current_template={second_name!r}, "
		f"got {mode._current_template!r}"
	)
	assert mode._current_template != initial_template, (
		"template should have changed after on_submode_switch"
	)


#============================================
def test_draw_mode_has_submodes(main_window):
	"""Switch to draw mode and verify submodes are present from YAML."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("draw")
	mode = mode_manager.current_mode
	assert mode is not None, "draw mode should be active"
	assert isinstance(mode.submodes, list), "submodes should be a list"
	assert len(mode.submodes) > 0, (
		"draw mode should have submodes injected from YAML"
	)


#============================================
def test_biotemplate_mode_has_categories(main_window):
	"""Switch to biotemplate mode and verify category group is present."""
	mode_manager = main_window._mode_manager
	mode_manager.set_mode("biotemplate")
	mode = mode_manager.current_mode
	assert mode is not None, "biotemplate mode should be active"
	assert isinstance(mode.submodes, list), "submodes should be a list"
	assert len(mode.submodes) > 0, (
		"biotemplate mode should have submodes"
	)
	# group 0 should be the category group
	assert len(mode.submodes[0]) > 0, (
		"biotemplate mode group 0 (categories) should have entries"
	)
	# verify group_labels includes Category
	assert "Category" in mode.group_labels, (
		f"group_labels should contain 'Category', got {mode.group_labels}"
	)
