# Sugar Code Specification

## Overview

Sugar codes provide a compact notation for representing carbohydrate structures,
including both standard and modified sugars. This specification extends the original
sugar code format to support chemical modifications using lowercase letter codes
and numeric footnote markers.

**Key rule**: `len(sugar_code) == num_carbons` (triose=3, tetrose=4, pentose=5, hexose=6, heptose=7).

**Source of truth**: `sugar_codes.yml` from the biology-problems repository.

## Basic Format

### Standard Sugar Code

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
   - Can be replaced with lowercase letter codes or numeric footnote modifiers (see below)

3. **CONFIG** (1 character): Series configuration
   - `D` = D-series (penultimate carbon has OH on right)
   - `L` = L-series (penultimate carbon has OH on left)

4. **TERMINAL** (1 character): Terminal group
   - `M` = hydroxymethyl (CH2OH)

### Position Mapping

Each character maps to a carbon. For aldoses (`A` prefix):
```
A      R      L      R      D      M
C1     C2     C3     C4     C5     C6
(CHO)  (OH-R) (OH-L) (OH-R) (D-cfg)(CH2OH)
```

For 2-ketoses (`MK` prefix):
```
M      K      L      R      D      M
C1     C2     C3     C4     C5     C6
(CH2OH)(keto) (OH-L) (OH-R) (D-cfg)(CH2OH)
```

### Examples (from sugar_codes.yml)

**Trioses** (3 carbons):
```
ADM    = D-glyceraldehyde
MKM    = dihydroxyacetone (meso)
```

**Pentoses** (5 carbons):
```
ARRDM  = D-ribose
ALRDM  = D-arabinose
ARLDM  = D-xylose
ALLDM  = D-lyxose
```

**D-aldohexoses** (6 carbons):
```
ARLRDM = D-glucose
ARLLDM = D-galactose
ALLRDM = D-mannose
ARRRDM = D-allose
```

**D-ketohexoses** (6 carbons):
```
MKLRDM = D-fructose
MKRRDM = D-tagatose
MKRLDM = D-sorbose
```

**D-aldoheptoses** (7 carbons):
```
ARLRRDM = D-glycero-D-gluco-heptose
```

## Extended Format: Chemical Modifications

Two systems for modifications: **letter codes** (common, no footnotes needed)
and **numeric footnotes** (rare/custom, must be defined).

### Letter Codes (Common Modifications)

Lowercase letters replace `R` or `L` at stereocenter positions. No footnote
definition needed - the meaning is built into the letter.

| Letter | Modification | Description | Replaces |
|--------|-------------|-------------|----------|
| `d` | deoxy | No oxygen | OH -> H,H |
| `a` | amino | Amino group | OH -> NH2 |
| `n` | N-acetyl | N-acetyl amino group | OH -> NHAc |
| `p` | phosphate | Phosphate group | OH -> OPO3 |
| `f` | fluoro | Fluorine | OH -> F |
| `c` | carboxyl | Carboxyl (terminal) | CH2OH -> COOH |

**Examples using letter codes** (no footnotes needed):
```
AdRDM   = 2-deoxy-D-ribose (deoxyribose, DNA sugar)
AdLRDM  = 2-deoxy-D-glucose
AaLRDM  = glucosamine (2-amino-2-deoxy-D-glucose)
AnLRDM  = N-acetylglucosamine (GlcNAc)
ARLRDc  = D-glucuronic acid (C6 is COOH)
ARLRDp  = glucose-6-phosphate
```

### Numeric Footnotes (Rare/Custom Modifications)

Numbers (`1`-`9`) are *variable placeholders* for modifications not covered
by letter codes. Each number must be defined in a `[...]` section.

**Format**:
```
<SUGAR_CODE>[<DEFINITIONS>]
```

**Examples using numeric footnotes**:
```
A1LRDM[1=methyl]                 2-O-methyl-D-glucose (OCH3)
A1LRD2[1=sulfate, 2=phosphate]   C2 sulfate + C6 phosphate
```

### Mixing Letters and Numbers

Letter codes and numeric footnotes can be combined:
```
AdLRDp  = 2-deoxy-glucose-6-phosphate (all common, no footnotes)
AdLRD1[1=sulfate]   = 2-deoxy-glucose-6-sulfate (deoxy=common, sulfate=rare)
```

### Rules

- Lowercase letters and digits replace `R` or `L` at stereocenter positions
- Lowercase letters and digits also replace `M` at terminal position (`c` for carboxyl, `p` for phosphate, `1` for a custom footnote)
- Each position is exactly one character; for multiple modifications on one carbon, use a numeric footnote with a compound definition (e.g., `1=amino-phosphate`)
- All digits must be defined in `[...]`; letters need no definition
- Letters take priority: if a modification has a letter code, prefer it over a number

## Validation Rules

1. **Prefix**: Must match `^(A|MK|M[RL]K)`
2. **Suffix**: Must end in `[DL]M` or `[DL]<modifier>`
   - Exception: Meso compounds (`MKM`, `MRKRM`)
3. **D** may only appear in penultimate position
4. **Length** = number of carbons in the sugar
5. **Valid stereocenter characters**: `R`, `L`, lowercase letter codes (`d`, `a`, `n`, `p`, `f`, `c`), or digits (`1`-`9`)
6. All numeric footnotes must be defined; letter codes need no definition

## Conversion to Haworth Projection

### Algorithm

1. **Parse sugar code** -> prefix, stereocenters, config, terminal
2. **Determine ring type**: pyranose (6-membered) or furanose (5-membered)
3. **Map stereocenters to substituents**:
   - `R` -> OH down, H up (Fischer right -> Haworth down)
   - `L` -> OH up, H down
   - Modifications replace OH with specified group
4. **Apply anomeric configuration**:
   - D-alpha: anomeric OH down
   - D-beta: anomeric OH up
   - L-series: reversed
5. **Output HaworthSpec** with text labels per position

### Example: alpha-D-Glucopyranose

**Sugar code**: `ARLRDM` + pyranose + alpha

```
C1_up: "H"       C1_down: "OH"     <- alpha: OH down
C2_up: "H"       C2_down: "OH"     <- R: OH down
C3_up: "OH"      C3_down: "H"      <- L: OH up
C4_up: "H"       C4_down: "OH"     <- R: OH down
C5_up: "CH2OH"   C5_down: "H"      <- D-series: CH2OH up
```

### Example: beta-D-2-Deoxyribofuranose

**Sugar code**: `AdRDM` + furanose + beta

```
C1_up: "OH"      C1_down: "H"      <- beta: OH up
C2_up: "H"       C2_down: "H"      <- d (deoxy): both H
C3_up: "H"       C3_down: "OH"     <- R -> OH down (D-series)
C4_up: "CH2OH"   C4_down: "H"      <- terminal CH2OH up
```

## Limitations

1. **Non-standard ring sizes**: Oxetose (4-membered) and septanose (7-membered)
   rings require manual specification
2. **Branched sugars**: Not supported
3. **Multiple ring forms**: Pyranose vs furanose specified separately
4. **Anomeric position**: Alpha/beta is a parameter, not encoded in the sugar code

## References

- Original sugar code system: `sugarlib.py` (biology-problems repo)
- Vetted sugar codes: `sugar_codes.yml` (biology-problems repo)
- Haworth projection layout: `packages/oasa/oasa/haworth.py`
