# Custom plugins

Legacy note: This document is migrated from `docs/legacy/custom_plugins_en.html`. The
[GitHub repository](https://github.com/vosslab/bkchem) is the primary homepage
and documentation source. Legacy websites are archived and not maintained. Any
legacy email addresses are kept for attribution only and are not support
contacts.

## What is a plugin

BKChem supports custom plugins: small extensions that add menu actions or new
modes without modifying the core application. Most plugins are short Python
scripts paired with a short XML descriptor.

BKChem has two extension mechanisms: internal code plugins
(`packages/bkchem/bkchem/plugins/`) and filesystem addons (`addons/`). This
guide covers the filesystem addons.

## Plugin discovery

At startup BKChem scans plugin descriptor XML files from:

- `packages/bkchem/addons/` when running from source.
- `~/.bkchem/addons/` for user-installed addons.
- `share/bkchem/addons/` when installed system-wide.

Each descriptor points to a Python script and the menu label to show in the
Plugins menu.

## Script plugins vs. mode plugins

BKChem supports two plugin types:

- Script plugins add a menu entry that runs the Python script on demand.
- Mode plugins add a new drawing mode to the main toolbar (advanced usage).

This guide focuses on script plugins.

## XML descriptor

A plugin XML file is short and declarative:

```xml
<?xml version="1.0" encoding="utf-8"?>

<plugin>
  <meta>
    <author email="beda@zirael.org">Beda Kosata</author>
    <description>
      Finds all aromatic bonds in the current drawing (paper) and marks them by
      setting their color to red.
    </description>
  </meta>

  <source>
    <file>red_aromates.py</file>
    <menu-text lang="en">Mark aromatic bonds</menu-text>
    <menu-text lang="cs">Oznac aromaticke vazby</menu-text>
  </source>
</plugin>
```

Notes:

- `<source>` is required. It names the Python file and menu label.
- `<meta>` is optional but recommended for attribution and descriptions.
- `lang` lets you provide localized menu text.

## Python script

Plugin scripts receive a global `App` variable that is the live BKChem instance.
You can call its methods directly.

Warning: plugins can run arbitrary Python. Only install plugins from trusted
sources.

Sample script fragment:

```python
# cancel all selections
App.paper.unselect_all()

for mol in App.paper.molecules:
	mol.mark_aromatic_bonds()
	for bond in mol.bonds:
		if bond.aromatic:
			bond.line_color = "#aa0000"
			bond.redraw()
```

When the script returns, BKChem starts a new undo record so plugin changes are
undoable in one step.

## Sample plugins

Example addons ship with BKChem in `packages/bkchem/addons/`. Use them as
starting points for new scripts.
