# Sugar Code Specification

## Overview

Sugar codes provide a compact notation for representing carbohydrate structures, including both standard and modified sugars. This specification extends the original sugar code format to support chemical modifications using numeric position markers.

## Basic Format

### Standard Sugar Code

A sugar code consists of:

```
<PREFIX><STEREOCENTERS><CONFIG><TERMINAL>
```

**Components**:

1. **PREFIX** (1-3 characters): Defines the carbonyl type
   - `A` = aldose (aldehyde at C1)
   - `MK` = 2-ketose (ketone at C2, hydroxymethyl at C1)
   - `MRK` or `MLK` = 3-ketose (ketone at C3, stereocenter at C2)

2. **STEREOCENTERS** (0+ characters): Interior chiral carbons
   - `R` = OH on right (in Fischer projection)
   - `L` = OH on left (in Fischer projection)
   - Can be replaced with numeric modifiers (see below)

3. **CONFIG** (1 character): Series configuration
   - `D` = D-series (penultimate carbon has OH on right)
   - `L` = L-series (penultimate carbon has OH on left)

4. **TERMINAL** (1 character): Terminal group
   - `M` = hydroxymethyl (CH₂OH)

### Examples

```
ARRDM   = D-glucose (aldohexose)
ARDM    = D-ribose (aldopentose)
MKDM    = D-fructose (2-ketohexose)
ARLDM   = D-galactose (C4 epimer of glucose)
ALLDM   = L-glucose (enantiomer of D-glucose)
```

## Extended Format: Chemical Modifications

### Footnote-Based Modifiers

Chemical modifications are indicated using numeric footnote markers that must be defined explicitly.

**Format**:
```
<SUGAR_CODE>[<DEFINITIONS>]
```

Where:
- **SUGAR_CODE**: Contains numeric markers (1-9) replacing stereocenter letters
- **DEFINITIONS**: Comma-separated list defining what each number means

**Design Philosophy**:
- Numbers are *variable placeholders*, not pre-assigned meanings
- Each number must be defined in the definitions section
- Same number can represent different modifications in different contexts
- Trades readability for flexibility (similar to SMILES)

**Position Numbering**:
- Positions are numbered sequentially through the sugar code
- Position indices refer to carbon atoms in order from C1 to Cn
- The PREFIX defines C1 (and possibly C2)
- Each subsequent character defines the next carbon

### Position Mapping

For a sugar code, positions map to carbons as follows:

**Aldoses** (`A` prefix):
```
A    R    R    D    M
C1   C2   C3   C4   C5
```

**2-Ketoses** (`MK` prefix):
```
MK   R    D    M
C1   C3   C4   C5
C2   (keto carbon, no stereocenter)
```

**3-Ketoses** (`MRK` or `MLK` prefix):
```
M R  K    D    M
C1 C2 C3  C4   C5
```

### Common Modification Types

While numbers are variable, common modifications include:

| Modification | Description | Example Usage |
|-------------|-------------|---------------|
| deoxy | No oxygen (H replaces OH) | `[1=deoxy]` |
| amino | Amino group (NH₂ replaces OH) | `[2=amino]` |
| acetyl | N-acetyl on amino (NHCOCH₃) | `[3=acetyl]` (requires amino) |
| phosphate | Phosphate group (OPO₃²⁻) | `[4=phosphate]` |
| methyl | Methyl ether (OCH₃) | `[5=methyl]` |
| sulfate | Sulfate group (OSO₃⁻) | `[6=sulfate]` |
| fluoro | Fluorine (F replaces OH) | `[7=fluoro]` |
| carboxyl | Carboxyl (COOH replaces CH₂OH) | `[8=carboxyl]` |

### Examples of Modified Sugars

**Single modifications**:
```
A1DM[1=deoxy]              = 2-deoxy-D-ribose (deoxyribose, DNA)
A1RDM[1=deoxy]             = 2-deoxy-D-glucose
AR1DM[1=deoxy]             = 3-deoxy-D-glucose
A2RDM[2=amino]             = 2-amino-2-deoxy-D-glucose (glucosamine)
ARRD8[8=carboxyl]          = D-glucuronic acid (C6 is COOH)
ARRD4[4=phosphate]         = glucose-6-phosphate
```

### Multiple Modifications

**At different positions**:
```
A23RDM[2=amino, 3=acetyl]  = N-acetyl-glucosamine (GlcNAc)
A1R4DM[1=deoxy, 4=phosphate] = 2-deoxy-glucose-6-phosphate
```

**At the same position** (concatenate numbers):
```
A12DM[1=amino, 2=phosphate]    = 2-amino-2-phospho-D-ribose
A12RDM[1=deoxy, 2=fluoro]      = 2-deoxy-2-fluoro-D-glucose
```

**Rule**: When multiple numbers appear consecutively, they modify the same position. Modifications are applied in the order defined.

## Validation Rules

1. **Prefix**: Must match regex `^(A|MK|M[RL]K)`

2. **Suffix**: Must end in `[DL]M` or `[DL]<modifier>` (for terminal modifications)
   - Exception: Meso compounds (`MKM`, `MRKRM`) have no D/L designation

3. **Configuration letter**: `D` may only appear in penultimate position (immediately before terminal)

4. **Valid characters in sugar code**:
   - Letters: `A`, `M`, `K`, `R`, `L`, `D`
   - Digits: `1`-`9` (footnote markers in stereocenter positions)

5. **Stereocenter positions**: May contain `R`, `L`, or digit sequences

6. **Definitions section**: Required if any numeric markers are used
   - Format: `[<number>=<modification>, ...]`
   - All numbers in the sugar code must be defined

7. **Length**: Minimum 3 characters (`ADM` = D-glyceraldehyde)

## Full Regular Expression

**Sugar code only**:
```regex
^(A|MK|M[RL]K)([RL]|[1-9]+)*[DL](M|[1-9]+)$
```

**With definitions**:
```regex
^(A|MK|M[RL]K)([RL]|[1-9]+)*[DL](M|[1-9]+)\[([1-9]=[a-z]+)(,\s*[1-9]=[a-z]+)*\]$
```

Special cases (meso compounds):
```regex
^(MKM|MRKRM)$
```

## Conversion to Haworth Projection

### Algorithm

1. **Parse sugar code** to extract:
   - Carbonyl type (aldose/ketose)
   - Stereocenter configurations or modifications
   - Terminal group

2. **Determine ring type**:
   - Pyranose: 6-membered ring (5 carbons + 1 oxygen)
   - Furanose: 5-membered ring (4 carbons + 1 oxygen)

3. **Generate substituent dictionary**:
   - For each carbon in the ring, determine up/down substituents
   - `R` → down=H, up=OH (or HO for flipped positions)
   - `L` → down=OH (or HO), up=H
   - `1` (deoxy) → both positions are H
   - `2` (amino) → NH₂ and H
   - `4` (phosphate) → OPO₃²⁻ and H
   - etc.

4. **Apply anomeric configuration**:
   - Alpha/beta determines orientation at C1
   - D-series alpha = OH down, H up
   - D-series beta = OH up, H down
   - L-series reversed

5. **Generate Haworth spec**:
```python
haworth_spec = {
    "ring_type": "pyranose" | "furanose",
    "ring_atoms": [atom_ids],
    "front_edge": [atom_id_1, atom_id_2],
    "anomeric": "alpha" | "beta",
    "substituents": {
        "C1_up": label, "C1_down": label,
        "C2_up": label, "C2_down": label,
        # ... etc
    }
}
```

### Example: Deoxyribose

**Sugar code**: `A1DM`
**Anomeric**: `beta`
**Ring**: furanose

**Parsing**:
- `A` = aldose (C1 has aldehyde → C1 becomes anomeric)
- `1` = C2 is deoxy (no OH)
- `D` = D-series
- `M` = C4 has CH₂OH attached to C5

**Haworth spec**:
```python
{
    "ring_type": "furanose",
    "ring_atoms": ["O4", "C1", "C2", "C3", "C4"],
    "front_edge": ["C2", "C3"],
    "anomeric": "beta",
    "substituents": {
        "C1_up": "OH",      # beta anomer
        "C1_down": "H",
        "C2_up": "H",       # DEOXY
        "C2_down": "H",     # DEOXY
        "C3_up": "H",
        "C3_down": "OH",    # D-series
        "C4_up": "CH2OH",
        "C4_down": "H",
    }
}
```

## Limitations

1. **Non-standard ring sizes**: Oxetose (4-membered) and septanose (7-membered) rings require manual specification

2. **Branched sugars**: Not supported in this notation

3. **Multiple ring forms**: Must specify pyranose vs furanose separately

4. **Anomeric position**: Alpha/beta must be specified as a parameter, not encoded in the sugar code itself

5. **Absolute stereochemistry**: For mixed modifications, complex stereochemistry may require full Haworth spec

## References

- Original sugar code implementation: `/Users/vosslab/nsh/PROBLEM/biology-problems/problems/biochemistry-problems/carbohydrates_classification/sugarlib.py`
- Haworth projection rendering: `packages/oasa/oasa/haworth.py`
- Sugar code data: Biology problems repository `sugar_codes.yml`

## Version History

- v1.0 (2026-02-05): Initial specification with numeric modifier support
