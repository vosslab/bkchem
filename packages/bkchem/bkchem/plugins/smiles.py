#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

"""SMILES export plugin."""

import builtins
import sys
import tkinter.messagebox

import oasa_bridge

from . import plugin

_ = getattr( builtins, "_", None)
if not _:
	def _( text):
		return text
	builtins._ = _

ngettext = getattr( builtins, "ngettext", None)
if not ngettext:
	def ngettext( single, plural, count):
		return single if count == 1 else plural
	builtins.ngettext = ngettext



class smiles_exporter(plugin.exporter):
  """Exports to SMILES format."""
  doc_string = _("Exports to SMILES format.")

  def __init__( self, paper):
    plugin.exporter.__init__( self, paper)


  def on_begin( self):
    conts, u = self.paper.selected_to_unique_top_levels()
    mols = [o for o in conts if o.object_type == 'molecule']
    if not mols:
      tkinter.messagebox.showerror(
        _("No molecule selected."),
        _('You have to select exactly one molecule (any atom or bond will do).'))
      return 0
    elif len( mols) > 1:
      tkinter.messagebox.showerror(
        ngettext("%d molecules selected.",
                 "%d molecules selected.",
                 len(mols)) % len(mols),
        _('You have to select exactly one molecule (any atom or bond will do).'))
      return 0
    else:
      self.molecule = mols[0]
      return 1


  def write_to_file(self, name):
    if sys.version_info[0] > 2:
      if isinstance(name, (bytes, str)):
        f = open(name, 'w')
      else:
        f = name
    else:
      if isinstance(name, str):
        f = open(name, 'w')
      else:
        f = name
    text = oasa_bridge.mol_to_smiles( self.molecule)
    if text and not text.endswith( "\n"):
      text = text + "\n"
    f.write( text or "")
    f.close()



# PLUGIN INTERFACE SPECIFICATION
name = "SMILES"
extensions = [".smi", ".smiles"]
exporter = smiles_exporter
local_name = _("SMILES")
