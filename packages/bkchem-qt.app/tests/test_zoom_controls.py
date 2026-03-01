"""Tests for zoom controls: view API, main window handlers, and widget."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.widgets.zoom_controls


#============================================
def test_zoom_in_increases_percent(main_window):
	"""Calling on_zoom_in raises the zoom percent above 100."""
	main_window.on_zoom_in()
	assert main_window.view.zoom_percent > 100


#============================================
def test_zoom_out_decreases_percent(main_window):
	"""Calling on_zoom_out lowers the zoom percent below 100."""
	main_window.on_zoom_out()
	assert main_window.view.zoom_percent < 100


#============================================
def test_reset_zoom_returns_100(main_window):
	"""Zoom in then reset returns zoom percent to 100."""
	main_window.on_zoom_in()
	assert main_window.view.zoom_percent != 100
	main_window.on_reset_zoom()
	assert main_window.view.zoom_percent == pytest.approx(100.0)


#============================================
def test_zoom_to_fit_no_crash(main_window):
	"""Calling on_zoom_to_fit does not raise an exception."""
	main_window.on_zoom_to_fit()


#============================================
def test_zoom_to_content_no_crash(main_window):
	"""Calling on_zoom_to_content does not raise an exception."""
	main_window.on_zoom_to_content()


#============================================
def test_set_zoom_percent(main_window):
	"""set_zoom_percent(200) sets zoom to approximately 200%."""
	main_window.view.set_zoom_percent(200)
	assert main_window.view.zoom_percent == pytest.approx(200.0, abs=1.0)


#============================================
def test_zoom_controls_widget_exists(main_window):
	"""MainWindow has a _zoom_controls attribute that is a ZoomControls."""
	assert hasattr(main_window, "_zoom_controls")
	assert isinstance(
		main_window._zoom_controls,
		bkchem_qt.widgets.zoom_controls.ZoomControls,
	)


#============================================
def test_zoom_controls_label_updates(main_window):
	"""After zooming in, the zoom controls label no longer reads 100%."""
	main_window.on_zoom_in()
	label_text = main_window._zoom_controls._label.text()
	assert label_text != "100%"
