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

"""Support for exporters resides here.

"""

import sys

import xml_writer
import dom_extensions



def export_CD_SVG(paper, filename, gzipped=0):
  """Export to CD-SVG.

  Return 1 on success, 0 otherwise. Optionally compress with gzip.
  """
  try:
    if gzipped:
      import gzip
      f = gzip.open(filename, "wb")
    else:
      f = open(filename, "wb")
  except IOError as x:
    return 0

  exporter = xml_writer.SVG_writer(paper)
  exporter.construct_dom_tree(paper.top_levels)
  doc = exporter.document
  cdml = paper.get_package().childNodes[0]
  doc.childNodes[0].appendChild(cdml)
  dom_extensions.safe_indent(doc.childNodes[0],
                             dont_indent=("text", "ftext", "user-data"))

  s = doc.toxml('utf-8')
  f.write(s)
  f.close()

  return 1


def export_CDML(paper, filename, gzipped=0):
  """Export to CDML.

  Rreturn 1 on success, 0 otherwise. Optionally compress with gzip.
  """
  try:
    if gzipped:
      import gzip
      f = gzip.open(filename, "wb")
    else:
      f = open(filename, "wb")
  except IOError as x:
    return 0

  doc = paper.get_package()
  dom_extensions.safe_indent(doc.childNodes[0],
                             dont_indent=("text", "ftext", "user-data"))

  s = doc.toxml('utf-8')
  f.write(s)
  f.close()

  return 1

