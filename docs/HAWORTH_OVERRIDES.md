# Haworth overrides inventory

Last updated: 2026-02-11

Scope:
- Runtime/rendering overrides in `packages/oasa/oasa/*`.
- Haworth-specific tooling overrides in `tools/*` that influence validation and triage.

Classification rule:
- `Required Contract`: keep. Limited to chemistry semantics, ring template topology, and front-edge primitive semantics.
- `Hack Debt`: refactor toward BKChem-standard shared behavior.
- `Validate-only`: tooling/test enforcement only, not runtime policy ownership.

## Required contract (runtime/spec)

| ID | Location | Why required |
| --- | --- | --- |
| H-001 | `packages/oasa/oasa/haworth/__init__.py:27` | Fixed Haworth ring templates are the topology contract for pyranose/furanose silhouettes. |
| H-002 | `packages/oasa/oasa/haworth/__init__.py:46` | Forced orientation keeps substituent up/down chemistry semantics stable. |
| H-003 | `packages/oasa/oasa/haworth/__init__.py:55` | `front_style="haworth"` activates Haworth front-face semantics by default. |
| H-004 | `packages/oasa/oasa/haworth/__init__.py:291` | `q/w/w` front-edge tagging encodes Haworth front-face primitive semantics. |
| H-005 | `packages/oasa/oasa/haworth/__init__.py:311` | `haworth_position` is the shared marker for front/back front-face behavior. |
| H-006 | `packages/oasa/oasa/haworth/__init__.py:345` | Wedge orientation normalization preserves correct front-face directionality. |
| H-007 | `packages/oasa/oasa/bond.py:48` | Bond type `q` is the explicit Haworth front-edge primitive type. |
| H-008 | `packages/oasa/oasa/render_geometry.py:333` | Shared Haworth front-edge geometry primitive implementation. |
| H-009 | `packages/oasa/oasa/render_geometry.py:669` | Front wedge overlap extension is part of front-edge primitive seam contract. |
| H-010 | `packages/oasa/oasa/render_geometry.py:684` | `q` dispatch is required for front-edge primitive rendering. |
| H-011 | `packages/oasa/oasa/haworth/spec.py:16` | Ring-rule chemistry semantics (ALDO/KETO closure and anomeric mapping). |
| H-012 | `packages/oasa/oasa/haworth/spec.py:178` | Eligibility guard prevents unsupported chemistry from entering Haworth runtime. |
| H-013 | `packages/oasa/oasa/haworth/spec.py:203` | Anomeric alpha/beta x D/L direction mapping is core chemistry semantics. |
| H-014 | `packages/oasa/oasa/haworth/spec.py:281` | Two-carbon tail face derived from closure stereochemistry is chemistry semantics. |
| H-015 | `packages/oasa/oasa/haworth/renderer_config.py:31` | Stable ring slot topology and front-edge indices are topology contract. |
| H-016 | `packages/oasa/oasa/haworth/renderer.py:450` | Front/back ring-edge thickness ratios are part of Haworth front-face semantics. |
| H-017 | `packages/oasa/oasa/haworth/renderer.py:490` | Oxygen-adjacent edge clipping is required to keep ring primitive legal at oxygen glyph. |
| H-020 | `packages/oasa/oasa/haworth/renderer.py:642` | Tail defer-order is needed for deterministic two-carbon branch legality resolution. |
| H-027 | `packages/oasa/oasa/haworth/renderer.py:1623` | Branch connector style dispatch (`solid`/`hashed`) remains required until shared policy parity exists. |
| H-028 | `packages/oasa/oasa/haworth/renderer.py:1706` | Oxygen-adjacent color split is part of Haworth ring semantic styling. |
| H-029 | `packages/oasa/oasa/haworth/renderer.py:1752` | Rounded side-edge wedge path is part of front/side ring primitive semantics. |
| H-030 | `packages/oasa/oasa/haworth/renderer.py:261` | Strict runtime legality gate for generated Haworth ops. |
| H-031 | `packages/oasa/oasa/haworth/renderer_text.py:83` | OH/HO side ordering supports attach-side chemistry readability semantics. |
| H-032 | `packages/oasa/oasa/haworth/renderer_text.py:93` | CH2OH/HOH2C text-order aliasing preserves attach-side readability semantics. |
| H-033 | `packages/oasa/oasa/haworth/renderer_text.py:114` | Text offset model remains required until shared text attach policy fully subsumes Haworth labels. |
| H-034 | `packages/oasa/oasa/haworth/renderer_layout.py:61` | Deterministic hydroxyl layout pass remains required until shared layout policy has equivalent guarantees. |

## Hack debt (runtime; refactor to BKChem standard)

| ID | Location | Current override | BKChem-standard convergence target | Replacement mechanism | Removal gate test | Target deletion milestone |
| --- | --- | --- | --- | --- | --- | --- |
| H-018 | `packages/oasa/oasa/haworth/renderer.py:617` | Interior pyranose OH anchor forcing on `BL/BR`. | Anchor choice comes from shared attach/text policy, not ring-slot special-case branch. | Extend shared label attach policy in `render_geometry.py` to support interior-lane intent via generic constraints. | `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_phase4_known_failures.py` and `tests/test_phase4_non_haworth_sentinels.py`. | Phase 4b runtime policy consolidation |
| H-019 | `packages/oasa/oasa/haworth/renderer.py:626` | Furanose top clearance nudge and right-top OH ad-hoc offset. | Top-label clearance from shared collision/layout policy, no slot-label branch. | Move clearance to shared layout penalties in `renderer_layout.py` (or shared layout module) keyed by geometry, not slot names. | `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --fail-on-miss` plus known-failure smoke test. | Phase 4b label layout convergence |
| H-021 | `packages/oasa/oasa/haworth/renderer.py:835` | `force_vertical_chain` per-ring/slot conditional. | Straight connectors derived from generic direction/constraint policy for any vertical case. | Promote vertical-lock detection into shared endpoint resolver constraints (`AttachConstraints`) without Haworth slot checks. | `tests/test_phase4_non_haworth_sentinels.py`, plus matrix run with `tools/archive_matrix_summary.py -r`. | Phase 4b connector-policy unification |
| H-022 | `packages/oasa/oasa/haworth/renderer.py:876` | Haworth-local override from `auto` to `line` + `vertical_lock` for select labels. | `direction_policy="auto"` resolves canonical straightness from shared policy; no local coercion branches. | Add canonical-angle snapping/straightness behavior to shared `render_geometry.py` endpoint resolution path. | `tests/test_haworth_renderer.py`, `tests/smoke/test_haworth_phase4_known_failures.py`, `tests/test_phase4_non_haworth_sentinels.py`. | Phase 4b shared direction policy rollout |
| H-023 | `packages/oasa/oasa/haworth/renderer.py:1001` | Local CH3/H3C fallback ladder and font scaling. | Collision resolution handled by shared text layout engine; no methyl-specific fallback ladder. | Replace with generic conflict resolver in shared layout/text policy, driven by attach targets and overlap cost only. | `tests/smoke/test_haworth_phase4_known_failures.py` (Rhamnose CH3 checks) + strict overlap gate. | Phase 4c text-layout generalization |
| H-024 | `packages/oasa/oasa/haworth/renderer.py:1095` | Chain2 offset candidate fan-out solver local to Haworth. | Multi-segment chain placement uses generic branch layout policy with shared scoring model. | Extract chain2 candidate generation/scoring into shared branch layout helper; remove Haworth-local solver. | `tools/measure_glyph_bond_alignment.py --fail-on-miss` and `tests/test_measure_glyph_bond_alignment.py`. | Phase 4c branch layout extraction |
| H-025 | `packages/oasa/oasa/haworth/renderer.py:1407` | Hard-coded min standoff (`up=1.75`, `down=1.35`). | Standoff derived from shared glyph clearance and line-width policy. | Replace constants with geometry-derived minimum using shared glyph primitive distances. | `tests/smoke/test_haworth_phase4_known_failures.py` + `tools/archive_matrix_summary.py -r`. | Phase 4c spacing policy cleanup |
| H-026 | `packages/oasa/oasa/haworth/renderer.py:1571` | Hard-coded two-carbon profile vectors/parity branches. | Canonical angle and branch-side selection from shared lattice/direction policy and stereochemistry metadata. | Move angle/branch selection into shared policy tables keyed by semantic direction class, not slot-side heuristics. | `tests/test_haworth_renderer.py` targeted angle tests + full known-failure smoke test. | Phase 4c two-carbon tail policy normalization |
| H-035 | `packages/oasa/oasa/haworth/renderer_layout.py:240` | Ring-type-specific internal OH pair heuristic rules. | Pair overlap resolution from generic internal-label lane optimizer without ring-type branches. | Replace ring-specific branches with geometry-only pair scoring in shared layout policy. | `tests/smoke/test_haworth_phase4_known_failures.py` and independent measurement gate. | Phase 4c internal-label optimizer unification |

## Validate-only (tooling/test enforcement; not runtime policy)

| ID | Location | Enforcement role | Runtime policy owner |
| --- | --- | --- | --- |
| T-001 | `tools/archive_matrix_summary.py:178` | Regenerates previews from runtime path for matrix-level regression visibility. | `packages/oasa/oasa/haworth/renderer.py` + `packages/oasa/oasa/render_geometry.py` |
| T-002 | `tools/archive_matrix_summary.py:230` | Applies strict overlap validation during preview regeneration. | `packages/oasa/oasa/haworth/renderer.py` (`strict_validate_ops`) |
| T-003 | `tools/measure_glyph_bond_alignment.py:94` | Independent measurement option to exclude Haworth base ring from checks. | Runtime remains unchanged; measurement-only lens. |
| T-004 | `tools/measure_glyph_bond_alignment.py:511` | Canonicalizes label aliases (`HOH2C` family) for robust measurement grouping. | Runtime text emission remains in renderer/text modules. |
| T-005 | `tools/measure_glyph_bond_alignment.py:22` | Independent canonical lattice-angle compliance diagnostics (30-degree family). | Runtime angle generation policy in shared geometry/renderer code. |
| T-006 | `tools/measure_glyph_bond_alignment.py:1775` | Detects Haworth base ring heuristically for reporting/exclusion. | Runtime ring generation unchanged. |

## Senior coder handoff

- Reclassify all Haworth runtime rows as either `Required Contract` or `Hack Debt` only; do not leave ambiguous categories.
- For each `Hack Debt` row, converge toward shared BKChem runtime behavior through `render_geometry.py` or shared text/layout policy modules.
- Do not add new per-label, per-sugar, text-token, or op-id branches.
- Keep `T-*` rows strictly as validate-only enforcement; tooling must not become runtime policy authority.
