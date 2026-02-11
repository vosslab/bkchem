# Haworth overrides inventory

Last updated: 2026-02-11

Scope:
- Runtime/rendering overrides in `packages/oasa/oasa/*`.
- Haworth-specific tooling overrides in `tools/*` that influence validation or diagnostics.

Definition:
- An override is any Haworth-specific branch, constant set, or policy that intentionally diverges from generic BKChem rendering/measurement defaults.

## Runtime and spec overrides

| ID | Location | Override | Justification | Keep/remove |
| --- | --- | --- | --- | --- |
| H-001 | `packages/oasa/oasa/haworth/__init__.py:27` | Fixed ring templates (`PYRANOSE_TEMPLATE`, `FURANOSE_TEMPLATE`). | Enforces canonical Haworth silhouettes instead of free coordinate layout. | Keep |
| H-002 | `packages/oasa/oasa/haworth/__init__.py:46` | Forced ring orientation (`HAWORTH_EXPECTED_ORIENTATION`). | Keeps up/down substituent semantics stable across inputs. | Keep |
| H-003 | `packages/oasa/oasa/haworth/__init__.py:55` | Default `front_style="haworth"` in `build_haworth(...)`. | Activates Haworth depth cue contract by default. | Keep |
| H-004 | `packages/oasa/oasa/haworth/__init__.py:291` | Haworth front-edge tagging chooses one `q` edge and two `w` edges. | Encodes textbook front-face style (thick front bar + side wedges). | Keep |
| H-005 | `packages/oasa/oasa/haworth/__init__.py:311` | Writes `bond.properties_["haworth_position"]` (`front`/`back`). | Shared renderer needs this marker for Haworth-only wedge/front behavior. | Keep |
| H-006 | `packages/oasa/oasa/haworth/__init__.py:345` | Wedge orientation rewrite in `_orient_wedge(...)`. | Ensures consistent wedge direction relative to front face. | Keep |
| H-007 | `packages/oasa/oasa/bond.py:48` | Adds bond type `q` (wide rectangle Haworth front bond). | Creates explicit bond primitive type for Haworth front edge. | Keep |
| H-008 | `packages/oasa/oasa/render_geometry.py:333` | `haworth_front_edge_geometry(...)` and `haworth_front_edge_ops(...)`. | Implements Haworth front-edge primitive in shared geometry runtime. | Keep |
| H-009 | `packages/oasa/oasa/render_geometry.py:669` | For `w` edges with `haworth_position=front`, extends wedge overlap. | Avoids seam/gap where side wedge meets front bar. | Keep |
| H-010 | `packages/oasa/oasa/render_geometry.py:684` | `edge.type == 'q'` dispatch to Haworth front-edge ops. | Required renderer dispatch for Haworth front bonds. | Keep |
| H-011 | `packages/oasa/oasa/haworth/spec.py:16` | `_RING_RULES` for ALDO/KETO anomeric and closure carbons. | Haworth conversion contract requires chemistry-specific ring closure rules. | Keep |
| H-012 | `packages/oasa/oasa/haworth/spec.py:178` | `_ensure_haworth_eligible(...)` rejects unsupported pathway tokens. | Prevents invalid/unsupported inputs from entering Haworth renderer. | Keep |
| H-013 | `packages/oasa/oasa/haworth/spec.py:203` | `_anomeric_oh_direction(...)` hard-codes alpha/beta x D/L mapping. | Required stereochemical convention mapping for Haworth. | Keep |
| H-014 | `packages/oasa/oasa/haworth/spec.py:281` | Furanose two-carbon tail direction from closure-carbon stereochemistry. | Needed for correct face selection of two-carbon tails. | Keep |
| H-015 | `packages/oasa/oasa/haworth/renderer_config.py:31` | Fixed ring slot topology + front edge indices per ring type. | Stabilizes slot-addressed rendering and labeling logic. | Keep |
| H-016 | `packages/oasa/oasa/haworth/renderer.py:450` | Haworth ring edge thickness ratios (`front=0.15`, `back=0.04`). | Preserves front/back depth styling. | Keep |
| H-017 | `packages/oasa/oasa/haworth/renderer.py:490` | Oxygen-adjacent ring-edge clipping against oxygen exclusion target. | Prevents ring paint from entering oxygen glyph. | Keep |
| H-018 | `packages/oasa/oasa/haworth/renderer.py:617` | Interior pyranose up-hydroxyl anchors forced inward on `BL/BR`. | Fixes interior OH readability and alignment at ring center lanes. | Keep |
| H-019 | `packages/oasa/oasa/haworth/renderer.py:626` | Furanose top substituent clearance expansion and right-top OH nudge. | Avoids top-line collisions with oxygen/opposite branch labels. | Keep |
| H-020 | `packages/oasa/oasa/haworth/renderer.py:642` | Defers two-carbon furanose tails until simple labels are placed. | Tail chain2 placement needs final occupied-label map. | Keep |
| H-021 | `packages/oasa/oasa/haworth/renderer.py:835` | Vertical chain special handling (`force_vertical_chain`) for furanose top-left chain-like labels. | Enforces visually straight vertical connector through glyph centerline. | Keep (vertical exception) |
| H-022 | `packages/oasa/oasa/haworth/renderer.py:876` | Direction policy overrides (`auto` -> `line` + `vertical_lock`) for hydroxyl/vertical cases. | Enforces Phase 4 straight vertical connector contract. | Keep (vertical exception) |
| H-023 | `packages/oasa/oasa/haworth/renderer.py:1001` | `_resolve_methyl_label_collision(...)` local CH3/H3C fallback + 90% scaling. | Deterministic local fix for CH3 overlap in dense neighborhoods. | Keep, candidate to generalize |
| H-024 | `packages/oasa/oasa/haworth/renderer.py:1095` | Chain2 label solver with custom candidate offsets + overlap scoring. | Needed for legal branched tail placement without label clashes. | Keep |
| H-025 | `packages/oasa/oasa/haworth/renderer.py:1407` | Branched tail minimum standoff factors (`up=1.75`, `down=1.35`). | Prevents tails from collapsing into ring area when inherited length is short. | Keep |
| H-026 | `packages/oasa/oasa/haworth/renderer.py:1571` | `_furanose_two_carbon_tail_profile(...)` hard-codes branch vectors, parity behavior, hashed-branch side, anchors. | Captures explicit two-carbon branch-angle contract and side-parity rules. | Keep, but reduce hard-coded branching over time |
| H-027 | `packages/oasa/oasa/haworth/renderer.py:1623` | `_append_branch_connector_ops(...)` Haworth branch connector style logic (`solid`/`hashed`) + hatch legality filtering. | Ensures branched hash strokes obey strict attach legality near labels. | Keep |
| H-028 | `packages/oasa/oasa/haworth/renderer.py:1706` | Oxygen-adjacent edge split into oxygen-color vs line-color half-polygons. | Keeps oxygen-adjacent edge cue and readability. | Keep |
| H-029 | `packages/oasa/oasa/haworth/renderer.py:1752` | `_rounded_side_edge_path_op(...)` custom side-edge rounded wedge path. | Maintains Haworth-specific front-to-back side-edge visual style. | Keep |
| H-030 | `packages/oasa/oasa/haworth/renderer.py:261` | `strict_validate_ops(...)` strict overlap gate at Haworth-ops level. | Hard runtime legality gate for matrix regressions. | Keep |
| H-031 | `packages/oasa/oasa/haworth/renderer_text.py:83` | Side-aware hydroxyl order flip (`OH` <-> `HO`). | Keeps oxygen nearest connector side and improves readability. | Keep |
| H-032 | `packages/oasa/oasa/haworth/renderer_text.py:93` | Side-aware chain text flip (`CH2OH` -> `HOH2C`, `CHOH` -> `HOHC`). | Keeps left-side chain readability and trailing-carbon attach semantics. | Keep (tooling must normalize aliases) |
| H-033 | `packages/oasa/oasa/haworth/renderer_text.py:114` | Haworth-specific text offsets/baseline shifts for hydroxyl and C-led/C-trailed labels. | Aligns connector endpoint with intended glyph primitive centers. | Keep |
| H-034 | `packages/oasa/oasa/haworth/renderer_layout.py:61` | Two-pass hydroxyl layout optimizer with bounded candidate factors + ring-collision penalties. | Provides deterministic resolution for dense OH placement. | Keep |
| H-035 | `packages/oasa/oasa/haworth/renderer_layout.py:240` | Internal OH pair overlap resolver with ring-type-specific anchor and text-scale rules. | Fixes known interior OH overlap failure modes. | Keep |

## Tooling and diagnostics overrides

| ID | Location | Override | Justification | Keep/remove |
| --- | --- | --- | --- | --- |
| T-001 | `tools/archive_matrix_summary.py:178` | Regeneration path uses Haworth runtime `render_from_code(...)` directly. | Keeps matrix preview generation tied to runtime contract, not static fixtures. | Keep |
| T-002 | `tools/archive_matrix_summary.py:230` | Strict-render mode invokes `haworth_renderer.strict_validate_ops(...)`. | Enforces strict overlap legality during preview regeneration. | Keep |
| T-003 | `tools/measure_glyph_bond_alignment.py:94` | Default excludes detected Haworth base-ring geometry from diagnostics. | Prevents base ring template primitives from drowning out substituent regressions. | Keep |
| T-004 | `tools/measure_glyph_bond_alignment.py:511` | Canonicalizes chain alias text (`HOH2C` variants -> `CH2OH`) in measurements. | Keeps independent metrics robust to renderer text-order aliases. | Keep |
| T-005 | `tools/measure_glyph_bond_alignment.py:22` | Canonical lattice check uses 30-degree family (`0..330`) for measurement. | Independent geometry gate for straightness/canonical-angle conformance. | Keep |
| T-006 | `tools/measure_glyph_bond_alignment.py:1775` | Haworth base-ring detection heuristics (cycle + primitive detection). | Needed to implement ring exclusion without regeneration-time knowledge. | Keep, monitor for false-detects |

## Non-overrides (intentional exclusions)

- API compatibility shims:
  - `packages/oasa/oasa/haworth_renderer.py`
  - `packages/oasa/oasa/haworth_spec.py`
  These preserve import paths but do not add geometry policy.
- Test-only grep gates and smoke assertions are not renderer overrides; they are enforcement.

## Cleanup candidates (if objective is fewer Haworth-specific branches)

- Highest-complexity runtime candidates:
  - H-023 (`_resolve_methyl_label_collision`)
  - H-024 (`_solve_chain2_label_with_resolver`)
  - H-026 (`_furanose_two_carbon_tail_profile` side/parity map)
  - H-035 (`resolve_internal_hydroxyl_pair_overlap` ring-type branches)
- Any removal/refactor of these must keep Phase 4 gates green:
  - strict overlap
  - endpoint alignment metrics
  - canonical lattice-angle checks
