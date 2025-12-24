#!/usr/bin/env python3

"""GUI smoke test for BKChem."""

import argparse
import builtins
import os
import sys


#============================================
def parse_args():
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(description="Open BKChem GUI briefly.")
	parser.add_argument(
		'-s', '--seconds',
		dest='seconds',
		type=float,
		default=2.0,
		help='Seconds to keep the GUI open'
	)
	args = parser.parse_args()
	return args


#============================================
def main():
	"""Run the GUI smoke test."""
	args = parse_args()
	root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	if root_dir not in sys.path:
		sys.path.insert(0, root_dir)
	bkchem_dir = os.path.join(root_dir, 'bkchem')
	if bkchem_dir not in sys.path:
		sys.path.insert(0, bkchem_dir)
	if '_' not in builtins.__dict__:
		builtins.__dict__['_'] = lambda m: m
	if 'ngettext' not in builtins.__dict__:
		builtins.__dict__['ngettext'] = lambda s, p, n: s if n == 1 else p
	try:
		import tkinter
	except ModuleNotFoundError as exc:
		if exc.name == '_tkinter' or exc.name == 'tkinter':
			sys.stderr.write(
				"tkinter is not available. Install a Python build with Tk support "
				"(tcl/tk) and rerun this test.\n"
			)
			sys.exit(1)
		raise
	import main as bkchem_main
	BKChem = bkchem_main.BKChem
	app = BKChem()
	app.withdraw()
	app.initialize()
	app.deiconify()
	app.after(int(args.seconds * 1000), app.destroy)
	app.mainloop()


if __name__ == '__main__':
	main()
