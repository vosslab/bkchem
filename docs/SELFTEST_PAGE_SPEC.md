# OASA Capabilities Sheet: Layout Specification

## Purpose

The capabilities sheet (`selftest_sheet.py`) generates a single-page visual reference demonstrating all OASA rendering features. It serves as both a regression test and documentation.

## Design Principles

### 1. Measure, Don't Guess

**Never use magic numbers for positioning.** All layout is driven by measured bounding boxes.

```python
# BAD: Hand-placed coordinates
x = 60 + i * 185  # What is 185? Why 60?

# GOOD: Measured and computed
bbox = ops_bbox(ops)
width = bbox[2] - bbox[0]
x = center_x - width / 2
```

### 2. Normalize to Target Height

All molecules in a row are scaled to the same height, maintaining aspect ratio.

```python
def normalize_to_height(ops, target_height):
    """Scale ops uniformly to target height."""
    bbox = ops_bbox(ops)
    current_height = bbox[3] - bbox[1]
    scale = target_height / current_height
    return scale_and_translate(ops, scale)
```

### 3. Row-Based Layout

Molecules are organized in horizontal rows. Each row has:
- **Fixed target height** for normalization
- **Equal gutters** between molecules
- **Automatic spacing** based on measured widths

```python
def layout_row(vignettes, y_top, page_width, row_height, gutter, margin):
    """Layout molecules in a horizontal row with measured spacing."""
    # 1. Normalize all to same height
    # 2. Measure widths
    # 3. Compute equal spacing
    # 4. Position from left to right
```

## Page Structure

```
+-------------------------------------------------+
|  Title: "OASA Renderer Capabilities"            |
+-------------------------------------------------+
|                                                  |
|  Bond Grid (8 types x 5 colors = 40 cells)      |
|  +---+---+---+---+---+---+---+---+             |
|  | n | b | w | h | q | s |s^ |s# |  Black        |
|  +---+---+---+---+---+---+---+---+             |
|  |...|...|...|...|...|...|...|...|  Red         |
|  +---+---+---+---+---+---+---+---+             |
|                                                  |
+-------------------------------------------------+
|                                                  |
|  Row 1: Projection Styles (height=80pt)         |
|  +---------+  +---------+  +---------+         |
|  | Benzene |  | Haworth |  | Fischer |         |
|  +---------+  +---------+  +---------+         |
|                                                  |
+-------------------------------------------------+
|                                                  |
|  Row 2: Complex Molecules (height=120pt)        |
|  +-----------------------------------+          |
|  |         Cholesterol               |          |
|  +-----------------------------------+          |
|                                                  |
+-------------------------------------------------+
```

## Layout Parameters

### Bond Grid

```python
grid_x = 50        # Left margin
grid_y = 60        # Top of grid (below title)
cell_w = 70        # Cell width
cell_h = 35        # Cell height
label_offset = 15  # Space for labels
```

### Vignette Rows

```python
# Row 1: Projection styles
row1_y = 290           # Top edge of molecules
row1_height = 80       # Target height for normalization
row1_title_y = 280     # Title position (10pt above)

# Row 2: Complex molecules
row2_y = 460
row2_height = 120
row2_title_y = 450

# Spacing
margin = 40            # Left/right page margin
gutter = 20            # Gap between vignettes
```

## Vignette Categories

### Row 1: Projection Styles

These test different chemical projection conventions:

1. **Benzene** - Aromatic ring with interior double bonds
   - Tests: Ring detection, aromatic rendering
   - Target: Clean hexagon with alternating interior bonds

2. **Haworth** - Sugar ring projections (pyranose + furanose)
   - Tests: Wedge, hatch, wide-rectangle bonds
   - Target: Side-by-side rings with proper 3D perspective

3. **Fischer** - D-glucose vertical projection
   - Tests: Straight bonds, left/right positioning, no stereochem
   - Target: Vertical backbone with horizontal substituents

### Row 2: Stress Test

1. **Cholesterol** - Complex fused ring system from CDML
   - Tests: Many bonds, connectivity, real-world molecule
   - Target: Readable structure without distortion

## Implementation Guidelines

### Adding a New Vignette

1. **Write a builder function** that returns ops (not a molecule):

```python
def _build_my_molecule_ops():
    """Build molecule and return render ops."""
    mol = create_molecule()

    # Build rendering context
    context = render_ops.BondRenderContext(
        molecule=mol,
        line_width=1.0,
        bond_width=3.0,
        wedge_width=6.0,
        ...
    )

    # Generate ops for all bonds
    all_ops = []
    for bond in mol.edges:
        v1, v2 = bond.vertices
        start = (v1.x, v1.y)
        end = (v2.x, v2.y)
        context.bond_coords[bond] = (start, end)
        ops = render_ops.build_bond_ops(bond, start, end, context)
        all_ops.extend(ops)

    return all_ops
```

2. **Add to appropriate row**:

```python
row1_vignettes = [
    ("Benzene", _build_benzene_ops()),
    ("Haworth", _build_haworth_ops()),
    ("Fischer", _build_fischer_ops()),
    ("New Molecule", _build_my_molecule_ops()),  # <- Add here
]
```

3. **Adjust row parameters if needed**:

```python
# If molecules don't fit:
row1_height = 70  # Reduce height
gutter = 15       # Reduce spacing
```

The layout system will automatically measure, normalize, and position.

### Modifying Layout

**To change row heights:**

```python
row1_height = 100  # Larger molecules
row2_height = 140
```

**To change spacing:**

```python
gutter = 30        # More space between vignettes
margin = 50        # More page margin
```

**To add a third row:**

```python
row3_y = row2_y + row2_height + 80  # 80pt gap
row3_height = 100
row3_vignettes = [...]
row3_result = layout_row(row3_vignettes, ...)
```

## Utilities

### ops_bbox(ops)

Returns `(minx, miny, maxx, maxy)` for a list of render ops.

Handles: `LineOp`, `PolygonOp`, `CircleOp`, `PathOp`

### normalize_to_height(ops, target_height)

Scales ops uniformly to target height.

Returns: `(transformed_ops, actual_width, actual_height)`

### layout_row(vignettes, y_top, page_width, row_height, gutter, margin)

Layouts a row of vignettes with measured spacing.

Args:
- `vignettes`: List of `(title, ops)` tuples
- `y_top`: Y coordinate for top of row
- `page_width`: Total page width
- `row_height`: Target height for normalization
- `gutter`: Space between vignettes
- `margin`: Left/right page margin

Returns: List of `(title, positioned_ops, x_center, y_center)` for rendering

## Testing

### Visual Inspection

```bash
# Generate SVG for quick visual check
python packages/oasa/oasa/selftest_sheet.py --format svg
open oasa_capabilities_sheet.svg
```

Look for:
- No overlapping molecules
- Consistent baselines within rows
- Equal spacing (gutters)
- Readable labels
- No clipping at page edges

### Regression Testing

```bash
# Generate PDF for archival comparison
python packages/oasa/oasa/selftest_sheet.py --format pdf
```

Compare with previous version:
- Bond styles unchanged
- Molecular structures accurate
- Layout consistent

## Common Issues

### Molecules Overlap

**Cause:** Row height too large or gutter too small

**Fix:**
```python
row1_height = 70  # Reduce
gutter = 25       # Increase
```

### Molecule Clipped at Edge

**Cause:** Margin too small or molecule too wide

**Fix:**
```python
margin = 50           # Increase margin
row1_height = 70      # Reduce size
```

### Distorted Aspect Ratio

**Cause:** Manual scaling without bbox measurement

**Fix:** Use `normalize_to_height()` instead of manual scale factors.

### Inconsistent Baselines

**Cause:** Vertical centering instead of top-alignment

**Fix:** Row layout top-aligns all molecules automatically.

## Future Enhancements

### Priority 1: More Projections
- Newman projection
- Sawhorse projection
- Cyclohexane chair/boat conformations

### Priority 2: Advanced Stereochemistry
- Cahn-Ingold-Prelog (CIP) labels
- Axial chirality (allenes, biphenyls)
- E/Z double bond notation

### Priority 3: Dynamic Layout
- Auto-select row/column count based on vignette count
- Responsive to page size changes
- Optional vertical stacking for narrow pages

## References

- Main implementation: `packages/oasa/oasa/selftest_sheet.py`
- Render ops system: `packages/oasa/oasa/render_ops.py`
- Haworth layout: `packages/oasa/oasa/haworth.py`
- Bond semantics: `packages/oasa/oasa/bond_semantics.py`
