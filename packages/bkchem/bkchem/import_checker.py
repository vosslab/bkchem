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

"""Check whether all important imports are available.

"""

__all__ = ['PIL_available','Pmw_available','PIL_state','PIL_prefix',
           'oasa_available','python_version_ok','python_version']


Pmw_available = 1
try:
  import Pmw as _Pmw
  Pmw_available = bool( _Pmw) or 1
except ImportError:
  Pmw_available = 0

# Pillow support was removed; keep these names for compatibility.
PIL_available = 0
PIL_state = 'disabled'
PIL_prefix = 0


oasa_available = 1
try:
  import oasa as _oasa
  oasa_available = bool( _oasa) or 1
except ImportError:
  oasa_available = 0


python_version_ok = 1
import sys
if not (sys.version_info[0] > 2 or (sys.version_info[0] == 2 and sys.version_info[1] >= 6)):
  python_version_ok = 0

python_version = "%d.%d.%d" % sys.version_info[0:3]
