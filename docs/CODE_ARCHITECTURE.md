# Code architecture

## Overview
- BKChem is a Tkinter desktop application for drawing chemical structures.
- The UI is a Tk window with a canvas-based drawing surface and tool modes.
- The core chemistry model wraps the OASA (Open Architecture for Sketching
  Atoms and Molecules) library for atoms, bonds, and graphs.
- Native persistence is CDML, with SVG and other formats supported via exporters.
- Plugins extend import, export, and workflow features.

## Entry points and runtime
- `packages/bkchem/bkchem/bkchem.py` boots the app, loads preferences, sets
  locale, and parses CLI flags (batch mode, version, help).
- `packages/bkchem/bkchem/main.py` defines the `BKChem` Tk application class and
  builds menus, toolbars, mode buttons, and the main canvas.
- Batch mode uses the same model and exporters without interactive bindings.

## UI and interaction layer
- `packages/bkchem/bkchem/paper.py` implements `chem_paper`, the main Tk Canvas
  that manages the drawing stack, selection, and event bindings.
- `packages/bkchem/bkchem/modes.py`, `packages/bkchem/bkchem/interactors.py`,
  and `packages/bkchem/bkchem/context_menu.py` define editing modes and input
  handling.
- `packages/bkchem/bkchem/undo.py` and `packages/bkchem/bkchem/edit_pool.py`
  handle undo stacks and edit history.
- `packages/bkchem/bkchem/graphics.py` and
  `packages/bkchem/bkchem/helper_graphics.py` render helper shapes.

## Chemistry model and drawing objects
- `packages/bkchem/bkchem/molecule.py` subclasses `oasa.molecule` and the BKChem
  container base.
- `packages/bkchem/bkchem/atom.py` and `packages/bkchem/bkchem/bond.py` extend
  OASA atoms and bonds with drawing and UI metadata.
- `packages/bkchem/bkchem/group.py`, `packages/bkchem/bkchem/fragment.py`,
  `packages/bkchem/bkchem/reaction.py`, `packages/bkchem/bkchem/arrow.py`, and
  `packages/bkchem/bkchem/textatom.py` implement higher-level objects.

## OASA integration
- The `packages/oasa/` package provides the chemistry graph model and format
  parsers.
- `packages/bkchem/bkchem/oasa_bridge.py` translates between BKChem molecules
  and OASA molecules for SMILES, InChI, and molfile support.
- The OASA docs are the source of truth for the dependency architecture.
  [OASA code architecture](../packages/oasa/docs/CODE_ARCHITECTURE.md).

## File formats and I O
- CDML is the native document format; serialization lives in
  `packages/bkchem/bkchem/xml_writer.py`,
  `packages/bkchem/bkchem/dom_extensions.py`, and
  `packages/bkchem/bkchem/CDML_versions.py`.
- `packages/bkchem/bkchem/export.py` handles CDML and CD-SVG exports.
- `packages/bkchem/bkchem/non_xml_writer.py` provides bitmap export when PIL is
  available.
- `packages/bkchem/bkchem/plugins/` contains built-in exporters for formats
  such as PDF, PS, and SVG, plus integration helpers for Cairo.

## Configuration and shared state
- `packages/bkchem/bkchem/pref_manager.py`, `packages/bkchem/bkchem/config.py`,
  and `packages/bkchem/bkchem/os_support.py` manage preferences and filesystem
  paths.
- `packages/bkchem/bkchem/singleton_store.py` holds shared app state (current
  app, screen data).
- `packages/bkchem/bkchem/messages.py` and `packages/bkchem/bkchem/logger.py`
  provide user and log messaging.

## Plugin system
- `packages/bkchem/bkchem/plugin_support.py` loads XML descriptors from
  `packages/bkchem/addons/` and user addon directories and executes script
  addons.
- Internal exporter plugins live in `packages/bkchem/bkchem/plugins/` and are
  imported as code; they are separate from filesystem addons.
- Plugin scripts run with access to the live application instance.

## Data flow
1. `packages/bkchem/bkchem/bkchem.py` loads preferences, initializes locale, and
   creates a `BKChem` instance.
2. `BKChem.initialize()` builds the UI and constructs a `chem_paper` canvas.
3. User input is routed through modes and interactors into canvas operations.
4. `chem_paper` maintains a stack of top-level objects (molecules, arrows, text).
5. Model edits update atoms and bonds, which redraw onto the canvas.
6. Save and export paths serialize CDML or render SVG or bitmap output.
7. Imports use OASA parsers and `oasa_bridge` to create BKChem molecules.
