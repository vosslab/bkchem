# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for BKChem format plugins routed through oasa_bridge."""

# Local repo modules
import conftest
import pytest


conftest.add_bkchem_to_sys_path()

# local repo modules
from bkchem.plugins import CDXML
from bkchem.plugins import CML
from bkchem.plugins import CML2
from bkchem.plugins import plugin


def _write_text(path, text):
	path.write_text(text, encoding="utf-8")
	return str(path)


#============================================
def test_cml_importer_uses_bridge(monkeypatch, tmp_path):
	calls = []

	def _fake_read_cml(file_obj, paper, version=1):
		calls.append((file_obj.read(), paper, version))
		return ["ok"]

	monkeypatch.setattr(CML.oasa_bridge, "read_cml", _fake_read_cml)
	paper = object()
	importer = CML.CML_importer(paper)
	file_name = _write_text(tmp_path / "in.cml", "<cml/>")
	assert importer.get_molecules(file_name) == ["ok"]
	assert calls == [("<cml/>", paper, 1)]


#============================================
def test_cml2_importer_uses_bridge_version_2(monkeypatch, tmp_path):
	calls = []

	def _fake_read_cml(file_obj, paper, version=1):
		calls.append((file_obj.read(), paper, version))
		return ["ok2"]

	monkeypatch.setattr(CML2.oasa_bridge, "read_cml", _fake_read_cml)
	paper = object()
	importer = CML2.CML2_importer(paper)
	file_name = _write_text(tmp_path / "in2.cml", "<cml/>")
	assert importer.get_molecules(file_name) == ["ok2"]
	assert calls == [("<cml/>", paper, 2)]


#============================================
def test_cdxml_importer_uses_bridge(monkeypatch, tmp_path):
	calls = []

	def _fake_read_cdxml(file_obj, paper):
		calls.append((file_obj.read(), paper))
		return ["cdxml"]

	monkeypatch.setattr(CDXML.oasa_bridge, "read_cdxml", _fake_read_cdxml)
	paper = object()
	importer = CDXML.CDXML_importer(paper)
	file_name = _write_text(tmp_path / "in.cdxml", "<CDXML/>")
	assert importer.get_molecules(file_name) == ["cdxml"]
	assert calls == [("<CDXML/>", paper)]


#============================================
def test_cml_exporter_uses_bridge(monkeypatch, tmp_path):
	calls = []

	def _fake_write_cml_from_paper(paper, file_obj, version=1):
		calls.append((paper, version))
		file_obj.write("<cml/>")

	monkeypatch.setattr(CML.oasa_bridge, "write_cml_from_paper", _fake_write_cml_from_paper)
	paper = object()
	exporter = CML.CML_exporter(paper)
	file_name = str(tmp_path / "out.cml")
	exporter.write_to_file(file_name)
	assert calls == [(paper, 1)]
	assert (tmp_path / "out.cml").read_text(encoding="utf-8") == "<cml/>"


#============================================
def test_cml2_exporter_uses_bridge_version_2(monkeypatch, tmp_path):
	calls = []

	def _fake_write_cml_from_paper(paper, file_obj, version=1):
		calls.append((paper, version))
		file_obj.write("<cml2/>")

	monkeypatch.setattr(CML2.oasa_bridge, "write_cml_from_paper", _fake_write_cml_from_paper)
	paper = object()
	exporter = CML2.CML2_exporter(paper)
	file_name = str(tmp_path / "out2.cml")
	exporter.write_to_file(file_name)
	assert calls == [(paper, 2)]
	assert (tmp_path / "out2.cml").read_text(encoding="utf-8") == "<cml2/>"


#============================================
def test_cdxml_exporter_uses_bridge(monkeypatch, tmp_path):
	calls = []

	def _fake_write_cdxml_from_paper(paper, file_obj):
		calls.append(paper)
		file_obj.write("<CDXML/>")

	monkeypatch.setattr(CDXML.oasa_bridge, "write_cdxml_from_paper", _fake_write_cdxml_from_paper)
	paper = object()
	exporter = CDXML.CDXML_exporter(paper)
	file_name = str(tmp_path / "out.cdxml")
	exporter.write_to_file(file_name)
	assert calls == [paper]
	assert (tmp_path / "out.cdxml").read_text(encoding="utf-8") == "<CDXML/>"


#============================================
def test_importer_wraps_bridge_exception(monkeypatch, tmp_path):
	def _boom(*_args, **_kwargs):
		raise RuntimeError("bridge fail")

	monkeypatch.setattr(CML.oasa_bridge, "read_cml", _boom)
	importer = CML.CML_importer(object())
	file_name = _write_text(tmp_path / "bad.cml", "<cml/>")
	with pytest.raises(plugin.import_exception) as error:
		importer.get_molecules(file_name)
	assert "bridge fail" in str(error.value)


#============================================
def test_exporter_wraps_bridge_exception(monkeypatch, tmp_path):
	def _boom(*_args, **_kwargs):
		raise RuntimeError("bridge fail")

	monkeypatch.setattr(CDXML.oasa_bridge, "write_cdxml_from_paper", _boom)
	exporter = CDXML.CDXML_exporter(object())
	file_name = str(tmp_path / "bad.cdxml")
	with pytest.raises(plugin.export_exception) as error:
		exporter.write_to_file(file_name)
	assert "bridge fail" in str(error.value)
