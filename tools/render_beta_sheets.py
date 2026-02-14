#!/usr/bin/env python3

"""Build parallel and antiparallel beta-sheet molecules and render to SVG/CDML."""

# Standard Library
import math
import os
import subprocess
import sys


#============================================
def _get_repo_root():
	"""Return the repository root directory."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


#============================================
def _ensure_sys_path(repo_root: str):
	"""Add oasa package directory to sys.path."""
	oasa_dir = os.path.join(repo_root, "packages", "oasa")
	if oasa_dir not in sys.path:
		sys.path.insert(0, oasa_dir)


#============================================
def _ensure_dir(path: str):
	"""Create directory if it does not exist."""
	if not os.path.isdir(path):
		os.makedirs(path, exist_ok=True)


#============================================
# Geometry constants (in OASA coordinate points)
BOND_LENGTH = 20.0
ZIGZAG_ANGLE_DEG = 30.0
ZIGZAG_ANGLE_RAD = math.radians(ZIGZAG_ANGLE_DEG)
# horizontal and vertical steps per backbone bond
DX = BOND_LENGTH * math.cos(ZIGZAG_ANGLE_RAD)
DY = BOND_LENGTH * math.sin(ZIGZAG_ANGLE_RAD)
# perpendicular offset for carbonyl O and R groups
SIDE_OFFSET = 15.0
# vertical gap between two strands
STRAND_SEP = 80.0


#============================================
def _build_strand(mol, x_start: float, y_base: float,
	num_residues: int, direction: int = 1) -> dict:
	"""Build one peptide backbone strand with side groups.

	Args:
		mol: oasa.molecule to add atoms/bonds to
		x_start: starting x coordinate
		y_base: baseline y coordinate for the strand
		num_residues: number of amino acid residues
		direction: +1 for left-to-right, -1 for right-to-left

	Returns:
		dict with keys 'backbone', 'oxygens', 'r_groups' containing atom lists
	"""
	import oasa

	backbone_atoms = []
	oxygen_atoms = []
	r_group_atoms = []

	# current position along the backbone
	x = x_start
	# index tracks which backbone atom we are on (0-based)
	atom_index = 0

	for res_idx in range(num_residues):
		# each residue has 3 backbone atoms: N, Ca, C'
		symbols = ['N', 'C', 'C']
		for local_idx, symbol in enumerate(symbols):
			# zigzag: even indices go up (smaller y), odd go down (larger y)
			if atom_index % 2 == 0:
				y = y_base - DY
			else:
				y = y_base + DY

			a = oasa.atom(symbol=symbol)
			a.x = x
			a.y = y
			mol.add_vertex(a)
			backbone_atoms.append(a)

			# add side groups
			if local_idx == 1:
				# alpha-carbon: attach R group
				r_atom = oasa.atom(symbol='C')
				r_atom.properties_["label"] = "R"
				# R group perpendicular to backbone, opposite side from carbonyls
				# carbonyls point toward larger y, so R points toward smaller y
				if atom_index % 2 == 0:
					# Ca at peak (small y) -> R goes further up
					r_atom.x = x
					r_atom.y = y - SIDE_OFFSET
				else:
					# Ca at valley (large y) -> R goes further down
					r_atom.x = x
					r_atom.y = y + SIDE_OFFSET
				mol.add_vertex(r_atom)
				r_group_atoms.append(r_atom)
				# single bond Ca -> R
				r_bond = oasa.bond(order=1, type='n')
				mol.add_edge(a, r_atom, r_bond)

			elif local_idx == 2:
				# carbonyl carbon C': attach O with double bond
				o_atom = oasa.atom(symbol='O')
				# carbonyl points opposite to R group
				if atom_index % 2 == 0:
					# C' at peak -> O goes down
					o_atom.x = x
					o_atom.y = y + SIDE_OFFSET
				else:
					# C' at valley -> O goes up
					o_atom.x = x
					o_atom.y = y - SIDE_OFFSET
				mol.add_vertex(o_atom)
				oxygen_atoms.append(o_atom)
				# double bond C'=O
				o_bond = oasa.bond(order=2, type='n')
				mol.add_edge(a, o_atom, o_bond)

			# advance x for the next atom
			x += direction * DX
			atom_index += 1

		# connect backbone atoms within this residue
		# N-Ca bond
		start_idx = res_idx * 3
		n_bond = oasa.bond(order=1, type='n')
		mol.add_edge(backbone_atoms[start_idx], backbone_atoms[start_idx + 1], n_bond)
		# Ca-C' bond
		ca_bond = oasa.bond(order=1, type='n')
		mol.add_edge(backbone_atoms[start_idx + 1], backbone_atoms[start_idx + 2], ca_bond)

	# connect residues: C'(i) -> N(i+1) peptide bonds
	for res_idx in range(num_residues - 1):
		c_prime_idx = res_idx * 3 + 2
		n_next_idx = (res_idx + 1) * 3
		peptide_bond = oasa.bond(order=1, type='n')
		mol.add_edge(backbone_atoms[c_prime_idx], backbone_atoms[n_next_idx], peptide_bond)

	return {
		'backbone': backbone_atoms,
		'oxygens': oxygen_atoms,
		'r_groups': r_group_atoms,
	}


#============================================
def _add_hydrogen_bonds_parallel(mol, strand1: dict, strand2: dict):
	"""Add dashed hydrogen bonds between two parallel strands.

	Args:
		mol: oasa.molecule to add bonds to
		strand1: dict from _build_strand for strand 1
		strand2: dict from _build_strand for strand 2
	"""
	import oasa

	bb1 = strand1['backbone']
	bb2 = strand2['backbone']
	# in parallel sheets, H-bonds connect C=O of one strand to N-H of the other
	# C' atoms are at indices 2, 5, 8, 11 (every 3rd starting at 2)
	# N atoms are at indices 0, 3, 6, 9 (every 3rd starting at 0)
	# connect C'(strand1, res i) to N(strand2, res i+1) and vice versa
	num_residues = len(bb1) // 3
	for res_idx in range(num_residues - 1):
		# H-bond from O on strand1 C' to strand2 N
		o_atom = strand1['oxygens'][res_idx]
		n_atom_idx = (res_idx + 1) * 3
		if n_atom_idx < len(bb2):
			n_atom = bb2[n_atom_idx]
			hbond = oasa.bond(order=1, type='d')
			mol.add_edge(o_atom, n_atom, hbond)

		# H-bond from O on strand2 C' to strand1 N
		if res_idx < len(strand2['oxygens']):
			o_atom2 = strand2['oxygens'][res_idx]
			n_atom_idx2 = (res_idx + 1) * 3
			if n_atom_idx2 < len(bb1):
				n_atom2 = bb1[n_atom_idx2]
				hbond2 = oasa.bond(order=1, type='d')
				mol.add_edge(o_atom2, n_atom2, hbond2)


#============================================
def _add_hydrogen_bonds_antiparallel(mol, strand1: dict, strand2: dict):
	"""Add dashed hydrogen bonds between two antiparallel strands.

	Args:
		mol: oasa.molecule to add bonds to
		strand1: dict from _build_strand for strand 1 (left-to-right)
		strand2: dict from _build_strand for strand 2 (right-to-left)
	"""
	import oasa

	bb1 = strand1['backbone']
	bb2 = strand2['backbone']
	num_residues = len(bb1) // 3
	# in antiparallel sheets, H-bonds go nearly vertically
	# connect C'(strand1, res i) O to N(strand2, mirror res)
	# strand2 runs in reverse so residue 0 of strand2 is opposite residue (N-1) of strand1
	for res_idx in range(num_residues):
		mirror_idx = num_residues - 1 - res_idx
		# O from strand1 C' to N of strand2 mirror residue
		if res_idx < len(strand1['oxygens']):
			o_atom = strand1['oxygens'][res_idx]
			n_atom_idx = mirror_idx * 3
			if n_atom_idx < len(bb2):
				n_atom = bb2[n_atom_idx]
				hbond = oasa.bond(order=1, type='d')
				mol.add_edge(o_atom, n_atom, hbond)

		# O from strand2 C' to N of strand1 mirror residue
		if mirror_idx < len(strand2['oxygens']):
			o_atom2 = strand2['oxygens'][mirror_idx]
			n_atom_idx2 = res_idx * 3
			if n_atom_idx2 < len(bb1):
				n_atom2 = bb1[n_atom_idx2]
				hbond2 = oasa.bond(order=1, type='d')
				mol.add_edge(o_atom2, n_atom2, hbond2)


#============================================
def _build_parallel_sheet(num_residues: int = 4):
	"""Build a complete parallel beta-sheet molecule with two strands.

	Args:
		num_residues: number of residues per strand

	Returns:
		oasa.molecule with two parallel peptide strands and hydrogen bonds
	"""
	import oasa

	mol = oasa.molecule()
	mol.name = "parallel_beta_sheet"

	# strand 1: top, left-to-right
	x_start = 10.0
	y_base_1 = 40.0
	strand1 = _build_strand(mol, x_start, y_base_1, num_residues, direction=1)

	# strand 2: bottom, also left-to-right (parallel)
	y_base_2 = y_base_1 + STRAND_SEP
	strand2 = _build_strand(mol, x_start, y_base_2, num_residues, direction=1)

	# add hydrogen bonds between strands
	_add_hydrogen_bonds_parallel(mol, strand1, strand2)

	return mol


#============================================
def _build_antiparallel_sheet(num_residues: int = 4):
	"""Build a complete antiparallel beta-sheet molecule with two strands.

	Args:
		num_residues: number of residues per strand

	Returns:
		oasa.molecule with two antiparallel peptide strands and hydrogen bonds
	"""
	import oasa

	mol = oasa.molecule()
	mol.name = "antiparallel_beta_sheet"

	# strand 1: top, left-to-right
	x_start = 10.0
	y_base_1 = 40.0
	strand1 = _build_strand(mol, x_start, y_base_1, num_residues, direction=1)

	# strand 2: bottom, right-to-left (antiparallel)
	# start from the right end so strands are aligned
	total_width = num_residues * 3 * DX
	x_start_2 = x_start + total_width
	y_base_2 = y_base_1 + STRAND_SEP
	strand2 = _build_strand(mol, x_start_2, y_base_2, num_residues, direction=-1)

	# add hydrogen bonds between strands
	_add_hydrogen_bonds_antiparallel(mol, strand1, strand2)

	return mol


#============================================
def _render_svg(mol, path: str):
	"""Render molecule to SVG using the render_out pipeline.

	Args:
		mol: oasa.molecule to render
		path: output SVG file path
	"""
	import oasa.render_out

	oasa.render_out.render_to_svg(
		mol,
		path,
		show_hydrogens_on_hetero=True,
		show_carbon_symbol=False,
		margin=20,
		scaling=1.5,
	)


#============================================
def _write_cdml(mol, path: str):
	"""Write molecule to CDML file.

	Args:
		mol: oasa.molecule to write
		path: output CDML file path
	"""
	import oasa.cdml_writer

	with open(path, "w", encoding="utf-8") as handle:
		oasa.cdml_writer.mol_to_file(mol, handle)


#============================================
def main():
	"""Generate beta-sheet SVG renders and CDML fixtures."""
	repo_root = _get_repo_root()
	_ensure_sys_path(repo_root)

	# output directories
	svg_dir = os.path.join(repo_root, "output_smoke", "oasa_generic_renders")
	cdml_dir = os.path.join(repo_root, "tests", "fixtures", "oasa_generic")
	_ensure_dir(svg_dir)
	_ensure_dir(cdml_dir)

	# build and render parallel beta-sheet
	parallel_mol = _build_parallel_sheet(num_residues=4)
	parallel_svg = os.path.join(svg_dir, "parallel_beta_sheet.svg")
	parallel_cdml = os.path.join(cdml_dir, "parallel_beta_sheet.cdml")
	_render_svg(parallel_mol, parallel_svg)
	_write_cdml(parallel_mol, parallel_cdml)
	print("Parallel beta-sheet: %s" % parallel_svg)
	print("Parallel CDML: %s" % parallel_cdml)

	# build and render antiparallel beta-sheet
	antiparallel_mol = _build_antiparallel_sheet(num_residues=4)
	antiparallel_svg = os.path.join(svg_dir, "antiparallel_beta_sheet.svg")
	antiparallel_cdml = os.path.join(cdml_dir, "antiparallel_beta_sheet.cdml")
	_render_svg(antiparallel_mol, antiparallel_svg)
	_write_cdml(antiparallel_mol, antiparallel_cdml)
	print("Antiparallel beta-sheet: %s" % antiparallel_svg)
	print("Antiparallel CDML: %s" % antiparallel_cdml)

	# summary
	for mol_obj, name in [(parallel_mol, "Parallel"), (antiparallel_mol, "Antiparallel")]:
		num_atoms = len(mol_obj.vertices)
		num_bonds = len(mol_obj.edges)
		print("%s: %d atoms, %d bonds" % (name, num_atoms, num_bonds))


if __name__ == "__main__":
	main()
