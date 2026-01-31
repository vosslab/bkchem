# Haworth implementation plan

## Purpose
- Add a Haworth projection renderer for monosaccharides, targeting the look of
  the NEUROtiker SVG style while staying consistent with OASA and BKChem
  rendering conventions.
- Produce clean, publication-grade rings with front-edge bolding and
  consistent label placement.

## Scope
- Initial focus: pyranose (6-member) and furanose (5-member) rings with D/L
  and alpha/beta variants.
- Defer complex glycans until the base ring templates are stable.
- Keep the implementation optional so standard coordinate generation is
  unaffected.

## Style targets (from local SVG samples)
- Use filled polygons or thick strokes for front-facing ring edges.
- Use thinner strokes for back-facing ring edges and substituent bonds.
- Maintain a mild perspective skew for the ring (not a flat hexagon).
- Use existing OASA/BKChem font settings and label spacing to avoid custom
  typography rules.

## Assets for reference
- Local samples:
  - [Alpha-D-Glucopyranose.svg](../Alpha-D-Glucopyranose.svg)
  - [Alpha-D-Arabinofuranose.svg](../Alpha-D-Arabinofuranose.svg)
  - [D-Ribose_Haworth.svg](../D-Ribose_Haworth.svg)
  - [D-Xylulose_Haworth.svg](../D-Xylulose_Haworth.svg)
  - [Haworth_projection_of_a-L-Glucopyranose.svg](../Haworth_projection_of_a-L-Glucopyranose.svg)
- Additional sample files from the NEUROtiker galleries (external references,
  not stored in this repo).
  - [NEUROtiker archive 1](https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive1)
  - [NEUROtiker archive 2](https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive2)
  - [NEUROtiker archive 3](https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive3)

## Current rendering constraints
- OASA has a global `line_width` and `bond_width`, but no per-bond thickness.
- OASA bond type includes `'b'` (bold) but is not rendered specially yet.
- `svg_out.py` ignores `line_width` for edges and hard-codes stroke width.

## Proposed architecture
- Add an OASA module `oasa/haworth.py` that generates coordinates plus style
  hints for Haworth projections.
- Add a `haworth_layout` helper that:
  - Builds ring templates (pyranose and furanose).
  - Assigns atom order and ring orientation.
  - Tags front bonds as bold and back bonds as normal.
  - Positions substituents up/down based on D/L and alpha/beta choices.
- Add a minimal public API to request Haworth layout, for example:
  - `oasa.haworth.build_haworth(mol, mode="pyranose", stereo="alpha", series="D")`

## Rendering updates (OASA)
- Implement per-bond thickness:
  - In `cairo_out.py`, honor `bond.type == "b"` by increasing line width.
  - In `svg_out.py`, pass the `line_width` argument to the SVG elements and
    apply the bold override when `bond.type == "b"`.
- Keep defaults unchanged for non-Haworth drawings.

## Data model and detection
- Start with explicit user input (mode, series, alpha/beta, ring atom order).
- Avoid full SMILES stereochemistry inference in phase 1.
- Add a lightweight sugar template descriptor later if needed.

## Implementation phases
1) Rendering: add per-bond thickness support in Cairo and SVG.
2) Layout: implement pyranose and furanose ring templates with perspective
   skew and bond thickness tagging.
3) Substituents: position OH/CH2OH groups using up/down rules for D/L and
   alpha/beta.
4) API + tests: add a small smoke test and a reference PNG/SVG output.
5) Docs: document the new API and add usage examples.

## Open questions
- Where to host the Haworth entry point in BKChem (GUI tool, exporter option,
  or a separate script)?
- What minimal input format should be used to avoid ambiguous stereochemistry?
- Should bolding be a fixed multiplier or derived from the base line width?
