# Code architecture

## Overview
- BKChem is a Tkinter desktop application for drawing chemical structures.
- The UI is a Tk window with a canvas-based drawing surface and tool modes.
- The core chemistry model wraps the OASA library for atoms, bonds, and graphs.
- Native persistence is CDML, with SVG and other formats supported via exporters.
- Plugins extend import, export, and workflow features.

## Entry points and runtime
- `bkchem/bkchem.py` boots the app, loads preferences, sets locale, and parses CLI
  flags (batch mode, version, help).
- `bkchem/main.py` defines the `BKChem` Tk application class and builds menus,
  toolbars, mode buttons, and the main canvas.
- Batch mode uses the same model and exporters without interactive bindings.

## UI and interaction layer
- `bkchem/paper.py` implements `chem_paper`, the main Tk Canvas that manages the
  drawing stack, selection, and event bindings.
- `bkchem/modes.py`, `bkchem/interactors.py`, and `bkchem/context_menu.py`
  define editing modes and input handling.
- `bkchem/undo.py` and `bkchem/edit_pool.py` handle undo stacks and edit history.
- `bkchem/graphics.py` and `bkchem/helper_graphics.py` render helper shapes.

## Chemistry model and drawing objects
- `bkchem/molecule.py` subclasses `oasa.molecule` and the BKChem container base.
- `bkchem/atom.py` and `bkchem/bond.py` extend OASA atoms and bonds with drawing
  and UI metadata.
- `bkchem/group.py`, `bkchem/fragment.py`, `bkchem/reaction.py`,
  `bkchem/arrow.py`, and `bkchem/textatom.py` implement higher-level objects.

## OASA integration
- The `oasa/` subrepo provides the chemistry graph model and format parsers.
- `bkchem/oasa_bridge.py` translates between BKChem molecules and OASA molecules
  for SMILES, InChI, and molfile support.
- The `oasa` docs are the source of truth for the dependency architecture.
  [OASA code architecture](oasa/docs/CODE_ARCHITECTURE.md).

## File formats and I O
- CDML is the native document format; serialization lives in
  `bkchem/xml_writer.py`, `bkchem/dom_extensions.py`, and
  `bkchem/CDML_versions.py`.
- `bkchem/export.py` handles CDML and CD-SVG exports.
- `bkchem/non_xml_writer.py` provides bitmap export when PIL is available.
- `bkchem/plugins/` contains built-in exporters for formats such as PDF, PS,
  and SVG, plus integration helpers for Cairo and Piddle backends.

## Configuration and shared state
- `bkchem/pref_manager.py`, `bkchem/config.py`, and `bkchem/os_support.py` manage
  preferences and filesystem paths.
- `bkchem/singleton_store.py` holds shared app state (current app, screen data).
- `bkchem/messages.py` and `bkchem/logger.py` provide user and log messaging.

## Plugin system
- `bkchem/plugin_support.py` loads XML descriptors from `plugins/` and user
  plugin directories and executes script plugins.
- Plugin scripts run with access to the live application instance.

## Data flow
1. `bkchem/bkchem.py` loads preferences, initializes locale, and creates a
   `BKChem` instance.
2. `BKChem.initialize()` builds the UI and constructs a `chem_paper` canvas.
3. User input is routed through modes and interactors into canvas operations.
4. `chem_paper` maintains a stack of top-level objects (molecules, arrows, text).
5. Model edits update atoms and bonds, which redraw onto the canvas.
6. Save and export paths serialize CDML or render SVG or bitmap output.
7. Imports use OASA parsers and `oasa_bridge` to create BKChem molecules.
