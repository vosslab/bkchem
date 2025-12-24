# File structure

## Top level
- `oasa/` package source code.
- `docs/` documentation set for repo-wide conventions and guides.
- `tests/` lightweight test scripts and static check runners.
- `README.md` project overview and usage notes.
- `LICENSE` license text.
- `setup.py` packaging metadata and install entry point.
- `pyproject.toml` build system configuration.
- `MANIFEST.in` packaging include rules.
- `chemical_convert.py` conversion helper script.
- `.gitignore` and `.git/` version control metadata.

## Package layout (`oasa/`)
- `oasa/__init__.py` public API aggregation and feature availability flags.
- `oasa/graph/` graph primitives and core algorithms.
- `oasa/atom.py`, `oasa/bond.py`, `oasa/molecule.py` core chemistry model.
- `oasa/smiles.py`, `oasa/molfile.py`, `oasa/inchi.py`, `oasa/cdml.py` format I O.
- `oasa/coords_generator.py`, `oasa/coords_optimizer.py` coordinate layout.
- `oasa/geometry.py`, `oasa/transform.py`, `oasa/transform3d.py` geometry tools.
- `oasa/stereochemistry.py` stereochemistry helpers.
- `oasa/svg_out.py`, `oasa/cairo_out.py` rendering backends.
- `oasa/subsearch.py`, `oasa/query_atom.py`, `oasa/known_groups.py` search utilities.
- `oasa/oasa_exceptions.py` custom exception types.
- `oasa/periodic_table.py`, `oasa/linear_formula.py` chemistry references.
- `oasa/*.txt`, `oasa/*.txt.gz`, `oasa/*.db` bundled data assets.

## Documentation (`docs/`)
- `docs/REPO_STYLE.md` repo structure and file placement rules.
- `docs/PYTHON_STYLE.md` Python coding conventions.
- `docs/MARKDOWN_STYLE.md` Markdown formatting rules.
- `docs/AUTHORS.md` maintainers and contributors.
- `docs/CODE_ARCHITECTURE.md` system overview and data flow.
- `docs/FILE_STRUCTURE.md` directory map and generated assets.
- `docs/USAGE.md` usage notes and examples.

## Generated or temporary outputs
- `__pycache__/` and `*.pyc` created by Python execution.
- `build/`, `dist/`, and `oasa.egg-info/` created by packaging tools.
- `pyflakes.txt` created by the `run_pyflakes.sh` workflow from the style guide.

## Tests (`tests/`)
- `tests/mypy.ini` static typing configuration.
- `tests/legacy_test.py` legacy test runner.
- `tests/unittests.py` legacy unittest runner.

## Legacy logs
- `docs/legacy/2to3-all.log` and `docs/legacy/2to3-import.log` 2to3 conversion logs.
- `docs/legacy/progress.log` conversion progress notes and history.

## References
- [OASA project page](https://bkchem.zirael.org/oasa_en.html).
- [BKChem homepage](https://bkchem.zirael.org/).
