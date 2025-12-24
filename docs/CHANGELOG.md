# Changelog

## 2025-12-24
- Add [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) with system overview
  and data flow.
- Add [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) with directory map and
  generated assets.
- Rename `README` to `README.md`.
- Update packaging references to `README.md` in `MANIFEST.in` and `setup.py`.
- Scope `tests/run_pyflakes.sh` to core app sources under `bkchem/`.
- Refactor plugin scripts to expose `main(app)` and call it from
  `bkchem/plugin_support.py`.
- Fix core pyflakes warnings for missing gettext helpers and unused imports or
  variables.
- Rewrite `docs/INSTALL.md` with clearer Markdown structure and code blocks.
- Add `pip_requirements.txt` for runtime and optional pip3 dependencies.
- Address additional core pyflakes items in `external_data.py`,
  `singleton_store.py`, `import_checker.py`, `graphics.py`, `misc.py`,
  `edit_pool.py`, `main.py`, and `atom.py`.
- Remove `from tkinter import *` from `bkchem/main.py`.
- Fix `_` usage in `bkchem/edit_pool.py` and clean up unused variables and
  imports in `bkchem/main.py`.
- Add `tests/run_gui_smoke.py` to open the GUI briefly for a smoke test.
- Improve GUI smoke test error handling when Tk is unavailable.
- Add `Brewfile` with Homebrew dependencies for Tk support.
- Add `python-tk@3.12` to `Brewfile` and macOS Tk notes to
  `docs/INSTALL.md`.
- Update `tests/run_gui_smoke.py` to add the `bkchem/` package directory to
  `sys.path` for legacy relative imports.
- Update GUI smoke test to import `main` directly and replace deprecated
  `imp` usage with `importlib` in `bkchem/main.py`.
- Add gettext fallback in `bkchem/messages.py` for module-level strings.
- Initialize gettext fallbacks in `tests/run_gui_smoke.py`.
- Add [docs/TODO.md](docs/TODO.md) with a note to replace Piddle exporters with
  Cairo equivalents.
