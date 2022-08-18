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

"""Molfile Export plugin.

"""

import sys
try:
  import tkinter.messagebox as tkMessageBox
except ImportError:
  import tkinter.messagebox

from oasa import transform

import oasa_bridge

from . import plugin



class molfile_importer(plugin.importer):
  """Imports a molfile document.

  """
  gives_molecule = 1
  gives_cdml = 0

  doc_string = _("Imports a molfile document.")


  def __init__( self, paper):
    plugin.importer.__init__( self)
    self.paper = paper


  def on_begin( self):
    return 1


  def get_molecules(self, name):
    with open(name, 'r') as f:
      mols = oasa_bridge.read_molfile(f, self.paper)
    [invert_coords(mol) for mol in mols]
    return mols



class molfile_exporter(plugin.exporter):
  """Exports to molfile document.

  """
  doc_string = _("Exports to molfile document.")

  def __init__( self, paper):
    plugin.exporter.__init__( self, paper)


  def on_begin( self):
    conts, u = self.paper.selected_to_unique_top_levels()
    mols = [o for o in conts if o.object_type == 'molecule']
    if not mols:
      tkinter.messagebox.showerror( _("No molecule selected."),
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
    tr = invert_coords(self.molecule)
    oasa_bridge.write_molfile(self.molecule, f)
    invert_coords(self.molecule)
    f.close()



def invert_coords( molecule, tr=None):
  if not tr:
    ys = [a.y for a in molecule.vertices]
    center_y = (max( ys) + min( ys)) / 2.0
    tr = transform.transform()
    tr.set_move( 0, -center_y)
    tr.set_scaling_xy( 1, -1)
    tr.set_move( 0, center_y)

  molecule.transform( tr)
  return tr



name = "Molfile"
extensions = ['.mol']
exporter = molfile_exporter
importer = molfile_importer
local_name = _("Molfile")

if not oasa_bridge.oasa_available:
  del importer
  del exporter
