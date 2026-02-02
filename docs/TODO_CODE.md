# Todo code

- Mirror OASA modernization for BKChem (pyflakes cleanup and globals refactors).
- Expand `packages/oasa/oasa_cli.py` beyond Haworth once the CLI surface is finalized
  (format conversion, batch reference output generation).
- Decide whether to remove the legacy PostScript builtin exporter once Cairo is
  required.
- Evaluate optional RDKit/Open Babel integration for expanded import/export
  formats.
  - Target formats: SDF/SD, MOL2, PDB, CIF.
  - Coverage notes:
    - RDKit: SDF/SD, MOL2, PDB; CIF support is limited.
    - Open Babel: SDF/SD, MOL2, PDB, CIF (broader format coverage).
  - Candidate entry points:
    - `packages/bkchem/bkchem/oasa_bridge.py` for conversion hooks.
    - `packages/bkchem/bkchem/plugins/` for optional import/export plugins.
    - [docs/SUPPORTED_FORMATS.md](docs/SUPPORTED_FORMATS.md) to list new formats.
