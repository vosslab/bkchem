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



import os
import sys
import types
import xml.dom.minidom as dom

import dom_extensions



if sys.version_info[0] > 2:
  str = str


class pref_manager( object):

  def __init__( self, file_names=None):
    self.data = {}
    if file_names:
      for file_name in file_names:
        self.read_pref_file( file_name)


  def add_preference( self, name, value):
    self.data[ name] = value


  def remove_preference( self, name):
    if name in self.data:
      del self.data[ name]


  def get_preference( self, name):
    if name in self.data:
      return self.data[ name]
    else:
      return None


  def has_preference( self, name):
    return name in self.data


  def read_pref_file( self, name):
    if name and os.path.exists( name):
      try:
        doc = dom.parse( name)
      except:
        #print("corrupt preference file %s" % name)
        return
      self.read_from_dom( doc)


  def read_from_dom(self, doc):
    top = doc.getElementsByTagName("bkchem-prefs")[0]
    for child in dom_extensions.childNodesWithoutEmptySpaces(top):
      name = child.nodeName
      itype = child.getAttribute('type') or str

      if itype in ("ListType", "TupleType", "DictType"):
        value = eval(dom_extensions.getAllTextFromElement(child))
      else:
        if itype in ("UnicodeType"):
          itype = str
        else:
          itype = types.__dict__[itype]
        try:
          value = itype(dom_extensions.getAllTextFromElement(child))
        except:
          print("Preference manager: ignoring value %s of type %s"
                % (dom_extensions.getAllTextFromElement(child), itype),)
          break
      self.add_preference(name, value)


  def write_to_dom(self, doc=None):
    if not doc:
      doc = dom.Document()

    top = doc.createElement("bkchem-prefs")
    doc.appendChild(top)

    for k, v in list(self.data.items()):
      itype = 'UnicodeType'
      for tn in types.__dict__:
        if type(v) == types.__dict__[tn]:
          itype = tn
          break
      # Deal with string types explicitly
      if sys.version_info[0] > 2:
        if isinstance(v, bytes):
          v = v.decode('utf-8')
          itype = 'UnicodeType'
        elif isinstance(v, str):
          itype = 'UnicodeType'
      else:
        if isinstance(v, str):
          v = v.decode('utf-8')
          itype = 'UnicodeType'
        elif isinstance(v, str):
          itype = 'UnicodeType'
      el = dom_extensions.textOnlyElementUnder(top, k, v,
                                               attributes = (("type", itype),))
    return doc


  def write_to_file(self, f):
    try:
      s = self.write_to_dom().toxml('utf-8')
      f.write(s)
    except IOError:
      print("Failed to write to the personal preference file.")
