"""Clipboard manager for copy/paste of CDML molecule data."""

# Standard Library
import xml.dom.minidom

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import oasa.cdml_writer
import bkchem_qt.io.cdml_io
import bkchem_qt.bridge.oasa_bridge

# custom MIME type for BKChem CDML clipboard data
CDML_MIME_TYPE = "application/x-bkchem-cdml"

# paste offset in scene-space points to avoid exact overlap
_PASTE_OFFSET_PX = 20.0


#============================================
class ClipboardManager:
	"""Manages copy and paste of molecule data via the system clipboard.

	Molecules are serialized to CDML XML for clipboard storage and
	deserialized back when pasting. Supports both a custom MIME type
	(application/x-bkchem-cdml) and plain-text CDML as a fallback.
	"""

	#============================================
	def copy_selection(self, document) -> int:
		"""Serialize selected molecules to CDML and place on clipboard.

		Reads the selected MoleculeModels from the document, converts
		each to OASA molecules, serializes to a CDML XML string, and
		stores on the system clipboard with both a custom MIME type
		and a plain text fallback.

		Args:
			document: Document model with a ``selected_mols`` property.

		Returns:
			Number of molecules copied, or 0 if nothing was selected.
		"""
		mols = document.selected_mols
		if not mols:
			return 0
		# serialize selected molecules to CDML XML string
		cdml_text = _mols_to_cdml(mols)
		if not cdml_text:
			return 0
		# place on clipboard with custom MIME and plain text fallback
		clipboard = PySide6.QtWidgets.QApplication.clipboard()
		mime_data = PySide6.QtCore.QMimeData()
		mime_data.setData(
			CDML_MIME_TYPE,
			PySide6.QtCore.QByteArray(cdml_text.encode("utf-8")),
		)
		mime_data.setText(cdml_text)
		clipboard.setMimeData(mime_data)
		count = len(mols)
		return count

	#============================================
	def paste(self) -> list:
		"""Read CDML from clipboard and return parsed MoleculeModels.

		Checks the system clipboard for CDML data, first via the
		custom MIME type and then as plain text containing CDML tags.
		Parsed molecules are offset slightly to avoid exact overlap
		with previously pasted content.

		Returns:
			List of MoleculeModel instances, or empty list on failure.
			The first element is a status string: 'ok', 'no_data',
			or 'parse_error'. Actual return is a tuple (status, list).
		"""
		cdml_text = _read_cdml_from_clipboard()
		if cdml_text is None:
			return ("no_data", [])
		molecules = bkchem_qt.io.cdml_io.load_cdml_string(cdml_text)
		if not molecules:
			return ("parse_error", [])
		# offset pasted molecules to avoid exact overlap
		for mol_model in molecules:
			for atom_model in mol_model.atoms:
				atom_model.x = atom_model.x + _PASTE_OFFSET_PX
				atom_model.y = atom_model.y + _PASTE_OFFSET_PX
		return ("ok", molecules)

	#============================================
	def can_paste(self) -> bool:
		"""Check whether the clipboard contains valid CDML content.

		Returns:
			True if the clipboard has CDML data that could be pasted.
		"""
		clipboard = PySide6.QtWidgets.QApplication.clipboard()
		mime_data = clipboard.mimeData()
		if mime_data is None:
			return False
		if mime_data.hasFormat(CDML_MIME_TYPE):
			return True
		if mime_data.hasText():
			text = mime_data.text()
			if "<cdml" in text or "<molecule" in text:
				return True
		return False


#============================================
def _read_cdml_from_clipboard() -> str:
	"""Read CDML text from the system clipboard.

	Checks the custom MIME type first, then falls back to plain text
	containing recognized CDML tags.

	Returns:
		CDML XML string, or None if no CDML data is available.
	"""
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	mime_data = clipboard.mimeData()
	# prefer custom MIME type
	if mime_data.hasFormat(CDML_MIME_TYPE):
		raw = mime_data.data(CDML_MIME_TYPE)
		cdml_text = bytes(raw).decode("utf-8")
		return cdml_text
	# fall back to plain text containing CDML tags
	if mime_data.hasText():
		text = mime_data.text()
		if "<cdml" in text or "<molecule" in text:
			return text
	return None


#============================================
def _mols_to_cdml(mols: list) -> str:
	"""Serialize a list of MoleculeModels to a CDML XML string.

	Converts each MoleculeModel to an OASA molecule, then writes
	all molecules into a single CDML document.

	Args:
		mols: List of MoleculeModel instances to serialize.

	Returns:
		CDML XML string, or empty string on failure.
	"""
	xml_doc = xml.dom.minidom.Document()
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
			oasa_mol,
			doc=xml_doc,
			coord_to_text=bkchem_qt.io.cdml_io._px_to_cm_text,
		)
		cdml_el.appendChild(mol_el)
	xml_doc.appendChild(cdml_el)
	xml_text = xml_doc.toxml(encoding="utf-8").decode("utf-8")
	return xml_text
