#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program

#--------------------------------------------------------------------------




from . import smiles
from . import dom_extensions as dom_ext
from . import safe_xml
from .atom import atom
from .bond import bond
from . import bond_semantics
from . import cdml_bond_io
from .molecule import molecule
from .known_groups import cdml_to_smiles
from .periodic_table import periodic_table as PT
from .coords_generator import calculate_coords



def read_cdml( text):
  """returns the last molecule for now"""
  doc = safe_xml.parse_dom_from_string( text)
  #if doc.childNodes()[0].nodeName == 'svg':
  #  path = "/svg/cdml/molecule"
  #else:
  #  path = "/cdml/molecule"
  path = "//molecule"
  do_not_continue_this_mol = 0
  for mol_el in dom_ext.simpleXPathSearch( doc, path):
    atom_id_remap = {}
    mol = molecule()
    for atom_el in dom_ext.simpleXPathSearch( mol_el, "atom"):
      name = atom_el.getAttribute( 'name')
      if not name:
        #print("this molecule has an invalid symbol")
        do_not_continue_this_mol = 1
        break
      pos = dom_ext.simpleXPathSearch( atom_el, 'point')[0]
      x = cm_to_float_coord( pos.getAttribute('x'))
      y = cm_to_float_coord( pos.getAttribute('y'))
      z = cm_to_float_coord( pos.getAttribute('z'))
      if name in PT:
        # its really an atom
        a = atom( symbol=name,
                  charge=atom_el.getAttribute( 'charge') and int( atom_el.getAttribute( 'charge')) or 0,
                  coords=( x, y, z))
        mol.add_vertex( v=a)
      elif name in cdml_to_smiles:
        # its a known group
        group = smiles.text_to_mol( cdml_to_smiles[ name], calc_coords=0)
        a = group.vertices[0]
        a.x = x
        a.y = y
        a.z = z
        mol.insert_a_graph( group)
      atom_id_remap[ atom_el.getAttribute( 'id')] = a
    if do_not_continue_this_mol:
      break

    for bond_el in dom_ext.simpleXPathSearch( mol_el, "bond"):
      type_value = bond_el.getAttribute( 'type')
      bond_type, order, legacy = bond_semantics.parse_cdml_bond_type( type_value)
      if order == 0:
        # we ignore bonds with order 0
        continue
      if not bond_type:
        bond_type = 'n'
      v1 = atom_id_remap[ bond_el.getAttribute( 'start')]
      v2 = atom_id_remap[ bond_el.getAttribute( 'end')]
      e = bond( order=order, type=bond_type)
      if legacy:
        e.properties_[ 'legacy_bond_type'] = legacy
      cdml_bond_io.read_cdml_bond_attributes(
        bond_el,
        e,
        preserve_attrs={
          'line_width',
          'bond_width',
          'wedge_width',
          'double_ratio',
          'center',
          'auto_sign',
          'equithick',
          'simple_double',
        },
      )
      mol.add_edge( v1, v2, e=e)
      bond_semantics.canonicalize_bond_vertices( e)

    if mol.is_connected():
      # this is here to handle diborane and similar weird things
      yield mol
    else:
      for comp in mol.get_disconnected_subgraphs():
        yield comp


def cm_to_float_coord( x):
  if not x:
    return 0
  if x[-2:] == 'cm':
    return float( x[:-2])*72/2.54
  else:
    return float( x)


##################################################
# MODULE INTERFACE

reads_text = 1
reads_files = 1
writes_text = 0
writes_files = 0

def file_to_mol( f):
  return text_to_mol( f.read())

def text_to_mol( text):
  gen = read_cdml( text)
  try:
    mol = next(gen)
  except StopIteration:
    return None
  calculate_coords( mol, bond_length=-1)
  return mol

#
##################################################


##################################################
# DEMO

if __name__ == '__main__':

  import sys

  if len( sys.argv) < 1:
    print("you must supply a filename")
    sys.exit()

  # parsing of the file

  file_name = sys.argv[1]
  with open(file_name, 'r') as f:
    mol = file_to_mol(f)

  import time

  t = time.time()
  lens = sorted(map(len, mol.get_all_cycles()))
  print(lens)
  print(time.time() - t)
  print("total %d rings" % len( lens))

##     mring = mol.get_new_induced_subgraph( ring, mol.vertex_subgraph_to_edge_subgraph( ring))
##     if not mring.is_connected():
##       print(map( len, [a for a in mring.get_connected_components()]))
##       for vs in mring.get_connected_components():
##         print([a.symbol for a in vs])
      #import molfile
      #print(molfile.mol_to_text( mring))


  #calculate_coords( mol, bond_length=-1)

  #for a in mol.vertices:
  #  print(a.x, a.y)

  print(mol)
  #print(smiles.mol_to_text( mol))
