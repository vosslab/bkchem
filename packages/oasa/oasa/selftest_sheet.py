#!/usr/bin/env python3
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
#
#--------------------------------------------------------------------------

"""Renderer capabilities sheet generator.

Generates a single-page visual reference showing all OASA rendering capabilities:
- Bond types (normal, bold, wedge, hatch, wavy, etc.)
- Colors (per-bond colors)
- Complex features (aromatic rings, stereochemistry, Haworth projections)

Usage:
	# As library
	svg_text = build_renderer_capabilities_sheet()
	with open("capabilities.svg", "w") as f:
		f.write(svg_text)

	# From command line (default: PDF output)
	python selftest_sheet.py
	python selftest_sheet.py --format svg --out capabilities.svg
	python selftest_sheet.py --format png --out capabilities.png
"""

# Standard Library
import math
import os
import sys

# Handle imports for both module and script usage
if __name__ == "__main__":
	# When run as script: python selftest_sheet.py
	# Add packages directory to path so we can import oasa
	packages_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	if packages_dir not in sys.path:
		sys.path.insert(0, packages_dir)
	# Import the oasa package - classes are exported directly
	import oasa
	# Create aliases that work like modules with classes
	class _AtomModule:
		atom = oasa.atom
	class _BondModule:
		bond = oasa.bond
	class _MoleculeModule:
		molecule = oasa.molecule
	atom = _AtomModule
	bond_module = _BondModule
	molecule = _MoleculeModule
	dom_extensions = oasa.dom_extensions
	render_ops = oasa.render_ops
	haworth = oasa.haworth
else:
	# When used as module: from oasa import selftest_sheet
	from . import atom
	from . import bond as bond_module
	from . import dom_extensions
	from . import molecule
	from . import render_ops
	from . import haworth

try:
	import xml.dom.minidom as dom
except ImportError:
	import defusedxml.minidom as dom


#============================================
# Page dimensions at 72 DPI
PAGE_SIZES = {
	"letter": (612, 792),  # 8.5 x 11 inches
	"a4": (595, 842),      # 210 x 297 mm
}


#============================================
def get_page_dims(page, portrait):
	"""Get page dimensions in points.

	Args:
		page: "letter" or "a4"
		portrait: True for portrait, False for landscape

	Returns:
		(width, height) in points
	"""
	w, h = PAGE_SIZES.get(page, PAGE_SIZES["letter"])
	if not portrait:
		w, h = h, w
	return w, h


#============================================
def build_renderer_capabilities_sheet(page="letter", backend="svg", seed=0, output_path=None, cairo_format="png"):
	"""Build a capabilities sheet showing all rendering features.

	Args:
		page: Page size ("letter", "a4") - always portrait orientation
		backend: "svg" or "cairo"
		seed: Random seed for reproducible molecule generation (not used yet)
		output_path: Output file path (required for cairo backend)
		cairo_format: Format for cairo backend ("png" or "pdf")

	Returns:
		SVG text (str) for SVG backend
		None for cairo backend (writes directly to output_path)
	"""
	if backend == "cairo":
		if output_path is None:
			raise ValueError("output_path is required for cairo backend")
		try:
			import cairo
		except ImportError:
			raise ImportError("pycairo is required for cairo backend. Install with: pip install pycairo")

	if backend not in ("svg", "cairo"):
		raise ValueError(f"Unknown backend: {backend}. Must be 'svg' or 'cairo'")

	width, height = get_page_dims(page, portrait=True)

	if backend == "svg":
		# SVG backend - build DOM tree
		doc = dom.Document()
		svg = dom_extensions.elementUnder(
			doc,
			"svg",
			attributes=(
				("xmlns", "http://www.w3.org/2000/svg"),
				("version", "1.1"),
				("width", str(width)),
				("height", str(height)),
				("viewBox", f"0 0 {width} {height}"),
			)
		)

		# Add title
		title_g = dom_extensions.elementUnder(svg, "g", attributes=(("id", "title"),))
		_add_text(
			title_g,
			width / 2,
			30,
			"OASA Renderer Capabilities",
			font_size=20,
			anchor="middle",
			weight="bold",
		)

		# Section A: Bond grid
		grid_g = dom_extensions.elementUnder(svg, "g", attributes=(("id", "bond-grid"),))
		_build_bond_grid(grid_g)

		# Section B: Vignettes
		vignettes_g = dom_extensions.elementUnder(svg, "g", attributes=(("id", "vignettes"),))
		_build_vignettes(vignettes_g)

		# Footer
		footer_g = dom_extensions.elementUnder(svg, "g", attributes=(("id", "footer"),))
		_add_text(
			footer_g,
			width / 2,
			height - 20,
			"Generated by OASA selftest_sheet.py",
			font_size=10,
			anchor="middle",
			fill="#666",
		)

		return doc.toxml("utf-8").decode("utf-8")

	elif backend == "cairo":
		# Cairo backend - render directly to file
		import cairo

		# Create appropriate surface
		if cairo_format == "png":
			surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
		elif cairo_format == "pdf":
			surface = cairo.PDFSurface(output_path, width, height)
		elif cairo_format == "svg":
			surface = cairo.SVGSurface(output_path, width, height)
		else:
			raise ValueError(f"Unknown cairo format: {cairo_format}")

		context = cairo.Context(surface)

		# White background for PNG
		if cairo_format == "png":
			context.set_source_rgb(1, 1, 1)
			context.paint()

		# Collect and render all ops
		all_ops = _collect_all_ops(width, height)
		render_ops.ops_to_cairo(context, all_ops)

		# Add text labels using cairo
		_add_cairo_labels(context, width, height)

		# Finish rendering
		if cairo_format == "png":
			surface.write_to_png(output_path)
		surface.finish()

		return None


#============================================
def _add_text(parent, x, y, text, font_size=12, anchor="start", weight="normal", fill="#000"):
	"""Add text element to SVG."""
	attrs = (
		("x", str(x)),
		("y", str(y)),
		("font-family", "sans-serif"),
		("font-size", str(font_size)),
		("text-anchor", anchor),
		("fill", fill),
	)
	if weight != "normal":
		attrs += (("font-weight", weight),)
	text_elem = dom_extensions.elementUnder(parent, "text", attributes=attrs)
	text_elem.appendChild(parent.ownerDocument.createTextNode(text))


#============================================
def _build_bond_grid(parent):
	"""Build bond type x color grid (Section A)."""
	# Bond types to show
	bond_types = [
		('n', 'Normal'),
		('b', 'Bold'),
		('w', 'Wedge'),
		('h', 'Hatch'),
		('l', 'Left hatch'),
		('r', 'Right hatch'),
		('q', 'Wide rect'),
		('s', 'Wavy'),
	]

	# Colors to show
	colors = [
		('#000', 'Black'),
		('#f00', 'Red'),
		('#00f', 'Blue'),
		('#0a0', 'Green'),
		('#a0a', 'Purple'),
	]

	# Grid layout
	grid_x = 50
	grid_y = 60
	cell_w = 70
	cell_h = 35
	label_offset = 15

	# Column headers (bond type names)
	for col, (bond_type, bond_name) in enumerate(bond_types):
		x = grid_x + col * cell_w + cell_w / 2
		y = grid_y - 5
		_add_text(parent, x, y, bond_name, font_size=9, anchor="middle")

	# Row headers (color names)
	for row, (color, color_name) in enumerate(colors):
		x = grid_x - 10
		y = grid_y + label_offset + row * cell_h + cell_h / 2
		_add_text(parent, x, y, color_name, font_size=9, anchor="end", fill=color)

	# Grid cells
	for row, (color, _) in enumerate(colors):
		for col, (bond_type, _) in enumerate(bond_types):
			x = grid_x + col * cell_w
			y = grid_y + label_offset + row * cell_h

			# Create cell group
			cell_g = dom_extensions.elementUnder(
				parent, "g",
				attributes=(("id", f"cell-{bond_type}-{color}"),)
			)

			# Draw cell border (light gray)
			dom_extensions.elementUnder(
				cell_g, "rect",
				attributes=(
					("x", str(x)),
					("y", str(y)),
					("width", str(cell_w)),
					("height", str(cell_h)),
					("fill", "none"),
					("stroke", "#ddd"),
					("stroke-width", "0.5"),
				)
			)

			# Build bond fragment ops
			fragment_ops = _build_bond_fragment(bond_type, color)

			# Transform ops into cell position
			cx = x + cell_w / 2
			cy = y + cell_h / 2
			panel_ops = _transform_ops(fragment_ops, cx - 15, cy, scale=1.0)

			# Paint ops
			render_ops.ops_to_svg(cell_g, panel_ops)


#============================================
def _build_bond_fragment(bond_type, color):
	"""Build a tiny C-C bond fragment.

	Args:
		bond_type: Bond type code ('n', 'b', 'w', etc.)
		color: Hex color string

	Returns:
		List of ops for rendering
	"""
	# Handle special cases for bond order
	if bond_type == '=' or bond_type == 2:
		bond_order = 2
		bond_type_code = 'n'
	elif bond_type == '#' or bond_type == 3:
		bond_order = 3
		bond_type_code = 'n'
	else:
		bond_order = 1
		bond_type_code = bond_type

	# Create minimal molecule
	mol = molecule.molecule()
	a1 = atom.atom(symbol='C')
	a1.x = 0
	a1.y = 0
	a2 = atom.atom(symbol='C')
	a2.x = 30
	a2.y = 0
	mol.add_vertex(a1)
	mol.add_vertex(a2)

	bond = bond_module.bond(order=bond_order, type=bond_type_code)
	bond.vertices = (a1, a2)
	bond.properties_['line_color'] = color
	mol.add_edge(a1, a2, bond)

	# Build ops using existing infrastructure
	context = render_ops.BondRenderContext(
		molecule=mol,
		line_width=1.0,
		bond_width=3.0,
		wedge_width=4.0,
		bold_line_width_multiplier=1.2,
		shown_vertices=set(),
		bond_coords={bond: ((0, 0), (30, 0))},
		point_for_atom=None,
	)

	return render_ops.build_bond_ops(bond, (0, 0), (30, 0), context)


#============================================
def _transform_ops(ops, dx, dy, scale=1.0):
	"""Transform ops by translation and scaling.

	Args:
		ops: List of op objects
		dx, dy: Translation offsets
		scale: Scaling factor

	Returns:
		New list of transformed ops
	"""
	transformed = []
	for op in ops:
		if isinstance(op, render_ops.LineOp):
			p1 = (_scale_point(op.p1, scale, dx, dy))
			p2 = (_scale_point(op.p2, scale, dx, dy))
			transformed.append(render_ops.LineOp(
				p1=p1, p2=p2, width=op.width * scale,
				cap=op.cap, join=op.join, color=op.color, z=op.z
			))
		elif isinstance(op, render_ops.PolygonOp):
			points = tuple(_scale_point(p, scale, dx, dy) for p in op.points)
			transformed.append(render_ops.PolygonOp(
				points=points, fill=op.fill, stroke=op.stroke,
				stroke_width=op.stroke_width * scale, z=op.z
			))
		elif isinstance(op, render_ops.CircleOp):
			center = _scale_point(op.center, scale, dx, dy)
			transformed.append(render_ops.CircleOp(
				center=center, radius=op.radius * scale,
				fill=op.fill, stroke=op.stroke,
				stroke_width=op.stroke_width * scale, z=op.z
			))
		elif isinstance(op, render_ops.PathOp):
			commands = []
			for cmd, payload in op.commands:
				if payload is None:
					commands.append((cmd, None))
				elif cmd == "ARC":
					# ARC: (cx, cy, r, angle1, angle2)
					cx, cy, r, a1, a2 = payload
					new_center = _scale_point((cx, cy), scale, dx, dy)
					commands.append((cmd, (new_center[0], new_center[1], r * scale, a1, a2)))
				else:
					# M, L: (x, y)
					new_point = _scale_point((payload[0], payload[1]), scale, dx, dy)
					commands.append((cmd, (new_point[0], new_point[1])))
			transformed.append(render_ops.PathOp(
				commands=tuple(commands), fill=op.fill, stroke=op.stroke,
				stroke_width=op.stroke_width * scale,
				cap=op.cap, join=op.join, z=op.z
			))
		else:
			# Unknown op type, skip
			continue
	return transformed


#============================================
def _scale_point(point, scale, dx, dy):
	"""Scale and translate a point."""
	return (point[0] * scale + dx, point[1] * scale + dy)


#============================================
def _build_vignettes(parent):
	"""Build complex molecule vignettes (Section B)."""
	# Vignette layout - adjusted to fit on page
	title_y = 270          # Fixed y-position for all titles
	molecule_y = 360       # Fixed y-position for molecule start (well below titles)
	vignette_spacing = 170 # Horizontal spacing between vignettes (reduced to fit Haworth)
	vignette_scale = 1.5   # Reduced from 1.8 to fit both Haworth rings on page

	vignettes = [
		("Benzene (aromatic)", _build_benzene_ops),
		("Stereochemistry", _build_stereochem_ops),
		("Haworth projections", _build_haworth_ops),
	]

	for i, (title, builder_func) in enumerate(vignettes):
		x = 60 + i * vignette_spacing

		# Title on separate line above molecules
		_add_text(parent, x + 60, title_y, title, font_size=11, weight="bold")

		# Build vignette below title line
		vignette_g = dom_extensions.elementUnder(
			parent, "g",
			attributes=(("id", f"vignette-{i}"),)
		)
		ops = builder_func()
		panel_ops = _transform_ops(ops, x, molecule_y, scale=vignette_scale)
		render_ops.ops_to_svg(vignette_g, panel_ops)


#============================================
def _build_benzene_ops():
	"""Build benzene ring with alternating double bonds."""
	mol = molecule.molecule()

	# Hexagon vertices
	radius = 20
	atoms = []
	for i in range(6):
		angle = i * math.pi / 3 + math.pi / 6
		x = radius * math.cos(angle)
		y = radius * math.sin(angle)
		a = atom.atom(symbol='C')
		a.x = x
		a.y = y
		mol.add_vertex(a)
		atoms.append(a)

	# First, add all ring bonds to molecule (alternating single/double)
	bonds = []
	for i in range(6):
		a1 = atoms[i]
		a2 = atoms[(i + 1) % 6]
		order = 2 if i % 2 == 0 else 1  # Alternating
		b = bond_module.bond(order=order, type='n')
		b.vertices = (a1, a2)
		mol.add_edge(a1, a2, b)
		bonds.append(b)

	# Now that ring is complete, create rendering context
	context = render_ops.BondRenderContext(
		molecule=mol,
		line_width=1.0,
		bond_width=3.0,
		wedge_width=4.0,
		bold_line_width_multiplier=1.2,
		shown_vertices=set(),
		bond_coords={},
		point_for_atom=None,
	)

	# Build ops for all bonds (ring detection now works)
	all_ops = []
	for i, b in enumerate(bonds):
		a1 = atoms[i]
		a2 = atoms[(i + 1) % 6]
		start = (a1.x, a1.y)
		end = (a2.x, a2.y)
		context.bond_coords[b] = (start, end)
		ops = render_ops.build_bond_ops(b, start, end, context)
		all_ops.extend(ops)

	return all_ops


#============================================
def _build_stereochem_ops():
	"""Build molecule with wedge and hatch bonds."""
	mol = molecule.molecule()

	# Central carbon
	center = atom.atom(symbol='C')
	center.x = 0
	center.y = 0
	mol.add_vertex(center)

	# Four substituents in cardinal directions
	a1 = atom.atom(symbol='C')
	a1.x = 0
	a1.y = -20
	a2 = atom.atom(symbol='C')
	a2.x = 20
	a2.y = 0
	a3 = atom.atom(symbol='C')
	a3.x = 0
	a3.y = 20
	a4 = atom.atom(symbol='C')
	a4.x = -20
	a4.y = 0

	substituents = [
		(a1, 'w'),   # Up - wedge
		(a2, 'n'),   # Right - normal
		(a3, 'h'),   # Down - hatch
		(a4, 'n'),   # Left - normal
	]

	context = render_ops.BondRenderContext(
		molecule=mol,
		line_width=1.0,
		bond_width=3.0,
		wedge_width=6.0,
		bold_line_width_multiplier=1.2,
		shown_vertices=set(),
		bond_coords={},
		point_for_atom=None,
	)

	all_ops = []
	for sub_atom, bond_type in substituents:
		mol.add_vertex(sub_atom)
		b = bond_module.bond(order=1, type=bond_type)
		b.vertices = (center, sub_atom)
		mol.add_edge(center, sub_atom, b)

		start = (center.x, center.y)
		end = (sub_atom.x, sub_atom.y)
		context.bond_coords[b] = (start, end)
		ops = render_ops.build_bond_ops(b, start, end, context)
		all_ops.extend(ops)

	return all_ops


#============================================
def _build_haworth_ops():
	"""Build Haworth projection rings using the haworth module.

	Creates pyranose (6-membered) and furanose (5-membered) rings
	with proper wedge, hatch, and wide-rectangle bond styling.
	"""
	# Build pyranose (6-membered ring with oxygen)
	pyranose = _build_ring(6, oxygen_index=0)
	haworth.build_haworth(pyranose, mode="pyranose")

	# Build furanose (5-membered ring with oxygen)
	furanose = _build_ring(5, oxygen_index=0)
	haworth.build_haworth(furanose, mode="furanose")

	# Offset furanose to the right of pyranose (reduced spacing to fit on page)
	max_x = max(a.x for a in pyranose.vertices)
	min_x = min(a.x for a in pyranose.vertices)
	offset = (max_x - min_x) + 30.0  # Reduced from 50 to 30 to fit on page
	for a in furanose.vertices:
		a.x += offset

	# Combine both rings into one molecule
	pyranose.insert_a_graph(furanose)
	mol = pyranose

	# Build render ops for all bonds
	context = render_ops.BondRenderContext(
		molecule=mol,
		line_width=1.0,
		bond_width=3.0,
		wedge_width=6.0,
		bold_line_width_multiplier=1.2,
		shown_vertices=set(),
		bond_coords={},
		point_for_atom=None,
	)

	all_ops = []
	for bond in mol.edges:
		v1, v2 = bond.vertices
		start = (v1.x, v1.y)
		end = (v2.x, v2.y)
		context.bond_coords[bond] = (start, end)
		ops = render_ops.build_bond_ops(bond, start, end, context)
		all_ops.extend(ops)

	return all_ops


def _build_ring(size, oxygen_index=None):
	"""Build a simple ring molecule (helper for Haworth).

	Args:
		size: Number of atoms in ring
		oxygen_index: Optional index for oxygen atom (None = all carbons)

	Returns:
		molecule with ring structure
	"""
	mol = molecule.molecule()
	atoms = []
	for idx in range(size):
		symbol = 'C'
		if oxygen_index is not None and idx == oxygen_index:
			symbol = 'O'
		a = atom.atom(symbol=symbol)
		a.x = idx * 20
		a.y = 0
		mol.add_vertex(a)
		atoms.append(a)

	for idx in range(size):
		b = bond_module.bond(order=1, type='n')
		v1 = atoms[idx]
		v2 = atoms[(idx + 1) % size]
		b.vertices = (v1, v2)
		mol.add_edge(v1, v2, b)

	return mol


#============================================
def _collect_all_ops(width, height):
	"""Collect all rendering ops for cairo backend.

	Returns:
		List of render ops for bond grid and vignettes
	"""
	all_ops = []

	# Bond types and colors
	bond_types = [
		('n', 'Normal'), ('b', 'Bold'), ('w', 'Wedge'), ('h', 'Hatch'),
		('l', 'Left hatch'), ('r', 'Right hatch'), ('q', 'Wide rect'), ('s', 'Wavy'),
	]
	colors = [('#000', 'Black'), ('#f00', 'Red'), ('#00f', 'Blue'), ('#0a0', 'Green'), ('#a0a', 'Purple')]

	# Grid layout
	grid_x = 50
	grid_y = 75  # 60 + 15 (label offset)
	cell_w = 70
	cell_h = 35

	# Grid cells - collect ops for each bond/color combination
	for row, (color, _) in enumerate(colors):
		for col, (bond_type, _) in enumerate(bond_types):
			x = grid_x + col * cell_w
			y = grid_y + row * cell_h

			# Build bond fragment ops
			fragment_ops = _build_bond_fragment(bond_type, color)

			# Transform ops into cell position
			cx = x + cell_w / 2
			cy = y + cell_h / 2
			panel_ops = _transform_ops(fragment_ops, cx - 15, cy, scale=1.0)

			all_ops.extend(panel_ops)

	# Vignettes - adjusted to fit on page
	molecule_y = 360       # Molecules positioned well below title line
	vignette_spacing = 170 # Reduced to fit Haworth rings on page
	vignette_scale = 1.5   # Reduced from 1.8 to fit both Haworth rings

	vignettes = [
		("Benzene (aromatic)", _build_benzene_ops),
		("Stereochemistry", _build_stereochem_ops),
		("Haworth projections", _build_haworth_ops),
	]

	for idx, (label, builder_func) in enumerate(vignettes):
		ops = builder_func()
		x = 60 + idx * vignette_spacing
		panel_ops = _transform_ops(ops, x, molecule_y, scale=vignette_scale)
		all_ops.extend(panel_ops)

	return all_ops


#============================================
def _add_cairo_labels(context, width, height):
	"""Add text labels to cairo context.

	Args:
		context: Cairo context
		width: Page width
		height: Page height
	"""
	import cairo

	# Title
	context.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
	context.set_font_size(20)
	context.set_source_rgb(0, 0, 0)
	text = "OASA Renderer Capabilities"
	extents = context.text_extents(text)
	context.move_to((width - extents.width) / 2, 30)
	context.show_text(text)

	# Bond type column headers
	bond_types = ['Normal', 'Bold', 'Wedge', 'Hatch', 'Left hatch', 'Right hatch', 'Wide rect', 'Wavy']
	context.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
	context.set_font_size(9)
	grid_x = 50
	grid_y = 60
	cell_w = 70
	for col, name in enumerate(bond_types):
		x = grid_x + col * cell_w + cell_w / 2
		y = grid_y - 5
		extents = context.text_extents(name)
		context.move_to(x - extents.width / 2, y)
		context.show_text(name)

	# Color row headers
	colors = [('#000', 'Black'), ('#f00', 'Red'), ('#00f', 'Blue'), ('#0a0', 'Green'), ('#a0a', 'Purple')]
	cell_h = 35
	label_offset = 15
	for row, (color_hex, color_name) in enumerate(colors):
		# Parse hex color (handle both #RGB and #RRGGBB formats)
		if len(color_hex) == 4:  # #RGB
			r = int(color_hex[1] * 2, 16) / 255
			g = int(color_hex[2] * 2, 16) / 255
			b = int(color_hex[3] * 2, 16) / 255
		else:  # #RRGGBB
			r = int(color_hex[1:3], 16) / 255
			g = int(color_hex[3:5], 16) / 255
			b = int(color_hex[5:7], 16) / 255
		context.set_source_rgb(r, g, b)
		x = grid_x - 10
		y = grid_y + label_offset + row * cell_h + cell_h / 2
		extents = context.text_extents(color_name)
		context.move_to(x - extents.width, y + extents.height / 2)
		context.show_text(color_name)

	# Vignette labels - on separate line well above molecules
	vignette_labels = ["Benzene (aromatic)", "Stereochemistry", "Haworth projections"]
	vignette_spacing = 180
	title_y = 270
	context.set_source_rgb(0, 0, 0)
	context.set_font_size(11)
	context.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
	for idx, label in enumerate(vignette_labels):
		x = 60 + idx * vignette_spacing + 60  # +60 to center over molecule
		y = title_y
		extents = context.text_extents(label)
		context.move_to(x - extents.width / 2, y)
		context.show_text(label)

	# Footer
	context.set_font_size(10)
	context.set_source_rgb(0.4, 0.4, 0.4)
	text = "Generated by OASA selftest_sheet.py"
	extents = context.text_extents(text)
	context.move_to((width - extents.width) / 2, height - 20)
	context.show_text(text)


#============================================
def main():
	"""CLI entry point."""
	import argparse

	parser = argparse.ArgumentParser(
		description="Generate OASA renderer capabilities sheet"
	)
	parser.add_argument(
		"-o", "--out",
		dest="output",
		default=None,
		help="Output file path (default: oasa_capabilities_sheet.{format})"
	)
	parser.add_argument(
		"--format",
		default="pdf",
		choices=["svg", "png", "pdf"],
		help="Output format (default: pdf)"
	)
	parser.add_argument(
		"--page",
		default="letter",
		choices=["letter", "a4"],
		help="Page size (default: letter, always portrait)"
	)

	args = parser.parse_args()

	# Set default output filename if not specified
	if args.output is None:
		args.output = f"oasa_capabilities_sheet.{args.format}"

	print(f"Generating capabilities sheet...")

	if args.format == "svg":
		# SVG backend
		svg_text = build_renderer_capabilities_sheet(
			page=args.page,
			backend="svg"
		)
		with open(args.output, "w", encoding="utf-8") as f:
			f.write(svg_text)
		print(f"Wrote {len(svg_text)} bytes to {args.output}")

	else:
		# Cairo backend for PNG and PDF
		try:
			import cairo
		except ImportError:
			print("ERROR: pycairo is required for PNG and PDF output")
			print("Install with: pip install pycairo")
			return 1

		# Render to cairo
		build_renderer_capabilities_sheet(
			page=args.page,
			backend="cairo",
			output_path=args.output,
			cairo_format=args.format
		)

		import os
		file_size = os.path.getsize(args.output)
		print(f"Wrote {file_size} bytes to {args.output}")


#============================================
if __name__ == "__main__":
	main()
