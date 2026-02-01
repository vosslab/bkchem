# Changelog

## 2026-02-01
- Remove legacy left/right hatch references from
  [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md).
- Define plugins, addons, and codecs in `README.md`,
  `docs/USAGE.md`, and `docs/CUSTOM_PLUGINS.md` to avoid terminology drift.
- Add the codec registry plan in
  [docs/CODEC_REGISTRY_PLAN.md](docs/CODEC_REGISTRY_PLAN.md).
- Add refactor progress tracking in `refactor_progress.md`.
- Add an OASA codec registry with default SMILES/InChI/molfile/CDML
  registration in `packages/oasa/oasa/codec_registry.py`.
- Expose `codec_registry` from `packages/oasa/oasa/__init__.py`.
- Add CDML text/file writer helpers and module capability flags in
  `packages/oasa/oasa/cdml_writer.py`.
- Route `packages/oasa/chemical_convert.py` through the codec registry and
  allow CDML output selection.
- Add codec registry coverage in `tests/test_codec_registry.py`.
- Add renderer capabilities sheet generator in
  `packages/oasa/oasa/selftest_sheet.py` (LGPL-3.0-or-later) with row-based
  layout, measured bounding boxes, and Fischer projection support.
- Refactor Haworth and Fischer vignettes in `packages/oasa/oasa/selftest_sheet.py`
  to use SMILES → layout → render pipeline instead of hand-placed coordinates,
  testing connectivity-driven molecule rendering.
- Add orange color row to bond grid in `packages/oasa/oasa/selftest_sheet.py`
  (8 types × 6 colors = 48 cells) and adjust vignette positions to accommodate
  taller grid.
- Add capabilities sheet layout specification in
  [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md) documenting the
  measure-first layout system and vignette organization.
- Add CDML architecture plan in
  [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md) for future
  BKChem/OASA separation with layer responsibilities and phased integration.
- Add [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) with a
  provenance-based license migration strategy from GPL-2.0 to mixed
  GPL-2.0 / LGPL-3.0-or-later licensing for new and rewritten components.
- Add [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md)
  to plan the shared render-ops backend for SVG and Cairo.
- Refine [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md)
  with a shared context-provider rule and ops-JSON acceptance criteria.
- Add invariants and scope boundaries to
  [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md) to
  pin down rounding, ordering, and out-of-scope text rendering.
- Add rounded wedge geometry helpers in
  `packages/oasa/oasa/wedge_geometry.py` and default wedge bonds to the rounded
  ops path in `packages/oasa/oasa/render_ops.py`.
- Refine rounded wedge geometry to use flat wide ends with corner fillets and
  update Haworth wedges, snapshots, and unit coverage in
  `packages/oasa/oasa/wedge_geometry.py`,
  `packages/oasa/oasa/render_ops.py`,
  `tests/fixtures/render_ops_snapshot.json`, and
  `tests/test_wedge_geometry.py`.
- Update [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md) to describe
  corner fillets and the flat-base wedge shape.
- Include the in-ring oxygen in the Haworth SVG/PNG smoke layout builder in
  `tests/test_haworth_layout.py`.
- Move the furanose oxygen to the top position and add a furanose oxygen
  placement check in `packages/oasa/oasa/haworth.py` and
  `tests/test_haworth_layout.py`.
- Add Phase 0 BKChem CDML fixtures (basic types, stereo, aromatic ring, wavy
  color, BKChem widths) under `tests/fixtures/bkchem_phase0/`.
- Add a subprocess-backed BKChem CDML load/save/reload smoke test in
  `tests/test_bkchem_cdml_smoke.py`.
- Add unit coverage for the Phase 0 CDML fixtures in
  `tests/test_bkchem_cdml_fixtures_unit.py`.
- Add OASA bond semantics helpers (legacy type normalization and vertex
  canonicalization) in `packages/oasa/oasa/bond_semantics.py`.
- Normalize legacy bond types and canonicalize wedge/hashed vertex ordering on
  CDML read in `packages/oasa/oasa/cdml.py`.
- Normalize legacy bond types and canonicalize wedge/hashed vertex ordering on
  BKChem CDML read in `packages/bkchem/bkchem/bond.py`.
- Add vertex ordering tests for wedge/hashed bonds in
  `tests/test_bond_vertex_ordering.py`.
- Add CDML bond semantics tests (legacy type normalization and canonicalized
  vertex ordering) in `tests/test_cdml_bond_semantics.py`.
- Add CDML bond attribute helpers (presence tracking, unknown preservation,
  and serialization selection) in `packages/oasa/oasa/cdml_bond_io.py`.
- Route OASA CDML bond parsing through shared CDML attribute helpers in
  `packages/oasa/oasa/cdml.py`.
- Route BKChem CDML bond parsing and serialization through shared CDML
  attribute helpers in `packages/bkchem/bkchem/bond.py`.
- Add CDML bond IO unit tests in `tests/test_cdml_bond_io.py`.
- Add a BKChem CDML bond serialization smoke test in
  `tests/test_bkchem_cdml_bond_smoke.py`.
- Export `bond_semantics`, `cdml_bond_io`, and `safe_xml` from
  `packages/oasa/oasa/__init__.py` so BKChem uses local helpers.
- Remove remaining shebangs from pytest-only modules to satisfy the shebang
  lint check in `tests/test_bkchem_cdml_bond_smoke.py`,
  `tests/test_bkchem_cdml_fixtures_unit.py`,
  `tests/test_bkchem_cdml_smoke.py`,
  `tests/test_bond_vertex_ordering.py`,
  `tests/test_cdml_bond_io.py`, and
  `tests/test_cdml_bond_semantics.py`.
- Switch BKChem wedge rendering to the shared rounded wedge geometry and
  render Haworth `q` bonds as round-capped thick lines in
  `packages/bkchem/bkchem/bond.py`.
- Add BKChem rounded wedge and Haworth `q` rendering tests in
  `tests/test_bkchem_round_wedge.py`.
- Add shared atom color palettes in `packages/oasa/oasa/atom_colors.py` and
  enable SVG atom/bond coloring parity with Cairo in
  `packages/oasa/oasa/svg_out.py` and `packages/oasa/oasa/cairo_out.py`.
- Refine `docs/CDML_ARCHITECTURE_PLAN.md` with writer API details, unit
  convention, namespace handling, feature-flag guidance, and fixture updates.
- Add an OASA CDML molecule writer in `packages/oasa/oasa/cdml_writer.py`,
  route OASA CDML reads through it in `packages/oasa/oasa/cdml.py`, and add
  a basic writer unit test in `tests/test_cdml_writer.py`.
- Add `config.use_oasa_cdml_writer` and a gated BKChem molecule serializer
  path in `packages/bkchem/bkchem/config.py` and
  `packages/bkchem/bkchem/molecule.py`.
- Extend bond CDML helpers to store present/unknown attributes on the bond
  object (while keeping properties_ compatibility) in
  `packages/oasa/oasa/cdml_bond_io.py`.
- Expose `render_ops` and `wedge_geometry` from `packages/oasa/oasa/__init__.py`
  and update BKChem bond rendering to import them directly in
  `packages/bkchem/bkchem/bond.py`.
- Remove unused XML import from `packages/oasa/oasa/selftest_sheet.py`.
- Regenerate reference outputs under `docs/reference_outputs/` using
  `tools/render_reference_outputs.py`.
- Remove shebangs from pytest modules in `tests/test_bkchem_cdml_roundtrip.py`,
  `tests/test_cdml_roundtrip_oasa.py`, and `tests/oasa_legacy_test.py`.
- Add SPDX headers to new LGPL files in
  `packages/oasa/oasa/cdml_writer.py`,
  `packages/oasa/oasa/atom_colors.py`,
  `tests/test_cdml_writer.py`, and
  `tests/test_bkchem_round_wedge.py`.
- Remove the executable bit from `tests/oasa_legacy_test.py` to satisfy
  shebang alignment checks.
- Add OASA CDML writer round-trip tests in
  `tests/test_cdml_writer_roundtrip.py`.
- Add a BKChem CDML writer-flag smoke test in
  `tests/test_bkchem_cdml_writer_flag.py`.
- Add a CDML golden fixture corpus under `tests/fixtures/cdml/` (benzene,
  stereochem, haworth, cholesterol, legacy, embedded SVG) and load tests in
  `tests/test_cdml_fixture_loads.py`.
- Add a legacy fixture migration check in `tests/test_cdml_versioning.py`.
- Switch SVG pretty-print parsing to `defusedxml.minidom` in
  `packages/oasa/oasa/svg_out.py`.
- Fix Cairo import handling in the renderer capabilities sheet generator in
  `packages/oasa/oasa/selftest_sheet.py`.
- Update `launch_bkchem_gui.sh` to include local OASA paths in `PYTHONPATH`.
- Add a CDML round-trip fixture in
  `tests/fixtures/cdml_roundtrip/custom_attr.cdml`.
- Generate reference outputs under `docs/reference_outputs/` using
  `tools/render_reference_outputs.py`.
- Add Phase 3 CDML round-trip fixtures in `tests/fixtures/cdml_roundtrip/`.
- Add OASA CDML round-trip metadata tests in
  `tests/test_cdml_roundtrip_oasa.py`.
- Add BKChem CDML round-trip subprocess smoke test in
  `tests/test_bkchem_cdml_roundtrip.py`.
- Ensure BKChem CDML smoke tests include local OASA paths in
  `tests/test_bkchem_cdml_smoke.py`.
- Remove shebangs from pytest modules that are not intended to be executable:
  `tests/test_bkchem_cdml_bond_smoke.py`,
  `tests/test_bkchem_cdml_fixtures_unit.py`,
  `tests/test_bkchem_cdml_smoke.py`,
  `tests/test_bond_vertex_ordering.py`,
  `tests/test_cdml_bond_io.py`,
  `tests/test_cdml_bond_semantics.py`.
- Remove left/right hatch rendering and map any legacy `l`/`r` bonds to standard
  hatch output in `packages/oasa/oasa/render_ops.py`, plus update the bond
  styles smoke list in `tests/test_oasa_bond_styles.py`.
- Drop the Haworth wedge front-cap hook so Haworth wedges use the shared rounded
  wedge path in `packages/oasa/oasa/render_ops.py`.
- Remove the legacy straight-wedge fallback so all wedges use the rounded
  geometry path in `packages/oasa/oasa/render_ops.py`.
- Add `launch_bkchem_gui.sh` to start the BKChem GUI from the repo root.
- Update the bond-style SVG smoke test to expect path output for rounded wedges
  in `tests/test_oasa_bond_styles.py`.
- Define shared render ops, serialization, and bond op generation in
  `packages/oasa/oasa/render_ops.py`.
- Migrate SVG/Cairo bond rendering to shared render ops in
  `packages/oasa/oasa/svg_out.py` and `packages/oasa/oasa/cairo_out.py`.
- Add a render-ops snapshot test and fixture in
  `tests/test_render_ops_snapshot.py` and
  `tests/fixtures/render_ops_snapshot.json`.
- Update the bond-style printer SVG smoke assertion to expect path output in
  `tests/test_oasa_bond_styles.py`.
- Remove unused bond drawing helpers from the Cairo backend so it only renders
  shared ops in `packages/oasa/oasa/cairo_out.py`.
- Move Haworth front-bond coordinate lookup into shared render ops by passing
  bond coordinate providers from both SVG and Cairo backends.
- Add Haworth substituent placement rules for D/L and alpha/beta in
  `packages/oasa/oasa/haworth.py`.
- Add ops-level substituent orientation tests in
  `tests/test_haworth_layout.py`.
- Add folder-based template catalog scanning utilities in
  `packages/bkchem/bkchem/template_catalog.py` plus a scan test in
  `tests/test_template_catalog.py`.
- Add biomolecule template label formatting and biomolecule template directory
  discovery helpers in `packages/bkchem/bkchem/template_catalog.py`.
- Add a biomolecule template manager, mode, and Insert-menu entry for
  template insertion in `packages/bkchem/bkchem/main.py`,
  `packages/bkchem/bkchem/modes.py`, and
  `packages/bkchem/bkchem/singleton_store.py`.
- Add CDML biomolecule templates (carbs, protein, lipids, nucleic acids) under
  `packages/bkchem/bkchem_data/templates/biomolecules/`.
- Add biomolecule template insertion smoke coverage in
  `tests/test_biomolecule_templates.py`, plus label formatting coverage in
  `tests/test_template_catalog.py`.
- Add [docs/REFERENCE_OUTPUTS.md](docs/REFERENCE_OUTPUTS.md) and a
  `tools/render_reference_outputs.py` helper to generate Haworth and wavy-bond
  reference SVG/PNG outputs under `docs/reference_outputs/`.
- Add a reference output smoke test in `tests/test_reference_outputs.py`.
- Refresh [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) and
  [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) with updated component and
  repository layout details.
- Add new doc set stubs and pointers:
  [docs/NEWS.md](docs/NEWS.md),
  [docs/RELATED_PROJECTS.md](docs/RELATED_PROJECTS.md),
  [docs/ROADMAP.md](docs/ROADMAP.md),
  [docs/TODO.md](docs/TODO.md),
  [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md),
  [docs/USAGE.md](docs/USAGE.md).
- Fix mixed-indentation lines in `packages/oasa/oasa/render_ops.py`.
- Add [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md) with a
  comprehensive plan for robust, reusable rounded wedge geometry that works
  for all wedge bonds (both standard stereochemistry and Haworth projections).
  The plan uses a clean 4-parameter endpoint-based API (tip_point, base_point,
  wide_width, narrow_width=0.0) where the wedge is directional (expands from
  tip to base), length and angle are derived outputs (not inputs), includes
  area-based validation tests to verify correctness at all orientations, and
  eliminates scaling/mirroring parameters (directionality encoded in endpoint
  order, scaling is caller's responsibility).

## 2026-01-31
- Add [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  to outline Haworth projection goals, scope, and implementation phases.
- Document the biomolecule template side feature in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md),
  covering CDML templates and the initial macro categories.
- Add the wavy-bond smoke glucose note to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Note that biomolecule template categories are inferred from folder names by
  scanning CDML files on load in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Note that template subcategories are inferred from subfolder names in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Expand [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  with Haworth bond style notes (left/right hatch, wide rectangle),
  CDML ownership guidance, insert-only template workflow, and the
  wavy_bond.png reference.
- Add a testing plan (unit and smoke tests) to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Add staged rollout notes with testable outcomes to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Expand [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  with bond style specs, including the NEUROtiker-derived bold multiplier and
  the sine-wave wavy bond decision.
- Note template distribution in the macOS app bundle and the Insert-menu
  entry point in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Implement Stage 1 renderer updates: SVG wedge/hatch/bold support and
  per-bond line widths in SVG/Cairo (`packages/oasa/oasa/svg_out.py`,
  `packages/oasa/oasa/cairo_out.py`).
- Add a smoke test for SVG/PNG bond style rendering (normal, bold, wedge,
  hatch) in `tests/test_oasa_bond_styles.py`.
- Update the Stage 2 plan in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  to cover full new bond type support and add a post-Stage 2 printer-style
  smoke test plan with colored bonds.
- Rename the bond style smoke test outputs to
  `oasa_bond_styles_smoke.svg` and `oasa_bond_styles_smoke.png`.
- Add `defusedxml` as a required dependency and use it for safe XML parsing via
  new `safe_xml` helpers in BKChem and OASA.
- Set the shared BKChem/OASA version registry to `26.02`.
- Update version references and fallbacks to `26.02` in release history,
  format docs, and the OASA README.
- Bump the CDML format version to `26.02` with a compatibility transformer and
  add `tests/test_cdml_versioning.py` for legacy CDML smoke coverage.
- Add [docs/VERSIONING_DOCS.md](docs/VERSIONING_DOCS.md) to track release and
  CDML version update locations.
- Add a Haworth CLI phase to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md),
  including a draft `oasa_cli.py --haworth` command and smoke testing notes.
- Update `tests/oasa_legacy_test.py` to write named outputs into a temporary
  directory so test files are cleaned up after the run.
- Use `defusedxml.minidom` in `tests/test_cdml_versioning.py` to satisfy
  Bandit B318.
- Start Stage 2 Haworth work: add new bond type rendering (wavy variants,
  left/right hatch, wide rectangle) plus per-bond colors in OASA SVG/Cairo,
  update BKChem bond/SVG handling for the new types, and add a printer
  self-test smoke in `tests/test_oasa_bond_styles.py`.
- Add a `--save` flag to `tests/test_oasa_bond_styles.py` so bond-style smoke
  outputs can be written to the current working directory.
- Implement Stage 3 Haworth layout in OASA with ring templates and front-edge
  bond tagging, and add `tests/test_haworth_layout.py` for layout and SVG
  smoke coverage.
- Allow `tests/test_haworth_layout.py` to save SVG output to the current
  working directory with the shared `--save` pytest flag.
- Expand the bond-style printer self-test grid to use bond types along the
  x-axis and colors along the y-axis, increase output size, and densify
  wavy-bond sampling for smoother SVG output.
- Flatten the Haworth ring template (no skew) and increase wide-rectangle
  bond thickness in OASA and BKChem rendering.
- Tag Haworth front edges with left hatch, wide rectangle, and right hatch
  bond styles by default, and fix midpoint lookup when resolving hatch sides.
- Drop Haworth ring distortion parameters (skew/vertical squash) in favor of
  flat ring geometry plus Haworth bond styles, and update the plan text.
- Replace regular-polygon Haworth rings with non-regular pyranose/furanose
  templates derived from sample geometry.
- Make Haworth front edges use wedge side bonds plus a wide rectangle by
  default, update the smoke test to render both ring types, and switch to
  symmetric non-regular templates.
- Rotate Haworth ring atom order so a ring oxygen sits at the top portion of
  the template when present, and add a smoke assertion for that placement.
- Combine the Haworth pyranose/furanose smoke render into a single
  side-by-side SVG output.
- Set ring bond vertex order to match the ring traversal and pick the
  Haworth rectangle edge by frontmost midpoint with adjacent wedges.
- Flip the furanose template vertically to keep the front edge at the
  bottom, and normalize Haworth ring traversal orientation for consistent
  left/right behavior.
- Orient Haworth wedge bonds so the front vertex is the wide end, and add a
  smoke assertion that the front edge is the max-midpoint-y edge.
- Add intentional overlap for Haworth wide rectangles and wedges in SVG/Cairo
  output to eliminate seam gaps without changing atom coordinates.
- Lengthen the furanose front edge by widening the template coordinates.
- Render Haworth wide rectangles as thick stroked lines with round caps to
  smooth joins and clean up the silhouette.
- Inset Haworth round-capped front edges by half the line width to avoid
  protruding past wedge joins.
- Drop wedge cap circles; keep wedge polygons and round-capped front edges
  for cleaner Haworth joins.
- Replace Haworth wedge bases with rounded arc paths aligned to the front
  edge cap center to eliminate join artifacts.
- Extend the Haworth layout smoke test to render Cairo PNG output alongside
  SVG output (skipping when pycairo is unavailable).
- Offset wedge cap centers inward to keep wedge length stable, and flip the
  Haworth Cairo smoke molecule so PNG orientation matches SVG.
- Increase the default Cairo render scaling factor for higher-resolution PNG
  output.
- Replace legacy XML parsing in BKChem and OASA with `safe_xml` wrappers,
  including ftext markup parsing and CDML/CDATA imports.
- Replace `eval()` with `ast.literal_eval()` in preference and external data
  parsing.
- Harden NIST WebBook fetchers with scheme/host validation and randomized
  request delays.
- Replace `tempfile.mktemp()` with a temporary directory in the ODF exporter.
- Parameterize structure database SQL lookups in OASA.
- Add a plugin path allowlist and explicit exec annotations for plugin and
  batch script execution.
- Normalize indentation to tabs in the files flagged by
  `tests/test_indentation.py`.
- Annotate validated WebBook urlopen calls to silence Bandit B310.
- Expand the Haworth plan scope to cover pyranose and furanose rings, and add
  local SVG references.
- Update [docs/TODO_CODE.md](docs/TODO_CODE.md) to match the Haworth scope.
- Align Haworth style notes with existing renderer defaults and add external
  NEUROtiker archive references.
- Replace the TODO list with [docs/TODO_REPO.md](docs/TODO_REPO.md) and
  [docs/TODO_CODE.md](docs/TODO_CODE.md).
- Refresh todo references in [README.md](../README.md),
  [docs/REPO_STYLE.md](docs/REPO_STYLE.md), and
  [packages/oasa/docs/REPO_STYLE.md](../packages/oasa/docs/REPO_STYLE.md).

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
- Add [tests/bkchem_batch_examples.py](../tests/bkchem_batch_examples.py) to exercise
  the batch script examples against a temporary CDML file.
- Rename BKChem test runners to drop the `run_` prefix.
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
- Initialize BKChem preferences in GUI and batch test runners to avoid
  Store.pm errors.
- Align BKChem test runner preference initialization with legacy imports to
  avoid duplicate singleton modules.
- Add `tests/run_smoke.sh` to run BKChem smoke tests together.
- Remove the background Tk thread from the batch example logic to avoid Tcl
  threading errors on macOS.
- Move BKChem example scripts out of `docs/scripts/` into `tests/`.
- Inline legacy batch script behavior into `tests/bkchem_batch_examples.py`
  and remove the standalone example scripts.
- Add success checks to BKChem smoke and batch example tests.
- Add `tests/bkchem_manual.py` for interactive manual testing.
- Extend `tests/run_smoke.sh` to include the OASA smoke render and verify output.
- Filter optional plugin-load warnings from the smoke test output.
- Number the smoke test output steps in `tests/run_smoke.sh`.
- Keep `tests/run_smoke.sh` running all tests and report failures at the end.
- Fix BKChem batch examples to use `bkchem.main.BKChem()` instead of legacy
  `bkchem.myapp`.
- Add `tests/oasa_smoke_formats.py` to render SVG, PDF, and PNG variants in
  smoke tests.
- Switch BKChem plugin imports to explicit relative paths so optional plugins
  load reliably under Python 3 packaging.
- Surface plugin import errors with module names and exception details, with
  optional tracebacks when debug mode is enabled.
- Add `tests/bkchem_plugin_smoke.py` and `tests/run_plugin_smoke.sh` to report
  loaded plugins and fail fast on missing plugin imports.
- Drop the legacy OpenOffice Draw export plugin and remove its unused manifest.
- Refresh the ODF exporter description to reference OpenDocument and LibreOffice.
- Allow BKChem plugin loader to import config when plugins are loaded as a
  top-level package.
- Skip the standard-value replacement prompt when opening built-in templates.
- Add SMILES and InChI export plugins powered by OASA for BKChem exports.
- Expand the BKChem plugin smoke test to report plugin modes, extensions, and
  doc strings (optional summary output).
## 2026-02-01
- Regenerate biomolecule template CDML files from `biomolecule_smiles.txt`.
- Add `tools/generate_biomolecule_templates.py` to rebuild biomolecule templates.
- Split biomolecule template selection into category and template dropdowns.
- Match the disabled edit-pool background to the UI theme to avoid a black bar.
- Fix mixed indentation in `packages/oasa/oasa/selftest_sheet.py`.
- Pretty-print SVG output when writing files in `packages/oasa/oasa/svg_out.py`.
- Add [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  with a phased plan for aligning BKChem and OASA bond semantics.
- Teach `tools/generate_biomolecule_templates.py` to read YAML input and add
  legacy name mapping when generating template paths.
- Regenerate biomolecule templates from `biomolecule_smiles.yaml`.
- Remove left/right hatch references from
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md) and
  focus on deterministic vertex ordering for hashed bonds.
- Refine [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  to call out vertex ordering rules, snapshot guidance, and updated risks.
- Add explicit canonicalization helper and serialization policy to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md).
- Add test strategy section to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  covering fixtures, invariants, and vertex ordering tests.
- Expand the test strategy in
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  with atom label and coordinate transform smoke tests plus fixture suite scope.
- Add maintainability expansion guidance to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  covering shared OASA core boundaries, next semantic layers, and a deletion
  gate.
- Add measurable phases with pass criteria to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md),
  including the test harness phase and deletion gate phase.

## 2026-01-31
- Add an optional export check to the BKChem plugin smoke test, writing sample
  files and reporting output sizes.
- Use the macOS system menu bar when running on Darwin, keeping in-window menus
  for other platforms.
- Add [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md) to document the
  CDML file format.
- Add [docs/SUPPORTED_FORMATS.md](docs/SUPPORTED_FORMATS.md) with import/export
  formats and default save behavior.
- Update [docs/TODO.md](docs/TODO.md) with new follow-up items.
- Note optional RDKit/Open Babel integration as a potential format expansion path.
- Expand RDKit/Open Babel TODO with candidate files and docs.
- Add format coverage notes to the RDKit/Open Babel TODO entry.
- Add `inchi` to the Homebrew dependencies.
- Clarify required and optional dependencies in [docs/INSTALL.md](docs/INSTALL.md).
- Mark `pycairo` as a required dependency.
- Resolve OASA mypy errors by tightening class imports, annotations, and a
  stderr print fix.
- Adjust OASA graph base classes to allow extended `attrs_to_copy` tuples.
- Fix macOS system menubar initialization with Pmw MainMenuBar.
- Update OASA digraph base import for the refactored graph module exports.
- Update OASA config to reference the molecule class directly after import
  refactors.
- Normalize standard comparison to avoid false "Replace standard values" prompts
  when files match current defaults.
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
- Add `tests/bkchem_gui_smoke.py` to open the GUI briefly for a smoke test.
- Improve GUI smoke test error handling when Tk is unavailable.
- Add `Brewfile` with Homebrew dependencies for Tk support.
- Add `python-tk@3.12` to `Brewfile` and macOS Tk notes to
  `docs/INSTALL.md`.
- Update `tests/bkchem_gui_smoke.py` to add the BKChem package directory to
  `sys.path` for legacy relative imports.
- Update GUI smoke test to import `bkchem.main` directly and replace deprecated
  `imp` usage with `importlib` in `bkchem/main.py`.
- Add gettext fallback in `bkchem/messages.py` for module-level strings.
- Initialize gettext fallbacks in `tests/bkchem_gui_smoke.py`.
- Add [docs/TODO.md](docs/TODO.md) with a note to replace legacy exporters with
  Cairo equivalents.
