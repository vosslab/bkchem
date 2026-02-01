# LICENSE_MIGRATION.md

License migration strategy for the BKChem monorepo.

## Summary

This repository is transitioning from GPL-2.0 to a mixed GPL-2.0 / LGPL-3.0-or-later licensing model based on code provenance. The goal is to preserve legal compatibility while making modern renderer and library components available under LGPL for broader reuse.

## Core Principle: Provenance, Not Percentage

**Default rule:**
- All new files are `LGPL-3.0-or-later`
- Any file that contains GPLv2-derived code stays `GPL-2.0`

No percentage tests. No intent tests. Just provenance.

## Mixed Licensing Is Intentional

- **Legacy BKChem and OASA files**: `GPL-2.0`
- **Newly introduced files**: `LGPL-3.0-or-later`
- **Compatibility**: LGPL code can be used by GPL-2.0 code, but not vice versa
- **Architecture alignment**: BKChem depends on OASA, not the other way around

This is a clean, conservative, and future-proof approach that matches how long-lived scientific and GUI projects survive license transitions.

## SPDX Headers Are Required

### New files

Every new file must include an SPDX header at the top:

```python
# SPDX-License-Identifier: LGPL-3.0-or-later
```

For Python files with shebangs, the SPDX header comes after the shebang:

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
```

### Legacy files

Do not touch the license header unless you are certain the file is a clean rewrite.

If a file was edited in place, preserves structure, or obviously evolved from an older implementation, treat it as `GPL-2.0` even if it is heavily modified.

## Conservative Relicensing Policy

A file remains `GPL-2.0` if:
- It was edited in place
- It preserves original structure
- It obviously evolved from an older implementation
- You are uncertain about provenance

A file can be relicensed to `LGPL-3.0-or-later` only if:
- It is a completely new file with no GPLv2-derived code
- It is a full rewrite from scratch with a new implementation
- It is moved to a new path as part of a clean rewrite

**When in doubt, keep it GPL-2.0.**

## Licensing Boundaries

The renderer backend boundary aligns with licensing:

### LGPL-3.0-or-later (reusable library components)
- `packages/oasa/oasa/render_ops.py`
- `packages/oasa/oasa/wedge_geometry.py`
- `packages/oasa/oasa/bond_semantics.py`
- `packages/oasa/oasa/cdml_bond_io.py`
- `packages/oasa/oasa/safe_xml.py`
- `packages/oasa/oasa/atom_colors.py`
- Layout logic: `packages/oasa/oasa/haworth.py`
- Tests for LGPL components
- CLI tooling
- Future renderer utilities

### GPL-2.0 (legacy and GUI-specific code)
- BKChem GUI: `packages/bkchem/bkchem/main.py`
- CDML glue: legacy parts of `packages/oasa/oasa/cdml.py`
- BKChem bond rendering: `packages/bkchem/bkchem/bond.py`
- Legacy IO and external data fetchers
- Plugin system
- Template catalog

This boundary is not strict, but it is a useful guide.

## Compatibility Rules

1. **LGPL code can be used by GPL-2.0 code**
   - BKChem (GPL-2.0) can depend on OASA render ops (LGPL-3.0-or-later)
   - This is safe and legally sound

2. **GPL-2.0 code cannot be relicensed "upward" to LGPL**
   - Legacy code with GPLv2 provenance stays GPL-2.0
   - No exceptions

3. **Third-party code must be compatible**
   - LGPL-3.0-or-later is compatible with GPL-2.0
   - GPL-2.0 is not compatible with proprietary software
   - LGPL-3.0-or-later allows proprietary linking

## Migration Workflow

### Adding a new file
1. Write the file from scratch
2. Add the SPDX header: `# SPDX-License-Identifier: LGPL-3.0-or-later`
3. Commit and document in [docs/CHANGELOG.md](CHANGELOG.md)

### Rewriting an existing file
1. Verify the file is a complete rewrite with no GPLv2-derived code
2. Move to a new path if desired (optional but recommended)
3. Add the SPDX header: `# SPDX-License-Identifier: LGPL-3.0-or-later`
4. Document the rewrite and relicensing in [docs/CHANGELOG.md](CHANGELOG.md)

### Editing an existing file
1. Do not change the license header
2. Keep the file as `GPL-2.0`
3. If the file has no SPDX header, add one: `# SPDX-License-Identifier: GPL-2.0`

## Long-Term Vision

### Phase 1: Establish mixed licensing (current)
- New files are LGPL-3.0-or-later
- Legacy files stay GPL-2.0
- SPDX headers are added to all files

### Phase 2: Expand LGPL components
- Rewrite additional renderer utilities
- Extract layout algorithms into LGPL modules
- Build a clean LGPL rendering API

### Phase 3: Stabilize boundaries
- Document clear GPL/LGPL boundaries in [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)
- Ensure LGPL components are self-contained
- Maintain GPL-2.0 for BKChem GUI and legacy IO

### Long-term outcome
- Modern OASA renderer backend: LGPL-3.0-or-later (reusable by proprietary software)
- BKChem GUI and legacy components: GPL-2.0 (preserves original licensing)
- Clean separation allows future projects to use OASA without GPL constraints

## Legal and Community Considerations

### Why this works
- Provenance-based approach is legally defensible
- No retroactive relicensing of GPLv2 code
- Conservative policy minimizes legal risk
- Mixed licensing is common in long-lived open-source projects

### Preventing future confusion
- Explicit SPDX headers in every file
- This document explains the strategy
- [docs/CHANGELOG.md](CHANGELOG.md) tracks all relicensing decisions
- No "cleanup" PRs that change licenses without provenance review

### Community trust
- Transparent migration process
- Conservative relicensing policy
- No license changes without clear provenance
- Respects original GPL-2.0 contributions

## References

- SPDX License List: https://spdx.org/licenses/
- GPL-2.0: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
- LGPL-3.0: https://www.gnu.org/licenses/lgpl-3.0.html
- GPL Compatibility: https://www.gnu.org/licenses/gpl-faq.html#AllCompatibility

## See Also

- [LICENSE](../LICENSE): Full GPL-2.0 license text (repository default)
- [docs/REPO_STYLE.md](REPO_STYLE.md): Repository licensing rules
- [docs/CHANGELOG.md](CHANGELOG.md): Record of all licensing changes
- [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md): Component boundaries
