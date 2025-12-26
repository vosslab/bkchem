# Changelog

## 2025-12-26
- Update [README.md](../README.md) with monorepo overview, doc links, and
  package locations.
- Refresh [docs/INSTALL.md](docs/INSTALL.md) with merged repo run instructions
  and updated Python requirements.
- Revise [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) for the
  `packages/bkchem/` and `packages/oasa/` layout plus the local website mirror.
- Update [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) to use the new
  monorepo paths and OASA doc references.
- Update [packages/oasa/README.md](../packages/oasa/README.md) for monorepo
  install and test locations.
- Add `pyproject.toml` packaging for BKChem and OASA, remove legacy
  `setup.py`, and add a `bkchem` console entry point.
- Teach BKChem path resolution to look in `bkchem_data` and shared install
  directories before legacy relative paths.
- Add [docs/MIGRATION.md](docs/MIGRATION.md) with the BKChem and OASA merge
  summary.
- Switch documentation and packaging metadata to the GitHub repository as the
  primary homepage and mark legacy sites as archived.
- Update Windows installer metadata URLs to point at the GitHub project.
- Migrate legacy HTML and DocBook docs into Markdown
  (`docs/USER_GUIDE.md`, `docs/BATCH_MODE.md`, `docs/CUSTOM_PLUGINS.md`,
  `docs/CUSTOM_TEMPLATES.md`, `docs/EXTERNAL_IMPORT.md`).
- Add [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md) with planned
  distribution paths for BKChem and OASA.
- Add legacy notices to HTML and DocBook sources that now point to Markdown.
- Fix initial pyflakes findings in batch scripts and gettext helpers in core
  modules.
- Define OASA as "Open Architecture for Sketching Atoms and Molecules" across
  docs and metadata.
- Add BKChem modernization follow-ups to [docs/TODO.md](docs/TODO.md).
- Fix more pyflakes findings in BKChem core modules and plugin exporters.
- Exclude the local website mirror from the pyflakes scan.
- Fix additional pyflakes issues in logger, interactors, plugins, and tests.
- Remove Piddle export plugins and Piddle-specific tuning hooks.
- Remove Piddle strings from locale catalogs.
- Rename filesystem plugin scripts to addons, update plugin discovery paths,
  packaging data files, and documentation references.
- Fix more pyflakes findings in core modules, addon scripts, and exporters, and
  prune the website mirror from pyflakes scans.
- Fix additional pyflakes issues in addons, import/export plugins, and core
  helpers (unused imports, gettext fallbacks, and minor logic fixes).
- Resolve remaining pyflakes findings across core modules and plugins, and
  harden the pyflakes runner to skip local website mirrors.
- Add `version.txt` as a shared version registry and wire BKChem and OASA
  version reads to it.
- Standardize BKChem and OASA to use the same version string from
  `version.txt`.
- Bump the shared BKChem/OASA version to `0.16beta1`.
- Add [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md) from the legacy
  progress log.
- Restore the pyflakes runner skip list for `bkchem_webpage` and
  `bkchem_website`.
- Add [tests/run_bkchem_batch_examples.py](../tests/run_bkchem_batch_examples.py) to exercise
  the batch script examples against a temporary CDML file.
- Consolidate test scripts under `tests/`, add OASA-specific runners with
  `oasa_` prefixes, and remove duplicate pyflakes scripts.
- Update OASA docs and file structure notes to reference the new test paths.
- Rename Markdown docs to ALL CAPS filenames and refresh references across
  README, legacy HTML stubs, and doc links.
- Update REPO_STYLE naming rules (root and OASA) for ALL CAPS documentation
  filenames.
- Expand [README.md](../README.md) with highlights, legacy screenshots, and
  updated wording for OASA and repository positioning.
- Add dedicated BKChem and OASA sections to [README.md](../README.md) with
  differences, use cases, and the backend relationship.
- Fix BKChem test runners to add the legacy module path so `import data` resolves.
- Keep `packages/bkchem/` ahead of the legacy module path so `bkchem.main` imports
  correctly in the BKChem test runners.
- Remove legacy HTML/DocBook sources now that Markdown docs are canonical.
- Update `packages/bkchem/prepare_release.sh` to skip DocBook generation when
  sources are no longer present.
- Remove legacy log references from OASA file-structure docs after deleting
  `docs/legacy/`.
- Remove `packages/oasa/LICENSE` and standardize on the root `LICENSE` file.
- Update repo style licensing rules to reflect GPLv2 for the whole repository.
- Update BKChem and OASA packaging metadata to GPL-2.0-only and clean up the
  OASA MANIFEST license references.
- Expand the root README docs list to include every Markdown document under
  `docs/`.
- Update [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md) with the simone16
  0.15 fork acknowledgment and a 0.16beta1 entry.
- Refine the 0.15 simone16 release entry with a date range and concise highlights.
- Add `docs/assets/` screenshots and update the root README to use them.
- Add a draft BKChem package README and link it from the root README.

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
- Add `tests/run_bkchem_gui_smoke.py` to open the GUI briefly for a smoke test.
- Improve GUI smoke test error handling when Tk is unavailable.
- Add `Brewfile` with Homebrew dependencies for Tk support.
- Add `python-tk@3.12` to `Brewfile` and macOS Tk notes to
  `docs/INSTALL.md`.
- Update `tests/run_bkchem_gui_smoke.py` to add the BKChem package directory to
  `sys.path` for legacy relative imports.
- Update GUI smoke test to import `bkchem.main` directly and replace deprecated
  `imp` usage with `importlib` in `bkchem/main.py`.
- Add gettext fallback in `bkchem/messages.py` for module-level strings.
- Initialize gettext fallbacks in `tests/run_bkchem_gui_smoke.py`.
- Add [docs/TODO.md](docs/TODO.md) with a note to replace legacy exporters with
  Cairo equivalents.
