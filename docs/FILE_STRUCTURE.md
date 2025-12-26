# File structure

## Top level
- `packages/` monorepo packages for BKChem and OASA.
- `docs/` project documentation and style guides.
- `docs/assets/` screenshots used in `README.md`.
- `bkchem_webpage/` local mirror of the BKChem website for documentation.
- `tests/` repo-level test runners and smoke tests.
- `tools/` small maintenance scripts.
- `pip_requirements.txt`, `Brewfile` dependency manifests.
- `README.md`, `LICENSE`, `AGENTS.md` project references.
- `version.txt` shared version registry for BKChem and OASA (same version string).

## BKChem package (`packages/bkchem/`)
- `packages/bkchem/bkchem/` BKChem application package.
- `packages/bkchem/bkchem/bkchem.py` application bootstrap, locale, and CLI flags.
- `packages/bkchem/bkchem/main.py` main Tk application class and menu setup.
- `packages/bkchem/bkchem/paper.py` canvas and document container (`chem_paper`).
- `packages/bkchem/bkchem/molecule.py`, `packages/bkchem/bkchem/atom.py`,
  `packages/bkchem/bkchem/bond.py` core chemical objects.
- `packages/bkchem/bkchem/group.py`, `packages/bkchem/bkchem/fragment.py`,
  `packages/bkchem/bkchem/reaction.py` higher-level data.
- `packages/bkchem/bkchem/arrow.py`, `packages/bkchem/bkchem/textatom.py`,
  `packages/bkchem/bkchem/classes.py` drawing objects.
- `packages/bkchem/bkchem/modes.py`, `packages/bkchem/bkchem/interactors.py`,
  `packages/bkchem/bkchem/context_menu.py` UI modes.
- `packages/bkchem/bkchem/undo.py`, `packages/bkchem/bkchem/edit_pool.py` undo
  tracking and edit history.
- `packages/bkchem/bkchem/oasa_bridge.py` translation layer between BKChem and OASA.
- `packages/bkchem/bkchem/xml_writer.py`, `packages/bkchem/bkchem/non_xml_writer.py`
  export writers.
- `packages/bkchem/bkchem/export.py` CDML and CD-SVG export helpers.
- `packages/bkchem/bkchem/plugin_support.py` plugin discovery and execution.
- `packages/bkchem/bkchem/plugins/` built-in export backends and format handlers.
- `packages/bkchem/addons/` user-facing addon scripts and XML descriptors.
- `packages/bkchem/bkchem_data/` templates, images, pixmaps, locale, and DTDs.
- `packages/bkchem/pyproject.toml`, `packages/bkchem/MANIFEST.in` packaging
  metadata.
- `packages/bkchem/bkchem.iss`, `packages/bkchem/prepare_release.sh` release assets.

## OASA package (`packages/oasa/`)
- `packages/oasa/oasa/` OASA package source code.
- `packages/oasa/docs/` dependency documentation, including
  [OASA file structure](../packages/oasa/docs/FILE_STRUCTURE.md).
- `tests/oasa_*` OASA static checks, smoke scripts, and legacy test helpers.
- `packages/oasa/chemical_convert.py` conversion helper script.
- `packages/oasa/README.md` dependency overview and status notes.
- `packages/oasa/pyproject.toml` packaging metadata.
- `packages/oasa/pip_requirements.txt` OASA-specific dependencies.

## Generated or temporary outputs
- `__pycache__/` and `*.pyc` Python bytecode.
- `build/`, `dist/`, `*.egg-info/` packaging outputs.
- `pyflakes.txt` created by `tests/run_pyflakes.sh`.
