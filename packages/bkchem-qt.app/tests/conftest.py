"""Shared pytest fixtures for bkchem-qt tests."""

# Standard Library
import os
import gc

# PIP3 modules
import pytest
import PySide6.QtWidgets
import PySide6.QtTest

# local repo modules
import bkchem_qt.themes.theme_manager
import bkchem_qt.main_window


# force offscreen rendering so tests run without a display server
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


#============================================
def _env_is_truthy(name: str) -> bool:
	"""Return True when an env var is set to a truthy value."""
	value = os.environ.get(name, "").strip().lower()
	return value in ("1", "true", "yes", "on")


#============================================
def _env_int(name: str, default: int = 0) -> int:
	"""Parse integer env var with safe fallback."""
	raw = os.environ.get(name, "")
	if not raw.strip():
		return default
	try:
		return int(raw)
	except ValueError:
		return default


VISUAL_TEST_MODE = _env_is_truthy("BKCHEM_QT_TEST_VISUAL")
VISUAL_HOLD_MS = max(0, _env_int("BKCHEM_QT_TEST_VISUAL_HOLD_MS", 0))


#============================================
def _using_offscreen_backend() -> bool:
	"""Return True when tests are running with offscreen Qt platform."""
	return os.environ.get("QT_QPA_PLATFORM", "").strip().lower() == "offscreen"


#============================================
def _should_show_windows(request) -> bool:
	"""Decide whether GUI windows should be shown during pytest runs.

	Visual mode is enabled either explicitly via env var or implicitly
	when capture is disabled (-s) on a non-offscreen platform.
	"""
	if VISUAL_TEST_MODE:
		return True
	capture_mode = request.config.getoption("capture")
	return capture_mode == "no" and not _using_offscreen_backend()


#============================================
@pytest.fixture(scope="session")
def qapp():
	"""Return the QApplication singleton, creating it if needed.

	Returns:
		QApplication: The application instance.
	"""
	app = PySide6.QtWidgets.QApplication.instance()
	if app is None:
		app = PySide6.QtWidgets.QApplication([])
	yield app
	# Explicit Qt teardown avoids GC-time shiboken crashes on interpreter exit.
	for widget in list(app.topLevelWidgets()):
		widget.close()
		widget.deleteLater()
	app.processEvents()
	PySide6.QtWidgets.QApplication.sendPostedEvents()
	app.processEvents()
	gc.collect()


#============================================
@pytest.fixture(scope="session")
def theme_manager(qapp):
	"""Return a ThemeManager bound to the QApplication.

	Args:
		qapp: The QApplication fixture.

	Returns:
		ThemeManager: The theme manager instance.
	"""
	tm = bkchem_qt.themes.theme_manager.ThemeManager(qapp)
	return tm


#============================================
@pytest.fixture(scope="module")
def main_window(qapp, theme_manager, request):
	"""Return a MainWindow shared across tests in the same module.

	Module scope avoids creating 45+ MainWindow instances during the
	full test suite. Each test module gets one MainWindow that is
	closed at module teardown.

	Args:
		qapp: The QApplication fixture.
		theme_manager: The ThemeManager fixture.

	Yields:
		MainWindow: The main window instance.
	"""
	mw = bkchem_qt.main_window.MainWindow(theme_manager)
	if _should_show_windows(request):
		mw.show()
		mw.raise_()
		mw.activateWindow()
		qapp.processEvents()
	yield mw
	mw.close()
	mw.deleteLater()
	qapp.processEvents()


#============================================
@pytest.fixture(autouse=True)
def _reset_main_window(main_window):
	"""Reset document and scene state before each test for isolation."""
	# clear all molecules from document (also clears undo stack)
	main_window.document.clear()
	# remove all scene items except paper rect and grid group
	scene = main_window.scene
	keep = {id(scene._paper_item)}
	if scene._grid_group is not None:
		keep.add(id(scene._grid_group))
	for item in list(scene.items()):
		if id(item) in keep:
			continue
		# skip grid children (they belong to the group)
		if item.group() is scene._grid_group:
			continue
		scene.removeItem(item)
	# reset zoom to 100%
	main_window.view.reset_zoom()
	yield
	if main_window.isVisible() and VISUAL_HOLD_MS > 0:
		main_window.repaint()
		PySide6.QtWidgets.QApplication.processEvents()
		PySide6.QtTest.QTest.qWait(VISUAL_HOLD_MS)
