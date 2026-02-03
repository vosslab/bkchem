# Refactor progress

Last updated: 2026-02-03

## Snapshot
- Registry refactor: OASA codec registry is implemented and in use by the CLI.
- Rendering refactor: SVG/Cairo unified via render ops, rounded wedges default.
- CDML refactor: OASA CDML writer is the only BKChem serialization path.
- Haworth CLI: batch SMILES rendering is available via `packages/oasa/oasa_cli.py`.
- Menu refactor: [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md) is
  the master plan; implementation is not started.
- PubChem integration: plan is documented; implementation not started.
- Data reorg: OASA isotope data moved to JSON and legacy data sources removed.

## Not started
- Menu refactor implementation:
  [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md) and the supporting
  docs define the plan, but no code migration has landed yet.
- [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md):
  Implementation work not started; docs describe the refactor scope and plan.
- [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md):
  Analysis complete; implementation not started.
- [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md):
  Tool registry and migration are planned but not implemented.
- [docs/PUBCHEM_API_PLAN.md](docs/PUBCHEM_API_PLAN.md):
  PubChem lookups are planned with no code landed yet.
- BKChem modernization (from [docs/TODO_CODE.md](docs/TODO_CODE.md)):
  Mirror OASA cleanup work (pyflakes cleanup and globals refactors).
- Legacy export decision (from [docs/TODO_CODE.md](docs/TODO_CODE.md)):
  Decide whether to remove the legacy PostScript builtin exporter now that
  Cairo is required.
- Format expansion evaluation (from [docs/TODO_CODE.md](docs/TODO_CODE.md)):
  RDKit/Open Babel format expansion planning (SDF/SD, MOL2, PDB, CIF).
- Repo modernization and distribution (from [docs/TODO_REPO.md](docs/TODO_REPO.md)):
  Publish OASA to PyPI, plan BKChem binary distribution, mirror OASA packaging
  metadata + version reporting for BKChem, decide BKChem mypy scope and add a
  runner, reconcile licensing guidance, and document runtime dependencies.
- [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md):
  Automated installer tooling is planned for macOS dmg, Windows installer, and
  Linux Flatpak builds.

## In progress
- [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md):
  Stages 1-3 and 5-7 are complete; Stage 4 (correct OH/substituent placement)
  is still in progress.
- [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md):
  Active policy; continue enforcing SPDX headers on new files.
- [docs/TODO_CODE.md](docs/TODO_CODE.md):
  Still relevant backlog; needs updates for plugin/addon removal work.
- [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md):
  Needs updates to reflect the plugin/addon removal plan from the menu refactor.
- OASA CLI expansion:
  Planned next step is to broaden `packages/oasa/oasa_cli.py` once the public
  CLI surface is finalized.

## Completed
- [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md):
  Render ops, SVG/Cairo thin painters, ops snapshots, and drift tests are in place.
- [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md):
  Rounded wedge geometry is shared via `wedge_geometry.py` and used by render ops
  and BKChem bond rendering.
- [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md):
  Phases 0-5 complete; Phase 4 optional. Bond semantics normalized with tests.
- [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md):
  Phases 1-2 complete; Phase 3 optional. OASA CDML writer is default path.
- [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md):
  Updated for normalized hashed bonds and current bond type list.
- [docs/CODEC_REGISTRY_PLAN.md](docs/CODEC_REGISTRY_PLAN.md):
  Phase 1-5 complete; registry used by CLI and BKChem oasa_bridge.
- Menu refactor documentation set:
  [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md),
  [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md),
  [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md), and
  [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md).
- Data reorganization:
  Isotope data moved to `packages/oasa/oasa_data/isotopes.json`, legacy OASA data
  files removed, and `tools/convert_isotope_data.py` added for refresh.
