# Complete bond-label attachment plan

## Purpose

Define one attachment engine that handles all bond-to-label attachment in OASA
and BKChem, remove renderer-specific attachment exceptions, and make overlap
behavior deterministic across SVG, PNG, PDF, and BKChem canvas rendering.

This is the follow-on plan to
[docs/archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](../archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md),
which delivered shared bbox clipping but did not fully remove all specialized
attachment paths.

## Phase status tracker

- [ ] Phase A: Spec + engine + baseline matrix
- [ ] Phase B: Migrate OASA renderers (molecular + Haworth)
- [ ] Phase C: Migrate BKChem + delete compatibility code

## Scope

In scope:
- OASA molecular rendering via
  [packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py).
- OASA Haworth schematic rendering via
  [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py).
- BKChem attachment paths in
  [packages/bkchem/bkchem/bond.py](../../packages/bkchem/bkchem/bond.py) and
  related label-leader attachment callers.
- Shared geometry APIs and shared overlap test gates.
- Documentation updates for the final attachment contract.

Out of scope:
- General glyph-outline clipping for all fonts (token-level geometric
  approximation is sufficient for this plan).
- New chemistry semantics in CDML beyond existing optional `attach_atom`.

## Why old plan fell short

The archived plan standardized bbox clipping and token intent (`first|last`),
but full unification is still incomplete:

- Haworth keeps specialized oxygen-target logic and slot constraints in
  [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py).
- BKChem still computes attachment clipping in its own path using Tk metrics in
  [packages/bkchem/bkchem/bond.py](../../packages/bkchem/bkchem/bond.py).
- Some tests still rely on label-class-specific overlap exemptions instead of a
  unified legality contract.

Result: behavior drifts even when global tests pass.

## Current blocking findings

These findings are explicitly in scope for this plan and must be resolved by
the end of Phase C:

- Hashed branch rendering still relies on a near-invisible carrier plus filtered
  hatch spans, which can look detached from the attached token.
- One overlap regression assertion is effectively non-protective
  (`overlap >= 0.0`) and must be replaced by a real threshold or strict
  non-overlap invariant.
- Smoke overlap gates still exempt many own non-hydroxyl connectors, allowing
  regressions to pass.
- Documentation and changelog path references can drift and must be checked by
  release hygiene.

## Design goals

- One shared attachment contract across OASA and BKChem.
- No renderer-specific attachment exceptions.
- No test-only exemptions for specific label text (`OH`, `HO`, etc.).
- Deterministic output for a fixed input across all render backends.
- Backward-compatible rollout with additive API evolution first.

## Required invariants

These invariants define done:

- Every connector endpoint attached to text is resolved by one shared
  target-resolution API.
- Every connector passes a strict paint-overlap gate using the same target
  primitives used by production rendering.
- Own-connector legality is defined by target geometry (aperture/target shape),
  not by label string or renderer-specific if-statements.
- Haworth may supply constrained connector segments (for example
  vertical-only), and endpoint clipping must preserve the supplied segment
  direction while resolving attachment.
- OASA SVG/PDF/PNG connector endpoints are equal within tolerance.
- BKChem and OASA produce equivalent connector endpoint geometry for matched
  fixtures (within tolerance and font-policy constraints).

## Unified target contract

### Target primitives

Add a shared attachment target abstraction in
[packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py)
or a dedicated helper module if that keeps responsibilities cleaner.

Required primitive kinds:
- `box`: axis-aligned rectangle target.
- `circle`: center + radius target.
- `segment`: optional narrow aperture target for directional token-edge use.
- `composite`: ordered target list with primary + fallback.

### Constraints

Support explicit constraints, attached to targets:
- `line_width`: used for paint clearance calculations.
- `clearance`: extra safety margin.
- `vertical_lock`: preserve vertical endpoint movement when required.
- `direction_policy`: side-preferred vs vertical-preferred for ambiguous entry.

### Token selector precedence

Token selection must be deterministic and renderer-independent:
- If `attach_element` is present, it wins.
- Else use `attach_atom="first|last"` (default `first` when missing).
- If neither selector is present, use minimal deterministic defaults:
  `attach_atom="first"` only; avoid label-specific implicit defaults.

### Core API

Additive shared API (names may vary, behavior is required):

```python
resolve_attach_endpoint(
    bond_start: tuple[float, float],
    target: AttachTarget,
    interior_hint: tuple[float, float] | None = None,
    constraints: AttachConstraints | None = None,
) -> tuple[float, float]
```

```python
validate_attachment_paint(
    line_start: tuple[float, float],
    line_end: tuple[float, float],
    line_width: float,
    forbidden_regions: list[AttachRegion],
    allowed_regions: list[AttachRegion] | None = None,
) -> bool
```

`validate_attachment_paint(...)` must compute forbidden regions from attachment
targets and constraints, not from cosmetic text mask polygons.

Keep `clip_bond_to_bbox(...)` as a compatibility wrapper routed internally to
the new engine.

## Haworth special-case contract

Haworth special behavior is in scope for this plan, but it must be expressed as
contract inputs to the shared engine, not as renderer-only endpoint hacks.

### Required intent model

Define a small per-substituent intent payload for Haworth attachment calls:

- `site_id`: deterministic position id (`C1_up`, `C3_down`, etc.).
- `label_text`: rendered text token stream.
- `attach_selector`: `attach_element` or `attach_atom` selector.
- `target_shape`: one of shared primitives (`box`, `circle`, `segment`,
  `composite`).
- `connector_constraint`: optional geometric constraint (`vertical_lock`,
  directional preference, slot lane).
- `bond_style`: `plain`, `wedge`, `hashed`, or `wavy`.

### Required behavioral rules

- No per-sugar-name renderer conditionals for attachment endpoints.
- Haworth vertical-only behavior is implemented by constrained connector input
  segments passed to shared clipping.
- Oxygen-targeted attachment (`OH`/`HO`) is represented by selector + target,
  not hardcoded string branches in endpoint math.
- Two-carbon tail stereography is represented by `bond_style` plus constrained
  branch vector policy, then clipped through shared target logic.
- Rounded wedge and hashed rendering must consume the clipped label-end
  endpoint so full painted geometry obeys overlap legality.

### Known special cases that must be covered

- Upward regular hydroxyl connectors (current dominant overlap source).
- Furanose left/right two-carbon side-chain stereography parity.
- L-rhamnose terminal methyl visibility/placement parity.
- CH2OH/HOH2C reversible text orientation with stable attachment target.

### Acceptance criteria for Haworth contract completion

- Haworth attachment paths contain zero renderer-specific endpoint exceptions.
- All Haworth special-case behavior is configured through the shared intent
  payload and target constraints.
- Strict overlap gate passes without label text exemptions.
- Archive matrix parity cases for side-chain stereography and methyl placement
  are green.

## Migration phases

### Phase A: Spec + engine + baseline matrix

Deliverables:
- Inventory all production attachment entry points (OASA molecular, Haworth,
  BKChem bonds, leader lines) and current special fallbacks.
- Commit baseline matrix fixtures for known regressions (Talose overlap,
  Allose/Gulose hashed branch issues, L-rhamnose methyl, two-carbon tail
  endpoints).
- Introduce shared target primitives + constraints.
- Implement directional edge intersection and circle target clipping in shared
  geometry.
- Define token selector precedence and deterministic default selector rules.
- Keep all old entry points functional through wrappers.

Files:
- [packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py)
- new helper module if needed (for example
  `packages/oasa/oasa/attachment_geometry.py`)

Tests:
- Add one shared fixture source used by unit and smoke tests.
- Add unit tests for each primitive and constraint combination.
- Verify deterministic behavior across vertical, horizontal, diagonal entries.
- Add circle-target legality tests: endpoint on circle boundary and epsilon past
  endpoint enters forbidden interior while segment up to endpoint stays legal.
- Require a test-clean baseline for targeted attachment suites before migration
  coding starts.

Key deliverable:
- Shared attachment engine exists, wrappers are in place, baseline fixture
  matrix is committed, and unit tests pass.

### Phase B: Migrate OASA renderers (molecular + Haworth)

Deliverables:
- Route molecular attachment endpoint resolution through shared primitive API.
- Remove direct line-rect clipping branches from molecular bond path.
- Replace Haworth-specific endpoint exceptions with shared target primitives:
  oxygen attachment becomes `circle` (with explicit clearance and slot
  constraints), token attachments become directional token-edge targets.
- Route Haworth special cases via the intent payload (selector, target,
  constraints, bond style) so behavior is declarative and testable.
- Remove label-specific overlap exemptions in production and tests.
- Replace hashed branch fallback heuristics with target-resolved hashed endpoint
  behavior that remains visibly attached without a near-invisible carrier hack.
- For rounded wedge and hashed bonds, generate final geometry from the clipped
  label-end endpoint so the full shape respects attachment legality (not just a
  centerline approximation).
- Replace non-protective overlap assertions with strict geometric invariants.

Files:
- [packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py)
- [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py)
- [packages/oasa/oasa/haworth/renderer_text.py](../../packages/oasa/oasa/haworth/renderer_text.py)
- [tests/test_connector_clipping.py](../../tests/test_connector_clipping.py)
- [tests/test_haworth_renderer.py](../../tests/test_haworth_renderer.py)
- [tests/smoke/test_haworth_renderer_smoke.py](../../tests/smoke/test_haworth_renderer_smoke.py)
- [tests/test_phase_c_render_pipeline.py](../../tests/test_phase_c_render_pipeline.py)

Tests:
- OASA endpoint parity across SVG/PDF/PNG must pass.
- Archive matrix must pass without label-specific exemptions.
- Add strict own-connector legality tests based only on target geometry.
- Add explicit hashed-branch attachment tests that fail on detached/floating
  terminal appearance.

Key deliverable:
- OASA has zero attachment exceptions, Haworth oxygen and token attachments are
  expressed as targets, and matrix smoke tests pass with strict overlap checks.

### Phase B.1 addendum: furanose side-chain stereography parity

This addendum is a focused parity task within Phase B.

#### Objective

Close the largest remaining visual/semantic gap vs reference outputs:
furanose two-carbon left-side chain stereography (hashed cue and above/below
placement impression).

#### Scope

In scope:
- Furanose two-carbon side-chain branch rendering in
  [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py)
- Related parity tests in
  [tests/test_haworth_renderer.py](../../tests/test_haworth_renderer.py)
  and
  [tests/smoke/test_haworth_renderer_smoke.py](../../tests/smoke/test_haworth_renderer_smoke.py)

Out of scope:
- Reverting current OH/HO readability improvements.
- Per-sugar hardcoded special cases.

#### Required implementation rules

- Derive branch style and placement from one deterministic stereocenter rule
  for this side-chain class.
- Do not use per-code exceptions.
- Ensure hashed/dashed cue appears when expected by the parity class.
- Ensure side-chain branch vector and terminal label lane produce the expected
  above/below visual impression.
- Keep branch endpoints target-resolved (attachment legality still applies).

#### Required fixtures

Start with explicit known gap fixtures, including:
- D-galactose furanose alpha
- neighboring furanose two-carbon-tail cases in the same parity class

#### Acceptance criteria

- Ring geometry and bold-face edge conventions remain unchanged.
- Vertical substituent cleanliness remains unchanged.
- OH/HO collision improvements remain intact.
- Furanose left-side two-carbon tail hashed/plane cue matches expected parity
  class across the fixture set.
- Matrix smoke plus strict overlap gate remain green.

### Phase C: Migrate BKChem + delete compatibility code

Deliverables:
- Replace BKChem direct clipping path with shared target-resolution adapter.
- Keep BKChem font-metric placement if needed, but endpoint resolution must be
  shared and deterministic under adapter rules.
- Remove dead compatibility branches and duplicated helpers.
- Remove test exemptions based on label class or renderer.
- Keep only contract-based legality checks.
- Add fail-fast CI gates for overlap and parity.
- Remove remaining blanket own-connector exemptions from smoke gates (except for
  explicitly modeled allowed target apertures).

Files:
- [packages/bkchem/bkchem/bond.py](../../packages/bkchem/bkchem/bond.py)
- BKChem leader-line modules that currently clip directly.

Tests:
- Add BKChem vs OASA endpoint equivalence fixtures for representative cases.
- Keep existing BKChem round/wedge and CDML roundtrip tests green.
- Full test suite must pass with no exception bypass flags.

Key deliverable:
- BKChem endpoints are resolved via shared engine, standalone clipping paths are
  removed, and exception branches are deleted.

## Backward compatibility

- `clip_bond_to_bbox(...)` remains as a compatibility wrapper while callers are
  migrated to shared targets.
- Existing `attach_atom="first|last"` behavior remains valid.
- Optional element-based attachment selectors are additive and do not break old
  inputs.
- Any caller without new metadata follows deterministic defaults.
- No CDML migration is required for existing files.
- Older readers that ignore new selectors may show slightly different visual
  attachment points, but structure and chemistry semantics remain unchanged.

## Release checklist (not a phase)

- `pytest tests/`
- archive matrix smoke
- selftest sheet generation
- endpoint parity checks across render backends
- two consecutive release cycles with zero bond-label regressions
- docs/changelog path validation for moved or archived plan/spec files

## Strict overlap gate

This gate is mandatory for Phase B and Phase C completion.

### Canonical validator

Add one canonical strict validator in
[tests/smoke/test_haworth_renderer_smoke.py](../../tests/smoke/test_haworth_renderer_smoke.py):

- `assert_no_bond_label_overlap_strict(ops, context)`
- No label-text exemptions (`OH`, `HO`, etc.).
- No own-connector exemptions except explicitly modeled target apertures.

### Geometry basis

Legality must be checked against painted geometry and target-based forbidden
regions:

- `LineOp`: use stroke radius (`width / 2`) against forbidden-region interior.
- `PathOp` (wedge) and `PolygonOp` bond shapes: validate the full painted shape
  envelope, not centerline approximations only.
- Forbidden regions come from attachment targets (token box/ellipse/circle and
  constraints), not cosmetic masks.

### Per-label legality rules

- Endpoint may terminate on target boundary.
- Connector paint may not enter strict forbidden interior (epsilon inset).
- Add epsilon sanity checks so boundary math remains deterministic.
- Numeric policy: edge touch is legal, and any penetration greater than
  `epsilon = 0.5 px` into forbidden interior is a hard failure.

### Smoke/system enforcement

The strict validator must run for:

- matrix smoke render checks with `show_hydrogens=True`
- matrix smoke render checks with `show_hydrogens=False`
- full archive matrix checks

Failure messages must include:
- case id
- bond op id
- label op id
- overlap metric (distance/penetration value)

### Unit/regression coverage

Add targeted strict-gate tests in
[tests/test_haworth_renderer.py](../../tests/test_haworth_renderer.py):

- forced overlap fails
- edge-touch passes
- legal own-connector aperture case passes
- non-aperture own-connector penetration fails

### CI policy

Strict overlap tests are fail-fast release gates and cannot be optional.

## Test plan matrix

| Area | Test files | Gate |
| --- | --- | --- |
| Shared primitives | `tests/test_label_bbox.py`, new primitive tests | unit |
| OASA molecular | `tests/test_connector_clipping.py` | unit/integration |
| Haworth geometry | `tests/test_haworth_renderer.py` | unit/regression |
| Haworth matrix | `tests/smoke/test_haworth_renderer_smoke.py` | smoke/system |
| Backend parity | `tests/test_phase_c_render_pipeline.py`, `tests/test_render_layout_parity.py` | integration |
| BKChem parity | existing BKChem tests + new endpoint fixtures | integration/regression |

## Risk management

- Use additive API first; do not break existing callers in Phase A.
- Migrate OASA first, then BKChem, with green gates between phases.
- Keep rollback path by preserving wrappers until late Phase C.
- Avoid refactoring attachment and unrelated rendering logic in same PR.

## Documentation updates required

When Phase C is complete:
- Archive
  [docs/archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](../archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md)
  as historical baseline.
- Update
  [docs/CDML_FORMAT_SPEC.md](../CDML_FORMAT_SPEC.md)
  to reflect finalized attachment contract semantics.
- Add final behavior notes to
  [docs/CODE_ARCHITECTURE.md](../CODE_ARCHITECTURE.md)
  and
  [docs/FILE_STRUCTURE.md](../FILE_STRUCTURE.md)
  if module boundaries change.

## Done checklist

- [ ] All attachment endpoints route through one shared target API.
- [ ] OASA molecular path has zero direct clipping exceptions.
- [ ] Haworth path has zero attachment exceptions.
- [ ] BKChem path has zero standalone attachment clipping logic.
- [ ] No label-type-specific overlap bypass exists in tests.
- [ ] Cross-backend endpoint parity gates pass.
- [ ] Archive matrix smoke passes with strict overlap gates.
- [ ] Documentation is updated and old plan is archived as superseded baseline.
