# File structure

## Top level
- `bkchem/` application package with UI, model, and exporters.
- `oasa/` dependency subrepo; the package lives in `oasa/oasa/`.
- `docs/` project documentation and style guides.
- `doc/` legacy HTML documentation and scripts.
- `plugins/` user-facing plugin scripts and XML descriptors.
- `templates/` CDML templates shipped with the application.
- `dtd/` CDML DTD and schema files.
- `images/` logos and application icon assets.
- `pixmaps/` UI bitmap assets.
- `locale/` translations (`BKChem.mo` files).
- `tests/` test runners (pyflakes).
- `tools/` small maintenance scripts.
- `setup.py`, `MANIFEST.in` packaging metadata.
- `prepare_release.sh`, `run-virtual-test.sh` helper scripts.
- `README.md`, `INSTALL`, `BUGS`, `LICENSE` project references.
- `bkchem.iss` Windows installer script.
- `2to3-*.log`, `progress.log` conversion history logs.
- `__init__.py` root-level import placeholder.

## Application package (`bkchem/`)
- `bkchem/bkchem.py` application bootstrap, locale, and CLI flags.
- `bkchem/main.py` main Tk application class and menu setup.
- `bkchem/paper.py` canvas and document container (`chem_paper`).
- `bkchem/molecule.py`, `bkchem/atom.py`, `bkchem/bond.py` core chemical objects.
- `bkchem/group.py`, `bkchem/fragment.py`, `bkchem/reaction.py` higher-level data.
- `bkchem/arrow.py`, `bkchem/textatom.py`, `bkchem/classes.py` drawing objects.
- `bkchem/modes.py`, `bkchem/interactors.py`, `bkchem/context_menu.py` UI modes.
- `bkchem/undo.py`, `bkchem/edit_pool.py` undo tracking and edit history.
- `bkchem/oasa_bridge.py` translation layer between BKChem and OASA.
- `bkchem/xml_writer.py`, `bkchem/non_xml_writer.py` export writers.
- `bkchem/export.py` CDML and CD-SVG export helpers.
- `bkchem/plugin_support.py` plugin discovery and execution.
- `bkchem/plugins/` built-in export and rendering backends.
- `bkchem/config.py`, `bkchem/pref_manager.py`, `bkchem/os_support.py` config
  and path helpers.
- `bkchem/singleton_store.py`, `bkchem/messages.py`, `bkchem/logger.py` shared
  state and messaging.
- `bkchem/oasa/` empty directory (currently unused).

## OASA subrepo (`oasa/`)
- `oasa/oasa/` OASA package source code.
- `oasa/docs/` dependency documentation, including
  [OASA file structure](oasa/docs/FILE_STRUCTURE.md).
- `oasa/tests/` static checks and legacy tests.
- `oasa/chemical_convert.py` conversion helper script.
- `oasa/README.md` dependency overview and status notes.

## Generated or temporary outputs
- `__pycache__/` and `*.pyc` Python bytecode.
- `build/`, `dist/`, `*.egg-info/` packaging outputs.
- `oasa/build/`, `oasa/oasa.egg-info/` OASA packaging outputs.
- `pyflakes.txt` created by `tests/run_pyflakes.sh`.
