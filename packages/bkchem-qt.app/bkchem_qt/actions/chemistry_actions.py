"""Chemistry menu action registrations for BKChem-Qt."""

# Standard Library
import collections

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import oasa.periodic_table
import oasa.peptide_utils
import bkchem_qt.io.format_bridge
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.actions.file_actions
import bkchem_qt.undo.commands
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _get_mols_for_info(app) -> list:
	"""Return selected molecules, or all document molecules if none selected.

	Args:
		app: MainWindow instance with document attribute.

	Returns:
		List of MoleculeModel instances.
	"""
	mols = app.document.selected_mols
	if not mols:
		mols = app.document.molecules
	return mols


#============================================
def _compute_formula(mol) -> str:
	"""Compute the molecular formula string for a MoleculeModel.

	Uses Hill system ordering: C first, H second, then alphabetical.

	Args:
		mol: MoleculeModel instance.

	Returns:
		Formula string, e.g. 'C6H12O6'.
	"""
	# count element symbols across all atoms
	counts = collections.Counter()
	for atom_model in mol.atoms:
		counts[atom_model.symbol] += 1
	# Hill system: C first, H second, then alphabetical
	parts = []
	for element in ("C", "H"):
		if element in counts:
			count = counts[element]
			if count == 1:
				parts.append(element)
			else:
				parts.append(f"{element}{count}")
	# remaining elements in alphabetical order
	for element in sorted(counts.keys()):
		if element in ("C", "H"):
			continue
		count = counts[element]
		if count == 1:
			parts.append(element)
		else:
			parts.append(f"{element}{count}")
	formula = "".join(parts)
	return formula


#============================================
def _compute_molecular_weight(mol) -> float:
	"""Compute the molecular weight for a MoleculeModel.

	Sums atomic weights from the OASA periodic table for each atom.

	Args:
		mol: MoleculeModel instance.

	Returns:
		Molecular weight as a float.
	"""
	total = 0.0
	pt = oasa.periodic_table.periodic_table
	for atom_model in mol.atoms:
		entry = pt.get(atom_model.symbol)
		if entry:
			total += entry.get("weight", 0.0)
		else:
			total += 0.0
	return total


#============================================
def _chemistry_info(app) -> None:
	"""Display summary info on selected (or all) molecules.

	Shows atom count, bond count, formula, and molecular weight for
	each molecule in a QMessageBox.

	Args:
		app: MainWindow instance.
	"""
	mols = _get_mols_for_info(app)
	if not mols:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Molecule Info", "No molecules in the document."
		)
		return
	# build info text for each molecule
	lines = []
	for idx, mol in enumerate(mols, start=1):
		n_atoms = len(mol.atoms)
		n_bonds = len(mol.bonds)
		formula = _compute_formula(mol)
		mw = _compute_molecular_weight(mol)
		mol_name = mol.name if mol.name else f"Molecule {idx}"
		lines.append(f"--- {mol_name} ---")
		lines.append(f"  Atoms: {n_atoms}")
		lines.append(f"  Bonds: {n_bonds}")
		lines.append(f"  Formula: {formula}")
		lines.append(f"  Molecular weight: {mw:.2f}")
		lines.append("")
	info_text = "\n".join(lines)
	PySide6.QtWidgets.QMessageBox.information(
		app, "Molecule Info", info_text
	)


#============================================
def _chemistry_check(app) -> None:
	"""Check selected molecules for valency violations.

	For each selected molecule, checks each atom's free_valency.
	Reports any atoms with free_valency < 0 in a QMessageBox.

	Args:
		app: MainWindow instance.
	"""
	mols = app.document.selected_mols
	if not mols:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Check Chemistry", "No molecules selected."
		)
		return
	# check each atom in each molecule
	problems = []
	for mol in mols:
		for atom_model in mol.atoms:
			free_val = atom_model.free_valency
			if free_val < 0:
				msg = (
					f"Atom {atom_model.symbol} "
					f"(charge={atom_model.charge}): "
					f"free valency = {free_val}"
				)
				problems.append(msg)
	if problems:
		result_text = "Valency violations found:\n\n" + "\n".join(problems)
	else:
		result_text = "All atoms pass valency check."
	PySide6.QtWidgets.QMessageBox.information(
		app, "Check Chemistry", result_text
	)


#============================================
def _expand_groups(app) -> None:
	"""Show placeholder dialog for group expansion.

	Args:
		app: MainWindow instance.
	"""
	PySide6.QtWidgets.QMessageBox.information(
		app, "Expand Groups",
		"Group expansion requires OASA fragment library support.\n"
		"This feature will be available in a future release."
	)


#============================================
def _int_to_roman_oxidation(n: int) -> str:
	"""Convert an integer to a signed Roman numeral oxidation state string.

	Standard chemistry convention: +III, -II, 0, etc.

	Args:
		n: Integer oxidation number.

	Returns:
		Signed Roman numeral string (e.g. -2 -> '-II', +3 -> '+III', 0 -> '0').
	"""
	if n == 0:
		return "0"
	# build the roman numeral from the absolute value
	abs_n = abs(n)
	roman_pairs = [
		(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
		(100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
		(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
	]
	parts = []
	for value, numeral in roman_pairs:
		while abs_n >= value:
			parts.append(numeral)
			abs_n -= value
	sign = "+" if n > 0 else "-"
	roman_str = sign + "".join(parts)
	return roman_str


#============================================
def _oxidation_number(app) -> None:
	"""Compute and display oxidation numbers for atoms in selected molecules.

	For each selected molecule, iterates atoms and computes the oxidation
	number via the OASA electronegativity-based algorithm. Results are
	displayed in a QMessageBox with per-molecule headings.

	Args:
		app: MainWindow instance.
	"""
	mols = app.document.selected_mols
	if not mols:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Oxidation Number", "No molecules selected."
		)
		return
	# build result text for each molecule
	lines = []
	for idx, mol in enumerate(mols, start=1):
		mol_name = mol.name if mol.name else f"Molecule {idx}"
		lines.append(f"--- {mol_name} ---")
		for atom_model in mol.atoms:
			ox_num = atom_model.oxidation_number
			roman = _int_to_roman_oxidation(ox_num)
			lines.append(f"  {atom_model.symbol}: {roman}")
		lines.append("")
	result_text = "\n".join(lines)
	PySide6.QtWidgets.QMessageBox.information(
		app, "Oxidation Number", result_text
	)


#============================================
def _read_smiles(app) -> None:
	"""Prompt for a SMILES string and import as a molecule.

	Parses the SMILES via OASA, generates 2D coordinates, converts
	to a MoleculeModel, and adds it to the scene.

	Args:
		app: MainWindow instance.
	"""
	text, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Import SMILES", "Enter SMILES string:"
	)
	if not ok or not text.strip():
		return
	smiles_string = text.strip()
	# parse via OASA smiles_lib
	try:
		from oasa import smiles_lib
		oasa_mol = smiles_lib.text_to_mol(smiles_string)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "SMILES Error",
			f"Failed to parse SMILES:\n{exc}"
		)
		return
	# generate 2D coordinates
	try:
		from oasa import coords_generator
		coords_generator.calculate_coords(oasa_mol, bond_length=1.0, force=1)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Coordinate Error",
			f"Failed to generate coordinates:\n{exc}"
		)
		return
	# convert and add to scene
	mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(oasa_mol)
	bkchem_qt.actions.file_actions._add_molecules_to_scene(app, [mol_model])
	app.statusBar().showMessage("Imported SMILES molecule", 3000)


#============================================
def _read_inchi(app) -> None:
	"""Prompt for an InChI string and import as a molecule.

	Parses the InChI via OASA, generates 2D coordinates, converts
	to a MoleculeModel, and adds it to the scene.

	Args:
		app: MainWindow instance.
	"""
	text, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Import InChI", "Enter InChI string:"
	)
	if not ok or not text.strip():
		return
	inchi_string = text.strip()
	# parse via OASA inchi_lib
	try:
		from oasa import inchi_lib
		oasa_mol = inchi_lib.text_to_mol(inchi_string)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "InChI Error",
			f"Failed to parse InChI:\n{exc}"
		)
		return
	# generate 2D coordinates
	try:
		from oasa import coords_generator
		coords_generator.calculate_coords(oasa_mol, bond_length=1.0, force=1)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Coordinate Error",
			f"Failed to generate coordinates:\n{exc}"
		)
		return
	# convert and add to scene
	mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(oasa_mol)
	bkchem_qt.actions.file_actions._add_molecules_to_scene(app, [mol_model])
	app.statusBar().showMessage("Imported InChI molecule", 3000)


#============================================
def _read_peptide(app) -> None:
	"""Prompt for a peptide sequence and import as a molecule.

	Validates single-letter amino acid codes, converts the sequence
	to SMILES via OASA, generates 2D coordinates, converts to a
	MoleculeModel, and adds it to the scene.

	Args:
		app: MainWindow instance.
	"""
	# build prompt listing supported amino acid codes
	supported = sorted(oasa.peptide_utils.AMINO_ACID_SMILES.keys())
	supported_str = ", ".join(supported)
	prompt_text = (
		"Enter a single-letter amino acid sequence (e.g. ANKLE):\n"
		f"Supported: {supported_str}"
	)
	text, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Import Peptide Sequence", prompt_text
	)
	if not ok or not text.strip():
		return
	# validate input letters before sending to OASA
	sequence = text.strip().upper()
	bad_letters = [
		aa for aa in sequence
		if aa not in oasa.peptide_utils.AMINO_ACID_SMILES
	]
	if bad_letters:
		unique_bad = ", ".join(sorted(set(bad_letters)))
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Peptide Sequence Error",
			f"Unrecognized amino acid code(s): {unique_bad}\n"
			f"Supported: {supported_str}"
		)
		return
	# convert peptide sequence to SMILES
	try:
		smiles_string = oasa.peptide_utils.sequence_to_smiles(sequence)
	except ValueError as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Peptide Sequence Error",
			f"Failed to convert peptide sequence:\n{exc}"
		)
		return
	# parse SMILES via OASA smiles_lib
	try:
		from oasa import smiles_lib
		oasa_mol = smiles_lib.text_to_mol(smiles_string)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "SMILES Error",
			f"Failed to parse peptide SMILES:\n{exc}"
		)
		return
	# generate 2D coordinates
	try:
		from oasa import coords_generator
		coords_generator.calculate_coords(oasa_mol, bond_length=1.0, force=1)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Coordinate Error",
			f"Failed to generate coordinates:\n{exc}"
		)
		return
	# convert and add to scene
	mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(oasa_mol)
	bkchem_qt.actions.file_actions._add_molecules_to_scene(app, [mol_model])
	app.statusBar().showMessage(
		f"Imported peptide sequence '{sequence}'", 3000
	)


#============================================
def _gen_smiles(app) -> None:
	"""Export SMILES for the single selected molecule.

	Copies the SMILES string to the clipboard and displays it
	in a dialog.

	Args:
		app: MainWindow instance.
	"""
	mols = app.document.selected_mols
	if len(mols) != 1:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Export SMILES",
			"Please select exactly one molecule."
		)
		return
	mol = mols[0]
	try:
		smiles_str = bkchem_qt.io.format_bridge.export_smiles(mol)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "SMILES Export Error",
			f"Failed to generate SMILES:\n{exc}"
		)
		return
	# copy to clipboard
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	clipboard.setText(smiles_str)
	# show in dialog
	PySide6.QtWidgets.QMessageBox.information(
		app, "Export SMILES",
		f"SMILES (copied to clipboard):\n\n{smiles_str}"
	)


#============================================
def _gen_inchi(app) -> None:
	"""Export InChI for the single selected molecule.

	Copies the InChI string to the clipboard and displays InChI
	and InChIKey in a dialog.

	Args:
		app: MainWindow instance.
	"""
	mols = app.document.selected_mols
	if len(mols) != 1:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Export InChI",
			"Please select exactly one molecule."
		)
		return
	mol = mols[0]
	try:
		inchi_str, inchikey_str, warnings = (
			bkchem_qt.io.format_bridge.export_inchi(mol)
		)
	except Exception as exc:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "InChI Export Error",
			f"Failed to generate InChI:\n{exc}"
		)
		return
	# copy InChI to clipboard
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	clipboard.setText(inchi_str)
	# build display message
	lines = [
		f"InChI (copied to clipboard):\n{inchi_str}",
		f"\nInChIKey:\n{inchikey_str}",
	]
	if warnings:
		lines.append(f"\nWarnings:\n{', '.join(warnings)}")
	info_text = "\n".join(lines)
	PySide6.QtWidgets.QMessageBox.information(
		app, "Export InChI", info_text
	)


#============================================
def _set_name(app) -> None:
	"""Set the name of the single selected molecule via input dialog.

	Uses ChangePropertyCommand for undo support.

	Args:
		app: MainWindow instance.
	"""
	mols = app.document.selected_mols
	if len(mols) != 1:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Set Molecule Name",
			"Please select exactly one molecule."
		)
		return
	mol = mols[0]
	current_name = mol.name or ""
	new_name, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Set Molecule Name", "Molecule name:",
		text=current_name
	)
	if not ok:
		return
	# push undoable command
	cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
		mol, "name", current_name, new_name, "Set Molecule Name"
	)
	app.document.undo_stack.push(cmd)


#============================================
def _set_id(app) -> None:
	"""Set the ID of the single selected molecule via input dialog.

	Uses ChangePropertyCommand for undo support.

	Args:
		app: MainWindow instance.
	"""
	mols = app.document.selected_mols
	if len(mols) != 1:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Set Molecule ID",
			"Please select exactly one molecule."
		)
		return
	mol = mols[0]
	current_id = mol.mol_id or ""
	new_id, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Set Molecule ID", "Molecule ID:",
		text=current_id
	)
	if not ok:
		return
	# push undoable command
	cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
		mol, "mol_id", current_id, new_id, "Set Molecule ID"
	)
	app.document.undo_stack.push(cmd)


#============================================
def _create_fragment(app) -> None:
	"""Show placeholder dialog for fragment creation.

	Args:
		app: MainWindow instance.
	"""
	PySide6.QtWidgets.QMessageBox.information(
		app, "Create Fragment",
		"Fragment operations require OASA fragment library support.\n"
		"This feature will be available in a future release."
	)


#============================================
def _view_fragments(app) -> None:
	"""Show placeholder dialog for viewing fragments.

	Args:
		app: MainWindow instance.
	"""
	PySide6.QtWidgets.QMessageBox.information(
		app, "View Fragments",
		"Fragment operations require OASA fragment library support.\n"
		"This feature will be available in a future release."
	)


#============================================
def _convert_to_linear(app) -> None:
	"""Show placeholder dialog for linear form conversion.

	Args:
		app: MainWindow instance.
	"""
	PySide6.QtWidgets.QMessageBox.information(
		app, "Convert to Linear Form",
		"Fragment operations require OASA fragment library support.\n"
		"This feature will be available in a future release."
	)


#============================================
def register_chemistry_actions(registry, app) -> None:
	"""Register all Chemistry menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# predicates
	def has_selection():
		"""Return True when the document has selected items."""
		return app.document.has_selection

	def one_mol_selected():
		"""Return True when exactly one molecule is selected."""
		return app.document.one_mol_selected

	# display summary info on selected molecules
	registry.register(MenuAction(
		id='chemistry.info',
		label_key='Info',
		help_key='Display summary formula and other info on all selected molecules',
		accelerator=None,
		handler=lambda: _chemistry_info(app),
		enabled_when=None,
	))

	# check if selected objects have chemical meaning
	registry.register(MenuAction(
		id='chemistry.check',
		label_key='Check chemistry',
		help_key='Check if the selected objects have chemical meaning',
		accelerator=None,
		handler=lambda: _chemistry_check(app),
		enabled_when=has_selection,
	))

	# expand all selected groups to their structures
	registry.register(MenuAction(
		id='chemistry.expand_groups',
		label_key='Expand groups',
		help_key='Expand all selected groups to their structures',
		accelerator=None,
		handler=lambda: _expand_groups(app),
		enabled_when=has_selection,
	))

	# compute and display oxidation number
	registry.register(MenuAction(
		id='chemistry.oxidation_number',
		label_key='Compute oxidation number',
		help_key='Compute and display the oxidation number of selected atoms',
		accelerator=None,
		handler=lambda: _oxidation_number(app),
		enabled_when=has_selection,
	))

	# import a SMILES string as structure
	registry.register(MenuAction(
		id='chemistry.read_smiles',
		label_key='Import SMILES',
		help_key='Import a SMILES string and convert it to structure',
		accelerator=None,
		handler=lambda: _read_smiles(app),
		enabled_when=None,
	))

	# import an InChI string as structure
	registry.register(MenuAction(
		id='chemistry.read_inchi',
		label_key='Import InChI',
		help_key='Import an InChI string and convert it to structure',
		accelerator=None,
		handler=lambda: _read_inchi(app),
		enabled_when=None,
	))

	# import a peptide amino acid sequence as structure
	registry.register(MenuAction(
		id='chemistry.read_peptide',
		label_key='Import Peptide Sequence',
		help_key='Import a peptide amino acid sequence and convert it to structure',
		accelerator=None,
		handler=lambda: _read_peptide(app),
		enabled_when=None,
	))

	# export SMILES for the selected structure
	registry.register(MenuAction(
		id='chemistry.gen_smiles',
		label_key='Export SMILES',
		help_key='Export SMILES for the selected structure',
		accelerator=None,
		handler=lambda: _gen_smiles(app),
		enabled_when=one_mol_selected,
	))

	# export InChI for the selected structure
	registry.register(MenuAction(
		id='chemistry.gen_inchi',
		label_key='Export InChI',
		help_key='Export an InChI for the selected structure by calling the InChI program',
		accelerator=None,
		handler=lambda: _gen_inchi(app),
		enabled_when=one_mol_selected,
	))

	# set the name of the selected molecule
	registry.register(MenuAction(
		id='chemistry.set_name',
		label_key='Set molecule name',
		help_key='Set the name of the selected molecule',
		accelerator=None,
		handler=lambda: _set_name(app),
		enabled_when=one_mol_selected,
	))

	# set the ID of the selected molecule
	registry.register(MenuAction(
		id='chemistry.set_id',
		label_key='Set molecule ID',
		help_key='Set the ID of the selected molecule',
		accelerator=None,
		handler=lambda: _set_id(app),
		enabled_when=one_mol_selected,
	))

	# create a fragment from the selected part of the molecule
	registry.register(MenuAction(
		id='chemistry.create_fragment',
		label_key='Create fragment',
		help_key='Create a fragment from the selected part of the molecule',
		accelerator=None,
		handler=lambda: _create_fragment(app),
		enabled_when=has_selection,
	))

	# show already defined fragments
	registry.register(MenuAction(
		id='chemistry.view_fragments',
		label_key='View fragments',
		help_key='Show already defined fragments',
		accelerator=None,
		handler=lambda: _view_fragments(app),
		enabled_when=None,
	))

	# convert selected part of chain to linear fragment
	registry.register(MenuAction(
		id='chemistry.convert_to_linear',
		label_key='Convert selection to linear form',
		help_key='Convert selected part of chain to linear fragment',
		accelerator=None,
		handler=lambda: _convert_to_linear(app),
		enabled_when=has_selection,
	))
