# PubChem API plan

## Goals
- Provide a reliable molecule lookup path that can supply names, identifiers,
  and basic properties for OASA and BKChem workflows.
- Reuse existing PubChem parsing logic from
  `/Users/vosslab/nsh/biology-problems/problems/biochemistry-problems/PUBCHEM/pubchemlib.py`
  when practical.
- Keep the integration lightweight and explicit, without hidden environment
  variables or silent network calls.

## Non-goals
- Do not replace existing OASA core chemistry logic.
- Do not add UI changes in BKChem as part of the first iteration.
- Do not add new dependencies beyond what is already in `pip_requirements.txt`
  unless clearly required.

## Data sources
- Use the PubChem REST API as the authoritative lookup source.
- Seed or validate against the existing local dataset at
  `/Users/vosslab/nsh/biology-problems/data/pubchem_molecules_data.yml`.

## Data model
- Store normalized identifiers: PubChem CID, InChI, InChIKey, SMILES.
- Store a display name and any common synonyms returned by PubChem.
- Store minimal properties needed by BKChem and OASA (for example formula and
  molecular weight), not the full PubChem payload.

## Storage and caching
- Cache responses under `packages/oasa/oasa_data/pubchem_cache/` with one JSON
  file per CID.
- Track a compact index file mapping lookup keys to CIDs for fast reuse.
- Support a configurable cache refresh age (default: never refresh unless
  forced by a user command).

## Interface design
- Add a small `oasa.pubchem` module that exposes `lookup_by_name`,
  `lookup_by_inchi`, and `lookup_by_inchikey`.
- Add a single CLI tool (under `tools/`) that accepts a query, prints a summary,
  and optionally writes cache files.

## Error handling
- Fail fast on network errors with a clear message that includes the query.
- Return `None` for a not-found lookup rather than raising, so callers can
  decide how to proceed.
- Log when a cached response is used versus a network call.

## Rate limits and etiquette
- Respect PubChem usage guidance and avoid tight request loops.
- Use a randomized delay between requests, similar to other network helpers in
  this repo.

## Tests
- Unit tests for parsing and normalization.
- Integration tests that run only when a local cache fixture is available.
- No live network calls in CI tests by default.

## Rollout steps
- Add the `oasa.pubchem` module and a CLI tool.
- Import and adapt `pubchemlib.py` helpers from the biology-problems repo.
- Add cache fixtures and tests.
- Document usage in `docs/USAGE.md` and `packages/oasa/docs/USAGE.md`.
