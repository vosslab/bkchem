# Refactor progress

Last updated: 2026-02-01

## Snapshot
- Registry refactor: OASA codec registry is implemented and in use by the CLI.
- Rendering refactor: SVG/Cairo unified via render ops, rounded wedges default.
- CDML refactor: OASA CDML writer is the only BKChem serialization path.
- Haworth CLI: batch SMILES rendering is available via `packages/oasa/oasa_cli.py`.

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
- Status: Phases 1-7 complete.
- Notes: Ring templates, oxygen placement, substituent rules, and bond styles
  are implemented with render ops support. Haworth smoke tests pass. CLI and
  usage docs cover batch output.
- Next: None unless new ring types or CLI formats are added.

### [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
- Status: Phases 0-5 complete; Phase 4 optional.
- Notes: Bond semantics normalized, CDML attribute helpers shared, metadata
  round-trip tests are in place. GUI parity work (q, rounded wedge) is done.
- Next: Optional GUI parity work only.

### [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md)
- Status: Phases 1-2 complete; Phase 3 optional.
- Notes: OASA CDML writer is the default path; round-trip fixtures and tests
  exist.
- Next: Optional expansion beyond molecules only.

### [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md)
- Status: Updated for normalized hashed bonds and current bond type list.
- Next: None unless CDML adds new bond attributes.

### [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md)
- Status: Registry-backed import/export guidance is documented.
- Next: None unless new plugin entry points are added.

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
- Expand `packages/oasa/oasa_cli.py` once the public CLI surface is finalized (format
  conversion, batch reference output generation).
