#!/usr/bin/env python3

"""Run the legacy batch script examples against a sample file."""

# Standard Library
import argparse
import builtins
import importlib.util
import os
import shutil
import sys
import tempfile


#============================================
def parse_args():
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Run BKChem batch script examples against a temporary CDML file."
	)
	parser.add_argument(
		'-i', '--input',
		dest='input_file',
		default=None,
		help='Input CDML file to copy into a temp workspace'
	)
	args = parser.parse_args()
	return args


#============================================
def ensure_sys_path(root_dir):
	"""Ensure BKChem package paths are on sys.path."""
	bkchem_pkg_dir = os.path.join(root_dir, 'packages', 'bkchem')
	if bkchem_pkg_dir not in sys.path:
		sys.path.insert(0, bkchem_pkg_dir)


#============================================
def ensure_gettext_fallbacks():
	"""Ensure gettext helpers exist for module-level strings."""
	if '_' not in builtins.__dict__:
		builtins.__dict__['_'] = lambda m: m
	if 'ngettext' not in builtins.__dict__:
		builtins.__dict__['ngettext'] = lambda s, p, n: s if n == 1 else p


#============================================
def verify_tkinter():
	"""Verify Tk is available for GUI-backed scripts."""
	try:
		import tkinter
	except ModuleNotFoundError as exc:
		if exc.name in ('_tkinter', 'tkinter'):
			raise RuntimeError(
				"tkinter is not available. Install a Python build with Tk support "
				"(tcl/tk) and rerun this test."
			) from exc
		raise
	tkinter.TkVersion


#============================================
def load_script_module(name, path):
	"""Load a module from a file path."""
	spec = importlib.util.spec_from_file_location(name, path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Unable to load script module: {path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


#============================================
def run_batch_demo(batch_script_path, input_path):
	"""Run the batch demo script via BKChem batch mode."""
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize_batch()
	app.process_batch(['-b', batch_script_path, input_path])
	app.destroy()


#============================================
def run_script1(script_path, input_path):
	"""Run script1.py with a temporary input file."""
	script_module = load_script_module('bkchem_script1_example', script_path)
	if hasattr(script_module, 'bkchem') and hasattr(script_module.bkchem, 'myapp'):
		script_module.bkchem.myapp.withdraw()

	original_argv = sys.argv[:]
	sys.argv = [script_path, input_path]
	try:
		script_module.main()
	finally:
		sys.argv = original_argv


#============================================
def main():
	"""Run batch script examples on a temporary CDML copy."""
	args = parse_args()
	root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	ensure_sys_path(root_dir)
	ensure_gettext_fallbacks()
	verify_tkinter()

	default_input = os.path.join(
		root_dir,
		'packages',
		'bkchem',
		'bkchem_data',
		'templates',
		'templates.cdml'
	)
	input_path = args.input_file or default_input
	if not os.path.isfile(input_path):
		raise FileNotFoundError(f"Input file does not exist: {input_path}")

	batch_script_path = os.path.join(root_dir, 'docs', 'scripts', 'batch_demo1.py')
	script1_path = os.path.join(root_dir, 'docs', 'scripts', 'script1.py')

	with tempfile.TemporaryDirectory() as temp_dir:
		temp_input = os.path.join(temp_dir, os.path.basename(input_path))
		shutil.copy2(input_path, temp_input)

		run_batch_demo(batch_script_path, temp_input)
		run_script1(script1_path, temp_input)


if __name__ == '__main__':
	main()
