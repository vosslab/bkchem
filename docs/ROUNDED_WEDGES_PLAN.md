# Rounded wedges plan

## Purpose
Create a **universal** rounded wedge geometry primitive that works for:
- Standard stereochemistry wedges (chiral centers, chemistry notation)
- Haworth projection wedges (carbohydrate rings)
- Any other wedge bond type in chemical structure drawing
- Both SVG and Cairo rendering backends

**Critical design principles**:
1. The rounded wedge is a general geometric primitive, NOT Haworth-specific
2. It should work for any wedge bond in any context without requiring special properties
3. **The wedge is directional** - defined by two endpoints (tip and base), not angle
4. **The wedge expands from tip to base** - length and angle are derived, not inputs
5. No mirroring logic needed - directionality is encoded in endpoint order

## Current problems

### Code duplication
Rounded wedge geometry is computed in two places:
- `packages/oasa/oasa/svg_out.py:310` (`_draw_rounded_wedge`)
- `packages/oasa/oasa/render_ops.py:118` (`haworth_wedge_ops`)

### Tight coupling
- `_draw_rounded_wedge` requires `cap_center` and `cap_normal` from Haworth-specific context
- Regular wedges use straight polygon edges (svg_out.py:352-356)
- No way to request rounded edges for standard stereochemistry wedges

### Arc direction issues
The SVG arc parameters are hardcoded in legacy code:
```python
d_path = ("M %s %s L %s %s A %s %s 0 0 1 %s %s L %s %s Z" %
          (n1[0], n1[1], w1[0], w1[1], t, t, w2[0], w2[1], n2[0], n2[1]))
```

The `0 0 1` arc flags mean:
- `0` = small arc (not large arc)
- `0` = counter-clockwise sweep
- `1` = (this should be sweep-flag, not hardcoded)

This breaks when the wedge orientation changes and is not suitable for
small corner fillets.

### Confusing angle-based APIs
Some wedge implementations use angle as an input parameter, which is wrong because:
- A wedge is directional (tip vs base)
- Wedge from A->B is different from wedge from B->A
- Angle should be DERIVED from endpoints, not an input
- This matches chemistry conventions (bonds defined by atom positions)

## Proposed solution

### File organization

**New file: `packages/oasa/oasa/wedge_geometry.py`**

This file contains ALL rounded wedge geometry computation. It must be:
- **Pure geometry only** - no rendering, no chemistry domain logic
- **Self-contained** - no imports from haworth.py, svg_out.py, cairo_out.py, bond.py
- **Universal** - works for any wedge (stereochemistry, Haworth, future uses)
- **Testable** - pure functions with deterministic outputs

Contents:
```
wedge_geometry.py
  |
  +-- rounded_wedge_geometry()  # Main public API
  +-- rounded_wedge_path_from_corners()  # Helper for custom base normals
  +-- _compute_wedge_corners()  # Helper: narrow/wide corner points
  +-- _corner_fillet()          # Helper: corner fillet geometry
  +-- _compute_wedge_area()     # Helper: area formula for validation
  +-- _wedge_to_path_commands() # Helper: SVG/Cairo path commands
```

### Phase 1: Pure geometry module
Create `packages/oasa/oasa/wedge_geometry.py` with **pure, universal** geometry functions.

**IMPORTANT**: This module must be completely general and have ZERO dependencies on:
- Haworth-specific code (no imports from `haworth.py`)
- Bond properties or molecule objects (no imports from `bond.py`)
- Rendering backends (no imports from `svg_out.py` or `cairo_out.py`)
- Chemistry domain logic

It should only contain pure geometric functions operating on points and widths.

#### Core function signature
```python
def rounded_wedge_geometry(
	tip_point: tuple[float, float],
	base_point: tuple[float, float],
	wide_width: float,
	narrow_width: float = 0.0,
	corner_radius: float | None = None
) -> dict:
	"""Compute rounded wedge polygon with rounded wide corners.

	The wedge is DIRECTIONAL: it expands from tip_point (narrow) to base_point (wide).
	Length and angle are DERIVED from the two endpoints, not inputs.

	This is the natural definition for chemistry wedge bonds, which are defined
	by their endpoints (atoms), not by abstract length/angle parameters.

	Args:
		tip_point: (x, y) center of narrow end (the tip)
		base_point: (x, y) center of wide end
		wide_width: Width at the wide end
		narrow_width: Width at the narrow end (default 0.0 for true point tip)
			Use 0.0 for standard chemistry wedges (pointed tip)
			Use small value for numerical stability if needed
			Use nonzero for stylized wedges
		corner_radius: Optional rounding radius for the wide corners

	Returns:
		{
			"tip": (x, y),
			"base": (x, y),
			"narrow_left": (x, y),   # May equal tip if narrow_width=0
			"narrow_right": (x, y),  # May equal tip if narrow_width=0
			"wide_left": (x, y),
			"wide_right": (x, y),
			"corner_radius": float,
			"length": float,         # DERIVED: distance(tip, base)
			"angle": float,          # DERIVED: atan2(base - tip)
			"path_commands": [...]   # For PathOp
			"area": float            # For validation tests
		}
	"""
```

**Design principles:**
- Wedge from A->B is DIFFERENT from wedge from B->A (tip vs base swap)
- Length and angle are DERIVED, not inputs (for debugging/tests only)
- Chemistry bonds are defined by atom endpoints, so this is natural
- Narrow width defaults to 0.0 (standard pointed wedge)
- Scaling is caller's responsibility, not geometry's (no width_scale parameter)



### Phase 2: Integrate into render_ops
Import and use the pure geometry module in the **existing** `packages/oasa/oasa/render_ops.py`:

**Note**: Backend unification is already complete! `render_ops.py` already contains:
- Op dataclasses (LineOp, PolygonOp, CircleOp, PathOp)
- `build_bond_ops(edge, start, end, context)` - main bond dispatcher
- `haworth_wedge_ops()` - current Haworth wedge implementation
- `ops_to_svg()` and `ops_to_cairo()` painters

Add wedge geometry import:

```python
@dataclasses.dataclass(frozen=True)
class WedgeOp:
	tip_point: tuple[float, float]    # Narrow end
	base_point: tuple[float, float]   # Wide end center
	wide_width: float
	narrow_width: float = 0.0
	fill: str = "#000"
```

Update `haworth_wedge_ops` to use `wedge_geometry.rounded_wedge_geometry`.

Add `wedge_to_path_op` converter:
```python
def wedge_to_path_op(wedge: WedgeOp) -> PathOp:
	"""Convert WedgeOp to PathOp for rendering."""
	geom = rounded_wedge_geometry(
		wedge.tip_point,
		wedge.base_point,
		wedge.wide_width,
		wedge.narrow_width
	)
	return PathOp(
		commands=geom["path_commands"],
		fill=wedge.fill,
	)
```

**Note**: No helper function needed! The WedgeOp dataclass already takes endpoints directly.
If you have old code using separate tip/base points, just pass them:
```python
# Direct construction (preferred)
wedge_op = WedgeOp(
	tip_point=tip,
	base_point=base,
	wide_width=w,
	narrow_width=n
)
```

### Phase 3: Update SVG renderer
Replace `svg_out._draw_rounded_wedge` with render ops:

```python
def _draw_wedge(self, parent, start, end, edge, fill_color=None, rounded=True):
	# Bond vertices define tip and base
	v1, v2 = edge.vertices
	tip = self.transformer.transform_xy(v1.x, v1.y)
	base = self.transformer.transform_xy(v2.x, v2.y)

	if rounded:
		wedge_op = WedgeOp(
			tip_point=tip,
			base_point=base,
			wide_width=self.wedge_width,
			narrow_width=0.0,  # Pointed tip (standard chemistry)
			fill=fill_color or "#000"
		)
		path_op = wedge_to_path_op(wedge_op)
		ops_to_svg(parent, [path_op])
	else:
		# Fall back to straight polygon (for legacy/testing)
```

### Phase 4: Update Cairo renderer
Add wedge rendering to `cairo_out.py`:

```python
def _draw_wedge(self, context, edge, fill_color=None, rounded=True):
	v1, v2 = edge.vertices
	tip = self.transformer.transform_xy(v1.x, v1.y)
	base = self.transformer.transform_xy(v2.x, v2.y)

	if rounded:
		wedge_op = WedgeOp(
			tip_point=tip,
			base_point=base,
			wide_width=self.wedge_width,
			narrow_width=0.0,  # Pointed tip
			fill=fill_color or (0, 0, 0)
		)
		path_op = wedge_to_path_op(wedge_op)
		ops_to_cairo(context, [path_op])
	else:
		# Straight polygon fallback
```

### Phase 5: Enable for all wedges
Update bond rendering decision logic:

```python
# In svg_out.py and cairo_out.py
if bond.type == 'w':
	# Use rounded wedges by default for all wedge bonds
	self._draw_wedge(parent, start, end, edge,
	                 fill_color=color, rounded=True)
```

### Phase 6: Documentation and cleanup
- Document that wedges always expand from tip to base
- Document that endpoint order controls directionality (no angle/mirroring parameters)
- Remove any legacy angle-input or mirroring logic from old implementations
- Add examples showing how to orient wedges via endpoint placement

## Geometry details

### Computing corner fillets
Given tip point T, base point B, widths n (narrow) and w (wide):

1. **Derive length and angle**:
   - `dx = B.x - T.x`
   - `dy = B.y - T.y`
   - `L = sqrt(dx^2 + dy^2)` (length)
   - `theta = atan2(dy, dx)` (angle)
2. **Unit bond vector**: `u = (dx/L, dy/L)`
3. **Perpendicular** (rotated 90deg CCW): `perp = (-dy/L, dx/L)`
4. **Narrow corners** (at the tip T):
   - `N_left = T + perp * (n/2)`
   - `N_right = T - perp * (n/2)`
5. **Wide corners** (at the base B):
   - `W_left = B + perp * (w/2)`
   - `W_right = B - perp * (w/2)`
6. **Corner radius**:
   - Default `r = 0.25 * w`
   - Clamp by the base width (`r <= w/2`)
   - Clamp by side lengths and interior angles so fillets do not overlap
7. **Fillet geometry** (per corner):
   - Let `v1` = unit vector along the side edge
   - Let `v2` = unit vector along the base edge
   - Interior angle `phi = acos(v1 dot v2)`
   - Tangent offset `t = r / tan(phi / 2)`
   - Tangent points = `corner + v1 * t`, `corner + v2 * t`
   - Arc center = `corner + bisector * (r / sin(phi / 2))`
8. **Directionality**:
   - Wedge from T->B is DIFFERENT from wedge from B->T
   - The endpoint order defines which end is narrow vs wide
   - No mirroring parameter needed - swap endpoints to reverse direction

### Area computation (for validation)
Use the trapezoid body as the validation area:

```
A_trap = L * (n + w) / 2
```

This ignores the small corner fillet cutouts, but remains
orientation-independent and stable for unit tests.

### SVG path format
```
M N_left.x N_left.y
L L_side_tangent.x L_side_tangent.y
A r r 0 0 1 L_base_tangent.x L_base_tangent.y
L R_base_tangent.x R_base_tangent.y
A r r 0 0 1 R_side_tangent.x R_side_tangent.y
L N_right.x N_right.y
Z
```

The base stays flat, and only the two wide corners are rounded.

### Cairo path format
```python
context.move_to(N_left.x, N_left.y)
context.line_to(L_side_tangent.x, L_side_tangent.y)
context.arc(L_center.x, L_center.y, r, L_angle_start, L_angle_end)
context.line_to(R_base_tangent.x, R_base_tangent.y)
context.arc(R_center.x, R_center.y, r, R_angle_start, R_angle_end)
context.line_to(R_side_tangent.x, R_side_tangent.y)
context.line_to(N_right.x, N_right.y)
context.close_path()
context.fill()
```

## Testing strategy

### Unit tests
File: `tests/test_wedge_geometry.py`

1. **Basic geometry**:
   - Horizontal wedge (angle=0deg) produces correct corners
   - Vertical wedge (angle=90deg) produces correct corners
   - Diagonal wedges (45deg, 135deg, etc.) produce correct corners
   - Arc angles are in correct range

2. **Area invariance** (key validation test):
   - Compute wedge at angles [0deg, 45deg, 90deg, 135deg, 180deg, 225deg, 270deg, 315deg]
   - All should have **identical area** (within floating point tolerance)
   - Area formula: `A = L*(n+w)/2`
   - Test with multiple length/width combinations
   - This proves geometry is rotationally correct

3. **Rotation + endpoint swap equivalence**:
   - Define midpoint: `M = ((tip.x + base.x)/2, (tip.y + base.y)/2)`
   - Rotate geometry 180deg around M -> should match geometry from swapped endpoints
   - Test: `geom(tip, base, w, n)` rotated 180deg == `geom(base, tip, w, n)`
   - This verifies the wedge is directional and geometry is consistent

4. **Edge cases**:
   - Zero-length wedge raises ValueError
   - Negative length raises ValueError
   - Narrow width larger than wide width (inverted wedge) - allow or error?
   - Very small widths (numerical stability)
   - Angle wraparound (2pi == 0)

### Smoke tests
File: `tests/test_rounded_wedges_smoke.py`

1. **Standard stereochemistry**:
   - Render a chiral center with four wedge bonds in cardinal directions
   - Assert SVG contains arc paths
   - Assert PNG output is non-empty

2. **Haworth projection**:
   - Render pyranose ring with rounded wedges
   - Compare to existing haworth_layout_smoke.svg
   - Assert visual similarity (same number of arcs)

3. **Rotational equivalence**:
   - Render wedge at angle 0deg and wedge at angle 180deg
   - They should be 180deg rotations of each other
   - Verify by checking corner positions relative to center

### Render comparison
Add optional visual diff check:
- Render same molecule with `rounded=True` and `rounded=False`
- Save both SVG outputs
   - Document expected differences (rounded corners vs straight corners)

## Migration path

### Stage 1: Create geometry module (no integration)
- **Create `packages/oasa/oasa/wedge_geometry.py`** as a standalone module
- Implement `rounded_wedge_geometry()` and internal helpers
- Add unit tests in `tests/test_wedge_geometry.py`
- Module has ZERO imports from haworth, svg_out, cairo_out, or bond modules
- No changes to rendering code yet - geometry module is completely independent

### Stage 2: Integrate into render_ops (backend unification)
- Add `WedgeOp` dataclass
- Update `haworth_wedge_ops` to use new geometry
- Tests confirm ops-layer output matches

### Stage 3: Update SVG renderer
- Replace `_draw_rounded_wedge` with `wedge_to_path_op`
- Haworth smoke tests still pass
- SVG output is byte-identical (or visually identical)

### Stage 4: Update Cairo renderer
- Add wedge rendering via ops
- PNG smoke tests still pass

### Stage 5: Enable for all wedges
- Change default wedge rendering to use rounded edges
- Smoke test all bond types

### Stage 6: Documentation and cleanup
- Document endpoint-based definition (no angle parameters)
- Remove any legacy angle-input or mirroring code
- Add examples showing wedge directionality

## Acceptance criteria

- [ ] All wedge bonds use the same geometry code (universal primitive)
- [ ] SVG and Cairo produce visually identical wedges
- [ ] Haworth smoke tests still pass (using universal wedge, not special case)
- [ ] Standard stereochemistry wedges can use rounded style
- [ ] New unit tests cover edge cases
- [ ] **Zero Haworth-specific logic in wedge geometry module** (must be general!)
- [ ] Geometry module has no imports from haworth.py
- [ ] Area validation tests prove rotational correctness

## Deferred features

### Variable corner radius
Default corner radius is a fraction of the wide width.
Could support custom corner radius per bond or per renderer.
Defer until needed.

### Double-rounded wedges
Arc at both narrow and wide ends (lens shape).
Defer until needed.

### Gradient fills
Wedges with color gradients narrow->wide.
Defer until needed.

## References

### SVG arc parameters
- [SVG Path Arc Command](https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Paths#arcs)
- Sweep flag: 0 for CCW, 1 for CW
- Geometry module computes arc angles from tangent points, not fixed sweep flags

### Cairo arc functions
- [cairo.Context.arc](https://pycairo.readthedocs.io/en/latest/reference/context.html#cairo.Context.arc)
- [cairo.Context.arc_negative](https://pycairo.readthedocs.io/en/latest/reference/context.html#cairo.Context.arc_negative)

### Chemistry conventions
- Wedge bonds point toward viewer (bold/filled)
- Hatch bonds point away from viewer (dashed lines)
- Rounded corners help the wedge read as a single solid stroke
