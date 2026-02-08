# Source and provenance

These SVGs were downloaded from Wikimedia Commons, from User:NEUROtiker gallery archive pages:
- https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive1
- https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive2
- https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive3
- https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive4

Download script:
- `fetch_neurotiker_haworth_archives.py`

Licensing note:
- On Wikimedia Commons, these files are generally treated as public domain because they are considered non-creative factual chemical depictions.

# Notes on the NEUROtiker Haworth SVG archive (reference targets)

The `neurotiker_haworth_archive/` set is a great visual reference, but it is not a perfect target.

0) NEUROtiker SVGs omit explicit hydrogens. Our Haworth renderer supports explicit H labels as an option, but it should stay off by default when we are trying to match NEUROtiker style.

1) Text positioning is better than ours overall, but it still has collisions. For example:
   - `Beta-D-Lyxofuranose.svg` has "OHHO" too close. It should read more like "OH HO".
   - `Alpha-D-Talopyranose.svg` is a useful contrast, since NEUROtiker tends to always use "OH" and not "HO".

2) `Beta-D-Erythrofuranose.svg` shows "OH  OH". Not sure if "HO  OH" would look better.

3) `Amylopektin_Haworth.svg` is next level. This should be a stretch goal for multi-ring layout.

4) `D-Tagatose_Haworth.svg` has many of the collision issues, so it is a good test molecule for font spacing and inner-ring crowding.

5) `D-Psicose_Haworth.svg` is a good test molecule for external label positioning and connector spacing.

6) Stretch goals: disaccharides like sucrose, lactose, maltose, and isomaltose.
   - `Maltose_Haworth.svg`
   - `Lactose_Haworth.svg`

7) Chitin should also be a stretch goal:
   - `Chitin_Haworth.svg`
