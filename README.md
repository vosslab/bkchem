# BKChem and OASA monorepo

This repo is an unofficial fork of BKChem that now bundles the BKChem GUI and
the OASA (Open Architecture for Sketching Atoms and Molecules) chemistry
library in one workspace.

## Packages
- `packages/bkchem/` BKChem Tk GUI for drawing chemical structures.
- `packages/oasa/` OASA (Open Architecture for Sketching Atoms and Molecules)
  library and CLI converters used by BKChem.

## Docs
- [docs/INSTALL.md](docs/INSTALL.md) for running from source and optional installs.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) and
  [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) for repo layout details.
- [docs/MIGRATION.md](docs/MIGRATION.md) for the repository merge summary.
- [docs/user_guide.md](docs/user_guide.md) for the migrated BKChem manual.
- [docs/batch_mode.md](docs/batch_mode.md) and
  [docs/external_import.md](docs/external_import.md) for scripting and batch use.
- [docs/custom_plugins.md](docs/custom_plugins.md) and
  [docs/custom_templates.md](docs/custom_templates.md) for extension workflows.
- [docs/release_distribution.md](docs/release_distribution.md) for release plans.
- [packages/oasa/README.md](packages/oasa/README.md) for OASA-specific usage.

## Distribution
- Planned: publish OASA to PyPI from this monorepo.
- Planned: ship BKChem binary installers (macOS dmg, Linux Flatpak, Windows).

## Local website mirror
- `bkchem_webpage/` contains a local copy of the legacy BKChem website.

## Project home
- [GitHub repository](https://github.com/vosslab/bkchem) is the primary homepage.

## Legacy references
- [Legacy BKChem site](https://bkchem.zirael.org/) (Python 2 era, not maintained).
- [Legacy OASA site](https://bkchem.zirael.org/oasa_en.html) (Python 2 era, not maintained).

## License
- See `LICENSE` and `packages/oasa/LICENSE`.
