# Plan: Surface Per-Label Alignment Metrics in Reports

## Context

The measurement tool (`tools/measure_glyph_bond_alignment.py`) already computes two
key per-label metrics buried in the JSON report, but does not aggregate or display
them in the text report or console output:

1. **Bond-end-to-glyph-body gap distance** (`endpoint_gap_distance_to_glyph_body`) --
   the whitespace gap between the nearest bond endpoint and the glyph body boundary.
   Measures spacing consistency.
2. **Perpendicular distance to alignment center**
   (`endpoint_perpendicular_distance_to_alignment_center`) -- how far the glyph's
   optical center is from the infinite extension of the bond line. Measures whether
   the bond "points at" the glyph.

Current state: 78 SVGs, 362 labels, 83.7% alignment rate (303/362). The per-label
data exists in `alignment_by_glyph` in the JSON debug section but is excluded from
the compact summary and absent from the text report and console output.

Builds on: `docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md` (Phase 4 complete).

## File Modified

- `tools/measure_glyph_bond_alignment.py`

## Changes

### 1. Compute per-label-type stats in `_summary_stats()` (~line 3654)

Inside the existing `for glyph_text in sorted(alignment_by_glyph_measurements.keys()):`
loop, the code already collects `glyph_body_gap_distances` (line ~3671). Add:

- Collect `perpendicular_distances` list from each measurement's
  `perpendicular_distance_to_alignment_center` field (line ~3458).
- Apply `_length_stats()` to both lists.
- Store results in `alignment_by_glyph[glyph_text]` as:
  - `"gap_distance_stats"`: `_length_stats(glyph_body_gap_distances)`
  - `"perpendicular_distance_stats"`: `_length_stats(perpendicular_distances)`

### 2. Add `alignment_label_type_stats` to compact summary

Create a new top-level summary key `alignment_label_type_stats` containing a
dict mapping label text to `{count, aligned_count, alignment_rate,
gap_distance_stats, perpendicular_distance_stats}`. This is a compact subset
of `alignment_by_glyph` (without the per-measurement arrays).

Ensure this key is NOT in `_JSON_SUMMARY_EXCLUDE_KEYS` so it appears in the
compact JSON summary.

### 3. Add per-label-type table to `_text_report()` (~line 4005)

Insert a new banner section between ALIGNMENT SUMMARY and GEOMETRY CHECKS:

```
========================================================
 PER-LABEL ALIGNMENT STATISTICS
========================================================
Label    Count  Aligned  Rate     Gap(mean/sd)     Perp(mean/sd)
OH         152      133  87.5%    15.42 / 2.75      2.14 / 4.67
HO         136      111  81.6%    14.16 / 1.63      2.88 / 5.17
CH2OH       68       57  83.8%    18.00 / 4.99      3.50 / 7.92
CH3          4        0   0.0%     9.48 / 0.24      1.15 / 0.00
COOH         2        2 100.0%    14.53 / 0.00      0.64 / 0.00
```

Data source: `summary["alignment_label_type_stats"]` from step 2.

Use f-string column formatting for alignment. Show `(none)` for label types
with no measurements.

### 4. Add per-label-type table to console output in `main()` (~line 4280)

After the "Top misses:" section and before the `fail_on_miss` check, print
the same table (or a more compact 1-line-per-label version).

### 5. Add to `violation_summary` in JSON report

Include `alignment_label_type_stats` in the `_violation_summary()` output
(line ~3933) so it appears at the top level of the JSON report alongside
existing violation data.

## What This Does NOT Change

- No rendering code changes (separate plan)
- No tolerance recalibration
- No new metrics computed -- all data already exists per-label
- The `alignment_by_glyph` detailed array stays in debug section only

## Verification

```bash
# Pyflakes lint
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -x -q

# Run measurement tool -- verify new tables appear
source source_me.sh && python3 tools/measure_glyph_bond_alignment.py \
    -i "output_smoke/archive_matrix_previews/generated/*.svg"

# Check JSON report has new key
python3 -c "import json; r=json.load(open('output_smoke/glyph_bond_alignment_report.json')); print(sorted(r['summary'].get('alignment_label_type_stats', {}).keys()))"

# Verify text report has new section
grep -A 10 'PER-LABEL' output_smoke/glyph_bond_alignment_report.txt

# Full test suite
source source_me.sh && python3 -m pytest tests/ -x -q
```
