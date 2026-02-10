# Code architecture

## Overview
- BKChem is a Tkinter desktop application for drawing chemical structures.
- OASA (Open Architecture for Sketching Atoms and Molecules) provides the
  chemistry graph model, format conversions, and render backends.
- CDML is the native document format, with SVG and other formats supported via
  exporters and plugins.

## Major components
- Application entry points
  - [packages/bkchem/bkchem/bkchem.py](packages/bkchem/bkchem/bkchem.py) boots
    the app, loads preferences, and parses CLI flags.
  - [packages/bkchem/bkchem/cli.py](packages/bkchem/bkchem/cli.py) exposes the
    console entry point for BKChem.
  - [packages/bkchem/bkchem/main.py](packages/bkchem/bkchem/main.py) defines the
    `BKChem` Tk application class, menus, and mode wiring.
- UI and interaction layer
  - [packages/bkchem/bkchem/paper.py](packages/bkchem/bkchem/paper.py) implements
    `chem_paper`, the main Tk Canvas for drawing, selection, and events.
  - [packages/bkchem/bkchem/modes.py](packages/bkchem/bkchem/modes.py),
    [packages/bkchem/bkchem/interactors.py](packages/bkchem/bkchem/interactors.py),
    and [packages/bkchem/bkchem/context_menu.py](packages/bkchem/bkchem/context_menu.py)
    define editing modes and input handlers.
  - [packages/bkchem/bkchem/undo.py](packages/bkchem/bkchem/undo.py) and
    [packages/bkchem/bkchem/edit_pool.py](packages/bkchem/bkchem/edit_pool.py)
    manage undo stacks and edit history.
- Chemistry model and drawing objects
  - [packages/bkchem/bkchem/molecule.py](packages/bkchem/bkchem/molecule.py)
    wraps [packages/oasa/oasa/molecule.py](packages/oasa/oasa/molecule.py).
  - [packages/bkchem/bkchem/atom.py](packages/bkchem/bkchem/atom.py) and
    [packages/bkchem/bkchem/bond.py](packages/bkchem/bkchem/bond.py) extend OASA
    atoms and bonds with drawing metadata.
  - [packages/bkchem/bkchem/group.py](packages/bkchem/bkchem/group.py),
    [packages/bkchem/bkchem/fragment.py](packages/bkchem/bkchem/fragment.py),
    [packages/bkchem/bkchem/reaction.py](packages/bkchem/bkchem/reaction.py),
    [packages/bkchem/bkchem/arrow.py](packages/bkchem/bkchem/arrow.py), and
    [packages/bkchem/bkchem/textatom.py](packages/bkchem/bkchem/textatom.py)
    implement higher-level drawing objects.
- OASA core library
  - [packages/oasa/oasa/](packages/oasa/oasa/) contains the chemistry graph
    model, parsers, and conversions.
  - [packages/oasa/oasa/render_ops.py](packages/oasa/oasa/render_ops.py) defines
    shared render ops for SVG and Cairo.
  - [packages/oasa/oasa/svg_out.py](packages/oasa/oasa/svg_out.py) and
    [packages/oasa/oasa/cairo_out.py](packages/oasa/oasa/cairo_out.py) render
    shared ops to SVG and Cairo surfaces.
  - [packages/oasa/oasa/haworth.py](packages/oasa/oasa/haworth.py) provides
    Haworth layout helpers for carbohydrate projections.
- File formats and I/O
  - CDML serialization is handled by
    [packages/oasa/oasa/cdml_writer.py](packages/oasa/oasa/cdml_writer.py),
    [packages/bkchem/bkchem/paper.py](packages/bkchem/bkchem/paper.py),
    and [packages/bkchem/bkchem/CDML_versions.py](packages/bkchem/bkchem/CDML_versions.py).
  - Export routing lives in
    [packages/bkchem/bkchem/format_loader.py](packages/bkchem/bkchem/format_loader.py),
    [packages/bkchem/bkchem/main.py](packages/bkchem/bkchem/main.py), and
    [packages/bkchem/bkchem/oasa_bridge.py](packages/bkchem/bkchem/oasa_bridge.py).
  - Built-in exporters live under
    [packages/bkchem/bkchem/plugins/](packages/bkchem/bkchem/plugins/).
- Templates and reusable structures
  - Template loading is handled by
    [packages/bkchem/bkchem/temp_manager.py](packages/bkchem/bkchem/temp_manager.py)
    and catalog discovery in
    [packages/bkchem/bkchem/template_catalog.py](packages/bkchem/bkchem/template_catalog.py).
  - Built-in templates live under
    [packages/bkchem/bkchem_data/templates/](packages/bkchem/bkchem_data/templates/),
    including biomolecule templates in
    [packages/bkchem/bkchem_data/templates/biomolecules/](packages/bkchem/bkchem_data/templates/biomolecules/).
- Plugin system
  - [packages/bkchem/bkchem/plugin_support.py](packages/bkchem/bkchem/plugin_support.py)
    loads addon XML descriptors and scripts from
    [packages/bkchem/addons/](packages/bkchem/addons/).

## Data flow
1. [packages/bkchem/bkchem/bkchem.py](packages/bkchem/bkchem/bkchem.py) loads
   preferences, initializes locale, and creates a `BKChem` instance.
2. [packages/bkchem/bkchem/main.py](packages/bkchem/bkchem/main.py) builds the UI
   and constructs a [packages/bkchem/bkchem/paper.py](packages/bkchem/bkchem/paper.py)
   canvas.
3. User input routes through modes and interactors into canvas operations.
4. `chem_paper` maintains a stack of top-level objects (molecules, arrows, text).
5. Model edits update atoms and bonds, which redraw onto the canvas.
6. Save and export paths serialize CDML or render SVG/bitmap output through OASA.
7. Imports use OASA parsers and
   [packages/bkchem/bkchem/oasa_bridge.py](packages/bkchem/bkchem/oasa_bridge.py)
   to create BKChem molecules.

## Testing and verification
- Tests live under [tests/](tests/) with smoke and lint runners such as
  [tests/run_smoke.sh](tests/run_smoke.sh) and
  [tests/test_pyflakes_code_lint.py](tests/test_pyflakes_code_lint.py).
- Haworth and render ops coverage includes
  [tests/test_haworth_layout.py](tests/test_haworth_layout.py),
  [tests/test_oasa_bond_styles.py](tests/test_oasa_bond_styles.py), and
  [tests/test_render_ops_snapshot.py](tests/test_render_ops_snapshot.py).
- Reference image checks live in
  [tests/test_reference_outputs.py](tests/test_reference_outputs.py).

## Extension points
- Add new BKChem addons under [packages/bkchem/addons/](packages/bkchem/addons/)
  with XML descriptors for discovery.
- Add export plugins under
  [packages/bkchem/bkchem/plugins/](packages/bkchem/bkchem/plugins/).
- Add templates under
  [packages/bkchem/bkchem_data/templates/](packages/bkchem/bkchem_data/templates/)
  or subfolders scanned by
  [packages/bkchem/bkchem/template_catalog.py](packages/bkchem/bkchem/template_catalog.py).

## Known gaps
- Verify how installer packaging bundles `bkchem_data` assets in macOS and
  Windows distributions.
