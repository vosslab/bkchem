"""Shared pytest fixtures for bkchem-qt tests."""

# Standard Library
import os

# PIP3 modules
import pytest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.themes.theme_manager
import bkchem_qt.main_window


# force offscreen rendering so tests run without a display server
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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
	return app


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
@pytest.fixture()
def main_window(qapp, theme_manager):
	"""Create a fresh MainWindow for each test, then close it.

	Args:
		qapp: The QApplication fixture.
		theme_manager: The ThemeManager fixture.

	Yields:
		MainWindow: The main window instance.
	"""
	mw = bkchem_qt.main_window.MainWindow(theme_manager)
	yield mw
	mw.close()
