# Refactor progress

Last updated: 2026-02-01

## Snapshot
- Registry refactor: OASA codec registry is implemented and in use by the CLI.
- Rendering refactor: SVG/Cairo unified via render ops, rounded wedges default.
- CDML refactor: OASA CDML writer exists, BKChem can use it behind a flag.

## Plan status by document

### [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md)
- Status: Complete.
- Notes: Render ops, SVG/Cairo thin painters, ops snapshots, and drift tests are in place.
- Next: Keep stable; no further work unless new primitive types are added.

### [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md)
- Status: Complete.
- Notes: Rounded wedge geometry is shared via `wedge_geometry.py` and used by
  render ops and BKChem bond rendering.
- Next: None unless geometry tuning is requested.

### [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
- Status: Phases 1-4 complete; Phase 5 partial.
- Notes: Ring templates, oxygen placement, substituent rules, and bond styles
  are implemented with render ops support. Haworth smoke tests pass.
- Next: Add CLI entry point and usage docs for batch Haworth output.

### [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
- Status: Phases 0-3 complete; Phase 4 optional; Phase 5 in progress.
- Notes: Bond semantics normalized, CDML attribute helpers shared, metadata
  round-trip tests are in place. GUI parity work (q, rounded wedge) is done.
- Next: Decide when to flip the `BKCHEM_USE_OASA_CDML` default and remove the
  legacy BKChem parsing path (Phase 5).

### [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md)
- Status: Phase 1 complete; Phase 2 mostly complete; Phase 3 optional.
- Notes: OASA CDML writer exists; BKChem uses it behind a flag; round-trip
  fixtures and tests exist.
- Next: Remove legacy code paths once the new default settles.

### [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md)
- Status: Needs review for legacy l/r references and current bond type list.
- Next: Update bond type list to reflect the removal of left/right variants and
  current normalization rules.

### [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md)
- Status: Still documents legacy plugins.
- Next: Add a short section noting registry-backed import/export and how
  plugins should rely on `oasa_bridge` once Phase 3 of the codec plan lands.

### [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md)
- Status: Active policy.
- Notes: New registry and CDML writer files include SPDX headers.
- Next: Keep enforcing SPDX headers on new files.

### [docs/TODO_CODE.md](docs/TODO_CODE.md)
- Status: Still relevant.
- Next: Consider adding the codec registry milestones and the Phase 5 CDML
  default flip as near-term tasks.

### [docs/CODEC_REGISTRY_PLAN.md](docs/CODEC_REGISTRY_PLAN.md)
- Status: Phase 1-5 complete.
- Notes: Registry exists, CLI uses it, BKChem oasa_bridge routes through it, and
  plugin guidance plus drift tests are in place.
- Next: None unless new formats are added.

## Short-term priorities
- Complete codec registry Phase 3: route `oasa_bridge` and BKChem format plugins
  through `oasa.codec_registry`.
- Decide on the Phase 5 CDML default flip and legacy path removal.
- Update `docs/BKCHEM_FORMAT_SPEC.md` for current bond type semantics.
