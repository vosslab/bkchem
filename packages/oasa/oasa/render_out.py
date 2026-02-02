#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
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
#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program
#--------------------------------------------------------------------------

# Standard Library
import os

# local repo modules
from . import svg_out


#============================================
def _resolve_format(filename, format_override):
	if format_override:
		return format_override.lower()
	extension = os.path.splitext(filename)[1].lower().lstrip(".")
	if extension in ("svg", "png", "pdf"):
		return extension
	raise ValueError(
		"Output format could not be determined; use format=svg|png|pdf or a matching filename."
	)


#============================================
def _apply_svg_options(renderer, options):
	for key, value in options.items():
		if not hasattr(renderer, key):
			raise ValueError(f"Unknown svg_out option: {key}")
		setattr(renderer, key, value)


#============================================
def mol_to_output(mol, filename, format=None, **options):
	"""Render a molecule to SVG or Cairo-backed output using a single entry point."""
	output_format = _resolve_format(filename, format)
	if output_format == "svg":
		renderer = svg_out.svg_out()
		if options:
			_apply_svg_options(renderer, options)
		doc = renderer.mol_to_svg(mol)
		svg_text = svg_out.pretty_print_svg(doc.toxml("utf-8"))
		with open(filename, "w", encoding="utf-8") as handle:
			handle.write(svg_text)
		return filename
	try:
		from . import cairo_out
	except ImportError as exc:
		raise RuntimeError("Cairo output requires pycairo.") from exc
	cairo_out.mol_to_cairo(mol, filename, format=output_format, **options)
	return filename


#============================================
def mols_to_output(mols, filename, format=None, **options):
	"""Render multiple molecules via the merged output entry point."""
	output_format = _resolve_format(filename, format)
	if output_format == "svg":
		raise ValueError("SVG output only supports single-molecule rendering.")
	try:
		from . import cairo_out
	except ImportError as exc:
		raise RuntimeError("Cairo output requires pycairo.") from exc
	cairo_out.mols_to_cairo(mols, filename, format=output_format, **options)
	return filename
