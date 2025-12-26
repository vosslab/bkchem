#!/usr/bin/env python3

# Standard Library
import os

if 'App' not in globals():
	App = None
if 'Args' not in globals():
	Args = []


#============================================
def update_svgs_in_path(path):
	"""Call update_svg for a file or for all .svg files in a directory."""
	made = 0
	ignored = 0

	if os.path.isfile(path):
		update_svg(path)
	elif os.path.isdir(path):
		for filename in os.listdir(path):
			if os.path.splitext(filename)[1] == ".svg":
				result = update_svg(os.path.join(path, filename))
				if result:
					made += 1
				else:
					ignored += 1

	print(f"Resaved {made} files, ignored {ignored}")


#============================================
def update_svg(path):
	"""Open a file in BKChem, update atom font sizes, and save."""
	if App is None:
		print("This script must be run in BKChem batch mode.")
		return 0

	print(path, "...", end=' ')
	if App.load_CDML(path, replace=1):
		print("OK")
		for mol in App.paper.molecules:
			for atom in mol.atoms:
				atom.font_size = 12
		App.save_CDML()
		return 1

	print("ignoring")
	return 0


#============================================
def main():
	if not Args:
		print("You must supply a path as first argument to the batch script.")
		return
	for arg in Args:
		update_svgs_in_path(arg)


if globals().get('__name__') in (None, '__main__'):
	main()
