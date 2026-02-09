#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#--------------------------------------------------------------------------

"""CDXML import-export plugin routed through oasa_bridge."""

# Standard Library
import builtins

# local repo modules
import oasa_bridge

from . import plugin

_ = getattr( builtins, "_", None)
if not _:
	def _( text):
		return text
	builtins._ = _


#============================================
class CDXML_importer(plugin.importer):
	"""Imports a CDXML (ChemDraw XML format) document."""

	doc_string = _("Imports a CDXML (ChemDraw XML format) document.")
	gives_molecule = 1
	gives_cdml = 0

	def __init__( self, paper):
		self.paper = paper

	def on_begin( self):
		return 1

	def get_molecules( self, file_name):
		try:
			with open( file_name, "r") as handle:
				return oasa_bridge.read_cdxml( handle, self.paper)
		except Exception as error:
			raise plugin.import_exception( str(error))


#============================================
class CDXML_exporter(plugin.exporter):
	"""Exports a CDXML (ChemDraw XML) document."""

	doc_string = _("Exports a CDXML (ChemDraw XML) document")

	def __init__( self, paper):
		self.paper = paper

	def on_begin( self):
		return 1

	def write_to_file( self, file_name):
		try:
			with open( file_name, "w") as handle:
				oasa_bridge.write_cdxml_from_paper( self.paper, handle)
		except Exception as error:
			raise plugin.export_exception( str(error))


# PLUGIN INTERFACE SPECIFICATION
name = "CDXML"
extensions = [".cdxml", ".xml"]
importer = CDXML_importer
exporter = CDXML_exporter
local_name = _("CDXML")
