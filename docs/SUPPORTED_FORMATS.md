# Supported formats

## Default save format
BKChem saves CD-SVG by default. "Save As" defaults to `.svg`, and names without
an extension are saved as `.svg`.

## Native formats
- CD-SVG: `.svg`, `.svgz` (SVG with embedded CDML)
- CDML: `.cdml`, `.cdgz`

## Import formats (built-in plugins)
- CML 1.0: `.cml`, `.xml`
- CML 2.0: `.cml`, `.xml`
- Molfile: `.mol`
- CDXML: `.cdxml` (import and export)

## Export formats (built-in plugins)
- CD-SVG: `.svg`, `.svgz`
- CDML: `.cdml`, `.cdgz`
- SVG (Cairo): `.svg`
- PDF (Cairo): `.pdf`
- PNG (Cairo): `.png`
- PostScript (Cairo): `.ps`, `.eps`
- PostScript (builtin): `.ps`, `.eps`
- ODF (OpenDocument): `.odg`, `.zip`
- SMILES: `.smi`, `.smiles`
- InChI: `.inchi`, `.txt` (requires external InChI binary)

## Notes on optional dependencies
- Cairo exporters require `pycairo`.
- InChI export requires the InChI binary configured via Options -> InChI
  program path.

## Potential future formats
These are common chemistry exchange formats that are not supported today:
- SDF/SD files
- MOL2
- PDB
- CIF

