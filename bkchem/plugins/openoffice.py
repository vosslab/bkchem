#--------------------------------------------------------------------------
#     This file is part of BKchem - a chemical drawing program
#     Copyright (C) 2002  Beda Kosata <kosatab@vscht.cz>

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
#
#
#
#--------------------------------------------------------------------------

"""Openoffice Draw export plugin"""

# there is a problem with font sizes. It seems that OpenOffice does not distinguish
# between pt and px. Unfortunately it seems that the font sizes handling is also different
# in the Tcl/Tk 8.3.4 than in the version I have used before. Maybe I would have to switch
# to px sizes instead of pt sizes.


import plugin
import xml.dom.minidom as dom
import dom_extensions as dom_ext
import dom_extensions
import math
import operator
import os_support

## DEFINITIONS

class OO_exporter( plugin.exporter):

  def __init__( self, paper):
    self.paper = paper
    self.used_styles = []

  def on_begin( self):
    return 1
##     import tkMessageBox
##     yes = tkMessageBox.askyesno( _("Really export?"),
##                                  _('This plugin is not finished and will probably not work correctly.') + ' ' +
##                                  _('Proceed?'))
##     return yes

  def write_to_file( self, name):
    self.doc = dom.Document()
    out = self.doc
    root = dom_ext.elementUnder( out, 'office:document-content',
                                 (('office:class', 'drawing'),
                                  ('office:version', '1.0'),
                                  ('xmlns:draw', 'http://openoffice.org/2000/drawing'),
                                  ('xmlns:form', "http://openoffice.org/2000/form"),
                                  ('xmlns:office',"http://openoffice.org/2000/office"),
                                  ('xmlns:style',"http://openoffice.org/2000/style"),
                                  ('xmlns:svg',"http://www.w3.org/2000/svg"),
                                  ('xmlns:text',"http://openoffice.org/2000/text"),
                                  ('xmlns:fo',"http://www.w3.org/1999/XSL/Format")))

    self.styles_element = dom_ext.elementUnder( root, 'office:automatic-styles')
    # drawing page
    body = dom_ext.elementUnder( root, 'office:body')
    page = dom_ext.elementUnder( body, 'draw:page', (('draw:master-page-name','vychozi'),
                                                     ('draw:name', 'page1')))
    for o in self.paper.stack:
      if o.object_type == 'molecule':
        group = dom_ext.elementUnder( page, 'draw:g')
        for b in o.bonds:
          self.add_bond( b, group)
        for b in o.atoms_map:
          self.add_atom( b, group)
      elif o.object_type == 'arrow':
        self.add_arrow( o, page)
      elif o.object_type == 'text':
        self.add_text( o, page)
      elif o.object_type == 'plus':
        self.add_plus( o, page)
      elif o.object_type == 'rect':
        self.add_rect( o, page)
      elif o.object_type == 'oval':
        self.add_oval( o, page)
      elif o.object_type == 'polygon':
        self.add_polygon( o, page)

#    dom_ext.safe_indent( root)
    
    import tempfile
    # content file
    cfname = tempfile.mktemp()
    f = open( cfname, "w")
    f.write( out.toxml())
    f.close()
    # styles file
    sfname = tempfile.mktemp()
    f = open( sfname, "w")
    f.write( self.create_styles_document().toxml())
    f.close()
    import zipfile
    zip = zipfile.ZipFile( name, 'w', zipfile.ZIP_DEFLATED)
    manifest = os_support.get_path( 'oo_manifest.xml', 'template')
    if manifest:
      zip.write( os_support.get_path( 'oo_manifest.xml', 'template'), 'META-INF/manifest.xml')
      zip.write( cfname, 'content.xml')
      zip.write( sfname, 'styles.xml')
      zip.close()
    else:
      zip.close()
      raise plugin.export_exception( _("The manifest file not found in the plugin directory"))


  def add_bond( self, b, page):
    """adds bond item to page"""
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( b.line_color),
                        stroke_width=self.paper.px_to_cm( b.line_width))
    style_name = self.get_appropriate_style_name( s)
    l_group = page
    if b.type <= 3:
      if not (b.type == 2 and b.center): 
        coords = reduce( operator.add, [o.get_xy() for o in b.get_atoms()])
        coords = map( self.paper.px_to_cm, coords)
        self.create_oo_line( coords, page, style_name)
      if b.second:
        coords = map( self.paper.px_to_cm, self.paper.coords( b.second))
        self.create_oo_line( coords, page, style_name)
      if b.third:
        coords = map( self.paper.px_to_cm, self.paper.coords( b.third))
        self.create_oo_line( coords, page, style_name)
    elif b.type == 4:
      s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( b.line_color),
                          fill_color=self.paper.any_color_to_rgb_string( b.line_color))
      style_name = self.get_appropriate_style_name( s)
      x1, y1, x2, y2, x3, y3 = map( self.paper.px_to_cm, self.paper.coords( b.item))
      point_array = [(x1,y1), (x2,y2), (x3,y3)]
      self.create_oo_polygon( point_array, page, style_name)
    elif b.type == 5:
      for i in b.items:
        coords = map( self.paper.px_to_cm, self.paper.coords( i))
        self.create_oo_line( coords, page, style_name)


  def add_atom( self, a, page):
    """adds atom to document"""
    if a.show:
      gr_style = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( a.line_color),
                                 fill_color=self.paper.any_color_to_rgb_string( a.area_color))
      gr_style_name = self.get_appropriate_style_name( gr_style)
      para_style = paragraph_style( font_size='%dpx' % round(a.font_size*1), font_family=a.font_family, color=a.line_color)
      para_style_name = self.get_appropriate_style_name( para_style)
      txt_style = text_style( font_size='%dpx' % round(a.font_size*1), font_family=a.font_family)
      txt_style_name = self.get_appropriate_style_name( txt_style)

      coords = map( self.paper.px_to_cm, self.paper.coords( a.selector))
      self.create_oo_text( '<ftext>%s</ftext>' % a.get_ftext(), coords, page, para_style_name, txt_style_name, gr_style_name)
    # marks
    for name,m in a.marks.iteritems():
      if m:
        if name == 'radical':
          self.add_radical_mark( m, page)
        elif name == 'biradical':
          self.add_radical_mark( m, page)
        elif name == 'electronpair':
          self.add_electronpair_mark( m, page)
        elif name == 'minus':
          self.add_plus_mark( m, page)
        elif name == 'plus':
          self.add_plus_mark( m, page)

##       s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( m.outline),
##                           fill_color=self.paper.any_color_to_rgb_string( m.line_color),
##                           stroke_width=self.paper.px_to_cm( o.line_width))
##       style_name = self.get_appropriate_style_name( s)
##       x, y, x2, y2 = map( self.paper.px_to_cm, o.coords)
##       dom_extensions.elementUnder( page, 'draw:rect',
##                                    (( 'svg:x', '%fcm' %  x),
##                                     ( 'svg:y', '%fcm' %  y),
##                                     ( 'svg:width', '%fcm' %  (x2-x)),
##                                     ( 'svg:height', '%fcm' % (y2-y)),
##                                     ( 'draw:style-name', style_name)))



  def add_text( self, a, page):
    """adds text object to document"""
    gr_style = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( a.line_color),
                                 fill_color=self.paper.any_color_to_rgb_string( a.area_color))
    gr_style_name = self.get_appropriate_style_name( gr_style)
    para_style = paragraph_style( font_size='%dpx' % round(a.font_size*1), font_family=a.font_family, color=a.line_color)
    para_style_name = self.get_appropriate_style_name( para_style)
    txt_style = text_style( font_size='%dpx' % round(a.font_size*1), font_family=a.font_family)
    txt_style_name = self.get_appropriate_style_name( txt_style)

    coords = map( self.paper.px_to_cm, self.paper.coords( a.selector))
    self.create_oo_text( '<ftext>%s</ftext>' % a.text, coords, page, para_style_name, txt_style_name, gr_style_name)


  def add_plus( self, a, page):
    """adds text object to document"""
    gr_style = graphics_style()
    gr_style_name = self.get_appropriate_style_name( gr_style)
    para_style = paragraph_style( font_size='%dpx' % round(a.font_size*1), font_family=a.font_family, color=a.line_color)
    para_style_name = self.get_appropriate_style_name( para_style)
    txt_style = text_style( font_size='%dpx' % round(a.font_size*1), font_family=a.font_family)
    txt_style_name = self.get_appropriate_style_name( txt_style)

    coords = map( self.paper.px_to_cm, self.paper.coords( a.selector))
    self.create_oo_text( '<ftext>+</ftext>', coords, page, para_style_name, txt_style_name, gr_style_name)

  def add_arrow( self, a, page):
    end_pin, start_pin = None,None
    if a.pin==1 or a.pin==3:
      end_pin = 1
    if a.pin==2 or a.pin==3:
      start_pin = 1
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( a.line_color),
                        marker_end=end_pin,
                        marker_start=start_pin,
                        stroke_width=self.paper.px_to_cm( a.line_width))
    style_name = self.get_appropriate_style_name( s)
    point_array = []
    maxX, maxY, minX, minY = None,None,None,None
    for p in a.points:
      x,y = map( self.paper.px_to_cm, p.get_xy())
      if not maxX or x > maxX:
        maxX = x
      if not minX or x < minX:
        minX = x
      if not maxY or y > maxY:
        maxY = y
      if not minY or y < minY:
        minY = y
      point_array.append( (x,y))
    points = ""
    for (x,y) in point_array:
      points += "%d,%d " % ((x-minX)*1000, (y-minY)*1000)

    line = dom_extensions.elementUnder( page, 'draw:polyline',
                                        (( 'svg:x', '%fcm' % minX),
                                         ( 'svg:y', '%fcm' % minY),
                                         ( 'svg:width', '%fcm' % (maxX-minX)),
                                         ( 'svg:height', '%fcm' % (maxY-minY)),
                                         ( 'svg:viewBox', '0 0 %d %d' % ((maxX-minX)*1000,(maxY-minY)*1000)),
                                         ( 'draw:points', points),
                                         ( 'draw:layer', 'layout'),
                                         ( 'draw:style-name', style_name)))


  def add_polygon( self, o, page):
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( o.line_color),
                        fill_color=self.paper.any_color_to_rgb_string( o.area_color),
                        stroke_width=self.paper.px_to_cm( o.line_width))
    style_name = self.get_appropriate_style_name( s)
    points = [map( self.paper.px_to_cm, p.get_xy()) for p in o.points]
    self.create_oo_polygon( points, page, style_name)

  def add_rect( self, o, page):
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( o.line_color),
                        fill_color=self.paper.any_color_to_rgb_string( o.area_color),
                        stroke_width=self.paper.px_to_cm( o.line_width))
    style_name = self.get_appropriate_style_name( s)
    x, y, x2, y2 = map( self.paper.px_to_cm, o.coords)
    dom_extensions.elementUnder( page, 'draw:rect',
                                       (( 'svg:x', '%fcm' %  x),
                                        ( 'svg:y', '%fcm' %  y),
                                        ( 'svg:width', '%fcm' %  (x2-x)),
                                        ( 'svg:height', '%fcm' % (y2-y)),
                                        ( 'draw:style-name', style_name)))
    

  def add_oval( self, o, page):
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( o.line_color),
                        fill_color=self.paper.any_color_to_rgb_string( o.area_color),
                        stroke_width=self.paper.px_to_cm( o.line_width))
    style_name = self.get_appropriate_style_name( s)
    x, y, x2, y2 = map( self.paper.px_to_cm, o.coords)
    dom_extensions.elementUnder( page, 'draw:ellipse',
                                       (( 'svg:x', '%fcm' %  x),
                                        ( 'svg:y', '%fcm' %  y),
                                        ( 'svg:width', '%fcm' %  (x2-x)),
                                        ( 'svg:height', '%fcm' % (y2-y)),
                                        ( 'draw:style-name', style_name)))
    

  def add_radical_mark( self, o, page):
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( o.atom.line_color),
                        fill_color=self.paper.any_color_to_rgb_string( o.atom.line_color),
                        stroke_width=self.paper.px_to_cm( 0.1))
    style_name = self.get_appropriate_style_name( s)
    for i in o.items:
      x, y, x2, y2 = map( self.paper.px_to_cm, self.paper.coords( i))
      size = self.paper.px_to_cm( o.size)
      dom_extensions.elementUnder( page, 'draw:ellipse',
                                   (( 'svg:x', '%fcm' %  x),
                                    ( 'svg:y', '%fcm' %  y),
                                    ( 'svg:width', '%fcm' %  size),
                                    ( 'svg:height', '%fcm' % size),
                                    ( 'draw:style-name', style_name)))

  def add_electronpair_mark( self, o, page):
    i = o.items[0]
    width = float( self.paper.itemcget( i, 'width'))
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( o.atom.line_color),
                        fill_color=self.paper.any_color_to_rgb_string( o.atom.line_color),
                        stroke_width=self.paper.px_to_cm( width))
    style_name = self.get_appropriate_style_name( s)
    coords = map( self.paper.px_to_cm, self.paper.coords( i))
    self.create_oo_line( coords, page, style_name)
      

  def add_plus_mark( self, o, page):
    s = graphics_style( stroke_color=self.paper.any_color_to_rgb_string( o.atom.line_color),
                        fill_color=self.paper.any_color_to_rgb_string( o.atom.area_color),
                        stroke_width=self.paper.px_to_cm( 1))
    style_name = self.get_appropriate_style_name( s)
    for i in o.items:
      if o.items.index( i) == 0:
        x, y, x2, y2 = map( self.paper.px_to_cm, self.paper.coords( i))
        size = self.paper.px_to_cm( o.size)
        dom_extensions.elementUnder( page, 'draw:ellipse',
                                     (( 'svg:x', '%fcm' %  x),
                                      ( 'svg:y', '%fcm' %  y),
                                      ( 'svg:width', '%fcm' %  size),
                                      ( 'svg:height', '%fcm' % size),
                                      ( 'draw:style-name', style_name)))
      else:
        coords = self.paper.coords( i)
        # because some weird bug in tcl/tk i had to hack the coordinates in marks.py
        # the hack is reversed here in order to get the coords back
        if o.items.index( i) == 1:
          coords[0] += -1
        elif o.items.index( i) == 2:
          coords[1] += -1
        # end of hack
        coords = map( self.paper.px_to_cm, coords)
        self.create_oo_line( coords, page, style_name)
        



# HELPER METHODS

  def get_appropriate_style_name( self, style):
    """if same style already exists return its name, otherwise append the current style and return its name"""
    for s in self.used_styles:
      if style == s:
        return s.name
    style.name = style.name + str( len( self.used_styles))
    self.used_styles.append( style)
    self.styles_element.appendChild( style.to_dom( self.doc))
    return style.name

  def ftext_dom_to_oo_dom( self, ftext, oo_dom):
    if ftext.nodeValue:
      # style inherited from parents
      parents = dom_extensions.getParentNameList( ftext)
      font_weight, font_style, text_position = None, None, None
      if 'b' in parents:
        font_weight = 'bold'
      if 'i' in parents:
        font_style = 'italic'
      if 'sub' in parents:
        text_position = "sub 70%"
      if 'sup' in parents:
        text_position = "super 70%"

      if ftext.parentNode.nodeName == 'ftext':
        oo_dom.appendChild( oo_dom.ownerDocument.createTextNode( ftext.nodeValue))
      else:
        st = span_style( font_style=font_style, font_weight=font_weight, text_position=text_position)
        element = dom_extensions.elementUnder( oo_dom, 'text:span', (('text:style-name', self.get_appropriate_style_name( st)),))
        element.appendChild( oo_dom.ownerDocument.createTextNode( ftext.nodeValue))
    else:
      for el in ftext.childNodes:
        self.ftext_dom_to_oo_dom( el, oo_dom)

## AUTOMATIZED CREATION OF OO OBJECTS

  def create_oo_line( self, coords, page, gr_style_name):
    x1, y1, x2, y2 = coords
    dom_extensions.elementUnder( page, 'draw:line',
                                 (( 'svg:x1', '%fcm' %  x1),
                                  ( 'svg:y1', '%fcm' %  y1),
                                  ( 'svg:x2', '%fcm' %  x2),
                                  ( 'svg:y2', '%fcm' %  y2),
                                  ( 'draw:layer', 'layout'),
                                  ( 'draw:style-name', gr_style_name)))
    

  def create_oo_text( self, ftext, coords, page, para_style_name, txt_style_name, gr_style_name):
    x, y, x2, y2 = coords
    box = dom_extensions.elementUnder( page, 'draw:text-box',
                                       (( 'svg:x', '%fcm' %  x),
                                        ( 'svg:y', '%fcm' %  y),
                                        ( 'svg:width', '%fcm' %  (x2-x)),
                                        ( 'svg:height', '%fcm' % (y2-y)),
                                        ( 'draw:style-name', gr_style_name),
                                        ( 'draw:text-style-name', para_style_name)))

    text = dom_extensions.elementUnder( box, 'text:p', (('text:style-name', para_style_name),))
    oo_text = dom_extensions.elementUnder( text, 'text:span', (('text:style-name', '%s' % txt_style_name),))
    to_parse = dom.parseString( ftext).childNodes[0]
    self.ftext_dom_to_oo_dom( to_parse, oo_text)

  def create_oo_polygon( self, points, page, gr_style_name):
    maxX, maxY, minX, minY = None,None,None,None
    for (x,y) in points:
      if not maxX or x > maxX:
        maxX = x
      if not minX or x < minX:
        minX = x
      if not maxY or y > maxY:
        maxY = y
      if not minY or y < minY:
        minY = y
    points_txt = ""
    for (x,y) in points:
      points_txt += "%d,%d " % ((x-minX)*1000, (y-minY)*1000)

    dom_extensions.elementUnder( page, 'draw:polygon',
                                 (( 'svg:x', '%fcm' % minX),
                                  ( 'svg:y', '%fcm' % minY),
                                  ( 'svg:width', '%fcm' % (maxX-minX)),
                                  ( 'svg:height', '%fcm' % (maxY-minY)),
                                  ( 'svg:viewBox', '0 0 %d %d' % ((maxX-minX)*1000,(maxY-minY)*1000)),
                                  ( 'draw:points', points_txt),
                                  ( 'draw:layer', 'layout'),
                                  ( 'draw:style-name', gr_style_name)))



  def create_styles_document( self):
    style_doc = dom.Document()
    root = dom_ext.elementUnder( style_doc, 'office:document-styles',
                                 (('office:version', '1.0'),
                                  ('xmlns:draw', 'http://openoffice.org/2000/drawing'),
                                  ('xmlns:form', "http://openoffice.org/2000/form"),
                                  ('xmlns:office',"http://openoffice.org/2000/office"),
                                  ('xmlns:style',"http://openoffice.org/2000/style"),
                                  ('xmlns:svg',"http://www.w3.org/2000/svg"),
                                  ('xmlns:text',"http://openoffice.org/2000/text"),
                                  ('xmlns:fo',"http://www.w3.org/1999/XSL/Format")))


    w = self.paper.get_paper_property( 'size_x')/10.0
    h = self.paper.get_paper_property( 'size_y')/10.0
    s = dom_ext.elementUnder( root, 'office:styles')
    as = dom_ext.elementUnder( root, 'office:automatic-styles')
    pm = dom_ext.elementUnder( as, 'style:page-master', (('style:name','PM1'),))
    dom_ext.elementUnder( pm, 'style:properties', (('fo:page-height','%fcm' % h),
                                                   ('fo:page-width','%fcm' % w),
                                                   ('style:print-orientation','portrait'),
                                                   ('fo:margin-bottom','0.5cm'),
                                                   ('fo:margin-left','0.5cm'),
                                                   ('fo:margin-top','0.5cm'),
                                                   ('fo:margin-right','0.5cm')))
    dp = dom_ext.elementUnder( as, 'style:style', (('style:family', 'drawing-page'),
                                                   ('style:name', 'dp1')))
    dom_ext.elementUnder( dp, 'style:properties', (('draw:backgroud-size','border'),
                                                   ('draw:fill', 'none')))

    oms = dom_ext.elementUnder( root, 'office:master-styles')
    mp = dom_ext.elementUnder( oms, 'style:master-page', (('draw:style-name','dp1'),
                                                          ('style:page-master-name','PM1'),
                                                          ('style:name', 'vychozi')))
    return style_doc


  
# PLUGIN INTERFACE SPECIFICATION
name = "OpenOffice Draw"
extensions = [".sxd",".zip"]
exporter = OO_exporter


## PRIVATE CLASSES AND FUNCTIONS

class style:

  def __init__( self):
    pass

  def __eq__( self, other):
    for a in self.__dict__:
      if a == 'name':
        continue
      if a in other.__dict__:
        if self.__dict__[a] != other.__dict__[a]:
          return 0
      else:
        return 0
    return 1

  def __ne__( self, other):
    return not self.__eq__( other)

  def to_dom( self, doc):
    pass

class graphics_style( style):

  def __init__( self, name='gr', stroke_color='#ffffff', fill='solid', fill_color='#ffffff', stroke_width=1,
                marker_end=None, marker_end_width=None, marker_start=None, marker_start_width=None):
    self.name = name
    self.family = 'graphics'
    self.stroke_color = stroke_color
    self.fill = fill
    self.fill_color = fill_color
    self.stroke_color = stroke_color
    self.stroke_width = stroke_width
    self.marker_end = marker_end
    self.marker_end_width = marker_end_width
    self.marker_start = marker_start
    self.marker_start_width = marker_start_width

  def to_dom( self, doc):
    style = doc.createElement( 'style:style')
    dom_extensions.setAttributes( style, (('style:family', self.family),
                                          ('style:name', self.name),
                                          ('style:parent-style-name','standard')))
    prop = dom_extensions.elementUnder( style, 'style:properties', (( 'draw:fill', self.fill),
                                                                    ( 'svg:stroke-color', self.stroke_color),
                                                                    ( 'draw:fill-color', self.fill_color),
                                                                    ( 'svg:stroke-width', '%fcm' % self.stroke_width),
                                                                    ( 'draw:auto-grow-width', 'true'),
                                                                    ( 'draw:auto-grow-height', 'true')))
    if self.marker_end:
      prop.setAttribute( 'draw:marker-end', 'Arrow')
      if self.marker_end_width:
        prop.setAttribute( 'draw:marker-end-width',
                           "%dcm" % self.marker_end_width)
    if self.marker_start:
      prop.setAttribute( 'draw:marker-start', 'Arrow')
      if self.marker_start_width:
        prop.setAttribute( 'draw:marker-start-width',
                           "%dcm" % self.marker_start_width)
      
    return style


class paragraph_style( style):

  def __init__( self, name='para', font_size='12pt', font_family='Helvetica', color="#000"):
    self.name = name
    self.family = 'paragraph'
    self.font_size = font_size
    if font_family in font_family_remap:
      self.font_family = font_family_remap[ font_family]
    else:
      self.font_family = font_family
    self.color = color


  def to_dom( self, doc):
    style = doc.createElement( 'style:style')
    dom_extensions.setAttributes( style, (('style:family', self.family),
                                          ('style:name', self.name)))
    dom_extensions.elementUnder( style, 'style:properties', (( 'fo:font-size', self.font_size),
                                                             ( 'fo:font-family', self.font_family),
                                                             ( 'fo:text-align', 'center'),
                                                             ( 'fo:color', self.color)))
    return style


class text_style( style):

  def __init__( self, name='text', font_size='12pt', font_family='Helvetica', font_style='normal', font_weight='normal'):
    self.name = name
    self.family = 'text'
    if font_family in font_family_remap:
      self.font_family = font_family_remap[ font_family]
    else:
      self.font_family = font_family
    self.font_size = font_size
    self.font_style = font_style
    self.font_weight = font_weight

  def to_dom( self, doc):
    style = doc.createElement( 'style:style')
    dom_extensions.setAttributes( style, (('style:family', self.family),
                                          ('style:name', self.name)))
    prop = dom_extensions.elementUnder( style, 'style:properties', (( 'fo:font-size', self.font_size),
                                                                    ( 'fo:font-family', self.font_family),
                                                                    ( 'fo:font-style', self.font_style),
                                                                    ( 'fo:font-weight', self.font_weight)))
    return style


class span_style( style):

  def __init__( self, name='span', font_style=None, font_weight=None, text_position=None):
    self.name = name
    self.family = 'text'
    self.font_style = font_style
    self.font_weight = font_weight
    self.text_position = text_position

  def to_dom( self, doc):
    style = doc.createElement( 'style:style')
    dom_extensions.setAttributes( style, (('style:family', self.family),
                                          ('style:name', self.name)))
    prop = dom_extensions.elementUnder( style, 'style:properties')
    if self.font_style:
      prop.setAttribute( 'fo:font-style', self.font_style)
    if self.font_weight:
      prop.setAttribute( 'fo:font-weight', self.font_weight)
    if self.text_position:
      prop.setAttribute( 'style:text-position', self.text_position)
      
    return style


font_family_remap = {'helvetica': 'Albany',
                     'times': 'Thorndale'}