# Haworth Schematic Renderer - Implementation Plan (Attempt 2)

## Background

Attempt 1 (`docs/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md`) used SMILES to build a
molecular graph, then rendered it through the standard atom/bond pipeline. This worked
for ring geometry (stages 1-3) but failed at stage 4 (substituent placement): OH and H
groups became atom objects with bonds, producing cluttered molecular diagrams instead of
clean Haworth projections.

Attempt 2 bypasses the molecular graph entirely. A custom sugar code string
(see `docs/SUGAR_CODE_SPEC.md`) feeds a schematic renderer that outputs `render_ops`
directly. Substituents are floating text labels, not atoms.

## Scope

This renderer is **schematic-only**. It produces a flat list of `render_ops` (primitive
drawing instructions) for visual output. It does NOT produce:
- Molecule objects (no atoms, bonds, or graph)
- Editable chemical drawings
- CDML-round-trippable data
- Anything that interacts with selection, editing, or molecule-semantic tools

Integration points are limited to contexts where molecule semantics are not required:
- `tools/selftest_sheet.py` vignettes (visual output only)
- Future standalone CLI for Haworth SVG/PNG export

If editable Haworth drawings are ever needed, that would require a separate approach
building on the molecular graph pipeline (see attempt 1 for why that is hard).

## Architecture

```
Sugar Code String          e.g. "ARLRDM" + "alpha" + "pyranose"
       |
  sugar_code.parse()       -> ParsedSugarCode dataclass
       |
  haworth_spec.generate()  -> HaworthSpec dataclass (substituent labels)
       |
  haworth_renderer.render() -> list[render_ops] (LineOp, TextOp, PolygonOp)
       |
  ops_to_svg / ops_to_cairo  (existing infrastructure)
```

No molecular graph. No atom/bond rendering. No `_build_molecule_ops()`.

## Phase 1: Sugar Code Parser

**New file**: `packages/oasa/oasa/sugar_code.py`

```python
@dataclasses.dataclass(frozen=True)
class ParsedSugarCode:
    prefix: str                          # "A", "MK", "MRK", "MLK"
    positions: list[tuple[str, tuple]]   # [("R", ()), ("d", ("deoxy",)), ...]
    config: str                          # "D" or "L"
    terminal: tuple[str, tuple]          # ("M", ()) or ("c", ("carboxyl",))
    footnotes: dict[str, str]            # {"1": "deoxy", ...}
    raw: str                             # original input

def parse(code_string: str) -> ParsedSugarCode
def _extract_footnotes(s: str) -> tuple[str, dict[str, str]]
def _parse_prefix(body: str) -> tuple[str, str]
def _parse_config_and_terminal(remainder: str, footnotes: dict) -> tuple[list, str, tuple]
```

**Key parsing logic**:
- Split `"A1LRDM[1=methyl]"` into body `"A1LRDM"` + footnotes `{"1": "methyl"}`
- Extract prefix by matching `^(A|MK|M[RL]K)`
- Scan remaining characters left-to-right: each character is one carbon position
- Config is always `D` or `L` in the penultimate position
- Terminal is the last character (`M`, or a letter code like `c`/`p`, or a digit)
- Letter codes (`d`, `a`, `n`, `p`, `f`, `c`) are resolved to their built-in meanings
- Digit markers are resolved via the footnotes dict
- Validate: all digits must have definitions; `len(body) == num_carbons`

**Validation matrix** (prefix + ring_type -> minimum carbon count and ring closure):

| Prefix | Ring Type | Min Carbons | Ring Closure | Ring Carbons | Exocyclic |
|--------|-----------|-------------|--------------|--------------|-----------|
| `A` | furanose | 4 (tetrose) | C1-O-C4 | C1,C2,C3,C4 | Cn>4 off C4 |
| `A` | pyranose | 5 (pentose) | C1-O-C5 | C1,C2,C3,C4,C5 | Cn>5 off C5 |
| `MK` | furanose | 5 (pentose) | C2-O-C5 | C2,C3,C4,C5 | C1 off C2, Cn>5 off C5 |
| `MK` | pyranose | 6 (hexose) | C2-O-C6 | C2,C3,C4,C5,C6 | C1 off C2, Cn>6 off C6 |

Sugars larger than the minimum have extra exocyclic carbons. For example, an
aldohexose (6 carbons) + furanose closes C1-O-C4 with C5 and C6 hanging off C4.
This is fully deterministic: one carbonyl = one anomeric center = one possible ring
closure per ring size.

The parser validates `len(body)` matches the sugar's carbon count. The spec generator
validates that the prefix + ring_type combination is in the matrix above and that the
carbon count meets the minimum. Mismatches raise `ValueError` with a descriptive message.

**New test file**: `tests/test_sugar_code.py`
- `test_parse_simple_aldose`: ARLRDM (D-glucose, 6 chars)
- `test_parse_pentose`: ARRDM (D-ribose, 5 chars)
- `test_parse_ketose`: MKLRDM (D-fructose, 6 chars)
- `test_parse_letter_code`: AdRDM (deoxyribose, 5 chars)
- `test_parse_with_footnotes`: A1LRDM[1=methyl] (6 chars)
- `test_parse_mixed`: AdLRD1[1=sulfate] (6 chars, letter + footnote)
- `test_parse_invalid_raises`: missing config, undefined footnotes, wrong length
- `test_parse_prefix_ring_mismatch`: pentose + pyranose aldose raises ValueError

## Phase 2: Haworth Spec Generator

**New file**: `packages/oasa/oasa/haworth_spec.py`

```python
@dataclasses.dataclass(frozen=True)
class HaworthSpec:
    ring_type: str                  # "pyranose" or "furanose"
    anomeric: str                   # "alpha" or "beta"
    config: str                     # "D" or "L"
    substituents: dict[str, str]    # {"C1_up": "OH", "C1_down": "H", ...}
    carbon_count: int               # 5 (pyranose) or 4 (furanose) ring carbons
    title: str                      # "alpha-D-Glucopyranose"

def generate(parsed: ParsedSugarCode, ring_type: str, anomeric: str) -> HaworthSpec
```

### Ring closure rules

The anomeric carbon and ring closure point are determined by prefix + ring type.
One carbonyl = one anomeric center = one possible ring closure per ring size.

| Prefix | Anomeric | Furanose closure | Pyranose closure |
|--------|----------|------------------|------------------|
| `A` | C1 | C1-O-C4 | C1-O-C5 |
| `MK` | C2 | C2-O-C5 | C2-O-C6 |

**General formula**: closure_carbon = anomeric + (ring_members - 2), where
ring_members = 4 (furanose) or 5 (pyranose) carbon atoms in the ring.

### Ring vs exocyclic carbon classification

Given a sugar code with `n` total carbons and a ring closing at Cx:

- **Ring carbons**: anomeric through Cx (inclusive)
- **Pre-anomeric exocyclic**: carbons before the anomeric (for `MK`: C1 hangs off C2)
- **Post-closure exocyclic**: carbons after Cx (Cx+1 through Cn hang off Cx)
- **Exocyclic chain length**: `n - closure_carbon` (post-closure) plus prefix
  exocyclic (1 for `MK`, 0 for `A`)

**Worked examples**:

| Sugar code | Ring type | n | Ring | Pre-exo | Post-exo |
|------------|-----------|---|------|---------|----------|
| ARLRDM (glucose) | pyranose | 6 | C1-C5 | none | C6 off C5 |
| ARLRDM (glucose) | furanose | 6 | C1-C4 | none | C5,C6 off C4 |
| ARRDM (ribose) | furanose | 5 | C1-C4 | none | C5 off C4 |
| ARRDM (ribose) | pyranose | 5 | C1-C5 | none | none |
| ARDM (erythrose) | furanose | 4 | C1-C4 | none | none |
| MKLRDM (fructose) | furanose | 6 | C2-C5 | C1 off C2 | C6 off C5 |
| MKLRDM (fructose) | pyranose | 6 | C2-C6 | C1 off C2 | none |

### Substituent assignment algorithm

For each ring carbon Ci, assign up/down labels:

1. **Anomeric carbon**: OH placed by alpha/beta rule
   - D-alpha -> OH down, H up
   - D-beta -> OH up, H down
   - L-series: reversed
2. **Interior ring stereocenters** (from sugar code R/L or letter codes):
   - `R` -> OH down, H up (Fischer right -> Haworth down)
   - `L` -> OH up, H down
   - `d` -> H down, H up (deoxy: both H)
   - Other letter codes: replace OH with the modification label
3. **Config carbon** (D or L, always penultimate in sugar code):
   - If in the ring: determines which direction the exocyclic chain points
   - D-series: exocyclic chain up; L-series: exocyclic chain down
   - If exocyclic: its own OH follows its R/L equivalent (D=right, L=left)
4. **Post-closure exocyclic chain** (off the last ring carbon):
   - 0 extra carbons: no exocyclic substituent (H on that side)
   - 1 extra carbon with `M` terminal: label = "CH2OH"
   - 1 extra carbon with modifier: label = modifier (e.g., "COOH" for `c`)
   - 2+ extra carbons: label = "CH(OH)CH2OH" or rendered as a mini chain
     (LineOp connectors with intermediate labels; see Phase 3 Step 5)
5. **Pre-anomeric exocyclic** (for `MK` prefix: C1 hangs off anomeric C2):
   - C1 is always CH2OH (from the `M` in `MK`)
   - Placed opposite to the anomeric OH
   - D-alpha: C2_up=OH, C2_down=CH2OH
   - D-beta: C2_up=CH2OH, C2_down=OH
   - **Collision note**: both visible labels are wide text. Renderer should
     increase `sub_length` for carbons where neither label is "H".

**Letter code label mapping**:

| Letter | Modification | Haworth label |
|--------|-------------|---------------|
| `d` | deoxy | H (both up and down) |
| `a` | amino | NH2 |
| `n` | N-acetyl | NHAc |
| `p` | phosphate | OPO3 |
| `f` | fluoro | F |
| `c` | carboxyl | COOH |

**New test file**: `tests/test_haworth_spec.py`

Standard cases:
- `test_glucose_alpha_pyranose`: ARLRDM + pyranose + alpha -> C1_down=OH, C2_down=OH, C3_up=OH, C5_up=CH2OH
- `test_glucose_beta_pyranose`: C1_up=OH (only change from alpha)
- `test_galactose_alpha`: ARLLDM + pyranose -> C4 epimer differs from glucose
- `test_deoxyribose_furanose`: AdRDM + furanose + beta -> C2 both H, C4_up=CH2OH
- `test_fructose_beta_furanose`: MKLRDM + furanose + beta -> C2_up=CH2OH, C2_down=OH
- `test_fructose_alpha_furanose`: MKLRDM + furanose + alpha -> C2_up=OH, C2_down=CH2OH
- `test_fructose_anomeric_both_wide`: verify both C2 labels are non-trivial (not "H")

Ring closure edge cases:
- `test_glucose_furanose`: ARLRDM + furanose -> ring C1-C4, exocyclic C5+C6 off C4
- `test_ribose_pyranose`: ARRDM + pyranose -> ring C1-C5, no exocyclic chain
- `test_erythrose_furanose`: ARDM + furanose -> ring C1-C4, no exocyclic chain
- `test_fructose_pyranose`: MKLRDM + pyranose -> ring C2-C6, C1 off C2, no post-exo

Exocyclic chain length:
- `test_exocyclic_0`: aldopentose pyranose has no exocyclic carbons
- `test_exocyclic_1`: aldohexose pyranose has 1 exocyclic carbon (CH2OH off C5)
- `test_exocyclic_2`: aldohexose furanose has 2 exocyclic carbons (C5+C6 off C4)

## Phase 3: Haworth Schematic Renderer

**New file**: `packages/oasa/oasa/haworth_renderer.py`

```python
def render(spec: HaworthSpec, bond_length: float = 30.0,
           font_size: float = 12.0, font_name: str = "sans-serif",
           show_carbon_numbers: bool = False,
           line_color: str = "#000", label_color: str = "#000",
           bg_color: str = "#fff") -> list
```

Font defaults match `render_ops.TextOp` (font_size=12.0, font_name="sans-serif").
Thickness multipliers are proportional to `bond_length`, not absolute values.
`bg_color` is used for the O-label mask polygon (see Step 4). Callers on non-white
backgrounds should pass their background color to avoid halo artifacts.

### Step 1: Ring coordinates

Reuse templates from `haworth.py`:
```python
from . import haworth
template = haworth.PYRANOSE_TEMPLATE  # or FURANOSE_TEMPLATE
o_index = haworth.PYRANOSE_O_INDEX    # or FURANOSE_O_INDEX
scaled = haworth._ring_template(ring_size, bond_length)
```

### Step 2: Template index to carbon number mapping

Confirmed from HTML templates in biology-problems repo
(`haworth_pyranose_table.html`, `haworth_furanose_table.html`):

```python
PYRANOSE_INDEX_TO_CARBON = {
    0: "C4",   # (-1.25, 0.00)  far left
    1: "C5",   # (-0.45, -0.75) top left
    2: None,   # (0.45, -0.75)  OXYGEN (O_INDEX=2)
    3: "C1",   # (1.25, 0.00)   far right (anomeric)
    4: "C2",   # (0.55, 0.70)   bottom right
    5: "C3",   # (-0.55, 0.70)  bottom left
}

FURANOSE_INDEX_TO_CARBON = {
    0: "C4",   # (-1.05, 0.00)  far left
    1: "C3",   # (-0.55, 0.70)  bottom left
    2: "C2",   # (0.55, 0.70)   bottom right
    3: "C1",   # (1.05, 0.00)   far right (anomeric)
    4: None,   # (0.00, -0.85)  OXYGEN (O_INDEX=4)
}
```

### Step 3: Draw ring edges as filled polygons

Each ring edge is a filled `PolygonOp` (4-point shape), not a line. This matches the
NEUROtiker reference SVGs where every edge is a `<path>` polygon.

**Core geometry**:
```python
def _edge_polygon(p1, p2, thickness_at_p1, thickness_at_p2):
    """Compute a 4-point filled polygon for a ring edge.
    Uniform edges: same thickness at both ends.
    Wedge edges: thickness tapers from thick to thin.
    """
```

**Three edge styles**:

1. **Front edge** (bottommost, e.g. C2-C3 in pyranose): thick uniform polygon
   - `thickness = bond_length * 0.15`

2. **Wedge side edges** (adjacent to front edge): tapered trapezoid
   - Thick end at front vertex: `bond_length * 0.15`
   - Thin end at back vertex: `bond_length * 0.04`

3. **Back edges** (all others): thin uniform polygon
   - `thickness = bond_length * 0.04`

**Edge classification** via explicit template metadata (not inferred from coordinates):

```python
# Front edge index = the edge starting at this vertex index.
# Canonical per template -- stable regardless of coordinate system orientation.
PYRANOSE_FRONT_EDGE_INDEX = 4   # edge from vertex 4 (C2) to vertex 5 (C3)
FURANOSE_FRONT_EDGE_INDEX = 1   # edge from vertex 1 (C3) to vertex 2 (C2)
```

Wedge edges are the two edges adjacent to the front edge (indices +/-1 mod ring_size).
All other edges are back edges. This avoids fragile y-midpoint inference that could
break under coordinate system flips or template rotations.

### Step 4: Place oxygen label

`TextOp("O")` at `coords[o_index]`, bold, dark red. A `PolygonOp` filled with
`bg_color` behind it to mask ring edges at that vertex. Default `bg_color="#fff"`;
callers rendering on transparent or colored backgrounds must pass their background
color to avoid halo artifacts.

### Step 5: Place substituent labels

**Critical design decision**: Substituents are ONLY `TextOp` + `LineOp`. No atoms.
No bonds. No molecular graph objects. Just:
- A short connector `LineOp` from the ring vertex outward
- A `TextOp("OH", x, y)` at the end of the connector

Per-carbon label directions (from HTML template analysis):

```python
PYRANOSE_LABEL_CONFIG = {
    "C1": {"up_dir": (1, -1),  "down_dir": (1, 1),  "anchor": "start"},   # far right
    "C2": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "end"},     # bottom right
    "C3": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "start"},   # bottom left
    "C4": {"up_dir": (-1, -1), "down_dir": (-1, 1), "anchor": "end"},     # far left
    "C5": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "middle"},  # top left
}

FURANOSE_LABEL_CONFIG = {
    "C1": {"up_dir": (1, -1),  "down_dir": (1, 1),  "anchor": "start"},   # far right
    "C2": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "end"},     # bottom right
    "C3": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "start"},   # bottom left
    "C4": {"up_dir": (-1, -1), "down_dir": (-1, 1), "anchor": "end"},     # far left
}
```

Note: furanose has the same spatial positions as pyranose C1-C4. The furanose
config omits C5 because in a furanose the number of ring carbons depends on
the sugar type: aldopentose furanose has C1-C4 in the ring with C5 exocyclic;
aldotetrose furanose has C1-C4 all in the ring with nothing exocyclic.

**Simple substituents** (0 or 1 exocyclic carbons):

For each ring carbon:
1. Look up `spec.substituents["C{n}_up"]` and `spec.substituents["C{n}_down"]`
2. Normalize direction vector, multiply by `sub_length = bond_length * 0.4`
3. Draw `LineOp` connector + `TextOp` label
4. TextOp supports `<sub>` tags for subscripts: `"CH<sub>2</sub>OH"`
5. For bbox measurement, strip HTML tags before computing text width:
   `_visible_text_length("CH<sub>2</sub>OH")` returns `5` (not `20`).
   Implementation: `re.sub(r"<[^>]+>", "", text)` then `len(result)`
6. For carbons where both labels are non-trivial (neither is "H"), increase
   `sub_length` by 1.5x to avoid label collision

**Multi-carbon exocyclic chains** (2+ exocyclic carbons, e.g. aldohexose furanose):

When the post-closure exocyclic chain has 2+ carbons (e.g. C5-C6 off C4 in
aldohexose furanose), render as a mini chain of connectors and labels extending
from the last ring carbon:

```
Ring-C4 ---LineOp---> "CHOH" ---LineOp---> "CH2OH"
          (sub_length)         (sub_length)
```

Each segment uses the same direction vector as the parent carbon's up/down
direction. The intermediate carbon's stereochemistry (R/L at the config position)
determines whether its OH label goes left or right of the chain. This is the
same connector+text approach used for simple substituents, just chained.

### Step 6: Optional carbon numbers

Small `TextOp` labels (font_size * 0.65) placed between vertex and ring center.

### Concrete example: alpha-D-Glucopyranose

Input: `sugar_code.parse("ARLRDM")` + pyranose + alpha

```
C1_up: "H"       C1_down: "OH"     <- alpha: OH down
C2_up: "H"       C2_down: "OH"     <- R: OH down
C3_up: "OH"      C3_down: "H"      <- L: OH up
C4_up: "H"       C4_down: "OH"     <- R: OH down
C5_up: "CH2OH"   C5_down: "H"      <- D-series: CH2OH up
```

Output: ~28 primitive render_ops (PolygonOp for ring edges + O mask, TextOp for labels,
LineOp for connectors). Zero molecule/atom/bond objects.

**New test file**: `tests/test_haworth_renderer.py`
- `test_render_returns_ops`: non-empty list
- `test_render_contains_text_ops`: has O, OH, H labels
- `test_render_contains_polygon_ops`: ring edge count
- `test_render_bbox_reasonable`: bounding box within expected range
- `test_render_furanose`: 5-member ring works
- `test_render_with_carbon_numbers`: adds number labels
- `test_render_aldohexose_furanose`: ARLRDM + furanose renders multi-carbon chain off C4
- `test_render_ribose_pyranose`: ARRDM + pyranose has no exocyclic chain
- `test_render_erythrose_furanose`: ARDM + furanose has no exocyclic chain
- `test_render_front_edge_stable`: verify front edge index matches template metadata
- `test_render_furanose_labels`: furanose label directions match FURANOSE_LABEL_CONFIG
- `test_render_bbox_sub_tags`: bbox for "CH<sub>2</sub>OH" matches visible width (5 chars)
- `test_render_fructose_anomeric_no_overlap`: both wide labels on C2 don't collide

## Phase 4: Integration

**Modify**: `tools/selftest_sheet.py`

Replace `_build_alpha_d_glucopyranose_ops()` and `_build_beta_d_fructofuranose_ops()`:

```python
def _build_alpha_d_glucopyranose_ops():
    parsed = sugar_code.parse("ARLRDM")
    spec = haworth_spec.generate(parsed, ring_type="pyranose", anomeric="alpha")
    return haworth_renderer.render(spec, bond_length=30)

def _build_beta_d_fructofuranose_ops():
    parsed = sugar_code.parse("MKLRDM")
    spec = haworth_spec.generate(parsed, ring_type="furanose", anomeric="beta")
    return haworth_renderer.render(spec, bond_length=30)
```

Remove dead code: `_build_alpha_d_glucopyranose_mol()`,
`_build_beta_d_fructofuranose_mol()`, `_add_explicit_h_to_haworth()`.

**Modify**: `packages/oasa/oasa/__init__.py`

Register new modules in imports and `_EXPORTED_MODULES`.

## Phase 5: Verify

- `python -m pytest tests/test_sugar_code.py -v`
- `python -m pytest tests/test_haworth_spec.py -v`
- `python -m pytest tests/test_haworth_renderer.py -v`
- `python tools/selftest_sheet.py --format svg` -> visually inspect output
- `python -m pytest tests/` -> full regression (existing tests still pass)

## Phase 6: Sugar Code to SMILES

**New file**: `packages/oasa/oasa/sugar_code_smiles.py`

```python
def sugar_code_to_smiles(code_string: str, ring_type: str, anomeric: str) -> str
    """Convert a sugar code + ring parameters to a SMILES string.

    Example:
        sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
        -> "OC[C@@H]1OC(O)[C@@H](O)[C@H](O)[C@@H]1O"
    """
```

**Approach**: Build the open-chain carbon skeleton from the sugar code, then apply ring
closure. The stereochemistry mapping (Fischer R/L to SMILES `@`/`@@`) is a fixed lookup
per carbon position because CIP priorities follow a predictable pattern along the sugar
chain.

**Steps**:
1. Parse sugar code to get prefix, stereocenters, config, terminal
2. Build open-chain: C1-C2-...-Cn with correct substituents at each position
3. Map Fischer R/L to CIP R/S at each stereocenter using a position-specific table:
   - For aldohexose: C2(R->@@, L->@), C3(R->@, L->@@), C4(R->@@, L->@), C5(D->@@, L->@)
   - For other sugar types: derive from the substituent priority ordering
4. Apply ring closure (pyranose: C1-O-C5, furanose: C1-O-C4 or C2-O-C5)
5. Set anomeric stereochemistry (alpha/beta)
6. Handle modifications: deoxy removes OH, amino replaces OH with NH2, etc.
7. Return canonical SMILES via OASA's `smiles.get_smiles()` for normalization

**Fischer-to-CIP lookup table** (for D-aldohexoses):

The CIP assignment at each carbon depends on substituent priorities. For standard
aldohexose carbons in pyranose ring form, this is deterministic because the chain
direction and ring oxygen create fixed priority orderings.

**New tests** in `tests/test_sugar_code_smiles.py`:
- `test_glucose_smiles`: ARLRDM + pyranose + alpha -> known glucose SMILES
- `test_galactose_smiles`: ARLLDM -> known galactose SMILES (C4 epimer)
- `test_ribose_smiles`: ARRDM + furanose + beta -> known ribose SMILES
- `test_fructose_smiles`: MKLRDM + furanose + beta -> known fructose SMILES
- `test_deoxyribose_smiles`: AdRDM + furanose + beta -> known deoxyribose SMILES
- `test_round_trip`: sugar code -> SMILES -> (Phase 7) -> sugar code matches original

## Phase 7: SMILES to Sugar Code (Best-Effort)

**New file**: `packages/oasa/oasa/smiles_to_sugar_code.py`

```python
class SugarCodeResult:
    sugar_code: str          # e.g. "ARLRDM"
    ring_type: str           # "pyranose" or "furanose"
    anomeric: str            # "alpha" or "beta"
    name: str                # "D-glucose" (if known)
    confidence: str          # "exact_match", "inferred", "unsupported"

def smiles_to_sugar_code(smiles_string: str) -> SugarCodeResult
```

**Two-tier approach**:

### Tier 1: Lookup table (high confidence)

Build a canonical SMILES lookup table from `sugar_codes.yml` at module load time.
For each entry in the YAML, generate all ring forms (pyranose alpha, pyranose beta,
furanose alpha, furanose beta) using Phase 6's `sugar_code_to_smiles()`, canonicalize
via OASA, and store the mapping.

```python
# Built at module load from sugar_codes.yml
_CANONICAL_LOOKUP = {
    "OC[C@@H]1OC(O)...": SugarCodeResult("ARLRDM", "pyranose", "alpha", "D-glucose", "exact_match"),
    ...
}
```

Input SMILES is canonicalized, then looked up. If found, return with
`confidence="exact_match"`.

### Tier 2: Structural inference (best-effort)

If no exact match, attempt to identify the sugar skeleton:

1. Parse SMILES to molecular graph via `oasa.smiles.read_smiles()`
2. Find the ring oxygen using `mol.get_smallest_independent_cycles()`:
   - Look for a 5-member or 6-member ring containing exactly one oxygen
3. Number ring carbons starting from the anomeric carbon (adjacent to ring O)
4. Determine ring type from ring size (6-member = pyranose, 5-member = furanose)
5. For each ring carbon, check substituents:
   - OH -> R or L (determine by CIP-to-Fischer reverse mapping)
   - H,H (no oxygen) -> `d` (deoxy)
   - NH2 -> `a` (amino)
   - NHAc -> `n` (N-acetyl)
   - F -> `f` (fluoro)
6. Determine D/L from penultimate carbon stereochemistry
7. Determine alpha/beta from anomeric carbon stereochemistry
8. Build sugar code string and return with `confidence="inferred"`

### Graceful failure

If the input cannot be recognized as a monosaccharide (no suitable ring, multiple
rings, unrecognized substituents), return a clear error:

```python
raise SugarCodeError(
    "The input SMILES is not compatible with the sugar code converter.\n"
    "Supported inputs are monosaccharides with a single pyranose or furanose ring.\n"
    "\n"
    "Examples of supported SMILES:\n"
    "  OC[C@@H]1OC(O)[C@@H](O)[C@H](O)[C@@H]1O   (alpha-D-glucopyranose)\n"
    "  OC[C@H]1OC(O)[C@@H](O)[C@@H]1O              (beta-D-ribofuranose)\n"
    "  OC[C@@H]1OC(O)(CO)[C@H](O)[C@@H]1O          (beta-D-fructofuranose)\n"
)
```

**New tests** in `tests/test_smiles_to_sugar_code.py`:
- `test_glucose_from_smiles`: known glucose SMILES -> ARLRDM + pyranose
- `test_galactose_from_smiles`: known galactose SMILES -> ARLLDM
- `test_deoxyribose_from_smiles`: known deoxyribose SMILES -> AdRDM + furanose
- `test_fructose_from_smiles`: known fructose SMILES -> MKLRDM + furanose
- `test_round_trip_all_common`: all entries from sugar_codes.yml round-trip
- `test_unsupported_smiles_error`: benzene, ethanol, disaccharides -> SugarCodeError
- `test_error_message_has_examples`: error message contains example SMILES

## Key Files

| Action | Phase | File |
|--------|-------|------|
| Create | 1 | `packages/oasa/oasa/sugar_code.py` |
| Create | 2 | `packages/oasa/oasa/haworth_spec.py` |
| Create | 3 | `packages/oasa/oasa/haworth_renderer.py` |
| Create | 6 | `packages/oasa/oasa/sugar_code_smiles.py` |
| Create | 7 | `packages/oasa/oasa/smiles_to_sugar_code.py` |
| Create | 1 | `tests/test_sugar_code.py` |
| Create | 2 | `tests/test_haworth_spec.py` |
| Create | 3 | `tests/test_haworth_renderer.py` |
| Create | 6 | `tests/test_sugar_code_smiles.py` |
| Create | 7 | `tests/test_smiles_to_sugar_code.py` |
| Modify | 4 | `tools/selftest_sheet.py` |
| Modify | 4 | `packages/oasa/oasa/__init__.py` |

**Reference files** (read-only):
- `packages/oasa/oasa/haworth.py` - ring templates and O_INDEX constants
- `packages/oasa/oasa/render_ops.py` - LineOp, TextOp, PolygonOp dataclasses
- `packages/oasa/oasa/render_geometry.py` - `haworth_front_edge_ops()`
- `packages/oasa/oasa/smiles.py` - SMILES parser/writer (Phase 6-7)
- `packages/oasa/oasa/stereochemistry.py` - CIP R/S handling (Phase 6-7)
- `docs/SUGAR_CODE_SPEC.md` - format specification
- `docs/sample_haworth/*.svg` - NEUROtiker reference renderings

## Review Response Log

Findings from code review and how each was addressed:

| ID | Finding | Resolution |
|----|---------|------------|
| P1a | Schematic-only scope not stated | Added "Scope" section: no molecules, no CDML, no editing. Integration limited to selftest vignettes and standalone CLI. |
| P1b | Front-edge detection by y-midpoint is fragile | Replaced with explicit `PYRANOSE_FRONT_EDGE_INDEX` / `FURANOSE_FRONT_EDGE_INDEX` template metadata. Added `test_render_front_edge_stable`. |
| P2a | Ketose 3-substituent anomeric underspecified | Clarified: only 2 visible labels (OH + CH2OH), H is implicit. Added collision avoidance note and `test_fructose_anomeric_no_overlap`. |
| P2b | Hard-coded Arial font | Changed defaults to match `render_ops.TextOp` (sans-serif, 12.0). All style params are caller-configurable. |
| P2c | White O-mask assumes white background | Added `bg_color` parameter (default "#fff") to `render()`. Documented that callers must pass their background color. |
| P3a | Missing FURANOSE_LABEL_CONFIG | Added explicit config. Same spatial directions as pyranose C1-C4, omits C5 (exocyclic). Added `test_render_furanose_labels`. |
| P3b | `<sub>` tag bbox inflation | Added `_visible_text_length()` with `re.sub(r"<[^>]+>", "", text)`. Added `test_render_bbox_sub_tags`. |
| P3c | num_carbons validation undefined | Added validation matrix (prefix + ring_type -> expected carbon count). Added `test_parse_prefix_ring_mismatch`. |
| R2-P1a | Plan hardcodes "terminal M = CH2OH at C5" | Replaced with general ring-closure rule table and exocyclic chain derivation algorithm. Ring vs exocyclic is computed from num_carbons + ring type, not hardcoded. |
| R2-P1b | Furanose aldohexose ring closure not specified | Added explicit ring-closure rules: aldose furanose = C1-O-C4, aldose pyranose = C1-O-C5, etc. Worked examples table covers all combinations. |
| R2-P2a | Ketose anomeric 3-substituent placement rule missing | Added deterministic rule: C1 CH2OH placed opposite to anomeric OH based on alpha/beta. Collision avoidance via increased sub_length. |
| R2-P2b | num_carbons not tied to ring type for exocyclic chain | Added "ring vs exocyclic carbon classification" algorithm deriving post-closure and pre-anomeric exocyclic chains from num_carbons and closure carbon. |
| R2-new | Multi-carbon exocyclic chains (2+) not handled | Added rendering rule: chain of LineOp+TextOp connectors extending from last ring carbon. Tests for aldohexose furanose, ribose pyranose, erythrose furanose. |

## Related Documents

- `docs/SUGAR_CODE_SPEC.md` - sugar code format specification
- `docs/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md` - previous attempt (SMILES-based)
