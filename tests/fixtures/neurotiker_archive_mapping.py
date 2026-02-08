"""Sugar code to NEUROtiker archive SVG filename mapping."""

ARCHIVE_DIR = "neurotiker_haworth_archive"

# Each entry: sugar_code -> {"name": ..., "ring_forms": {(ring_type, anomeric): filename}}
NEUROTIKER_ARCHIVE_MAP = {
	# === D-aldotetroses (4C) ===
	"ARDM": {
		"name": "D-Erythrose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Erythrofuranose.svg",
			("furanose", "beta"): "Beta-D-Erythrofuranose.svg",
		},
	},
	"ALDM": {
		"name": "D-Threose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Threofuranose.svg",
			("furanose", "beta"): "Beta-D-Threofuranose.svg",
		},
	},
	# === D-aldopentoses (5C) ===
	"ARRDM": {
		"name": "D-Ribose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Ribofuranose.svg",
			("furanose", "beta"): "Beta-D-Ribofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Ribopyranose.svg",
			("pyranose", "beta"): "Beta-D-Ribopyranose.svg",
		},
	},
	"ALRDM": {
		"name": "D-Arabinose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Arabinofuranose.svg",
			("furanose", "beta"): "Beta-D-Arabinofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Arabinopyranose.svg",
			("pyranose", "beta"): "Beta-D-Arabinopyranose.svg",
		},
	},
	"ARLDM": {
		"name": "D-Xylose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Xylofuranose.svg",
			("furanose", "beta"): "Beta-D-Xylofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Xylopyranose.svg",
			("pyranose", "beta"): "Beta-D-Xylopyranose.svg",
		},
	},
	"ALLDM": {
		"name": "D-Lyxose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Lyxofuranose.svg",
			("furanose", "beta"): "Beta-D-Lyxofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Lyxopyranose.svg",
			("pyranose", "beta"): "Beta-D-Lyxopyranose.svg",
		},
	},
	# === D-aldohexoses (6C) ===
	"ARRRDM": {
		"name": "D-Allose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Allofuranose.svg",
			("furanose", "beta"): "Beta-D-Allofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Allopyranose.svg",
			("pyranose", "beta"): "Beta-D-Allopyranose.svg",
		},
	},
	"ALRRDM": {
		"name": "D-Altrose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Altrofuranose.svg",
			("furanose", "beta"): "Beta-D-Altrofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Altropyranose.svg",
			("pyranose", "beta"): "Beta-D-Altropyranose.svg",
		},
	},
	"ARLRDM": {
		"name": "D-Glucose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Glucofuranose.svg",
			("furanose", "beta"): "Beta-D-Glucofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Glucopyranose.svg",
			("pyranose", "beta"): "Beta-D-Glucopyranose.svg",
		},
	},
	"ALLRDM": {
		"name": "D-Mannose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Mannofuranose.svg",
			("furanose", "beta"): "Beta-D-Mannofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Mannopyranose.svg",
			("pyranose", "beta"): "Beta-D-Mannopyranose.svg",
		},
	},
	"ARRLDM": {
		"name": "D-Gulose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Gulofuranose.svg",
			("furanose", "beta"): "Beta-D-Gulofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Gulopyranose.svg",
			("pyranose", "beta"): "Beta-D-Gulopyranose.svg",
		},
	},
	"ALRLDM": {
		"name": "D-Idose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Idofuranose.svg",
			("furanose", "beta"): "Beta-D-Idofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Idopyranose.svg",
			("pyranose", "beta"): "Beta-D-Idopyranose.svg",
		},
	},
	"ARLLDM": {
		"name": "D-Galactose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Galactofuranose.svg",
			("furanose", "beta"): "Beta-D-Galactofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Galactopyranose.svg",
			("pyranose", "beta"): "Beta-D-Galactopyranose.svg",
		},
	},
	"ALLLDM": {
		"name": "D-Talose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Talofuranose.svg",
			("furanose", "beta"): "Beta-D-Talofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Talopyranose.svg",
			("pyranose", "beta"): "Beta-D-Talopyranose.svg",
		},
	},
	# === D-2-ketopentoses (5C) ===
	"MKRDM": {
		"name": "D-Ribulose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Ribulofuranose.svg",
			("furanose", "beta"): "Beta-D-Ribulofuranose.svg",
		},
	},
	"MKLDM": {
		"name": "D-Xylulose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Xylulofuranose.svg",
			("furanose", "beta"): "Beta-D-Xylulofuranose.svg",
		},
	},
	# === D-2-ketohexoses (6C) ===
	"MKLRDM": {
		"name": "D-Fructose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Fructofuranose.svg",
			("furanose", "beta"): "Beta-D-Fructofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Fructopyranose.svg",
			("pyranose", "beta"): "Beta-D-Fructopyranose.svg",
		},
	},
	"MKLLDM": {
		"name": "D-Psicose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Psicofuranose.svg",
			("furanose", "beta"): "Beta-D-Psicofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Psicopyranose.svg",
			("pyranose", "beta"): "Beta-D-Psicopyranose.svg",
		},
	},
	"MKRRDM": {
		"name": "D-Tagatose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Tagatofuranose.svg",
			("furanose", "beta"): "Beta-D-Tagatofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Tagatopyranose.svg",
			("pyranose", "beta"): "Beta-D-Tagatopyranose.svg",
		},
	},
	"MKRLDM": {
		"name": "D-Sorbose",
		"ring_forms": {
			("furanose", "alpha"): "Alpha-D-Sorbofuranose.svg",
			("furanose", "beta"): "Beta-D-Sorbofuranose.svg",
			("pyranose", "alpha"): "Alpha-D-Sorbopyranose.svg",
			("pyranose", "beta"): "Beta-D-Sorbopyranose.svg",
		},
	},
	# === L-series modified sugars ===
	"ALRRLd": {
		"name": "L-Fucose",
		"ring_forms": {
			("pyranose", "alpha"): "Alpha-L-Fucopyranose.svg",
			("pyranose", "beta"): "Beta-L-Fucopyranose.svg",
		},
	},
	"ARRLLd": {
		"name": "L-Rhamnose",
		"ring_forms": {
			("pyranose", "alpha"): "Alpha-L-Rhamnopyranose.svg",
			("pyranose", "beta"): "Beta-L-Rhamnopyranose.svg",
		},
	},
	# === Uronic acid ===
	"ARLLDc": {
		"name": "D-Galacturonic acid",
		"ring_forms": {
			("pyranose", "alpha"): "Alpha-D-Galacturonopyranose.svg",
			("pyranose", "beta"): "Beta-D-Galacturonopyranose.svg",
		},
	},
}

# Filenames not mappable to sugar codes in Phase 0
NOT_MAPPABLE_FILENAMES = [
	"D-Allose_Haworth.svg",
	"D-Altrose_Haworth.svg",
	"D-Arabinose_Haworth.svg",
	"D-Erythrose_Haworth.svg",
	"D-Fructose_Haworth.svg",
	"D-Galactose_Haworth.svg",
	"D-Glucose_Haworth.svg",
	"D-Gulose_Haworth.svg",
	"D-Idose_Haworth.svg",
	"D-Lyxose_Haworth.svg",
	"D-Mannose_Haworth.svg",
	"D-Psicose_Haworth.svg",
	"D-Ribose_Haworth.svg",
	"D-Ribulose_Haworth.svg",
	"D-Sorbose_Haworth.svg",
	"D-Tagatose_Haworth.svg",
	"D-Talose_Haworth.svg",
	"D-Threose_Haworth.svg",
	"D-Xylose_Haworth.svg",
	"D-Xylulose_Haworth.svg",
	"Amylopektin_Haworth.svg",
	"Cellulose_Haworth.svg",
	"Chitin_Haworth.svg",
	"Lactose_Haworth.svg",
	"Maltose_Haworth.svg",
]


def all_mappable_entries():
	"""Yield (sugar_code, ring_type, anomeric, archive_filename, sugar_name)."""
	for code, info in NEUROTIKER_ARCHIVE_MAP.items():
		for (ring_type, anomeric), filename in info["ring_forms"].items():
			yield code, ring_type, anomeric, filename, info["name"]
