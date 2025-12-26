#!/usr/bin/env python3

# Standard Library
import sys
import threading

from bkchem import bkchem


#============================================
def main():
	if len(sys.argv) <= 1:
		print("You have to supply a filename.")
		return

	app = bkchem.myapp
	app.in_batch_mode = 1

	thread = threading.Thread(target=app.mainloop, name="app", daemon=True)
	thread.start()

	app.load_CDML(sys.argv[1])
	for mol in app.paper.molecules:
		for bond in mol.bonds:
			if bond.order == 2:
				bond.line_color = "#aa0000"
				bond.redraw()

	app.save_CDML()
	app.destroy()


if __name__ == '__main__':
	main()
