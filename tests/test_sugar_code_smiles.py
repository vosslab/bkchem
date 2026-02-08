"""Unit tests for sugar_code_to_smiles bootstrap conversions."""

# Third Party
import pytest

# Local repo modules
import conftest


conftest.add_oasa_to_sys_path()

import oasa.sugar_code_smiles as sugar_code_smiles


#============================================
def test_glucose_alpha_pyranose_smiles():
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	assert text == "O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O"


#============================================
def test_fructose_beta_furanose_smiles():
	text = sugar_code_smiles.sugar_code_to_smiles("MKLRDM", "furanose", "beta")
	assert text == "OC1C(O)(CO)OCC1O"


#============================================
def test_ring_and_anomeric_case_normalized():
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", " Pyranose ", " Alpha ")
	assert text == "O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O"


#============================================
def test_invalid_ring_type_raises():
	with pytest.raises(ValueError) as error:
		sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "heptanose", "alpha")
	assert "ring_type" in str(error.value)


#============================================
def test_invalid_anomeric_raises():
	with pytest.raises(ValueError) as error:
		sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "gamma")
	assert "anomeric" in str(error.value)


#============================================
def test_unsupported_combo_raises():
	with pytest.raises(ValueError) as error:
		sugar_code_smiles.sugar_code_to_smiles("ARLLDM", "pyranose", "alpha")
	assert "currently supports only" in str(error.value)

