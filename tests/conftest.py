# Standard Library
import os
import subprocess
import sys


def repo_root():
	output = subprocess.check_output(
		["git", "rev-parse", "--show-toplevel"],
		text=True,
	).strip()
	if not output:
		raise RuntimeError("git rev-parse --show-toplevel returned empty output")
	return output


def add_repo_root_to_sys_path():
	root = repo_root()
	if root not in sys.path:
		sys.path.insert(0, root)
	return root


def add_bkchem_to_sys_path():
	root = add_repo_root_to_sys_path()
	bkchem_dir = os.path.join(root, "packages", "bkchem")
	if bkchem_dir not in sys.path:
		sys.path.insert(0, bkchem_dir)
	bkchem_module_dir = os.path.join(bkchem_dir, "bkchem")
	if bkchem_module_dir not in sys.path:
		sys.path.append(bkchem_module_dir)
	return root


def add_oasa_to_sys_path():
	root = add_repo_root_to_sys_path()
	oasa_dir = os.path.join(root, "packages", "oasa")
	if oasa_dir not in sys.path:
		sys.path.insert(0, oasa_dir)
	return root
