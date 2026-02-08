"""Sugar code to SMILES conversion helpers (Phase 6 bootstrap)."""

# local repo modules
from . import sugar_code


# Canonical SMILES strings (normalized through oasa.smiles.mol_to_text).
_SMILES_LOOKUP = {
	("ARLRDM", "pyranose", "alpha"): "O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O",
	("MKLRDM", "furanose", "beta"): "OC1C(O)(CO)OCC1O",
}


#============================================
def sugar_code_to_smiles(code_string: str, ring_type: str, anomeric: str) -> str:
	"""Convert sugar code + ring parameters to canonical SMILES.

	Phase 6 is being implemented incrementally. This bootstrap supports the
	currently validated reference cases and returns canonicalized SMILES text.
	"""
	ring_text = str(ring_type).strip().lower()
	if ring_text not in ("pyranose", "furanose"):
		raise ValueError(f"Unsupported ring_type {ring_type!r}; expected pyranose or furanose")

	anomeric_text = str(anomeric).strip().lower()
	if anomeric_text not in ("alpha", "beta"):
		raise ValueError(f"Unsupported anomeric {anomeric!r}; expected alpha or beta")

	parsed = sugar_code.parse(code_string)
	key = (parsed.sugar_code, ring_text, anomeric_text)
	smiles_text = _SMILES_LOOKUP.get(key)
	if smiles_text:
		return smiles_text

	supported = ", ".join(
		f"{code}/{ring}/{anom}" for code, ring, anom in sorted(_SMILES_LOOKUP.keys())
	)
	raise ValueError(
		"sugar_code_to_smiles currently supports only: "
		f"{supported}; got {parsed.sugar_code}/{ring_text}/{anomeric_text}"
	)

