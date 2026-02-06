#!/usr/bin/env python3
"""Generate biomolecule CDML templates from biomolecule_smiles.yaml or .txt."""

# Standard Library
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ElementTree

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OASA_DIR = os.path.join(REPO_ROOT, "packages", "oasa")
if OASA_DIR not in sys.path:
	sys.path.insert(0, OASA_DIR)

# local repo modules
import oasa


TEMPLATE_ROOT = os.path.join(
	REPO_ROOT,
	"packages",
	"bkchem",
	"bkchem_data",
	"templates",
	"biomolecules",
)
DEFAULT_SMILES_YAML = os.path.join(REPO_ROOT, "docs", "biomolecule_smiles.yaml")
DEFAULT_SMILES_TXT = os.path.join(REPO_ROOT, "docs", "biomolecule_smiles.txt")

LEGACY_NAME_MAP = {
	"carbs/rings/furanose_scaffold": ("carbs", None, "furanose"),
	"carbs/rings/pyranose_scaffold": ("carbs", None, "pyranose"),
	"lipids/fatty_acids/palmitate_anion": ("lipids", None, "palmitate"),
	"nucleic_acids/bases/purine": ("nucleic_acids", "purine", "purine"),
	"nucleic_acids/bases/pyrimidine": ("nucleic_acids", "pyrimidine", "pyrimidine"),
	"protein/amino_acids/L-alanine": ("protein", None, "alanine"),
}


#============================================
def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Generate biomolecule CDML templates from biomolecule_smiles.yaml or .txt."
	)
	parser.add_argument(
		"-i",
		"--input",
		dest="input_path",
		default=None,
		help="Override the input file path.",
	)
	parser.add_argument(
		"--apply",
		action="store_true",
		help="Write generated templates to disk.",
	)
	return parser.parse_args()


#============================================
def read_version(path):
	"""Read the shared version string from version.txt."""
	with open(path, "r") as handle:
		for line in handle:
			text = line.strip()
			if not text or text.startswith("#"):
				continue
			if "=" not in text:
				continue
			name, value = [part.strip() for part in text.split("=", 1)]
			if name.lower() == "version" and value:
				return value
	raise ValueError("version not found in version.txt")


#============================================
def parse_smiles_entries(path):
	"""Parse biomolecule SMILES entries from YAML or text."""
	if path.endswith((".yaml", ".yml")):
		return parse_smiles_entries_yaml(path)
	return parse_smiles_entries_txt(path)


#============================================
def parse_smiles_entries_txt(path):
	"""Parse biomolecule_smiles.txt into a list of entries."""
	entries = []
	with open(path, "r") as handle:
		for line in handle:
			text = line.strip()
			if not text or text.startswith("#"):
				continue
			if ":" not in text:
				raise ValueError(f"Invalid biomolecule_smiles.txt line: {text}")
			label, smiles = text.split(":", 1)
			label = re.sub(r"\s*\(.*\)$", "", label.strip())
			parts = [part.strip() for part in label.split("/")]
			if len(parts) != 2:
				raise ValueError(f"Invalid biomolecule label: {label}")
			entries.append(
				{
					"category": parts[0],
					"subcategory": None,
					"name": parts[1],
					"display_name": parts[1],
					"smiles": smiles.strip(),
				}
			)
	return entries


#============================================
def parse_smiles_entries_yaml(path):
	"""Parse biomolecule_smiles.yaml into a list of entries."""
	entries = []
	stack = []
	with open(path, "r") as handle:
		for line in handle:
			raw = line.rstrip("\n")
			if not raw.strip() or raw.lstrip().startswith("#"):
				continue
			cleaned = _strip_yaml_comment(raw)
			if not cleaned.strip():
				continue
			indent = len(cleaned) - len(cleaned.lstrip(" "))
			content = cleaned.strip()
			if ":" not in content:
				continue
			key, value = content.split(":", 1)
			key = key.strip()
			value = value.strip()
			while stack and indent <= stack[-1][0]:
				stack.pop()
			if value == "":
				stack.append((indent, key))
				continue
			if key != "smiles":
				continue
			smiles = _strip_yaml_quotes(value)
			if not stack:
				raise ValueError("YAML smiles entry missing path context.")
			path_parts = [item[1] for item in stack]
			category = path_parts[0]
			group = path_parts[1] if len(path_parts) > 1 else None
			name = path_parts[-1]
			entry = {
				"category": category,
				"subcategory": group,
				"name": name,
				"display_name": name,
				"smiles": smiles,
			}
			entries.append(entry)
	return entries


#============================================
def _strip_yaml_comment(text):
	"""Remove trailing YAML comments while preserving quoted text."""
	result = []
	in_single = False
	in_double = False
	escape_next = False
	for char in text:
		if escape_next:
			result.append(char)
			escape_next = False
			continue
		if char == "\\" and in_double:
			escape_next = True
			result.append(char)
			continue
		if char == "'" and not in_double:
			in_single = not in_single
		elif char == '"' and not in_single:
			in_double = not in_double
		if char == "#" and not in_single and not in_double:
			break
		result.append(char)
	return "".join(result)


#============================================
def _strip_yaml_quotes(value):
	"""Strip wrapping single or double quotes from a YAML scalar."""
	value = value.strip()
	if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
		return value[1:-1]
	return value


#============================================
def category_to_dir(category):
	"""Convert a category label to a directory name."""
	return normalize_path_part(category)


#============================================
def normalize_path_part(text):
	"""Normalize a label for filesystem paths."""
	text = text.strip().lower()
	text = re.sub(r"[^a-z0-9]+", "_", text)
	return text.strip("_")


#============================================
def output_path_for_entry(entry):
	"""Return the CDML output path for a template entry."""
	category = entry["category"]
	group = entry.get("subcategory")
	name = entry["name"]
	legacy_key = f"{category}/{group}/{name}" if group else f"{category}/{name}"
	legacy = LEGACY_NAME_MAP.get(legacy_key)
	if legacy:
		category, group, name = legacy
	category_dir = category_to_dir(category)
	subcategory_dir = normalize_path_part(group) if group else None
	filename = normalize_path_part(name) or "template"
	if subcategory_dir:
		return os.path.join(TEMPLATE_ROOT, category_dir, subcategory_dir, f"{filename}.cdml")
	return os.path.join(TEMPLATE_ROOT, category_dir, f"{filename}.cdml")


#============================================
def build_molecule(smiles_text):
	"""Build an OASA molecule from SMILES with normalized bond length."""
	mol = oasa.smiles.text_to_mol(smiles_text, calc_coords=1)
	if not mol:
		raise ValueError(f"Failed to parse SMILES: {smiles_text}")
	mol.remove_unimportant_hydrogens()
	mol.normalize_bond_length(1.0)
	return mol


#============================================
def choose_anchor_atom(mol):
	"""Pick a deterministic anchor atom for template placement."""
	return max(mol.vertices, key=lambda atom: (atom.x, -atom.y, atom.symbol))


#============================================
def choose_anchor_neighbor(anchor):
	"""Pick a deterministic neighbor for the anchor bond."""
	if not anchor.neighbors:
		return None
	return sorted(anchor.neighbors, key=lambda atom: (atom.x, atom.y, atom.symbol))[0]


#============================================
def build_template_anchor(anchor, bond_length):
	"""Create a template anchor atom positioned one bond length to the right."""
	atom = oasa.atom(symbol="C")
	atom.x = anchor.x + bond_length
	atom.y = anchor.y
	atom.z = 0.0
	return atom


#============================================
def normalize_coordinates(atoms):
	"""Shift atoms so all coordinates are positive and start near 1 cm."""
	minx = min(atom.x for atom in atoms)
	miny = min(atom.y for atom in atoms)
	shift_x = 1.0 - minx
	shift_y = 1.0 - miny
	for atom in atoms:
		atom.x += shift_x
		atom.y += shift_y


#============================================
def indent_xml(elem, level=0):
	"""Indent XML elements for readability."""
	indent_text = "\n" + ("  " * level)
	child_indent = indent_text + "  "
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = child_indent
		for child in elem:
			indent_xml(child, level + 1)
		if not elem.tail or not elem.tail.strip():
			elem.tail = indent_text
	else:
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = indent_text


#============================================
def build_cdml_tree(entry, mol, anchor, neighbor, template_atom):
	"""Build an ElementTree for a biomolecule template."""
	version = read_version(os.path.join(REPO_ROOT, "version.txt"))
	root = ElementTree.Element(
		"cdml",
		{
			"version": version,
			"xmlns": "http://www.freesoftware.fsf.org/bkchem/cdml",
		},
	)
	info = ElementTree.SubElement(root, "info")
	author = ElementTree.SubElement(info, "author_program", {"version": version})
	author.text = "BKchem"
	ElementTree.SubElement(
		root,
		"paper",
		{
			"crop_svg": "0",
			"orientation": "portrait",
			"type": "A4",
		},
	)
	ElementTree.SubElement(
		root,
		"viewport",
		{
			"viewport": "0.000000 0.000000 640.000000 480.000000",
		},
	)
	standard = ElementTree.SubElement(
		root,
		"standard",
		{
			"area_color": "#ffffff",
			"font_family": "helvetica",
			"font_size": "14",
			"line_color": "#000",
			"line_width": "2.0px",
			"paper_crop_svg": "0",
			"paper_orientation": "portrait",
			"paper_type": "A4",
		},
	)
	ElementTree.SubElement(
		standard,
		"bond",
		{
			"double-ratio": "0.75",
			"length": "1.0cm",
			"wedge-width": "5.0px",
			"width": "6.0px",
		},
	)
	ElementTree.SubElement(standard, "arrow", {"length": "1.6cm"})

	molecule = ElementTree.SubElement(
		root,
		"molecule",
		{"id": "molecule1", "name": entry["display_name"]},
	)

	atom_id_map = {}
	sorted_atoms = sorted(mol.vertices, key=lambda atom: (atom.x, atom.y, atom.symbol))
	for index, atom in enumerate(sorted_atoms, start=1):
		atom_id_map[atom] = f"atom_{index}"

	template_atom_id = "atom_t"
	template = ElementTree.SubElement(molecule, "template", {"atom": template_atom_id})
	if anchor and neighbor:
		template.set("bond_first", atom_id_map[anchor])
		template.set("bond_second", atom_id_map[neighbor])

	atoms_to_write = sorted_atoms + [template_atom]
	normalize_coordinates(atoms_to_write)

	for atom in sorted_atoms:
		atom_el = ElementTree.SubElement(
			molecule,
			"atom",
			{"id": atom_id_map[atom], "name": atom.symbol},
		)
		if atom.charge:
			atom_el.set("charge", str(atom.charge))
		ElementTree.SubElement(
			atom_el,
			"point",
			{
				"x": f"{atom.x:.3f}cm",
				"y": f"{atom.y:.3f}cm",
			},
		)

	template_el = ElementTree.SubElement(
		molecule,
		"atom",
		{"id": template_atom_id, "name": template_atom.symbol},
	)
	ElementTree.SubElement(
		template_el,
		"point",
		{
			"x": f"{template_atom.x:.3f}cm",
			"y": f"{template_atom.y:.3f}cm",
		},
	)

	for bond in mol.bonds:
		bond_type = bond.type or "n"
		bond_order = bond.order or 1
		start_id = atom_id_map[bond.vertices[0]]
		end_id = atom_id_map[bond.vertices[1]]
		ElementTree.SubElement(
			molecule,
			"bond",
			{
				"double_ratio": "0.75",
				"end": end_id,
				"line_width": "1.0",
				"start": start_id,
				"type": f"{bond_type}{bond_order}",
			},
		)

	ElementTree.SubElement(
		molecule,
		"bond",
		{
			"double_ratio": "0.75",
			"end": atom_id_map[anchor],
			"line_width": "1.0",
			"start": template_atom_id,
			"type": "n1",
		},
	)

	indent_xml(root)
	return ElementTree.ElementTree(root)


#============================================
def write_cdml(tree, path, apply):
	"""Write the CDML tree to disk or report the path."""
	if not apply:
		print(path)
		return
	parent = os.path.dirname(path)
	if not os.path.isdir(parent):
		os.makedirs(parent, exist_ok=True)
	tree.write(path, encoding="utf-8", xml_declaration=True)


#============================================
def generate_templates(entries, apply):
	"""Generate all biomolecule templates."""
	for entry in entries:
		mol = build_molecule(entry["smiles"])
		anchor = choose_anchor_atom(mol)
		neighbor = choose_anchor_neighbor(anchor)
		template_atom = build_template_anchor(anchor, bond_length=1.0)
		tree = build_cdml_tree(entry, mol, anchor, neighbor, template_atom)
		output_path = output_path_for_entry(entry)
		write_cdml(tree, output_path, apply)


#============================================
def main():
	"""Run the template generator."""
	args = parse_args()
	input_path = args.input_path
	if input_path is None:
		if os.path.isfile(DEFAULT_SMILES_YAML):
			input_path = DEFAULT_SMILES_YAML
		else:
			input_path = DEFAULT_SMILES_TXT
	entries = parse_smiles_entries(input_path)
	generate_templates(entries, args.apply)


if __name__ == "__main__":
	main()
