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

import copy
import math
import xml.dom.minidom as dom

from . import misc
from . import geometry
from . import transform
from . import dom_extensions



class svg_out(object):

  show_hydrogens_on_hetero = False
  margin = 15
  line_width = 2
  bond_width = 6
  wedge_width = 6
  bold_line_width_multiplier = 1.2
  # should individual parts of an edge be grouped together
  group_items = True


  def __init__( self):
    pass

  def mol_to_svg( self, mol, before=None, after=None):
    """before and after should be methods or functions that will take one
    argument - svg_out instance and do whatever it wants with it - usually
    adding something to the resulting DOM tree"""
    self.document = dom.Document()
    top = dom_extensions.elementUnder( self.document,
                                       "svg",
                                       attributes=(("xmlns", "http://www.w3.org/2000/svg"),
                                                   ("version", "1.0")))
    self.top = dom_extensions.elementUnder( top, "g",
                                            attributes=(("stroke", "#000"),
                                                        ("stroke-width", str( self.line_width))))

    x1, y1, x2, y2 = None, None, None, None
    for v in mol.vertices:
      if x1 == None or x1 > v.x:
        x1 = v.x
      if x2 == None or x2 < v.x:
        x2 = v.x
      if y1 == None or y1 > v.y:
        y1 = v.y
      if y2 == None or y2 < v.y:
        y2 = v.y

    w = int( x2 - x1 + 2*self.margin)
    h = int( y2 - y1 + 2*self.margin)
    top.setAttribute( "width", str( w))
    top.setAttribute( "height", str( h))

    self.transformer = transform.transform()
    self.transformer.set_move( -x1+self.margin, -y1+self.margin)

    self.molecule = mol

    if before:
      before( self)

    for e in copy.copy( mol.edges):
      self._draw_edge( e)
    for v in mol.vertices:
      self._draw_vertex( v)

    if after:
      after( self)

    return self.document


  def paper_to_canvas_coord( self, x):
    return x


  def prepare_dumb_transformer( self):
    tr = transform.transform()
    tr.set_scaling( self.paper_to_canvas_coord( 1))
    return tr


  def _create_parent( self, item, top):
    if self.group_items:
      parent = dom_extensions.elementUnder( top, "g")
      if 'svg_id' in item.properties_:
        parent.setAttribute( "id", item.properties_['svg_id'])
    else:
      parent = self.top
    return parent


  def _draw_edge( self, e):
    v1, v2 = e.vertices
    start = self.transformer.transform_xy( v1.x, v1.y)
    end = self.transformer.transform_xy( v2.x, v2.y)
    parent = self._create_parent( e, self.top)

    line_width = self._bond_line_width( e)
    edge_color = self._edge_color( e)

    if e.order == 1:
      if e.type == 'w':
        self._draw_wedge( parent, start, end, fill_color=edge_color)
      elif e.type == 'h':
        self._draw_hatch( parent, start, end, stroke_color=edge_color)
      elif e.type == 'l':
        self._draw_side_hatch( parent, start, end, side=1, stroke_color=edge_color)
      elif e.type == 'r':
        self._draw_side_hatch( parent, start, end, side=-1, stroke_color=edge_color)
      elif e.type == 'q':
        self._draw_wide_rectangle( parent, start, end, fill_color=edge_color)
      elif e.type == 's':
        self._draw_wavy( parent, start, end,
                         style=self._wavy_style( e),
                         line_width=line_width,
                         stroke_color=edge_color)
      else:
        self._draw_line( parent, start, end, line_width=line_width, capstyle="round", stroke_color=edge_color)

    if e.order == 2:
      side = 0
      # find how to center the bonds
      # rings have higher priority in setting the positioning
      for ring in self.molecule.get_smallest_independent_cycles():
        if v1 in ring and v2 in ring:
          side += sum(geometry.on_which_side_is_point(start + end, self.transformer.transform_xy(a.x, a.y))
                          for a in ring
                              if a != v1 and a != v2)
      # if rings did not decide, use the other neigbors
      if not side:
        for v in v1.neighbors + v2.neighbors:
          if v != v1 and v!= v2:
            side += geometry.on_which_side_is_point( start+end, (self.transformer.transform_xy( v.x, v.y)))
      if side:
        self._draw_line( parent, start, end, line_width=line_width, capstyle="round", stroke_color=edge_color)
        x1, y1, x2, y2 = geometry.find_parallel( start[0], start[1], end[0], end[1], self.bond_width*misc.signum( side))
        self._draw_line( parent, (x1, y1), (x2, y2), line_width=line_width, capstyle="round", stroke_color=edge_color)
      else:
        for i in (1,-1):
          x1, y1, x2, y2 = geometry.find_parallel( start[0], start[1], end[0], end[1], i*self.bond_width*0.5)
          self._draw_line( parent, (x1, y1), (x2, y2), line_width=line_width, capstyle="round", stroke_color=edge_color)


    elif e.order == 3:
      self._draw_line( parent, start, end, line_width=line_width, capstyle="round", stroke_color=edge_color)
      for i in (1,-1):
        x1, y1, x2, y2 = geometry.find_parallel( start[0], start[1], end[0], end[1], i*self.bond_width*0.7)
        self._draw_line( parent, (x1, y1), (x2, y2), line_width=line_width, capstyle="round", stroke_color=edge_color)


  def _draw_vertex( self, v):
    parent = self._create_parent( v, self.top)

    if v.symbol != "C" or v.charge != 0 or v.multiplicity != 1:
      x = v.x - 5
      y = v.y + 6
      x1 = x
      x2 = x + 12
      y1 = y - 12
      y2 = y + 2
      text = v.symbol
      if self.show_hydrogens_on_hetero:
        if v.free_valency == 1:
          text += "H"
        elif v.free_valency > 1:
          text += "H%d" % v.free_valency
      # charge
      if v.charge == 1:
        text += "+"
      elif v.charge == -1:
        text += "-"
      elif v.charge > 1:
        text += str( v.charge) + "+"
      elif v.charge < -1:
        text += str( v.charge)
      # radicals
      if v.multiplicity in (2,3):
        self._draw_circle( parent, self.transformer.transform_xy((x2+x1)/2,y-17), fill_color="#000", opacity=1, radius=3)
        if v.multiplicity == 3:
          self._draw_circle( parent, self.transformer.transform_xy((x2+x1)/2,y+5), fill_color="#000", opacity=1, radius=3)
      self._draw_rectangle( parent, self.transformer.transform_4( (x1, y1, x2, y2)), fill_color="#fff")
      self._draw_text( parent, self.transformer.transform_xy(x,y), text)


  def _draw_line( self, parent, start, end, line_width=1, capstyle="", stroke_color=None):
    x1, y1 = start
    x2, y2 = end
    attrs = (( 'x1', str( x1)),
             ( 'y1', str( y1)),
             ( 'x2', str( x2)),
             ( 'y2', str( y2)),
             ( 'stroke-width', str( line_width)))
    if capstyle:
      attrs += (( 'stroke-linecap', capstyle),)
    if stroke_color:
      attrs += (( 'stroke', stroke_color),)
    dom_extensions.elementUnder( parent, 'line', attrs)


  def _draw_text( self, parent, xy, text, font_name="Arial", font_size=16):
    x, y = xy
    dom_extensions.textOnlyElementUnder( parent, "text", text,
                                         (( "x", str( x)),
                                          ( "y", str( y)),
                                          ( "font-family", font_name),
                                          ( "font-size", str( font_size)),
                                          ( 'fill', "#000")))


  def _draw_rectangle( self, parent, coords, fill_color="#fff", stroke_color="#fff"):
    x, y, x2, y2 = coords
    dom_extensions.elementUnder( parent, 'rect',
                                 (( 'x', str( x)),
                                  ( 'y', str( y)),
                                  ( 'width', str( x2-x)),
                                  ( 'height', str( y2-y)),
                                  ( 'fill', fill_color),
                                  ( 'stroke', stroke_color)))

  def _draw_polygon( self, parent, points, fill_color="#000", stroke_color="none"):
    points_text = " ".join( "%s,%s" % (x, y) for x, y in points)
    dom_extensions.elementUnder( parent, 'polygon',
                                 (( 'points', points_text),
                                  ( 'fill', fill_color),
                                  ( 'stroke', stroke_color)))

  def _draw_wedge( self, parent, start, end, fill_color=None):
    x1, y1 = start
    x2, y2 = end
    # Draw a filled wedge polygon for stereochemistry.
    x, y, x0, y0 = geometry.find_parallel( x1, y1, x2, y2, self.wedge_width/2.0)
    xa, ya, xb, yb = geometry.find_parallel( x1, y1, x2, y2, self.line_width/2.0)
    points = [(xa, ya), (x0, y0), (2*x2-x0, 2*y2-y0), (2*x1-xa, 2*y1-ya)]
    self._draw_polygon( parent, points, fill_color=fill_color or "#000", stroke_color="none")

  def _draw_hatch( self, parent, start, end, stroke_color=None):
    x1, y1 = start
    x2, y2 = end
    # Build hatch lines across a wedge footprint.
    x, y, x0, y0 = geometry.find_parallel( x1, y1, x2, y2, self.wedge_width/2.0)
    xa, ya, xb, yb = geometry.find_parallel( x1, y1, x2, y2, self.line_width/2.0)
    d = geometry.point_distance( x1, y1, x2, y2)
    if d == 0:
      return
    dx1 = (x0 - xa) / d
    dy1 = (y0 - ya) / d
    dx2 = (2*x2 - x0 - 2*x1 + xa) / d
    dy2 = (2*y2 - y0 - 2*y1 + ya) / d
    step_size = 2 * self.line_width
    ns = round( d / step_size) or 1
    step_size = d / ns
    for i in range( 1, int( round( d / step_size)) + 1):
      coords = [xa+dx1*i*step_size, ya+dy1*i*step_size, 2*x1-xa+dx2*i*step_size, 2*y1-ya+dy2*i*step_size]
      if coords[0] == coords[2] and coords[1] == coords[3]:
        if (dx1+dx2) > (dy1+dy2):
          coords[0] += 1
        else:
          coords[1] += 1
      self._draw_line( parent, coords[:2], coords[2:], line_width=self.line_width, capstyle="butt", stroke_color=stroke_color)

  def _draw_side_hatch( self, parent, start, end, side=1, stroke_color=None):
    x1, y1 = start
    x2, y2 = end
    d = geometry.point_distance( x1, y1, x2, y2)
    if d == 0:
      return
    dx = (x2 - x1) / d
    dy = (y2 - y1) / d
    px = -dy
    py = dx
    step_size = 2 * self.line_width
    ns = round( d / step_size) or 1
    step_size = d / ns
    offset = side * self.wedge_width
    for i in range( 0, int( round( d / step_size)) + 1):
      bx = x1 + dx * i * step_size
      by = y1 + dy * i * step_size
      ex = bx + px * offset
      ey = by + py * offset
      self._draw_line( parent, (bx, by), (ex, ey), line_width=self.line_width, capstyle="butt", stroke_color=stroke_color)

  def _draw_wavy( self, parent, start, end, style="sine", line_width=1, stroke_color=None):
    points = self._wave_points( start, end, style=style)
    if not points:
      return
    attrs = (( 'points', " ".join( "%s,%s" % (x, y) for x, y in points)),
             ( 'fill', 'none'),
             ( 'stroke-width', str( line_width)))
    if stroke_color:
      attrs += (( 'stroke', stroke_color),)
    dom_extensions.elementUnder( parent, 'polyline', attrs)

  def _draw_wide_rectangle( self, parent, start, end, fill_color=None):
    x1, y1 = start
    x2, y2 = end
    d = geometry.point_distance( x1, y1, x2, y2)
    if d == 0:
      return
    dx = (x2 - x1) / d
    dy = (y2 - y1) / d
    px = -dy
    py = dx
    half = (self.line_width * self.bold_line_width_multiplier) / 2.0
    points = [(x1 + px * half, y1 + py * half),
              (x1 - px * half, y1 - py * half),
              (x2 - px * half, y2 - py * half),
              (x2 + px * half, y2 + py * half)]
    self._draw_polygon( parent, points, fill_color=fill_color or "#000", stroke_color="none")

  def _wave_points( self, start, end, style="sine"):
    x1, y1 = start
    x2, y2 = end
    d = geometry.point_distance( x1, y1, x2, y2)
    if d == 0:
      return []
    dx = (x2 - x1) / d
    dy = (y2 - y1) / d
    px = -dy
    py = dx
    amplitude = max( self.line_width * 1.5, 1.0)
    wavelength = max( self.line_width * 6.0, 6.0)
    steps = int( max( d / (wavelength / 8.0), 8))
    step_size = d / steps
    points = []
    for i in range( steps + 1):
      t = i * step_size
      phase = (t / wavelength)
      if style == "triangle":
        value = 2 * abs( 2 * (phase - math.floor( phase + 0.5))) - 1
      elif style == "box":
        value = 1.0 if math.sin( 2 * math.pi * phase) >= 0 else -1.0
      elif style == "half-circle":
        half = wavelength / 2.0
        local = (t % half) / half
        value = math.sqrt( max( 0.0, 1 - (2 * local - 1) ** 2))
        if int( t / half) % 2:
          value *= -1
      else:
        value = math.sin( 2 * math.pi * phase)
      ox = px * amplitude * value
      oy = py * amplitude * value
      points.append( (x1 + dx * t + ox, y1 + dy * t + oy))
    return points

  def _edge_color( self, e):
    color = getattr( e, "line_color", None)
    if not color:
      color = e.properties_.get( "line_color") or e.properties_.get( "color")
    return color or None

  def _wavy_style( self, e):
    return (getattr( e, "wavy_style", None)
            or e.properties_.get( "wavy_style")
            or "sine")

  def _bond_line_width( self, e):
    if e.type == 'b':
      return self.line_width * self.bold_line_width_multiplier
    return self.line_width

  def _draw_circle( self, parent, xy, radius=5, fill_color="#fff", stroke_color="#fff", id="", opacity=0):
    x, y = xy
    el = dom_extensions.elementUnder( parent, 'ellipse',
                                      (( 'cx', str( x)),
                                       ( 'cy', str( y)),
                                       ( 'rx', str( radius)),
                                       ( 'ry', str( radius)),
                                       ( 'stroke-width', "1"),
                                       ( 'fill', fill_color),
                                       ( 'stroke', stroke_color),
                                       ( 'fill-opacity', str(opacity)),
                                       ( 'stroke-opacity', str(opacity)),
                                      ))
    if id:
      el.setAttribute( "id", id)


def mol_to_svg( mol, filename):
  c = svg_out()
  tree = c.mol_to_svg( mol)
  with open(filename, 'wb') as f:
    f.write(tree.toxml('utf-8'))


if __name__ == "__main__":

  #from . import inchi
  #mol = inchi.text_to_mol( "1/C7H6O2/c8-7(9)6-4-2-1-3-5-6/h1-5H,(H,8,9)", include_hydrogens=False, calc_coords=30)
  #from . import smiles
  #mol = smiles.text_to_mol( "CC[CH]", calc_coords=40)
  from . import molfile
  mol = molfile.file_to_mol(open("/home/beda/bkchem/bkchem/untitled0.mol", "r"))
  mol_to_svg( mol, "output.svg")
