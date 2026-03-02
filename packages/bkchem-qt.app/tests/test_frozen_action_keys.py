"""Test that all action keys follow the frozen English key policy.

Validates that every registered action key:
- matches the dotted lowercase pattern
- contains no spaces, uppercase, or display-text fragments
- belongs to a known frozen set that can only grow, not shrink
"""

# Standard Library
import re

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.actions.action_registry

# pattern: dotted lowercase, e.g. 'file.save', 'repair.clean_geometry'
_KEY_PATTERN = re.compile(r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$')

# frozen set of known action keys as of initial creation
# keys can be added but not removed or renamed without updating this set
_KNOWN_KEYS = frozenset({
	'file.new',
	'file.save',
	'file.save_as',
	'file.save_as_template',
	'file.load',
	'file.load_same_tab',
	'file.properties',
	'file.close_tab',
	'file.exit',
	'edit.undo',
	'edit.redo',
	'edit.cut',
	'edit.copy',
	'edit.paste',
	'edit.selected_to_svg',
	'edit.select_all',
	'view.zoom_in',
	'view.zoom_out',
	'view.zoom_reset',
	'view.zoom_to_fit',
	'view.zoom_to_content',
	'insert.biomolecule_template',
	'align.top',
	'align.bottom',
	'align.left',
	'align.right',
	'align.center_h',
	'align.center_v',
	'object.scale',
	'object.bring_to_front',
	'object.send_back',
	'object.swap_on_stack',
	'object.vertical_mirror',
	'object.horizontal_mirror',
	'object.configure',
	'chemistry.info',
	'chemistry.check',
	'chemistry.expand_groups',
	'chemistry.oxidation_number',
	'chemistry.read_smiles',
	'chemistry.read_inchi',
	'chemistry.read_peptide',
	'chemistry.gen_smiles',
	'chemistry.gen_inchi',
	'chemistry.set_name',
	'chemistry.set_id',
	'chemistry.create_fragment',
	'chemistry.view_fragments',
	'chemistry.convert_to_linear',
	'options.standard',
	'options.language',
	'options.logging',
	'options.inchi_path',
	'options.theme',
	'options.preferences',
	'repair.normalize_bond_lengths',
	'repair.snap_to_hex_grid',
	'repair.normalize_bond_angles',
	'repair.normalize_rings',
	'repair.straighten_bonds',
	'repair.clean_geometry',
	'help.keyboard_shortcuts',
	'help.about',
})


#============================================
class _FakeApp:
	"""Minimal stand-in for the main window used by action registrars.

	Returns a no-op callable for any attribute access so that
	handler=app.on_whatever resolves without AttributeError.
	"""

	def __init__(self):
		"""Initialize with required stubs for action registration."""
		self.document = _FakeDocument()
		self._scene = _FakeScene()

	def __getattr__(self, name):
		"""Return a no-op callable for any missing attribute."""
		return lambda *args, **kwargs: None

	def statusBar(self):
		"""Return a fake status bar."""
		return _FakeStatusBar()


#============================================
class _FakeDocument:
	"""Minimal stand-in for the document model."""

	def __init__(self):
		"""Initialize with empty molecule list and undo stack."""
		self.molecules = []
		self.undo_stack = _FakeUndoStack()
		self.selected_mols = []


#============================================
class _FakeUndoStack:
	"""Minimal stand-in for QUndoStack."""

	def undo(self):
		"""No-op undo."""

	def redo(self):
		"""No-op redo."""

	def canUndo(self):
		"""Return False."""
		return False

	def canRedo(self):
		"""Return False."""
		return False


#============================================
class _FakeScene:
	"""Minimal stand-in for the scene."""

	grid_spacing_pt = 40.0

	def items(self):
		"""Return empty item list."""
		return []


#============================================
class _FakeStatusBar:
	"""Minimal stand-in for the status bar."""

	def showMessage(self, msg, timeout=0):
		"""No-op message display."""


#============================================
def _get_all_registered_keys() -> set:
	"""Register all actions and return the set of action IDs."""
	app = _FakeApp()
	registry = bkchem_qt.actions.action_registry.register_all_actions(app)
	all_actions = registry.all_actions()
	return set(all_actions.keys())


#============================================
def test_all_keys_match_dotted_pattern():
	"""Every action key must match ^[a-z][a-z0-9]*(\\.[a-z][a-z0-9_]*)+$."""
	keys = _get_all_registered_keys()
	assert len(keys) > 0, "No action keys registered"
	bad_keys = []
	for key in sorted(keys):
		if not _KEY_PATTERN.match(key):
			bad_keys.append(key)
	assert not bad_keys, (
		f"Action keys violate dotted lowercase pattern: {bad_keys}"
	)


#============================================
def test_no_spaces_or_uppercase_in_keys():
	"""No key should contain spaces or uppercase letters."""
	keys = _get_all_registered_keys()
	for key in sorted(keys):
		assert ' ' not in key, f"Action key contains space: {key!r}"
		assert key == key.lower(), f"Action key has uppercase: {key!r}"


#============================================
def test_known_keys_not_removed():
	"""The frozen set of known keys must not shrink."""
	keys = _get_all_registered_keys()
	missing = _KNOWN_KEYS - keys
	assert not missing, (
		f"Known action keys were removed or renamed: {sorted(missing)}"
	)


#============================================
def test_known_keys_count():
	"""Registered keys should be at least as many as the frozen set."""
	keys = _get_all_registered_keys()
	assert len(keys) >= len(_KNOWN_KEYS), (
		f"Expected at least {len(_KNOWN_KEYS)} keys, got {len(keys)}"
	)
