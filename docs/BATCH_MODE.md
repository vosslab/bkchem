# Batch mode

Legacy note: This document is migrated from `docs/batch_mode_en.html`. The
[GitHub repository](https://github.com/vosslab/bkchem) is the primary homepage
and documentation source. Legacy websites are archived and not maintained.

## Overview

BKChem has a batch mode that runs a Python script without showing the main
window. Use the `-b` switch to run a script and exit:

```sh
bkchem -b path/to/script.py [args...]
```

Batch mode still initializes the Tk application. It requires a GUI environment
(even though the window is not displayed).

## How a batch script works

When BKChem runs a batch script it injects two globals. The structure is similar
to a [custom plugin](CUSTOM_PLUGINS.md):

- `App`: the live BKChem application instance.
- `Args`: a list of extra arguments passed after the script name.

The script can call any BKChem methods through `App` and can use normal Python
modules.

## Sample batch script

The example script lives at `docs/scripts/batch_demo1.py`. It loads every BKChem
file under the given paths, sets the atom font size to 12, and re-saves the
files.

Key snippet:

```python
if Args:
	for arg in Args:
		update_svgs_in_path(arg)
else:
	print("You must supply a path as first argument to the batch script.")
```

And the core processing loop:

```python
if App.load_CDML(f, replace=1):
	print("OK")
	for mol in App.paper.molecules:
		for atom in mol.atoms:
			atom.font_size = 12
	App.save_CDML()
	return 1
print("ignoring")
return 0
```

`App.load_CDML` returns true when the file is loaded successfully. The
`replace=1` argument reuses the current tab instead of opening a new one, which
keeps memory use lower during batch runs.
