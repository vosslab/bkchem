#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program
#
#--------------------------------------------------------------------------

"""Legacy non-XML bitmap export shim.

Pillow support has been removed from BKChem runtime requirements.
"""

__all__ = ['enabled', 'Bitmap_writer', 'RGB_color']


enabled = 0


def RGB_color(r, g, b):
	"""Convert RGB triple to packed integer."""
	return r * 65536 + g * 256 + b


class Bitmap_writer(object):
	"""Compatibility stub for removed Pillow-backed bitmap export."""

	def __init__( self, paper, mode='RGB'):
		_ = paper
		_ = mode
		raise RuntimeError(
			"Bitmap_writer is no longer available without Pillow; "
			"use Cairo export plugins instead."
		)
