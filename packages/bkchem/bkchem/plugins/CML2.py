#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#--------------------------------------------------------------------------

"""CML2 import-export plugin routed through oasa_bridge."""

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
class CML2_importer(plugin.importer):
	"""Import a CML (Chemical Markup Language) document (version 2.0)."""

	doc_string = _(
		"Imports a CML (Chemical Markup Language) document, uses version 2.0 "
		"of the CML standard."
	)
	gives_molecule = 1
	gives_cdml = 0

	def __init__( self, paper):
		self.paper = paper

	def on_begin( self):
		return 1

	def get_molecules( self, file_name):
		try:
			with open( file_name, "r") as handle:
				return oasa_bridge.read_cml( handle, self.paper, version=2)
		except Exception as error:
			raise plugin.import_exception( str(error))


#============================================
class CML2_exporter(plugin.exporter):
	"""Export a CML (Chemical Markup Language) document (version 2.0)."""

	doc_string = _(
		"Exports a CML (Chemical Markup Language) document, uses version 2.0 "
		"of the CML standard."
	)

	def __init__( self, paper):
		self.paper = paper

	def on_begin( self):
		return 1

	def write_to_file( self, file_name):
		try:
			with open( file_name, "w") as handle:
				oasa_bridge.write_cml_from_paper( self.paper, handle, version=2)
		except Exception as error:
			raise plugin.export_exception( str(error))


# PLUGIN INTERFACE SPECIFICATION
name = "CML2"
extensions = [".cml", ".xml"]
importer = CML2_importer
exporter = CML2_exporter
local_name = _("CML2")
