# Renderer capabilities sheet plan

## Purpose
Create a single-page visual reference showing all OASA rendering capabilities:
- Bond types (normal, bold, wedge, hashed, wavy, Haworth, etc.)
- Colors (per-bond colors, gradients)
- Complex features (aromatic rings, Haworth projections, stereochemistry)

This serves three audiences:
1. **Developers**: visual regression testing and capability verification
2. **Documentation**: "here is what OASA can render" reference
3. **Manual inspection**: easy-to-generate PDF/SVG for visual review

## Design principles

### 1. Shared generator function
**One function, multiple uses:**
- pytest calls it to generate and validate
- CLI calls it to produce output files
- No duplicated "how to build the sheet" logic

### 2. Standard page size
Use US Letter dimensions (not arbitrary canvas):
- **Portrait**: 8.5 x 11 inches = 612 x 792 points (at 72 DPI)
- **Landscape**: 11 x 8.5 inches = 792 x 612 points
- SVG: explicit width/height attributes
- Cairo: create surface with those dimensions

### 3. Work at ops level
Since backend unification is complete:
- Build ops for each vignette using existing molecule objects
- Transform ops into panel rectangles (translate + scale)
- Add labels as text ops (optional but useful)
- Painters (ops_to_svg, ops_to_cairo) handle the rest

## Sheet contents

### Section A: Bond style grid
**Grid layout**: bond types (columns) x colors (rows)

**Bond types to show:**
- Normal (`'n'`)
- Bold (`'b'`)
- Wedge (`'w'`)
- Hashed (`'h'`)
- Wide rectangle (`'q'` - Haworth front edge)
- Wavy (`'s'`)
- Double bond
- Triple bond

**Colors to show:**
- Black (`#000`)
- Red (`#f00`)
- Blue (`#00f`)
- Green (`#0a0`)
- Purple (`#a0a`)

**Cell content**: Tiny two-atom fragment (C-C bond) using that style and color.
Keep geometry identical across cells - visual differences come from rendering only.

### Section B: Complex molecule vignettes
**3-6 panels**, each exercising features the grid cannot:

1. **Aromatic ring**: benzene with alternating double bonds or aromatic circle
2. **Stereochemistry**: molecule with wedge and hashed bonds on chiral center
3. **Haworth rings**: pyranose and furanose side-by-side
4. **Mixed colors**: molecule with bonds in different colors
5. **Multi-bond**: molecule with single, double, triple bonds together
6. **Optional: wavy bond**: glucose with wavy anomeric bond

## File organization

### New module: `packages/oasa/oasa/selftest_sheet.py`
```
selftest_sheet.py
  |
  +-- build_renderer_capabilities_sheet()  # Main entry point
  +-- _build_bond_grid_ops()               # Section A
  +-- _build_vignette_ops()                # Section B
  +-- _transform_panel()                   # Layout helper
  +-- _add_label()                         # Text labels
```

### Main API
```python
def build_renderer_capabilities_sheet(
    page: str = "letter",
    portrait: bool = True,
    backend: str = "svg",
    seed: int = 0
) -> bytes | str:
    """Build a capabilities sheet showing all rendering features.

    Args:
        page: Page size ("letter", "a4")
        portrait: True for portrait, False for landscape
        backend: "svg" or "cairo"
        seed: Random seed for reproducible molecule generation

    Returns:
        SVG text (str) for SVG backend
        PNG/PDF bytes for Cairo backend
    """
```

## Implementation details

### Page dimensions
```python
PAGE_SIZES = {
    "letter": (612, 792),  # 8.5 x 11 inches at 72 DPI
    "a4": (595, 842),      # A4 at 72 DPI
}

def get_page_dims(page, portrait):
    w, h = PAGE_SIZES.get(page, PAGE_SIZES["letter"])
    if not portrait:
        w, h = h, w
    return w, h
```

### SVG structure
```xml
<svg width="612" height="792" viewBox="0 0 612 792"
     xmlns="http://www.w3.org/2000/svg">
  <g id="bond-grid">
    <!-- Section A: bond types x colors grid -->
  </g>
  <g id="vignettes">
    <!-- Section B: complex molecules -->
  </g>
</svg>
```

### Cairo backend
```python
if backend == "cairo":
    surface = cairo.SVGSurface(output_path, width, height)
    # or
    surface = cairo.PDFSurface(output_path, width, height)
    context = cairo.Context(surface)
    render_ops.ops_to_cairo(context, all_ops)
    surface.finish()
```

### Grid layout
```python
def _build_bond_grid_ops():
    bond_types = ['n', 'b', 'w', 'h', 'l', 'r', 'q', 's', '=', '#']
    colors = ['#000', '#f00', '#00f', '#0a0', '#a0a']

    grid_x = 50   # Left margin
    grid_y = 50   # Top margin
    cell_w = 50   # Cell width
    cell_h = 40   # Cell height

    ops = []
    for row, color in enumerate(colors):
        for col, bond_type in enumerate(bond_types):
            x = grid_x + col * cell_w
            y = grid_y + row * cell_h
            # Build tiny C-C fragment with this bond type and color
            fragment_ops = _build_bond_fragment(bond_type, color)
            # Transform into cell position
            panel_ops = _transform_panel(fragment_ops, x, y, scale=1.0)
            ops.extend(panel_ops)
    return ops
```

### Bond fragment
```python
def _build_bond_fragment(bond_type, color):
    """Build a tiny C-C bond fragment.

    Returns ops for a horizontal bond 20 units long.
    """
    # Create minimal molecule
    mol = oasa.molecule()
    a1 = oasa.atom(symbol='C', x=0, y=0)
    a2 = oasa.atom(symbol='C', x=20, y=0)
    mol.add_vertex(a1)
    mol.add_vertex(a2)

    bond = oasa.bond(order=1, type=bond_type)
    bond.vertices = (a1, a2)
    bond.properties_['line_color'] = color
    mol.add_edge(a1, a2, bond)

    # Build ops using existing infrastructure
    context = render_ops.BondRenderContext(
        molecule=mol,
        line_width=1.0,
        bond_width=3.0,
        wedge_width=4.0,
        bold_line_width_multiplier=1.2,
        shown_vertices=set(),
        bond_coords={bond: ((0, 0), (20, 0))},
    )
    return render_ops.build_bond_ops(bond, (0, 0), (20, 0), context)
```

## Testing

### Test file: `tests/test_renderer_capabilities_sheet.py`
```python
def test_svg_capabilities_sheet():
    """Generate SVG capabilities sheet and validate structure."""
    svg_text = build_renderer_capabilities_sheet(
        page="letter",
        portrait=True,
        backend="svg",
        seed=42
    )

    # Parse SVG
    doc = dom.parseString(svg_text)
    svg = doc.documentElement

    # Validate page dimensions
    assert svg.getAttribute("width") == "612"
    assert svg.getAttribute("height") == "792"

    # Validate content exists
    assert len(svg.getElementsByTagName("path")) > 10  # Wavy bonds, wedges
    assert len(svg.getElementsByTagName("line")) > 20  # Normal bonds

    # Output is non-empty
    assert len(svg_text) > 1000

def test_cairo_capabilities_sheet(tmp_path):
    """Generate PNG capabilities sheet and validate."""
    try:
        import cairo
    except ImportError:
        pytest.skip("pycairo required")

    output = tmp_path / "capabilities.png"
    build_renderer_capabilities_sheet(
        page="letter",
        portrait=True,
        backend="cairo",
        output_path=str(output)
    )

    # Validate file exists and has content
    assert output.exists()
    assert output.stat().st_size > 10000  # Reasonable PNG size
```

### Optional: ops snapshot test
If deterministic ordering and rounding are stable:
```python
def test_capabilities_sheet_ops_snapshot():
    """Regression test for ops output."""
    ops = _build_capabilities_ops(seed=42)
    snapshot = render_ops.ops_to_json_dict(ops, round_digits=2)

    # Compare to golden snapshot
    with open("tests/fixtures/capabilities_ops.json") as f:
        expected = json.load(f)

    assert snapshot == expected
```

## CLI

### Entry point: `oasa_cli.py` (or add to existing CLI)
```python
def cmd_render_selftest(args):
    """Generate renderer capabilities sheet."""
    output = build_renderer_capabilities_sheet(
        page=args.page,
        portrait=args.portrait,
        backend=args.backend,
        seed=args.seed
    )

    if args.backend == "svg":
        with open(args.out, "w") as f:
            f.write(output)
    else:
        # Cairo backend writes directly to file
        pass

    print(f"Wrote capabilities sheet to {args.out}")

    if args.open:
        import subprocess
        subprocess.run(["open", args.out])  # macOS
```

### Usage
```bash
# Generate SVG
oasa_cli.py render-selftest --out capabilities.svg --format svg --page letter

# Generate PNG
oasa_cli.py render-selftest --out capabilities.png --format png --page letter --dpi 300

# Generate PDF
oasa_cli.py render-selftest --out capabilities.pdf --format pdf --page letter

# Open immediately after generation (macOS)
oasa_cli.py render-selftest --out capabilities.svg --format svg --open
```

## Implementation order

### Stage 1: Basic bond grid (SVG only)
- Create `selftest_sheet.py` module
- Implement `build_renderer_capabilities_sheet()` for SVG backend
- Build bond grid: 10 bond types x 5 colors = 50 cells
- Add pytest test that validates SVG structure
- **Deliverable**: Single-page SVG with bond grid

### Stage 2: Add vignettes
- Add `_build_vignette_ops()` function
- Implement 3 vignettes: aromatic ring, stereochemistry, Haworth
- Layout vignettes below grid
- **Deliverable**: Complete SVG with grid + vignettes

### Stage 3: Cairo backend
- Add Cairo support to `build_renderer_capabilities_sheet()`
- Test PNG and PDF generation
- **Deliverable**: PNG/PDF output capability

### Stage 4: CLI wrapper
- Add CLI entry point
- Support `--out`, `--format`, `--page`, `--open` flags
- Document in docs/USAGE.md
- **Deliverable**: Easy-to-use CLI tool

### Stage 5: Polish (optional)
- Add labels to grid (bond type names, color hex codes)
- Add title and footer to page
- Add molecule names to vignettes
- Consider A4 page size support

## Relationship to existing tests

### Leave existing smoke tests alone
- `tests/test_oasa_bond_styles.py` - focused bond style tests
- `tests/test_haworth_layout.py` - Haworth-specific tests
- Other pytest files - unchanged

The capabilities sheet is a **manual inspection artifact** that pytest can also generate.
It's not replacing smoke tests - it's complementing them with a visual reference.

### When to use which
- **Smoke tests**: Fast, focused, run in CI
- **Capabilities sheet**: Comprehensive, visual, generated on demand
- **Ops snapshots**: Regression tests for exact rendering behavior

## Acceptance criteria

- [ ] `selftest_sheet.py` module exists with main generator function
- [ ] SVG backend produces valid SVG at US Letter size (612 x 792)
- [ ] Bond grid shows 10 bond types x 5 colors correctly
- [ ] At least 3 complex molecule vignettes render correctly
- [ ] pytest test validates SVG structure (parseable, correct dimensions)
- [ ] pytest test asserts expected number of primitives exist
- [ ] Cairo backend produces PNG/PDF (optional for Stage 1)
- [ ] CLI wrapper makes generation easy (optional for Stage 1)
- [ ] No duplication - pytest and CLI call same generator function

## Deferred features

### Multiple page sizes
Currently targeting US Letter. Could add A4, legal, etc. later.

### Interactive HTML version
Could generate HTML with CSS for browser viewing. Defer until needed.

### Comparison mode
Generate two sheets side-by-side to compare rendering changes. Defer until needed.

### Color gradient visualization
Show smooth gradients between atom colors. Defer until needed.

## References

### Page sizes
- US Letter: 8.5 x 11 inches = 612 x 792 points (72 DPI)
- A4: 210 x 297 mm = 595 x 842 points (72 DPI)

### SVG page setup
```xml
<svg width="612" height="792" viewBox="0 0 612 792"
     xmlns="http://www.w3.org/2000/svg">
```

### Cairo surfaces
- [cairo.SVGSurface](https://pycairo.readthedocs.io/en/latest/reference/surfaces.html#cairo.SVGSurface)
- [cairo.PDFSurface](https://pycairo.readthedocs.io/en/latest/reference/surfaces.html#cairo.PDFSurface)
- [cairo.ImageSurface](https://pycairo.readthedocs.io/en/latest/reference/surfaces.html#cairo.ImageSurface)
