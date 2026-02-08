# Changelog

## 2026-02-08
- Extend furanose top-side `up` connector lengths in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  for top-left/top-right slots (`ML`/`MR`) so endpoints clear above the ring
  oxygen glyph, improving match to reference top geometry; add regression coverage
  in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `MKLRDM` furanose-beta (`C2_up_connector`, `C5_up_connector`).
- Fix exocyclic `CH<sub>2</sub>OH` connector anchoring in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  so ring connectors terminate at the leading carbon (`C`) glyph center instead
  of the text midpoint/subscript region; add regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `ARRRDM` pyranose-alpha (`C5_up_label`).
- Fix generated-preview scaling inconsistency in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) by normalizing
  whitespace when estimating SVG text bbox widths; this prevents inflated widths
  from pretty-printed `<tspan>` indentation/newlines (notably `CH<sub>2</sub>OH`)
  that previously produced oversized viewBoxes and tiny rendered sugars.
- Add two-pass hydroxyl label layout in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  using a tiny candidate slot set (`1.00x`, `1.18x`, `1.34x` connector lengths)
  and minimum-gap collision scoring for `OH`/`HO` text boxes; this reduces crowded
  furanose-side hydroxyl collisions while preserving deterministic connector
  placement. Add regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for ALDM
  furanose-alpha spacing and direct candidate-slot selection behavior.
- Add CLI argument parsing to
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) with
  `--regenerate-haworth-svgs` (default off) so generated Haworth preview SVGs are
  only re-rendered on demand; default behavior now reuses existing previews and
  falls back to existing matrix SVG outputs when available.
- Calibrate furanose ring geometry from NEUROtiker archive references by adding
  [tools/neurotiker_furanose_geometry.py](tools/neurotiker_furanose_geometry.py)
  extraction/normalization of 40 furanose SVGs (mean slot coordinates, edge
  lengths, and internal angles), then adopt the measured mean template in
  [packages/oasa/oasa/haworth.py](packages/oasa/oasa/haworth.py) and update
  regression expectations in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Refine furanose ring geometry in [packages/oasa/oasa/haworth.py](packages/oasa/oasa/haworth.py)
  by shifting the middle left/right pentagon vertices inward/upward to better
  match NEUROtiker reference proportions.
- Improve hydroxyl connector/text separation in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  by keeping oxygen-centered horizontal alignment while increasing downward
  hydroxyl baseline offset to prevent bond-to-glyph overlap; add helper geometry
  functions plus regression tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  hydroxyl connector endpoints align with oxygen centers and do not overlap the
  oxygen glyph region.
- Harden [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) XML
  parsing by switching from stdlib `xml.etree.ElementTree.parse` to
  `defusedxml.ElementTree.parse`, resolving Bandit B314 in full-suite security
  checks.
- Update [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) so
  generated comparison previews are re-rendered with
  `show_hydrogens=False` (no explicit H labels/connectors) and displayed at
  80% scale via expanded normalized viewBox framing for easier side-by-side
  visual comparison against NEUROtiker references.
- Adjust hydroxyl label x-offset geometry in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  so connector endpoints align with the oxygen glyph center for both right-
  anchored `OH` labels and left-anchored `HO` labels; add regression tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) covering each
  anchor direction.
- Improve summary-page centering/scaling in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) by generating
  normalized generated-preview SVGs with tight content-fitted viewBoxes under
  `output_smoke/archive_matrix_previews/generated/`, and updating HTML/CSS preview
  frames to center content with non-distorting `max-width`/`max-height` scaling.
- Add [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) to build
  a single human-review HTML page at
  `output_smoke/archive_matrix_summary.html`, showing all 78 Phase 5b archive
  cases with side-by-side generated and reference SVG previews plus missing-file
  summary counts.
- Start Phase 6 sugar-code-to-SMILES implementation with a bootstrap converter
  in [packages/oasa/oasa/sugar_code_smiles.py](packages/oasa/oasa/sugar_code_smiles.py),
  export it from [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py),
  and add unit coverage in
  [tests/test_sugar_code_smiles.py](tests/test_sugar_code_smiles.py) for
  validated reference cases (`ARLRDM` pyranose alpha and `MKLRDM` furanose beta),
  input validation, and unsupported-combination errors.
- Update [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  Phase 6 section with bootstrap implementation status and remaining scope.
- Close Phase 0 in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  by marking the phase tracker checkbox complete and recording release-gate
  validation results: full test suite (`333 passed, 6 skipped`) plus successful
  selftest sheet SVG generation using `source source_me.sh` with Python 3.12.
- Add a phase-status checklist at the top of
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  to track completion across Phases 1-7 and Phase 0 exit closure.
- Update [AGENTS.md](AGENTS.md) environment instructions to require
  `source source_me.sh` before running Python commands.
- Expand NEUROtiker archive reference fixtures by adding
  [tests/fixtures/neurotiker_archive_mapping.py](tests/fixtures/neurotiker_archive_mapping.py)
  (sugar-code/ring/anomer -> archive filename mapping helpers) and
  [tests/fixtures/archive_ground_truth.py](tests/fixtures/archive_ground_truth.py)
  (manually verified substituent ground truth across the mappable archive set).
- Add archive-wide Haworth validation coverage:
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py) now parametrizes
  expected substituents against archive ground truth, and
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  now includes a full mappable archive matrix render smoke test.
- Improve Haworth renderer configurability and label geometry in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  add `show_hydrogens` and `oxygen_color` render controls, split oxygen-adjacent
  ring edges into two-color segments, tune connector-length multipliers, and use
  direction-aware baseline shifts so connector endpoints align more tightly to labels.
- Extend renderer regression tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for oxygen-edge
  polygon counts, updated connector-length constants, and hydrogen-hide behavior
  (suppress `H` labels/connectors while preserving non-hydrogen substituents).
- Expand Haworth selftest visual vignettes in
  [tools/selftest_sheet.py](tools/selftest_sheet.py) by adding a third row with
  alpha-D-Tagatopyranose and alpha-D-Psicofuranose builder cases for crowded-label
  positioning checks.
- Update design/roadmap notes in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with Phase 5b archive-reference testing details, Phase 5c rendering-polish notes,
  and explicit multi-ring/collision detection stretch-goal documentation.
- Add a focused Wikimedia downloader script at
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  that only accepts `User:NEUROtiker/gallery/archive1`, filters `File:` links by
  case-insensitive `haworth`, resolves original image URLs via Commons API, and
  writes a manifest JSON with source file page, URL, SHA1, MIME type, and local path.
- Harden Wikimedia fetch behavior in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py):
  keep requests strictly sequential with `time.sleep(delay_base + random.random())`
  before each request, add retry/backoff for transient HTTP/network failures
  including `429`, and continue per-file with manifest error records instead of
  aborting the entire run on first failure.
- Improve NEUROtiker archive filtering in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  to parse archive wikitext (`action=raw`) and match keyword on each `File:` line
  (including caption/description text), so Haworth entries are discovered even
  when filenames do not contain the word "haworth".
- Expand NEUROtiker archive matching in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  to accept any `User:NEUROtiker/gallery/archive#` URL and support
  comma-separated keyword terms (default `haworth,pyranose,furanose`) for caption/line
  matching, so pyranose/furanose Haworth entries in archive2+ are included even
  without explicit "haworth" in filenames.
- Simplify downloader CLI in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  to avoid argparse creep: keep only positional archive URLs plus `--dry-run`
  and `--limit`, default archive targets to `archive1` + `archive2` + `archive3`
  + `archive4`, and derive
  per-archive output folders/manifest paths automatically.
- Fix raw-page URL construction in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  by deriving MediaWiki `title` as `User:...` from `/wiki/...` paths (instead of
  `wiki/User:...`), resolving `HTTPError 404` on `--dry-run` archive fetches.
- Adjust Haworth substituent connector geometry in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  so side-carbon (`MR`/`ML`) up/down bonds are vertical (not diagonal) for both
  pyranose and furanose renderings, matching expected Haworth line direction for
  OH/H annotations.
- Add regression checks in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  side connectors stay vertical on representative pyranose and furanose cases.
- Improve hydroxyl label readability in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  by rendering side labels with oxygen nearest the bond endpoint: keep `OH` for
  right-anchored labels and use `HO` for left-anchored labels. Add regression
  checks in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  for `HO` on left-anchor slots and `OH` on right-anchor slots.
- Reduce bond/text collisions for crowded Haworth bottoms in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  flip BR/BL anchors to point outward from the ring center and apply a small
  anchor-based horizontal text nudge so label glyphs are placed at the bond end
  without the connector line crossing through letter strokes.
- Add a reusable visual-check generator script at
  [tools/haworth_visual_check_pdf.py](tools/haworth_visual_check_pdf.py)
  to render a fixed Haworth Phase 3 review sheet PDF from
  `sugar_code`/`haworth_spec`/`haworth_renderer` cases (including MKLRDM
  alpha/beta furanose and non-white `bg_color` panel), with optional
  `--show-carbon-numbers` for disambiguating substituent positions in manual QA.
- Implement Phase 4 Haworth selftest integration in
  [tools/selftest_sheet.py](tools/selftest_sheet.py): route
  `_build_alpha_d_glucopyranose_ops()` and
  `_build_beta_d_fructofuranose_ops()` through
  `sugar_code.parse()` -> `haworth_spec.generate()` ->
  `haworth_renderer.render()` (bond_length 30), and remove the older
  SMILES+`build_haworth`+explicit-H helper path so selftest sugar panels reflect
  the same renderer contract covered by Phase 2/3 tests.
- Add Phase 4 integration test coverage in
  [tests/test_selftest_haworth_builders.py](tests/test_selftest_haworth_builders.py)
  to assert both selftest sugar builders return non-empty ops with `PolygonOp`
  and `TextOp` content plus positive bounding boxes, matching the plan's
  direct in-process verification gate.
- Implement Phase 3 Haworth schematic renderer in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  with slot-stable carbon mapping (`MR/BR/BL/ML/TL`), ring-edge polygon
  thickness classes (front/wedge/back), oxygen mask + label ops, substituent
  connector/label placement, optional carbon numbers, and exocyclic mini-chain
  rendering for `CH(OH)CH2OH` plus generic `CHAIN<n>` labels.
- Add Phase 3 unit coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) (31 tests)
  for geometry placement, front-edge stability, subscript-visible-length
  handling, dual-wide label spacing multiplier, oxygen mask behavior, and
  exocyclic-chain direction/collinearity checks.
- Add Phase 3 smoke coverage in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py),
  generating SVG files from render ops across an A/MK sugar matrix (alpha/beta,
  pyranose/furanose), asserting non-empty `<svg` output with `PolygonOp` +
  `TextOp`, and including a non-white `bg_color` render path.
- Export `haworth_renderer` from
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py) for direct
  `oasa.haworth_renderer` access in integration points and tests.
- Extend exocyclic-chain labeling in
  [packages/oasa/oasa/haworth_spec.py](packages/oasa/oasa/haworth_spec.py):
  keep 2-carbon post-closure chains as `CH(OH)CH2OH` and emit `CHAIN<n>` for
  longer chains so Phase 3 renderer chain logic can scale past hexose cases.
- Implement Phase 2 Haworth spec generation in
  [packages/oasa/oasa/haworth_spec.py](packages/oasa/oasa/haworth_spec.py) with
  `HaworthSpec`, ring-closure matrix validation (`A`/`MK` x pyranose/furanose),
  alpha/beta substituent assignment, exocyclic-chain labeling, and Phase 0
  Haworth-eligibility gating for pathway carbon-state chemistry.
- Add Phase 2 unit/smoke coverage in
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py) and
  [tests/smoke/test_haworth_spec_smoke.py](tests/smoke/test_haworth_spec_smoke.py),
  including alpha/beta anomeric flips, ring-capacity errors, meso non-cyclizable
  checks, and pathway-profile rejection cases.
- Add a compact standard sanity-matrix test in
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py) for quick human-check
  expectations: ARLRDM pyranose alpha/beta C1 flip and MKLRDM furanose alpha/beta
  C2 OH/CH2OH swap.
- Export `sugar_code` and `haworth_spec` from
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py) for direct
  `oasa` module access in downstream integration/tests.
- Fix test/lint regressions after fixture cleanup:
  [tests/test_cdml_versioning.py](tests/test_cdml_versioning.py) now skips the
  legacy fixture check when `tests/fixtures/cdml/legacy_v0.11.cdml` is absent;
  [tools/check_translation.py](tools/check_translation.py) now uses consistent
  tab indentation and a `main()` guard to satisfy shebang/indentation checks;
  and [tools/selftest_sheet.py](tools/selftest_sheet.py) drops two pyflakes
  issues in `_add_explicit_h_to_haworth` (unused local and duplicate import).
- Simplify reference-output policy to Haworth-only artifacts: update
  [tests/test_reference_outputs.py](tests/test_reference_outputs.py),
  [tools/render_reference_outputs.py](tools/render_reference_outputs.py), and
  [docs/REFERENCE_OUTPUTS.md](docs/REFERENCE_OUTPUTS.md) to stop expecting or
  generating `wavy_glucose_reference.svg/png`.
- Update [tests/test_cdml_fixture_loads.py](tests/test_cdml_fixture_loads.py) to
  validate tracked fixtures in `tests/fixtures/cdml_roundtrip/` and treat the
  old `tests/fixtures/cdml/embedded_cdml.svg` check as optional (skip when the
  legacy fixture directory is intentionally absent).
- Add per-phase test matrix (deliverable/unit/integration/smoke/system) to
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md),
  defining smoke designs for phases 1-3, a Phase 4 unit/integration test around
  Haworth selftest builders, and a future SMILES round-trip smoke. Document test
  taxonomy angles (property-based, snapshot, fuzz, performance) for later use.
- Implement Phase 1 sugar-code parser in
  [packages/oasa/oasa/sugar_code.py](packages/oasa/oasa/sugar_code.py) with
  `ParsedSugarCode`, `parse()`, footnote/body split invariants, positional digit
  validation, side-qualified default hydrogen fill, unknown lowercase letter-code
  rejection, and parser-level key-family exclusivity checks (`n`, `nC`, `nL`, `nR`).
- Add Phase 1 parser tests in
  [tests/test_sugar_code.py](tests/test_sugar_code.py) (28 unit cases) and
  [tests/smoke/test_sugar_code_smoke.py](tests/smoke/test_sugar_code_smoke.py)
  using [tests/fixtures/smoke_sugar_codes.txt](tests/fixtures/smoke_sugar_codes.txt)
  for curated valid/invalid smoke coverage and `sugar_code_raw` round-trip checks.
- Export `atom_colors` and `dom_extensions` from
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py) so
  `tools/selftest_sheet.py` can access `oasa.atom_colors` and
  `oasa.dom_extensions` during test import, fixing collection-time
  `AttributeError` in [tests/test_fischer_explicit_h.py](tests/test_fischer_explicit_h.py).

## 2026-02-07
- Expand renderer test coverage in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with substituent geometry verification tests that check y-coordinates of
  up/down labels relative to ring vertices (not just label presence), including
  `test_render_alpha_glucose_c1_oh_below`, `test_render_beta_glucose_c1_oh_above`,
  `test_render_all_substituents_correct_side`, and L-series reversal test. Add
  a geometry gate to the Phase 0 acceptance gates.
- Add `_visible_text_length` unit tests and `sub_length` multiplier verification
  tests to
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md),
  documenting the character-count heuristic limitation as a Phase 0 non-goal.
- Add unknown letter code rejection rule and parser tests to
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  unrecognized lowercase letter codes raise `ValueError` with character and
  position, with `test_parse_unknown_letter_code_raises` and
  `test_parse_unknown_letter_code_uppercase_not_affected`.
- Document transparent background masking as a Phase 0 non-goal in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and add oxygen mask `bg_color` tests (`test_render_o_mask_uses_bg_color`,
  `test_render_o_mask_default_white`).
- Document collinear exocyclic chain rendering as a Phase 0 non-goal in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and add multi-carbon chain geometry tests including
  `test_render_exocyclic_3_collinear` for 7-carbon aldose furanose.
- Update Phase 0 exit checklist in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  to require unknown letter code rejection, geometry verification tests, and
  oxygen mask `bg_color` testing.
- Remove time estimates from menu refactor phases in
  [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md),
  [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md), and
  [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md).
- Add Phase 0 baseline performance measurement requirement to menu refactor
  plans in
  [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md),
  [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md), and
  [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md): measure
  actual `update_menu_after_selection_change()` timing before building
  PerformanceMonitor infrastructure; if current system is not slow, monitoring
  framework is premature.
- Add scope boundary notes to menu refactor plans: format handler migration to
  OASA is a separate architectural project that should have its own plan
  document, not be bundled with the menu refactor.

## 2026-02-06
- Tighten Attempt 2 Phase 0 parser/generator gating in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  standardize parser terminology to "backbone position index", require explicit
  per-index key-family exclusivity (`n` vs `nC`; no `n`/`nC` mixed with
  `nL`/`nR`), define `nC=<state>(<attachments...>)` as the only combined
  carbon-state+attachment form, and add explicit test/contract language that
  pathway-profile `nC` chemistry remains parseable but is rejected by
  `haworth_spec.generate()` in Phase 0 as non-Haworth-eligible.
- Finalize backbone-index terminology and side-qualified example validity in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  replace undefined example token `m` with canonical `CH3`, switch index wording
  from "carbon index" to "backbone index" for digit semantics, add explicit
  "not IUPAC numbering" clarification, change invalid example rationale to
  "digit must equal the backbone position it occupies", and state that plain
  `n=` is permitted only at non-chiral positions.
- Enforce global positional digit semantics in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  digits now always match carbon index positions (not placeholder IDs), add
  explicit invalid examples (`A1LRDM[1=methyl]`, `A2LRDM[2=CH3]`), require
  side-qualified keys at chiral stereocenters (`nL`/`nR`, or `nC` for carbon
  state), add parser-test requirements for these invalid cases, and update mixed
  example/test notation from `AdLRD1[1=sulfate]` to index-matched
  `AdLRD6[6=sulfate]`.
- Correct index/side footnote examples in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  replace stale `A1LRDM[1=methyl]` examples with `A2LRDM[2R=CH3]`, and align
  related parser example/test strings to the same index-based side-qualified form.
- Tighten digit/footnote rule consistency in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): change minimum-length
  wording to "3 total characters", explicitly separate digit semantics by mode
  (monosaccharide placeholder IDs vs pathway positional indices), make `n`/`nC`
  mutually exclusive with `nL`/`nR` per index, remove contradictory key-ordering
  language, and add a citrate-class note that side-qualified CAC attachment
  notation is bookkeeping rather than stereochemical chirality.
- Align pathway/CAC consistency in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  change isocitrate canonical code to `c23cc[2L=OH,2R=H,3C=COO-]` (carbon-state
  form), clarify that branching is supported in pathway mode but rejected in
  Haworth conversion mode, and add `P` (`phosphate-left`) to the Haworth plan's
  letter-code label mapping so it matches the spec.
- Tighten canonical carbon-state consistency in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): update pyruvate to
  `cK3[3C=CH3]`, update 1,3-bisphosphoglycerate to
  `1Rp[1C=C(=O)OPO3]`, update succinyl-CoA to
  `c234[2C=CH2,3C=CH2,4C=C(=O)SCoA]`, and add `C(=O)OPO3` to preferred
  canonical value tokens.
- Tighten pathway footnote disambiguation in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  require single plain/`nC` assignment per carbon index per bracket block,
  define `nC=<state>(<attachment...>)` parenthesis semantics, and set canonical
  PEP encoding to `c23[2C=C3(EPO3),3C=CH2]`.
- Tighten backbone-count wording in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  to state explicitly that prefix characters are part of the backbone position
  count (not separate metadata), preventing mis-parsing of forms like `MKLRDM`.
- Clarify mode semantics and terminal naming in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): rename `TERMINAL` to
  `C_TERMINAL_STATE`, separate validation into Monosaccharide mode vs Pathway
  mode for the penultimate config slot behavior, and note that the upstream YAML
  `dihydroxacetone` spelling is a known typo while spec text uses
  `dihydroxyacetone`.
- Simplify canonical PEP notation in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  from `c23[2=EPO3,2C=C3,3C=CH2]` to `c23[2C=CPO3,3C=CH2]` to avoid mixed
  duplicate C2 keys and keep carbon-state encoding compact.
- Replace provisional branch-word notation in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) with explicit substituent
  encoding guidance (for example `3R=COO-`) to keep pathway forms symbolic and
  avoid word-style branch labels.
- Align parser-plan wording in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with symbolic pathway notation (`c23[2=EPO3,2C=C3,3C=CH2]`) and backbone-length
  validation language.
- Convert pathway codebook notation in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  and parser-plan examples in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  from word labels to symbolic group/carbon-state tokens, add `nC` key support
  (for example `3C=CH2`), update PEP to `c23[2=EPO3,2C=C3,3C=CH2]`, and revise
  CAC canonical codes to use `nL`/`nR` where relevant and symbolic chemistry forms.
- Revise backbone-length semantics in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  and [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  define sugar-code length as backbone carbon count (not always total carbons),
  allow branched pathway compounds to exceed body length via `branch-to-<k>`, and
  update citrate/cis-aconitate/isocitrate canonical codes to 5-character bodies.
- Normalize pyruvate canonical token in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  from `cK3[3=methyl]` to `cK3[3=CH3]` to match preferred canonical substituent
  tokens.
- Refine side-qualified footnote behavior in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  single-sided `nL`/`nR` now implies missing side `H`, add equivalence examples
  (`A2M[2L=OH]` -> `ALM`, `A2M[2R=OH]` -> `ADM`), and define preferred canonical
  substituent tokens for parser normalization.
- Extend numeric footnote grammar in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with built-in side-qualified chiral keys (`nL`/`nR`), add ordering/validation
  rules, and document parser tests with example `A2M[2L=c,2R=m]`.
- Expand pathway-profile completeness in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  make digit placeholders location-matched (`digit == carbon index`) and ordered,
  update pyruvate to `cK3[3=CH3]`, add canonical glycolysis/CAC code tables
  (including citrate/isocitrate branch notation), and require this codebook before
  Phase 0 sign-off.
- Update [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) to keep pathway
  extensions single-character-per-carbon: add `p`/`P` stereochemical phosphate
  semantics, remove `C<n>=...` footnote keys in favor of numeric placeholders,
  add canonical digit-order guidance, and include examples such as `pKLRDp`,
  `pRLRDp`, `cK3[3=CH3]`, and `c23[2=phosphoenol,3=methylene]`.
- Refine `HaworthSpec` contract in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): remove `config` from
  `HaworthSpec`, document that `DEXTER`/`LAEVUS` are consumed during spec generation,
  and keep render-stage output as resolved up/down substituent labels only.
- Expand [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  for pathway-oriented coverage and meso clarity: add `MKp` as a valid meso triose
  derivative example, define pathway footnote extension rules, document
  validation constraints for those forms, and state that series orientation is
  resolved during spec generation before Haworth output.
- Update parser schema details in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) to split former `raw`
  language into `sugar_code` (body without footnotes) and `sugar_code_raw`
  (exact original input), with explicit split invariants and a parser test for
  footnote/body separation.
- Update parser schema language in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): internal `prefix` is now
  documented as normalized kind (`ALDO`/`KETO`/`3-KETO`) while literal prefix tokens
  remain in raw input text.
- Add an explicit uronic-acid note to [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  with terminal oxidation mapping examples:
  `ARLRDc` from `ARLRDM`, `ARLLDc` from `ARLLDM`, and `ALLRDc` from `ALLRDM`.
- Correct sugar-prefix and Haworth scope assumptions in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  treat canonical prefix set as `A`/`MK` only, remove `MRK`/`MLK` references,
  and define trioses (for example `ADM`, `MKM`) as valid sugar-code forms that are
  non-cyclizable in Haworth conversion (must raise ring-capacity `ValueError`).
- Clarify prefix handling in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  `MRK`/`MLK` are valid PREFIX tokens for parsing, while bare prefix-only strings
  (for example `MRK`, `MLK`) are invalid full sugar codes because config/terminal
  fields are missing.
- Superseding note: where older 2026-02-06 bullets mention `MRK`/`MLK` support,
  the final decision for this repo is to reject those prefixes and keep canonical
  parsing/conversion on `A` and `MK` only.
- Make minimum sugar length explicit in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  sugar code bodies must be at least 3 characters long, and one-/two-character
  codes are parser-invalid.
- Add explicit invalid-prefix rationale in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and parser requirements in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  `MRK`/`MLK` are rejected as non-canonical ambiguous/redundant aliases in this
  project, with a dedicated parser test case.
- Improve visual clarity in the PREFIX subsection of
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) by adding aligned star-fill
  examples (`A*****`, `MK****`) and an explicit note that `*` is visual-only and
  not part of literal sugar codes.
- Update [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  to resolve remaining implementation blockers before coding.
- Clarify parser vs renderer scope for sugar prefixes: parser remains spec-aligned
  (`A`, `MK`, `MRK`, `MLK`, meso handling), with Haworth conversion constraints
  defined explicitly by the ring-closure/capacity matrix.
- Remove provisional "v1" wording from
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  so the support matrix and NotImplemented constraints read as the intended final form.
- Resolve `MK` furanose mapping ambiguity by replacing fixed carbon-number template
  maps with role-based template maps plus dynamic carbon-to-slot mapping derived
  from prefix and ring type.
- Make alpha/beta orientation rules internally consistent for `MK` anomeric handling
  and align the fructose test expectations with those rules.
- Refine meso representation in the Haworth attempt-2 parser plan: replace
  `config=None` with explicit internal `config="MESO"` to avoid ambiguity with
  sugar-code `M` symbols while keeping meso forms (`MKM`, `MRKRM`) parseable.
- Refine Haworth attempt-2 internal config naming to use explicit words
  `DEXTER`/`LAEVUS`/`MESO` in parsed/spec dataclasses, while preserving sugar-code
  input tokens `D`/`L` and documenting token-to-internal normalization.
- Refine Haworth attempt-2 ring position naming by replacing numeric vertex-key
  label configs with semantic slot keys (`ML`, `TL`, `TO`, `MR`, `BR`, `BL`) and
  documenting dynamic carbon-to-slot mapping to keep position logic readable and
  stable across `A`/`MK` mappings.
- Finalize upfront scope in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  remove deferred "handled later" language, add `MRK`/`MLK` support to the
  conversion matrix and ring-closure rules, define meso series resolution via
  `series_override`/inference, and replace not-implemented tests with explicit
  support and ring-capacity validation tests.
- Update [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) to add a Haworth ring
  closure matrix covering `A`, `MK`, `MRK`, and `MLK`, require ring-capacity
  validation during conversion, and define meso series-orientation handling for
  Haworth mapping.
- Expand Phase 0 documentation in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) with explicit
  definition-of-done criteria, acceptance gates, deterministic/error contracts,
  and a clear scope boundary that keeps SMILES conversion work out of Phase 0.
- Create `docs/SUGAR_CODE_SPEC.md` defining sugar code notation for carbohydrate
  structures: prefix (A/MK) + stereocenters (R/L) + config (D/L) + terminal (M),
  with lowercase letter codes (d=deoxy, a=amino, n=N-acetyl, p=phosphate, f=fluoro,
  c=carboxyl) and numeric footnotes for rare modifications. Key invariant:
  `len(sugar_code) == num_carbons`.
- Rename `docs/HAWORTH_IMPLEMENTATION_PLAN.md` to
  `docs/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md` (via `git mv`) to preserve history
  and distinguish the SMILES-based approach (failed at stage 4 substituent rendering)
  from the new sugar-code-based approach.
- Create `docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md` with a schematic-only renderer
  architecture: sugar code parser -> Haworth spec generator -> render_ops output
  (TextOp + LineOp + PolygonOp), bypassing the molecular graph entirely.
  - Phase 1: sugar code parser with validation matrix (prefix + ring_type -> carbon
    count and ring closure)
  - Phase 2: Haworth spec generator with general ring-closure rules, ring vs exocyclic
    carbon classification, and substituent assignment algorithm
  - Phase 3: schematic renderer with filled polygon ring edges, explicit front-edge
    template metadata, per-ring-type label configs, bg_color parameter, and
    multi-carbon exocyclic chain rendering
  - Phase 4: selftest_sheet.py integration
  - Phase 5: verification
  - Phase 6: sugar code to SMILES conversion (Fischer-to-CIP mapping)
  - Phase 7: SMILES to sugar code (lookup table + best-effort structural inference)
- Address two rounds of review findings (P1a-P3c, R2-P1a-R2-new) documented in the
  plan's Review Response Log.

## 2026-02-05 (continued)
- Fix benzene rendering to use Kekule SMILES (`C1=CC=CC=C1`) for proper alternating
  single/double bond display.
- Fix `tools/selftest_sheet.py` import system to work when imported as a module by
  removing relative imports and always using absolute `oasa.*` imports.
- Fix `tests/test_fischer_explicit_h.py` to import selftest_sheet from tools/ directory.
- Improve Haworth projection clarity by labeling OH groups as "OH" text labels instead
  of showing separate O and H atoms, reducing connectivity ambiguity.
- Position ring H atoms opposite from substituents for clearer stereochemistry display.

## 2026-02-05
- Create missing CDML fixture files in `tests/fixtures/cdml/` (benzene, stereochem,
  haworth, cholesterol, legacy_v0.11, embedded_cdml) to fix test failures.
- Move `packages/oasa/oasa/selftest_sheet.py` to `tools/selftest_sheet.py` and update
  import paths to use git-based repo root detection.
- Fix `tools/generate_biomolecule_templates.py` to look for `biomolecule_smiles.yaml`
  in `docs/` directory instead of repo root.
- Fix `tools/check_translation.py` to use git-based repo root detection and locate
  locale directory correctly.
- Update all tools to use `git rev-parse --show-toplevel` for repo root detection
  per [docs/REPO_STYLE.md](docs/REPO_STYLE.md) guidance.
- Generate missing reference output files using `tools/render_reference_outputs.py`.
- Fix all failing tests: `test_cdml_fixture_loads.py`, `test_cdml_versioning.py`,
  and `test_reference_outputs.py` now pass.
- Replace alpha-D-glucopyranose CDML template with SMILES-based builder in
  `tools/selftest_sheet.py` to fix poor substituent placement in Haworth projection.
- Add beta-D-fructofuranose vignette to capabilities sheet (5-membered furanose ring).
- Add `beta-D-fructofuranose` SMILES to [docs/biomolecule_smiles.yaml](biomolecule_smiles.yaml).
- Add explicit hydrogen atoms to Haworth projections for both alpha-D-glucopyranose
  and beta-D-fructofuranose by adding H atoms to complete ring carbon valences.
- Fix benzene rendering to use aromatic bond type ('a') instead of alternating
  single/double bonds for proper display.
- Fix layout_row scaling bug when vignettes don't fit by iterating over normalized
  tuples instead of original vignettes.
- Note: Haworth projections are simplified 2D representations that show stereochemistry
  but do not accurately depict 3D geometry or all bond angles. The planar representation
  is a projection for clarity, not a reflection of the actual chair/envelope conformations.

## 2026-02-03
- Reorganize [refactor_progress.md](../refactor_progress.md) into master
  Not started, In progress, and Completed sections with updates for menu
  refactor docs, PubChem planning, and OASA data reorganization.
- Update [refactor_progress.md](../refactor_progress.md) to mark the Haworth
  plan as still in progress (Stage 4 OH placement), call out menu refactor
  documentation as completed, and align in-progress notes with TODO updates.
- Add [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md) to the
  refactor progress plan as a not-started automated installer tooling item.
- Update [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md) to add
  automated build tooling for macOS dmg, Windows installer, and Linux Flatpak.
- Add `packages/oasa/oasa_data/` and store isotopes as compact JSON in
  `packages/oasa/oasa_data/isotopes.json`, generated from the NIST ascii2 output
  source.
- Replace the inline isotopes dict in `packages/oasa/oasa/isotope_database.py`
  with a JSON loader pointing at the new data file and document the source URL.
- Add `tools/convert_isotope_data.py` to download NIST isotope data and
  regenerate JSON, plus packaging updates to ship the new JSON data via
  `packages/oasa/pyproject.toml` and `packages/oasa/MANIFEST.in`.
- Remove legacy OASA data sources `packages/oasa/oasa/names.db`,
  `packages/oasa/oasa/structures.txt.gz`, `packages/oasa/oasa/synonyms.txt.gz`,
  `packages/oasa/oasa/subsearch_data.txt`, and
  `packages/oasa/oasa/subsearch_rings.txt`.
- Remove unused OASA modules `packages/oasa/oasa/name_database.py`,
  `packages/oasa/oasa/structure_database.py`, and
  `packages/oasa/oasa/subsearch.py`.
- Update `packages/oasa/oasa/__init__.py` and OASA docs to drop removed module
  references and keep the OASA import path working.
- Harden `tools/convert_isotope_data.py` URL handling with scheme/host checks
  and a Bandit-annotated urlopen call.
- Add `docs/PUBCHEM_API_PLAN.md` with the planned PubChem lookup integration
  scope and rollout steps.
- Add the PubChem API plan to [docs/TODO_REPO.md](docs/TODO_REPO.md).

## 2026-02-02
- Add [tests/test_bkchem_gui_benzene.py](../tests/test_bkchem_gui_benzene.py)
  to build a benzene ring (hexagon with alternating double bonds) and include
  it in [tests/run_smoke.sh](../tests/run_smoke.sh).
- Replace deprecated inspect.getargspec with getfullargspec in
  [packages/bkchem/bkchem/undo.py](../packages/bkchem/bkchem/undo.py) to
  restore undo/redo under Python 3.12.
- Deiconify the GUI and add event-loop flush delays in
  [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py) so
  in-process event simulation works reliably on real Tk windows.
- Make [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py)
  drag simulation more robust with multi-step motions and a click fallback.
- Expand [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py)
  with draw-drag, chain extension, mode switching, and undo/redo event coverage,
  and add it to [tests/run_smoke.sh](../tests/run_smoke.sh).
- Set PYTHONPATH in [tests/run_smoke.sh](../tests/run_smoke.sh) to prefer local
  BKChem and OASA packages, matching the GUI launch script.
- Add [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py) to
  simulate in-process GUI events (draw click, edit selection, delete key) for
  BKChem smoke coverage.
- Add [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md) as executive
  summary tying together all menu refactor documentation: 6 core decisions (eliminate
  exec-based plugins, adopt YAML + Dataclass Hybrid menus, complete platform abstraction,
  backend/frontend separation with OASA as chemistry backend, modular built-in tools
  replacing addons, unified renderer architecture for GUI and export), performance
  requirements (< 100ms menu build, < 3ms avg / 5ms p95 state updates), 6-phase
  implementation plan (14 weeks total: format handlers to OASA, menu system core,
  menu migration, tools system, renderer unification, cleanup), risk mitigation
  strategies, success metrics (500 lines removed, 80% test coverage, zero exec calls),
  stakeholder communication guidance, Q&A section covering user workflows, extensibility,
  sandboxing rationale, performance, rollback strategy, translations, OASA standalone
  status. Summary includes comparison tables for plugin reclassification, backend/frontend
  boundaries, architecture benefits, and approval checklist.
- Fix non-ASCII characters in [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md)
  replacing degree symbols with "deg" and "degrees" text equivalents to ensure strict
  ASCII compliance for all documentation.
- Verify ASCII compliance for all menu refactor documentation
  (MENU_REFACTOR_ANALYSIS.md, BKCHEM_GUI_MENU_REFACTOR.md, MODULAR_MENU_ARCHITECTURE.md,
  MENU_REFACTOR_SUMMARY.md) - all pass grep checks with no non-ASCII characters.
- Add platform abstraction layer to [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  with MenuBackend interface (create_menubar, add_menu, add_menu_item, add_separator,
  add_cascade, set_item_state) making YAML structure and MenuBuilder 100%
  platform-agnostic, PmwMenuBackend with automatic platform detection, platform-specific
  adapters (PmwMacOSAdapter using MainMenuBar, PmwLinuxAdapter using standard MenuBar,
  PmwWindowsAdapter), opaque MenuHandle and MenuItemHandle eliminating all
  platform-specific code from menu builder, enabling easy port to Qt/Gtk/Cocoa by
  swapping backend implementation.
- Add performance monitoring section to [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  with PerformanceMonitor class (measure context manager, configurable warn threshold,
  stats tracking), instrumented MenuBuilder measuring build_menus and update_menu_states
  operations, performance acceptance criteria (menu build < 100ms one-time, state
  update < 3ms avg and < 5ms p95 for frequent operations), baseline benchmarking
  script comparing current vs new system, optimization strategy (state indexing for
  5-10x speedup, predicate caching for 2-3x speedup, after_idle batching), continuous
  monitoring in debug builds with automatic warning on slow operations.
- Add [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md)
  defining architecture for modular built-in chemistry tools (not plugins):
  Tool base class with metadata (id, name_key, category, requires_selection),
  ToolRegistry for discovery, tool categories (analysis, conversion, visual,
  fetchers, editing), automatic menu population via tool_category in YAML,
  migration plan for 8 current addons (angle_between_bonds, text_to_group,
  red_aromates, fetch_from_webbook, fragment_search, mass_scissors, animate_undo)
  converting XML + exec() scripts to built-in Tool subclasses, chemistry logic
  extraction to OASA backend (geometry.measure_bond_angle, aromaticity detection,
  fragment search, NIST fetchers), Python extension mechanism for user
  extensibility (safer than exec-based plugins using standard importlib), removes
  ~500 lines of plugin infrastructure while maintaining modularity and
  eliminating security risks from arbitrary code execution.
- Add [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md) with
  comprehensive analysis of plugin architecture, menu system complexity, and
  migration challenges: assess whether import/export format handlers should remain
  as plugins (recommendation: move core formats like CML/CDXML/molfile to format
  registry, keep renderer backends as optional plugins, sandbox script plugins,
  remove unused mode plugins), analyze menu hooks (plugin injection, recent files,
  selection-driven enablement) with simplification strategies (declarative plugin
  slots, observable managers, indexed state updates, restricted plugin locations
  reducing complexity by ~70%), document 7 major migration challenges with detailed
  solutions (format plugin compatibility via parallel registry, translation key
  stability via preserved label_key values, plugin backward compatibility via
  LegacyMenuShim, macOS platform handling via PlatformMenuAdapter, performance
  optimization via state indexing reducing updates from O(n^2) to O(n), toolbar
  unification deferral, testing without GUI via mock Pmw), provide 6-phase
  prioritized action plan with time estimates (10 weeks total) and success criteria
  per phase.
- Add "GPL v2 Code Coverage Assessment Plan" section to
  [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) with comprehensive
  methodology for assessing GPL v2 code coverage across repository using git log,
  classification system (pure GPL-2.0, pure LGPL-3.0-or-later, mixed), git history
  analysis commands, GPL v2 percentage calculation methods for mixed files (commit
  count, line changes, time-weighted), summary report format, SPDX header compliance
  tracking, implementation script structure, usage examples, and ongoing maintenance
  strategy. Plan assumes all edits prior to 2025 are GPL-2.0 and provides baseline
  metrics to track migration progress.
- Split rendering into geometry producer vs painters: add
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  with `BondRenderContext` and `build_bond_ops`, update svg/cairo backends,
  selftest, and render ops snapshot tests to use it.
- Update BKChem `bond._draw_q1` to use `render_geometry.haworth_front_edge_geometry`
  after the geometry split.
- Move SVG vertex rendering to ops: add `build_vertex_ops` helpers in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py),
  switch [packages/oasa/oasa/svg_out.py](packages/oasa/oasa/svg_out.py) and
  selftest molecule ops to use them.
- Add [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  documenting current menu construction and a refactor plan.
- Comprehensively rewrite [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  to recommend YAML + Dataclass Hybrid approach combining YAML menu structure
  (human-editable hierarchy) with Python dataclass action registry (type-safe handlers).
  Add architecture overview diagram, complete implementation examples for YAML menus,
  Python actions with lazy translation, menu builder combining YAML + actions, plugin API,
  toolbar unification, and comprehensive test suite. Replace implementation phases with
  detailed 7-phase plan (0: Analysis, 1: Action registry Python-only, 2: YAML structure
  for File menu, 3: Incremental migration menu-by-menu, 4: Plugin API integration,
  5: Toolbar unification, 6: Cleanup and testing, 7: Portability demo) with per-phase
  deliverables, success criteria, code examples, and specific task checklists. Document
  portability to Qt/Swift/web frameworks, i18n compatibility with .po files, comparison
  of approaches (human readability, ease of add/rearrange, difficulty, verbosity), and
  provide concrete first step with minimal working action registry and unit tests.
- Add [docs/BKCHEM_GUI_CODE_REVIEW.md](docs/BKCHEM_GUI_CODE_REVIEW.md) with
  a GUI code quality review and prioritized improvement areas.
- Expand [docs/BKCHEM_GUI_CODE_REVIEW.md](docs/BKCHEM_GUI_CODE_REVIEW.md) with
  additional architectural findings covering menu system architecture (tuple schema,
  enablement logic), mode system architecture (registration, plugin modes, submodes,
  toolbar creation), key sequence handling (CAMS modifiers, sequence building, focus
  fragility), context menu architecture (dynamic building, configurable properties),
  canvas event binding (platform-specific issues), singleton initialization (template
  managers), plugin menu integration, and recent files menu. Add expanded next steps
  with immediate/medium/long-term priorities including script execution boundaries,
  platform input normalization, key modifier recovery, mode system cleanup, unit test
  harness, event binding tests, and documentation requirements.
- Add [docs/BACKEND_CODE_REVIEW.md](docs/BACKEND_CODE_REVIEW.md) documenting
  backend rendering quality notes, risks, and follow-up recommendations.
- Rework `packages/oasa/oasa/selftest_sheet.py` to build a backend-agnostic
  ops list (including molecule vignettes via `_build_molecule_ops`) and render
  through a single SVG/Cairo sink, removing backend-specific composition and
  embedded SVG/PNG handling while keeping titles and grid labels as ops.
- Update `tests/test_fischer_explicit_h.py` to assert Fischer explicit hydrogen
  labels via `render_ops.TextOp` output instead of SVG DOM inspection.
- Update [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md) with "Vignette
  Contract (Hard Requirements)" section defining bbox invariant (finite, non-zero
  width/height required, raises ValueError on violation) and projection-specific
  invariants (Haworth must have in-ring O vertex and semantic front edge, raises
  AssertionError on violation). Selftest now treats broken rendering as a hard
  failure that aborts generation, preventing misleading output.
- Add defensive bbox validation in `packages/oasa/oasa/selftest_sheet.py`:
  `ops_bbox()` now raises ValueError on empty ops, NaN coordinates, zero-sized
  bbox, or invalid bbox; `normalize_to_height()` raises ValueError on empty ops,
  NaN/invalid target height, or NaN/invalid current height. Selftest now fails
  fast on rendering errors instead of silently producing broken output.
- Add `source_me.sh` at repo root for testing and development (not installation):
  configures PYTHONPATH for BKChem/OASA packages, sets Python 3.12 interpreter,
  and enables clean Python execution (no .pyc files, unbuffered output). Use with
  `source source_me.sh` before running tests or development scripts.
- Complete canonical Haworth integration in `packages/oasa/oasa/selftest_sheet.py`:
  add `_build_haworth_svg()` using canonical renderer path (svg_out.mol_to_svg,
  same as test_haworth_layout.py), add `_assert_haworth_invariants()` to verify
  exactly one in-ring oxygen vertex and at least one semantically tagged front
  bond before rendering, rewrite `_build_haworth_ops()` to use canonical pipeline
  (molecule from SMILES, haworth.build_haworth, invariant checks, svg_out rendering)
  and extract ops for layout system. Haworth now renders via projection grammar
  (semantic bond tags + layout) with atoms+bonds together from svg_out, not
  hand-assembled primitives. Oxygen appears because it's a vertex, not added text.
- Remove the `use_oasa_cdml_writer` flag and keep OASA CDML serialization as the
  only BKChem path, updating the serializer smoke test in
  `tests/test_bkchem_cdml_writer_flag.py`.
- Add `packages/oasa/oasa_cli.py` with a Haworth SMILES CLI for SVG/PNG output
  and a CLI smoke test in `tests/test_oasa_haworth_cli.py`.
- Update CLI references to the `packages/oasa/oasa_cli.py` path across plans
  and usage docs.
- Render the Haworth selftest vignette from the canonical molecule pipeline
  by embedding svg_out output in `packages/oasa/oasa/selftest_sheet.py`, and
  add mixed SVG/ops layout helpers to preserve semantic rendering.
- Resolve repo root in CDML/CLI tests via shared helpers in
  [tests/conftest.py](tests/conftest.py) (no git commands), and register the
  `--save` pytest option for smoke output preservation.
- Add [tests/test_haworth_cairo_layout.py](tests/test_haworth_cairo_layout.py)
  as a pre-merge baseline copy of Haworth layout tests, and update Haworth tests
  to use [tests/conftest.py](tests/conftest.py) path helpers.
- Document the Haworth CLI in [docs/USAGE.md](docs/USAGE.md) and
  [packages/oasa/docs/USAGE.md](packages/oasa/docs/USAGE.md).
- Update [refactor_progress.md](refactor_progress.md) to mark Haworth CLI and
  CDML/Bond alignment Phase 5 completion.
- Refresh [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md),
  [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md),
  [docs/TODO_CODE.md](docs/TODO_CODE.md),
  [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md), and
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  to reflect current semantics and registry guidance.
- Replace OASA-generated atom nodes with BKChem atom/group/text/query CDML
  elements in `packages/bkchem/bkchem/molecule.py` to preserve vertex-specific
  serialization details.
- Extend `tests/test_bkchem_cdml_writer_flag.py` dummy helpers with real-coordinate
  passthrough and unique IDs for atom replacement coverage.
- Add `tests/test_bkchem_cdml_vertex_tags.py` to ensure group/text/query tags
  are preserved in CDML output.
- Add `packages/oasa/oasa/render_out.py` with a merged mol-to-output entry point
  for SVG and Cairo-backed formats, and route the Haworth CLI through it.
- Replace test-local repo root and fixtures path lookups with
  [tests/conftest.py](tests/conftest.py) helpers, removing `os.path.dirname(__file__)`
  usage across tests and updates to helper scripts under `tests/`.
- Render Haworth smoke outputs via `render_out.mol_to_output` in the Haworth
  layout tests and use the merged output path for Haworth SVG embedding in
  `packages/oasa/oasa/selftest_sheet.py`.
- Align selftest molecule vignettes with the SPEC by rendering benzene, Fischer,
  Haworth, and cholesterol via the molecule renderer (no manual ops/labels),
  and composite vignette PNGs in the Cairo backend instead of ops.
- Use defusedxml parsing for embedded SVG fragments in
  `packages/oasa/oasa/selftest_sheet.py` to satisfy bandit XML safety checks.
- Add the selftest motto ("Do less, but show more. Let the backend handle the
  complexities.") to [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md)
  and [docs/RENDERER_CAPABILITIES_SHEET_PLAN.md](docs/RENDERER_CAPABILITIES_SHEET_PLAN.md).
- Resolve repo root in [tests/run_smoke.sh](tests/run_smoke.sh) from the script
  directory instead of running git.
- Fix ftext chunk splitting to avoid duplicated chunk objects and orphaned
  canvas text items, preventing atom labels from moving twice and leaving
  duplicates during drag operations.
- Ensure SVG text labels do not inherit stroke styling by explicitly setting
  `stroke="none"` on text ops and legacy SVG text drawing, fixing Haworth
  oxygen labels appearing black in SVG viewers while keeping fill-based coloring.
- Keep atom label text weight normal so SVG and Cairo/PNG outputs match after
  switching to fill-based text coloring.
- Increase Cairo text weight by default (font_weight=bold) so PNG/PDF output
  better matches SVG appearance; allow overriding via cairo_out options.
- Render atom labels in bold in SVG to match Cairo/PNG output weight.
- Use round linecaps for color-split bond segments to avoid visible gaps at
  Haworth ring junctions when gradients are used.
- Update Fischer rendering to show explicit H by default, keep OH/H bonds
  horizontal, place the aldehyde group at 120 degrees (O= and H), and label
  hydroxyl substituents as OH with CH2OH at the terminus using label properties.
- Adjust Fischer labels to use HO on the left side, keep the aldehyde H angled,
  and remove the terminal methyl from the cholesterol template so it renders as
  a terminal OH.
- Align left-side HO labels with the bond by using a label-specific anchor so
  the O sits at the attachment point.
- Increase default PNG resolution to 600 DPI by mapping Cairo PNG scaling to DPI
  (with explicit `dpi` override support) and add a `--dpi` option to the
  selftest sheet PNG output path.
- Add default PNG target width of 1500 px (overrideable via `target_width_px`)
  to produce larger postcard-like raster outputs when using Cairo.
- Add review notes to GUI docs clarifying menu tuple variants, key modifier
  handling, mode switching behavior, and translation asset locations.
- Add basic subscript/superscript markup support to render ops text output for
  SVG/Cairo, and label Fischer CH2OH as CH<sub>2</sub>OH to render as a subscript.
- Scale molecule label font size from a bond-length ratio in the selftest
  sheet renderer to keep text size consistent across templates, and render
  cholesterol with explicit OH on the terminal oxygen.
- Add alpha-D-glucopyranose CDML vignette to the selftest sheet and place it
  to the right of cholesterol in the second row.
- Render the alpha-D-glucopyranose vignette in Haworth form by applying
  `haworth.build_haworth` with D-series alpha substituent orientation mapping.
- Derive alpha-D-glucopyranose Haworth substituent orientations from ring
  topology (identify C1/C5 via the exocyclic carbon) and apply explicit
  up/down placement for all ring substituents.
- Replace non-ASCII box drawing and checkmark glyphs in
  [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md) with
  ASCII equivalents to satisfy compliance checks.
- Add review comments to [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  covering translation extraction, menu label stability, Pmw component lookup,
  and plugin insertion compatibility.
- Update [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  MenuBuilder implementation to address review comments: move top-level menu
  labels and cascade labels to Python action registry (not YAML) for gettext
  extraction, store menu component and item index (not translated labels) for
  state updates to avoid label collision fragility, use app._get_menu_component()
  instead of direct pmw_menubar.component() to preserve macOS compatibility,
  add CascadeDefinition dataclass with translation keys, update usage examples
  to show menu-level actions and cascade definitions, add backward compatibility
  shim (add_to_menu_by_label) for legacy plugins using translated label lookup
  with 4-phase migration path from label-based to menu-ID-based plugin API.
- Add review comments to [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md)
  clarifying GPL-2.0-only compatibility concerns, provenance vs percentage
  reporting, and limitations of date-based heuristics.
- Clarify in [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) that mixed
  GPLv2/new files must remain GPL-2.0 until all GPLv2 code is removed and the
  file is fully rewritten.
- Clarify that GPLv2 percentage metrics are reporting-only and intended to
  scope legacy content and support author outreach, not relicensing decisions.
- Add preferred one-command usage examples for the GPL coverage assessment
  script (summary, full report, CSV) to [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md).
- Add [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) for
  reporting-only GPL/LGPL coverage metrics and update
  [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) to reference the
  tools path.
- Fix date handling in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  by comparing date values to avoid timezone-aware vs naive datetime errors.
- Add an ASCII progress bar to [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  to show scan status while building coverage records.
- Fix GPL/LGPL classification in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  by comparing date values (not strings) and show normalized dates in per-file output.
- Prefer SPDX headers and legacy license text detection when classifying files
  in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py), and record the
  classification source in CSV output.
- Clamp GPL time-percentage calculations in
  [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) when the cutoff
  date predates the first commit to avoid negative values.
- Update [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) to require
  line-based (git blame) classification for GPL/LGPL reporting, with line-age
  percentage as the primary metric and commit/change metrics as secondary.
- Update [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) to
  classify files from git blame line dates, clean up per-file reporting, and
  report line-add metrics when requested.
- Replace non-ASCII checkmark glyphs in
  [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md) with
  ASCII equivalents for compliance.
- Add per-file spot-check samples (git blame lines around the cutoff) to
  [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) output when
  using `--file`.
- Make `tools/assess_gpl_coverage.py --file` process only the requested file
  without scanning the full repo or emitting a progress bar.
- Handle boundary commits in `tools/assess_gpl_coverage.py` spot-check output
  by accepting blame hashes prefixed with '^'.
- Clarify GPLv2 vs LGPLv3 labeling in
  [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) output for
  summaries and per-file reports.
- Silence SPDX "missing" noise in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  output, and make SPDX mismatch reporting opt-in via `--show-spdx`.
- Fix spot-check blame parsing so committer-time lines are processed, and label
  commit counts as GPLv2 vs LGPLv3 in per-file output.
- Center single-letter atom labels by default and scale label background boxes
  to font size to keep Haworth ring hetero atoms aligned after font scaling.

## 2026-02-01
- Update [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md) to establish
  molecule-level rendering as the architectural foundation: add canonical
  rendering rule requiring molecule graphs (not hand-assembled ops), define
  Haworth canonical invariants (in-ring O vertex, semantic front edge marking),
  add anti-patterns section prohibiting manual atom labels, reframe implementation
  guidelines to emphasize full renderer pipeline, and prioritize projection
  canonicalization over adding new features.
- Fix missing atom labels in Cairo/PNG output by adding `_render_cairo_atom_labels()`
  to `packages/oasa/oasa/selftest_sheet.py` and capturing label data for both
  row 1 and row 2 vignettes in `_add_cairo_labels()`. Previously, Cairo backend
  discarded atom labels returned by molecule builders, causing oxygen atoms to
  be invisible in PNG output while appearing correctly in SVG.
- Make Haworth ring ordering oxygen-anchored in `packages/oasa/oasa/haworth.py`
  by starting traversal at the oxygen atom when exactly one O is present in the
  ring, ensuring canonical layout independent of SMILES atom order.
- Add oxygen placement tests for non-first oxygen positions in
  `tests/test_haworth_layout.py` to verify canonical ordering stability.
- Update Haworth SMILES scaffolds in `packages/oasa/oasa/selftest_sheet.py` to
  oxygen-first format (O1CCCCC1 for pyranose, O1CCCC1 for furanose) for
  consistent canonical rendering.
- Replace hatch terminology with hashed in docs and Python code, remove legacy
  hatch-side handling, and update hashed labels in BKChem UI mode lists.
- Add explicit hydrogen rendering for Fischer projections in
  `packages/oasa/oasa/selftest_sheet.py` with `show_explicit_hydrogens` parameter
  that adds H labels for implicit substituents on stereocenters, matching OH label
  styling (font-size 9, proper text-anchor).
- Fix the Fischer explicit hydrogen test import path, remove the shebang, and
  avoid returning values from pytest tests in `tests/test_fischer_explicit_h.py`.
- Route BKChem conversion helpers through the OASA codec registry in
  `packages/bkchem/bkchem/oasa_bridge.py`.
- Document codec-registry-backed plugin guidance in
  [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md).
- Add BKChem codec-registry bridge tests in
  `tests/test_codec_registry_bkchem_bridge.py`.
- Flip the default `use_oasa_cdml_writer` flag to True in
  `packages/bkchem/bkchem/config.py`.
- Mark CDML architecture plan phases 1 and 2 complete in
  [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md).
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
  to use SMILES -> layout -> render pipeline instead of hand-placed coordinates,
  testing connectivity-driven molecule rendering.
- Add orange color row to bond grid in `packages/oasa/oasa/selftest_sheet.py`
  (8 types x 6 colors = 48 cells) and adjust vignette positions to accommodate
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
  including a draft `packages/oasa/oasa_cli.py haworth` command and smoke
  testing notes.
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
