#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later

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
def ops_bbox(ops):
	"""Return (minx, miny, maxx, maxy) for a list of render ops."""
	minx = miny = float("inf")
	maxx = maxy = float("-inf")

	def take_point(x, y):
		nonlocal minx, miny, maxx, maxy
		minx = min(minx, x)
		miny = min(miny, y)
		maxx = max(maxx, x)
		maxy = max(maxy, y)

	for op in ops:
		if isinstance(op, render_ops.LineOp):
			take_point(op.p1[0], op.p1[1])
			take_point(op.p2[0], op.p2[1])
		elif isinstance(op, render_ops.PolygonOp):
			for x, y in op.points:
				take_point(x, y)
		elif isinstance(op, render_ops.CircleOp):
			cx, cy = op.center
			r = op.radius
			take_point(cx - r, cy - r)
			take_point(cx + r, cy + r)
		elif isinstance(op, render_ops.PathOp):
			for cmd, payload in op.commands:
				if payload is None:
					continue
				if cmd == "ARC":
					cx, cy, r, _a1, _a2 = payload
					take_point(cx - r, cy - r)
					take_point(cx + r, cy + r)
				else:
					x, y = payload
					take_point(x, y)

	if minx == float("inf"):
		return (0.0, 0.0, 0.0, 0.0)
	return (minx, miny, maxx, maxy)


#============================================
def normalize_to_height(ops, target_height):
	"""Normalize ops to a target height, maintaining aspect ratio.

	Args:
		ops: List of render ops
		target_height: Desired height in points

	Returns:
		Tuple of (transformed_ops, actual_width, actual_height)
	"""
	if not ops:
		return [], 0, 0

	minx, miny, maxx, maxy = ops_bbox(ops)
	current_height = maxy - miny

	if current_height == 0:
		return ops, maxx - minx, 0

	scale = target_height / current_height

	# Scale ops
	scaled = _transform_ops(ops, 0, 0, scale=scale)

	# Translate so top-left is at origin
	minx_s, miny_s, maxx_s, maxy_s = ops_bbox(scaled)
	translated = _transform_ops(scaled, -minx_s, -miny_s, scale=1.0)

	return translated, (maxx_s - minx_s), (maxy_s - miny_s)


#============================================
def layout_row(vignettes, y_top, page_width, row_height, gutter=20, margin=40):
	"""Layout multiple vignettes in a horizontal row with equal spacing.

	Args:
		vignettes: List of (title, ops) tuples
		y_top: Y coordinate for top of row
		page_width: Total page width
		row_height: Target height for normalizing molecules
		gutter: Space between vignettes
		margin: Left/right margin

	Returns:
		List of (title, positioned_ops, x_center, y_center) for rendering
	"""
	if not vignettes:
		return []

	# Normalize all vignettes to same height
	normalized = []
	for title, ops in vignettes:
		norm_ops, width, height = normalize_to_height(ops, row_height)
		normalized.append((title, norm_ops, width, height))

	# Calculate total width and spacing
	total_content_width = sum(w for _, _, w, _ in normalized)
	num_gaps = len(normalized) - 1
	total_gap_width = num_gaps * gutter
	available_width = page_width - 2 * margin

	# If content doesn't fit, scale down uniformly
	if total_content_width + total_gap_width > available_width:
		scale_factor = available_width / (total_content_width + total_gap_width)
		# Re-normalize with adjusted height
		adjusted_height = row_height * scale_factor
		normalized = []
		for title, ops, _, _ in vignettes:
			norm_ops, width, height = normalize_to_height(ops, adjusted_height)
			normalized.append((title, norm_ops, width, height))
		total_content_width = sum(w for _, _, w, _ in normalized)

	# Position vignettes with equal gutters
	result = []
	x_current = margin

	for title, norm_ops, width, height in normalized:
		# Center of this vignette
		x_center = x_current + width / 2
		y_center = y_top + height / 2

		# Position ops at current x
		positioned = _transform_ops(norm_ops, x_current, y_top, scale=1.0)
		result.append((title, positioned, x_center, y_center))

		# Advance to next position
		x_current += width + gutter

	return result


#============================================
def place_ops_in_rect(ops, rect, align="center", padding=5, preserve_aspect=True):
	"""Place ops inside a rectangle with scaling and alignment.

	Args:
		ops: List of render ops to place
		rect: (x, y, width, height) rectangle to place ops in
		align: "center", "left", "right", "top", "bottom"
		padding: Padding inside rect in points
		preserve_aspect: If True, maintain aspect ratio

	Returns:
		List of transformed ops
	"""
	bbox = ops_bbox(ops)
	if bbox is None:
		return []

	minx, miny, maxx, maxy = bbox
	content_width = maxx - minx
	content_height = maxy - miny

	if content_width == 0 or content_height == 0:
		return []

	rect_x, rect_y, rect_width, rect_height = rect
	available_width = rect_width - 2 * padding
	available_height = rect_height - 2 * padding

	# Compute scale
	if preserve_aspect:
		scale = min(available_width / content_width, available_height / content_height)
	else:
		scale = min(available_width / content_width, available_height / content_height)

	scaled_width = content_width * scale
	scaled_height = content_height * scale

	# Compute offset based on alignment
	if align == "center":
		dx = rect_x + padding + (available_width - scaled_width) / 2 - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) / 2 - miny * scale
	elif align == "left":
		dx = rect_x + padding - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) / 2 - miny * scale
	elif align == "right":
		dx = rect_x + padding + (available_width - scaled_width) - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) / 2 - miny * scale
	elif align == "top":
		dx = rect_x + padding + (available_width - scaled_width) / 2 - minx * scale
		dy = rect_y + padding - miny * scale
	elif align == "bottom":
		dx = rect_x + padding + (available_width - scaled_width) / 2 - minx * scale
		dy = rect_y + padding + (available_height - scaled_height) - miny * scale
	else:
		dx = rect_x + padding - minx * scale
		dy = rect_y + padding - miny * scale

	# Transform ops
	return _transform_ops(ops, dx, dy, scale)


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
	cairo = None
	if backend == "cairo":
		if output_path is None:
			raise ValueError("output_path is required for cairo backend")
		try:
			import cairo as cairo_module
			cairo = cairo_module
		except ImportError:
			raise ImportError("pycairo is required for cairo backend. Install with: pip install pycairo")

	if backend not in ("svg", "cairo"):
		raise ValueError(f"Unknown backend: {backend}. Must be 'svg' or 'cairo'")

	width, height = get_page_dims(page, portrait=True)

	if backend == "svg":
		# SVG backend - build DOM tree
		# defusedxml doesn't have Document(), use implementation
		try:
			from xml.dom.minidom import getDOMImplementation
			impl = getDOMImplementation()
			doc = impl.createDocument(None, None, None)
		except:
			import xml.dom.minidom
			doc = xml.dom.minidom.Document()
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
		_build_vignettes(vignettes_g, width)

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

		# Use toprettyxml for readable output (not minified)
		xml_str = doc.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
		# Remove extra blank lines that toprettyxml adds
		lines = [line for line in xml_str.split('\n') if line.strip()]
		return '\n'.join(lines)

	elif backend == "cairo":
		# Cairo backend - render directly to file
		if cairo is None:
			raise RuntimeError("Cairo backend requested but pycairo is unavailable.")
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
		('q', 'Wide rect'),
		('s', 'Wavy (sine)'),
		('s_triangle', 'Wavy (tri)'),
		('s_box', 'Wavy (box)'),
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
	# Handle special cases for bond order and wavy styles
	wavy_style = None
	if bond_type == '=' or bond_type == 2:
		bond_order = 2
		bond_type_code = 'n'
	elif bond_type == '#' or bond_type == 3:
		bond_order = 3
		bond_type_code = 'n'
	elif bond_type == 's_triangle':
		bond_order = 1
		bond_type_code = 's'
		wavy_style = 'triangle'
	elif bond_type == 's_box':
		bond_order = 1
		bond_type_code = 's'
		wavy_style = 'box'
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
	if wavy_style:
		bond.properties_['wavy_style'] = wavy_style
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
def _build_cholesterol_ops():
	"""Build cholesterol molecule from CDML template."""
	import os

	# Handle imports for both module and script usage
	if __name__ == "__main__":
		import oasa
		cdml_module = oasa.cdml
	else:
		from . import cdml as cdml_module

	# CDML file lives in bkchem templates
	here = os.path.dirname(os.path.abspath(__file__))
	# Navigate from packages/oasa/oasa/ to packages/bkchem/bkchem_data/templates/
	path = os.path.join(
		here, "..", "..", "bkchem", "bkchem_data", "templates",
		"biomolecules", "lipids", "steroids", "cholesterol.cdml"
	)
	path = os.path.normpath(path)

	if not os.path.exists(path):
		# Return empty if file doesn't exist
		return []

	with open(path, 'r') as f:
		result = cdml_module.read_cdml(f.read())

	# read_cdml returns a generator, get first molecule
	try:
		mol = next(iter(result))
	except (StopIteration, TypeError):
		return []

	if mol is None:
		return []

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
	for b in mol.edges:
		v1, v2 = b.vertices
		start = (v1.x, v1.y)
		end = (v2.x, v2.y)
		context.bond_coords[b] = (start, end)
		all_ops.extend(render_ops.build_bond_ops(b, start, end, context))

	return all_ops


#============================================
def _build_vignettes(parent, page_width):
	"""Build complex molecule vignettes using row-based layout.

	Top row: Benzene, Haworth, Fischer (all projection styles)
	Bottom row: Cholesterol (complex stress test)
	"""
	# Row configuration
	row1_y = 290
	row1_height = 80
	row2_y = 460
	row2_height = 120
	margin = 40
	gutter = 20

	# Top row: projection styles
	row1_vignettes = [
		("Benzene", _build_benzene_ops()),
		("Haworth", _build_haworth_ops()),
		("Fischer", _build_fischer_ops()),
	]

	# Bottom row: stress test
	row2_vignettes = [
		("Cholesterol", _build_cholesterol_ops()),
	]

	# Layout row 1
	row1_result = layout_row(
		row1_vignettes,
		y_top=row1_y,
		page_width=page_width,
		row_height=row1_height,
		gutter=gutter,
		margin=margin
	)

	# Render row 1
	for idx, (title, positioned_ops, x_center, y_center) in enumerate(row1_result):
		# Title above molecule (15pt above)
		title_y = row1_y - 10
		_add_text(parent, x_center, title_y, title, font_size=11, weight="bold", anchor="middle")

		# Molecule ops
		vignette_g = dom_extensions.elementUnder(
			parent, "g",
			attributes=(("id", f"vignette-row1-{idx}"),)
		)
		render_ops.ops_to_svg(vignette_g, positioned_ops)

	# Layout row 2
	row2_result = layout_row(
		row2_vignettes,
		y_top=row2_y,
		page_width=page_width,
		row_height=row2_height,
		gutter=gutter,
		margin=margin
	)

	# Render row 2
	for idx, (title, positioned_ops, x_center, y_center) in enumerate(row2_result):
		# Title above molecule (15pt above)
		title_y = row2_y - 10
		_add_text(parent, x_center, title_y, title, font_size=11, weight="bold", anchor="middle")

		# Molecule ops
		vignette_g = dom_extensions.elementUnder(
			parent, "g",
			attributes=(("id", f"vignette-row2-{idx}"),)
		)
		render_ops.ops_to_svg(vignette_g, positioned_ops)


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

	# Offset furanose to the right of pyranose (minimal spacing to fit on page)
	max_x = max(a.x for a in pyranose.vertices)
	min_x_furanose = min(a.x for a in furanose.vertices)
	# Place furanose with just 20 units gap from pyranose
	offset = max_x - min_x_furanose + 20.0
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
def _build_fischer_ops():
	"""Build Fischer projection (D-glucose).

	Fischer projection: vertical backbone with horizontal substituents.
	Tests straight bond rendering and left/right positioning.
	No wedges or hatches needed - pure 2D representation.
	"""
	mol = molecule.molecule()

	# Vertical backbone: 6 carbons (C1 to C6)
	backbone_spacing = 25
	backbone = []
	for i in range(6):
		a = atom.atom(symbol='C')
		a.x = 0
		a.y = i * backbone_spacing
		mol.add_vertex(a)
		backbone.append(a)

	# Connect backbone with normal bonds and store references
	backbone_bonds = []
	for i in range(5):
		b = bond_module.bond(order=1, type='n')
		b.vertices = (backbone[i], backbone[i + 1])
		mol.add_edge(backbone[i], backbone[i + 1], b)
		backbone_bonds.append(b)

	# Horizontal substituents (alternating left/right for D-glucose)
	# C1 (aldehyde carbon): no horizontal substituents shown
	# C2: OH right, H left
	# C3: OH left, H right
	# C4: OH right, H left
	# C5: OH right, H left
	# C6 (CH2OH): no horizontal substituents shown

	substituent_length = 15
	substituents_data = [
		# (carbon_idx, [(symbol, dx), ...])
		(1, [('O', substituent_length), ('H', -substituent_length)]),  # C2
		(2, [('O', -substituent_length), ('H', substituent_length)]),  # C3
		(3, [('O', substituent_length), ('H', -substituent_length)]),  # C4
		(4, [('O', substituent_length), ('H', -substituent_length)]),  # C5
	]

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

	all_ops = []

	# Build backbone bonds first
	for i, b in enumerate(backbone_bonds):
		start = (backbone[i].x, backbone[i].y)
		end = (backbone[i + 1].x, backbone[i + 1].y)
		context.bond_coords[b] = (start, end)
		ops = render_ops.build_bond_ops(b, start, end, context)
		all_ops.extend(ops)

	# Add horizontal substituents
	for carbon_idx, subs in substituents_data:
		carbon = backbone[carbon_idx]
		for symbol, dx in subs:
			sub = atom.atom(symbol=symbol)
			sub.x = carbon.x + dx
			sub.y = carbon.y
			mol.add_vertex(sub)

			b = bond_module.bond(order=1, type='n')
			b.vertices = (carbon, sub)
			mol.add_edge(carbon, sub, b)

			start = (carbon.x, carbon.y)
			end = (sub.x, sub.y)
			context.bond_coords[b] = (start, end)
			ops = render_ops.build_bond_ops(b, start, end, context)
			all_ops.extend(ops)

	return all_ops


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
		('q', 'Wide rect'), ('s', 'Wavy (sine)'), ('s_triangle', 'Wavy (tri)'), ('s_box', 'Wavy (box)'),
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

	# Row-based vignette layout (same as SVG backend)
	row1_y = 290
	row1_height = 80
	row2_y = 460
	row2_height = 120
	margin = 40
	gutter = 20

	# Top row: projection styles
	row1_vignettes = [
		("Benzene", _build_benzene_ops()),
		("Haworth", _build_haworth_ops()),
		("Fischer", _build_fischer_ops()),
	]

	# Bottom row: stress test
	row2_vignettes = [
		("Cholesterol", _build_cholesterol_ops()),
	]

	# Layout and collect row 1
	row1_result = layout_row(
		row1_vignettes,
		y_top=row1_y,
		page_width=width,
		row_height=row1_height,
		gutter=gutter,
		margin=margin
	)
	for _, positioned_ops, _, _ in row1_result:
		all_ops.extend(positioned_ops)

	# Layout and collect row 2
	row2_result = layout_row(
		row2_vignettes,
		y_top=row2_y,
		page_width=width,
		row_height=row2_height,
		gutter=gutter,
		margin=margin
	)
	for _, positioned_ops, _, _ in row2_result:
		all_ops.extend(positioned_ops)

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
	bond_types = ['Normal', 'Bold', 'Wedge', 'Hatch', 'Wide rect', 'Wavy (sine)', 'Wavy (tri)', 'Wavy (box)']
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

	# Vignette labels using row-based layout (need to compute positions)
	row1_y = 290
	row1_height = 80
	row2_y = 460
	row2_height = 120
	margin = 40
	gutter = 20

	# Top row vignettes
	row1_vignettes = [
		("Benzene", _build_benzene_ops()),
		("Haworth", _build_haworth_ops()),
		("Fischer", _build_fischer_ops()),
	]

	row1_result = layout_row(
		row1_vignettes,
		y_top=row1_y,
		page_width=width,
		row_height=row1_height,
		gutter=gutter,
		margin=margin
	)

	context.set_source_rgb(0, 0, 0)
	context.set_font_size(11)
	context.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

	for title, _, x_center, _ in row1_result:
		title_y = row1_y - 10
		extents = context.text_extents(title)
		context.move_to(x_center - extents.width / 2, title_y)
		context.show_text(title)

	# Bottom row vignettes
	row2_vignettes = [
		("Cholesterol", _build_cholesterol_ops()),
	]

	row2_result = layout_row(
		row2_vignettes,
		y_top=row2_y,
		page_width=width,
		row_height=row2_height,
		gutter=gutter,
		margin=margin
	)

	for title, _, x_center, _ in row2_result:
		title_y = row2_y - 10
		extents = context.text_extents(title)
		context.move_to(x_center - extents.width / 2, title_y)
		context.show_text(title)

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

	print("Generating capabilities sheet...")

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
			_ = cairo
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
