"""Manually verified substituent labels for all mappable NEUROtiker archive sugars.

Ground truth derived from Fischer projection stereocenter rules and
cross-referenced against NEUROtiker archive SVGs.

Convention: R = OH on Fischer right = OH down in Haworth
            L = OH on Fischer left = OH up in Haworth
            D-series: exocyclic chain goes UP from config carbon
            L-series: exocyclic chain goes DOWN from config carbon
            Furanose with 2-carbon post-closure tail: chain face is
            opposite the closure-carbon OH face (closure stereocenter rule).

For alpha-D: anomeric OH goes DOWN
For beta-D:  anomeric OH goes UP
For alpha-L: anomeric OH goes UP (reversed)
For beta-L:  anomeric OH goes DOWN (reversed)
"""


def _alpha_flip(subs):
	"""Return a copy with the anomeric carbon's up/down swapped (alpha <-> beta)."""
	result = dict(subs)
	# Find anomeric carbon (lowest numbered)
	anomeric_keys = sorted(
		[k for k in result if k.endswith("_up")],
		key=lambda k: int(k.split("_")[0][1:])
	)
	if not anomeric_keys:
		return result
	anomeric = anomeric_keys[0].split("_")[0]  # e.g. "C1"
	up_key = f"{anomeric}_up"
	down_key = f"{anomeric}_down"
	result[up_key], result[down_key] = result[down_key], result[up_key]
	return result


# ============================================================================
# D-ALDOTETROSES (4C) - furanose only (C1-O-C4)
# Ring carbons: C1, C2, C3, C4. No exocyclic chain.
# ============================================================================

_ardm_alpha_fur = {
	# ARDM: C2=R(down), config=D at C3, terminal M at C4
	# Furanose: C1-O-C4, ring = C1,C2,C3,C4
	# C1 anomeric alpha-D: OH down
	"C1_up": "H", "C1_down": "OH",
	# C2: R -> OH down
	"C2_up": "H", "C2_down": "OH",
	# C3: D-config in ring: D = Fischer right = Haworth down
	"C3_up": "H", "C3_down": "OH",
	# C4: terminal M is part of ring closure, no exocyclic
	"C4_up": "H", "C4_down": "H",
}

_aldm_alpha_fur = {
	# ALDM: C2=L(up), config=D at C3
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	# C3: D-config in ring: D = Fischer right = Haworth down
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "H",
}

# ============================================================================
# D-ALDOPENTOSES (5C)
# Furanose: C1-O-C4, ring=C1..C4, exocyclic C5 off C4
# Pyranose: C1-O-C5, ring=C1..C5, no exocyclic
# ============================================================================

_arrdm_alpha_fur = {
	# ARRDM: C2=R(down), C3=R(down), config=D at C4
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	# C4: D-config, exocyclic C5(CH2OH) goes UP
	"C4_up": "CH2OH", "C4_down": "H",
}

_arrdm_alpha_pyr = {
	# Pyranose: C1-O-C5, ring=C1..C5
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	# C4: D-config
	"C4_up": "H", "C4_down": "OH",
	# C5: no exocyclic
	"C5_up": "H", "C5_down": "H",
}

_alrdm_alpha_fur = {
	# ALRDM: C2=L(up), C3=R(down)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "CH2OH", "C4_down": "H",
}

_alrdm_alpha_pyr = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "H", "C5_down": "H",
}

_arldm_alpha_fur = {
	# ARLDM: C2=R(down), C3=L(up)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "CH2OH", "C4_down": "H",
}

_arldm_alpha_pyr = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "H", "C5_down": "H",
}

_alldm_alpha_fur = {
	# ALLDM: C2=L(up), C3=L(up)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "CH2OH", "C4_down": "H",
}

_alldm_alpha_pyr = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "H", "C5_down": "H",
}

# ============================================================================
# D-ALDOHEXOSES (6C)
# Furanose: C1-O-C4, ring=C1..C4, exocyclic C5+C6 off C4
# Pyranose: C1-O-C5, ring=C1..C5, exocyclic C6 off C5
# ============================================================================

_arlrdm_alpha_pyr = {
	# ARLRDM: C2=R(down), C3=L(up), C4=R(down), config=D at C5
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "CH2OH", "C5_down": "H",
}

_arlrdm_alpha_fur = {
	# Furanose: ring C1-C4, C5+C6 off C4
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	# C4: exocyclic chain C5-C6 (D-config: UP direction)
	"C4_up": "CH(OH)CH2OH", "C4_down": "H",
}

_arlldm_alpha_pyr = {
	# ARLLDM: C2=R(down), C3=L(up), C4=L(up)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "CH2OH", "C5_down": "H",
}

_arlldm_alpha_fur = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "CH(OH)CH2OH",
}

_allrdm_alpha_pyr = {
	# ALLRDM: C2=L(up), C3=L(up), C4=R(down)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "CH2OH", "C5_down": "H",
}

_allrdm_alpha_fur = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "CH(OH)CH2OH", "C4_down": "H",
}

_arrrdm_alpha_pyr = {
	# ARRRDM: C2=R(down), C3=R(down), C4=R(down)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "CH2OH", "C5_down": "H",
}

_arrrdm_alpha_fur = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "CH(OH)CH2OH", "C4_down": "H",
}

_alrrdm_alpha_pyr = {
	# ALRRDM: C2=L(up), C3=R(down), C4=R(down)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "CH2OH", "C5_down": "H",
}

_alrrdm_alpha_fur = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "CH(OH)CH2OH", "C4_down": "H",
}

_arrldm_alpha_pyr = {
	# ARRLDM: C2=R(down), C3=R(down), C4=L(up)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "CH2OH", "C5_down": "H",
}

_arrldm_alpha_fur = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "CH(OH)CH2OH",
}

_alrldm_alpha_pyr = {
	# ALRLDM: C2=L(up), C3=R(down), C4=L(up)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "CH2OH", "C5_down": "H",
}

_alrldm_alpha_fur = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "CH(OH)CH2OH",
}

_allldm_alpha_pyr = {
	# ALLLDM: C2=L(up), C3=L(up), C4=L(up)
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "CH2OH", "C5_down": "H",
}

_allldm_alpha_fur = {
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "CH(OH)CH2OH",
}

# ============================================================================
# D-2-KETOPENTOSES (5C) - furanose only (C2-O-C5)
# Ring carbons: C2, C3, C4, C5. Pre-exocyclic: C1 off C2.
# ============================================================================

_mkrdm_alpha_fur = {
	# MKRDM: C3=R(down), config=D at C4
	# Furanose: C2-O-C5, ring=C2..C5, pre-exo C1 off C2, no post-exo
	# Anomeric C2: alpha-D -> OH down, CH2OH (C1) up
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	# C4: D-config in ring: D = Fischer right = Haworth down
	"C4_up": "H", "C4_down": "OH",
}

_mkldm_alpha_fur = {
	# MKLDM: C3=L(up), config=D at C4
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	# C4: D-config in ring
	"C4_up": "H", "C4_down": "OH",
}

# ============================================================================
# D-2-KETOHEXOSES (6C)
# Furanose: C2-O-C5, ring=C2..C5, pre-exo C1 off C2, post-exo C6 off C5
# Pyranose: C2-O-C6, ring=C2..C6, pre-exo C1 off C2, no post-exo
# ============================================================================

_mklrdm_alpha_fur = {
	# MKLRDM: C3=L(up), C4=R(down), config=D at C5
	# Anomeric C2: alpha-D -> OH down, CH2OH (C1) opposite = up
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "OH",
	# C5: D-config, exocyclic C6(CH2OH) up
	"C5_up": "CH2OH", "C5_down": "H",
}

_mklrdm_alpha_pyr = {
	# Pyranose: C2-O-C6, ring=C2..C6
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "H", "C5_down": "OH",
	"C6_up": "H", "C6_down": "H",
}

_mkll_alpha_fur = {
	# MKLLDM: C3=L(up), C4=L(up)
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "CH2OH", "C5_down": "H",
}

_mkll_alpha_pyr = {
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "H", "C5_down": "OH",
	"C6_up": "H", "C6_down": "H",
}

_mkrr_alpha_fur = {
	# MKRRDM: C3=R(down), C4=R(down)
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "CH2OH", "C5_down": "H",
}

_mkrr_alpha_pyr = {
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "OH",
	"C5_up": "H", "C5_down": "OH",
	"C6_up": "H", "C6_down": "H",
}

_mkrldm_alpha_fur = {
	# MKRLDM: C3=R(down), C4=L(up)
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "CH2OH", "C5_down": "H",
}

_mkrldm_alpha_pyr = {
	"C2_up": "CH2OH", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "OH", "C4_down": "H",
	"C5_up": "H", "C5_down": "OH",
	"C6_up": "H", "C6_down": "H",
}


# ============================================================================
# L-SERIES MODIFIED SUGARS - pyranose only
# L-series: alpha -> anomeric OH UP, beta -> anomeric OH DOWN
# ============================================================================

_alrrld_alpha_pyr = {
	# ALRRLd: L-Fucose (6-deoxy-L-galactose)
	# Pyranose: C1-O-C5
	# Alpha-L: anomeric OH goes UP
	"C1_up": "OH", "C1_down": "H",
	"C2_up": "OH", "C2_down": "H",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "H", "C4_down": "OH",
	# C5: 6-deoxy -> CH3 instead of CH2OH, L-config: chain down
	"C5_up": "H", "C5_down": "CH3",
}

_arrlld_alpha_pyr = {
	# ARRLLd: L-Rhamnose (6-deoxy-L-mannose)
	# Alpha-L: anomeric OH goes UP
	"C1_up": "OH", "C1_down": "H",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "H", "C3_down": "OH",
	"C4_up": "OH", "C4_down": "H",
	# C5: 6-deoxy -> CH3, L-config: chain down
	"C5_up": "H", "C5_down": "CH3",
}

# ============================================================================
# URONIC ACID - D-series pyranose only
# ============================================================================

_arlldc_alpha_pyr = {
	# ARLLDc: D-Galacturonic acid
	# Pyranose: C1-O-C5, exocyclic COOH off C5
	# Alpha-D: anomeric OH goes DOWN
	"C1_up": "H", "C1_down": "OH",
	"C2_up": "H", "C2_down": "OH",
	"C3_up": "OH", "C3_down": "H",
	"C4_up": "OH", "C4_down": "H",
	# C5: D-config, exocyclic COOH up
	"C5_up": "COOH", "C5_down": "H",
}

# ============================================================================
# ARCHIVE_GROUND_TRUTH: (sugar_code, ring_type, anomeric) -> substituent dict
# Beta forms are derived by flipping the anomeric carbon's up/down.
# ============================================================================

ARCHIVE_GROUND_TRUTH = {}

_ALPHA_BASES = {
	# Tetroses
	("ARDM", "furanose"): _ardm_alpha_fur,
	("ALDM", "furanose"): _aldm_alpha_fur,
	# Pentoses
	("ARRDM", "furanose"): _arrdm_alpha_fur,
	("ARRDM", "pyranose"): _arrdm_alpha_pyr,
	("ALRDM", "furanose"): _alrdm_alpha_fur,
	("ALRDM", "pyranose"): _alrdm_alpha_pyr,
	("ARLDM", "furanose"): _arldm_alpha_fur,
	("ARLDM", "pyranose"): _arldm_alpha_pyr,
	("ALLDM", "furanose"): _alldm_alpha_fur,
	("ALLDM", "pyranose"): _alldm_alpha_pyr,
	# Hexoses
	("ARRRDM", "furanose"): _arrrdm_alpha_fur,
	("ARRRDM", "pyranose"): _arrrdm_alpha_pyr,
	("ALRRDM", "furanose"): _alrrdm_alpha_fur,
	("ALRRDM", "pyranose"): _alrrdm_alpha_pyr,
	("ARLRDM", "furanose"): _arlrdm_alpha_fur,
	("ARLRDM", "pyranose"): _arlrdm_alpha_pyr,
	("ALLRDM", "furanose"): _allrdm_alpha_fur,
	("ALLRDM", "pyranose"): _allrdm_alpha_pyr,
	("ARRLDM", "furanose"): _arrldm_alpha_fur,
	("ARRLDM", "pyranose"): _arrldm_alpha_pyr,
	("ALRLDM", "furanose"): _alrldm_alpha_fur,
	("ALRLDM", "pyranose"): _alrldm_alpha_pyr,
	("ARLLDM", "furanose"): _arlldm_alpha_fur,
	("ARLLDM", "pyranose"): _arlldm_alpha_pyr,
	("ALLLDM", "furanose"): _allldm_alpha_fur,
	("ALLLDM", "pyranose"): _allldm_alpha_pyr,
	# Ketopentoses
	("MKRDM", "furanose"): _mkrdm_alpha_fur,
	("MKLDM", "furanose"): _mkldm_alpha_fur,
	# Ketohexoses
	("MKLRDM", "furanose"): _mklrdm_alpha_fur,
	("MKLRDM", "pyranose"): _mklrdm_alpha_pyr,
	("MKLLDM", "furanose"): _mkll_alpha_fur,
	("MKLLDM", "pyranose"): _mkll_alpha_pyr,
	("MKRRDM", "furanose"): _mkrr_alpha_fur,
	("MKRRDM", "pyranose"): _mkrr_alpha_pyr,
	("MKRLDM", "furanose"): _mkrldm_alpha_fur,
	("MKRLDM", "pyranose"): _mkrldm_alpha_pyr,
	# L-series modified sugars
	("ALRRLd", "pyranose"): _alrrld_alpha_pyr,
	("ARRLLd", "pyranose"): _arrlld_alpha_pyr,
	# Uronic acid
	("ARLLDc", "pyranose"): _arlldc_alpha_pyr,
}

for (code, ring_type), alpha_subs in _ALPHA_BASES.items():
	ARCHIVE_GROUND_TRUTH[(code, ring_type, "alpha")] = alpha_subs
	ARCHIVE_GROUND_TRUTH[(code, ring_type, "beta")] = _alpha_flip(alpha_subs)
