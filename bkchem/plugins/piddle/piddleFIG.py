"""piddleFIG - a Fig version 3.2 backend for the PIDDLE drawing module

Note that files are not stored in the .fig file itself, because the .fig format
does not allow for that; instead, they are placed in a directory named after
the name argument passed to FIGCanvas.

Also note that the max number of colours is 512, due to a .fig limitation.

2002 John J Lee

"""

# XXX
# Bugs:
#   string widths aren't right
#   transparent lines aren't transparent
# Could try harder:
#   latex fonts not supported
#   depths are all set to 50, which may be a mistake -- perhaps increment for
#    every object plotted?
#   could use default colours

import math, string, re, os

from . import piddlePSmetrics
from .piddle import *

degrees = math.pi / 180
# XXX should just use bp all the time, even for text?  not clear from piddle
#   docs
pt = 1200/72.27  # points
bp = 1200/72  # big points
bp_width = 80/72  # xfig measures in 1/80 for linewidths

# lifted from piddlePS
Roman="Roman"; Bold="Bold"; Italic="Italic"
PSFontMapStdEnc = { ("helvetica", Roman): "Helvetica-Roman",
                    ("helvetica", Bold): "Helvetica-Bold",
                    ("helvetica", Italic): "Helvetica-Oblique",
                    ("times", Roman) : "Times-Roman",
                    ("times", Bold) : "Times-Bold",
                    ("times", Italic) : "Times-Italic",
                    ("courier", Roman) : "Courier-Roman",
                    ("courier", Bold) : "Courier-Bold",
                    ("courier", Italic) : "Courier-Oblique",
                    ("symbol", Roman) : "Symbol",
                    ("symbol", Bold) :  "Symbol",
                    ("symbol", Italic) : "Symbol",
                    "EncodingName" : 'StandardEncoding' }


PSFontMapLatin1Enc = { ("helvetica", Roman): "Helvetica-Roman-ISOLatin1",
                       ("helvetica", Bold): "Helvetica-Bold-ISOLatin1",
                       ("helvetica", Italic): "Helvetica-Oblique-ISOLatin1",
                       ("times", Roman) : "Times-Roman-ISOLatin1",
                       ("times", Bold) : "Times-Bold-ISOLatin1",
                       ("times", Italic) : "Times-Italic-ISOLatin1",
                       ("courier", Roman) : "Courier-Roman-ISOLatin1",
                       ("courier", Bold) : "Courier-Bold-ISOLatin1",
                       ("courier", Italic) : "Courier-Oblique-ISOLatin1",
                       ("symbol", Roman) : "Symbol",
                       ("symbol", Bold) :  "Symbol",
                       ("symbol", Italic) : "Symbol",
                       "EncodingName" : 'Latin1Encoding' }

def color_distance(col1, col2):
    diff = col2 - col1
    return math.sqrt(diff.red**2 + diff.green**2 + diff.blue**2)


class FIGCanvas(Canvas):
    """Fig version 3.2 format canvas.

    This canvas is meant for generating Fig 3.2 format files (.fig), used for
    editing in the free xfig vector graphics program for X windows.
    """
    header_fmt = \
"""#FIG 3.2
%(orientation)s
%(justification)s
%(units)s
%(papersize)s
%(magnification)f
%(multiple-page)s
%(transparent-color)d
# Generated by PIDDLE
1200 2
"""
    text_fmt = ("4 %(justification)d %(color)d %(depth)d %(pen_style)d "
                "%(font)d %(font_size)f %(angle)f %(font_flags)d "
                "%(height)f %(length)f %(x)d %(y)d %(text)s")
    poly_fmt = ("2 %(line_type)d %(line_style)d %(thickness)d "
                "%(pen_color)d %(fill_color)d %(depth)d %(pen_style)d "
                "%(area_fill)d %(style_val)f %(join_style)d "
                "%(cap_style)d %(radius)d "
                "%(forward_arrow)d %(backward_arrow)d %(npoints)d")
    color_fmt = "0 %d #%.2x%.2x%.2x"  # rgb value
    coord_fmt = "%d %d"
    # header options
    # orientation
    Landscape = "Landscape"
    Portrait = "Portrait"
    # justification
    CenterJust = "Center"
    FlushLeftJust = "Flush Left"
    # units
    Metric = "Metric"
    Imperial = "Inches"
    # papersize
    Letter = "Letter"
    Legal = "Legal"
    Ledger = "Ledger"
    Tabloid = "Tabloid"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    A4 = "A4"
    A3 = "A3"
    A2 = "A2"
    A1 = "A1"
    A0 = "A0"
    B5 = "B5"
    # magnification (percentage)
    # multiple-page
    SinglePage = "Single"
    MultiplePage = "Multiple"
    # color number for transparent color for GIF export
    # transparent-color
    NoTransp = -2
    BackgroundTransp = -1
    # 0-31 for standard colors or 32- for user colors

    # object types
    Color = 0  # Color pseudo-object.
    Arc = 1
    Ellipse = 2
    Polyline = 3  # includes polygon and box
    Spline = 4  # includes closed/open approximated/interpolated/x-spline spline
    Text = 5
    Compound = 6  # Compound object which is composed of one or more objects

    # line_style
    DefaultLineStyle = -1
    Solid = 0
    Dashed = 1
    Dotted = 2
    Dash_dotted = 3
    Dash_double_dotted = 4
    Dash_triple_dotted = 5

    # polyline style
    PolyLine = 1
    Box = 2
    Polygon = 3
    ArcBox = 4
    BoundingBox = 5  # imported-picture bounding-box

    # text justification
    Left = 0
    Center = 1
    Right = 2

    # font style
    Rigid = 1  # text doesn't scale when scaling compound objects
    Special = 2  # for LaTeX
    Postscript = 4  # PostScript font (otherwise LaTeX font is used)
    Hidden = 8  # Hidden text

    # For font_flags bit 2 = 0 (LaTeX fonts)
    DefaultFont = 0
    Roman = 1
    Bold = 2
    Italic = 3
    SansSerif = 4
    Monospaced = 5

    # For font_flags bit 2 = 1 (PostScript fonts)
    DefaultFont = -1
    TimesRoman = 0
    TimesItalic = 1
    TimesBold = 2
    TimesBoldItalic = 3
    AvantGardeBook = 4
    AvantGardeBookOblique = 5
    AvantGardeDemi = 6
    AvantGardeDemiOblique = 7
    BookmanLight = 8
    BookmanLightItalic = 9
    BookmanDemi = 10
    BookmanDemiItalic = 11
    Courier = 12
    CourierOblique = 13
    CourierBold = 14
    CourierBoldOblique = 15
    Helvetica = 16
    HelveticaOblique = 17
    HelveticaBold = 18
    HelveticaBoldOblique = 19
    HelveticaNarrow = 20
    HelveticaNarrowOblique = 21
    HelveticaNarrowBold = 22
    HelveticaNarrowBoldOblique = 23
    NewCenturySchoolbookRoman = 24
    NewCenturySchoolbookItalic = 25
    NewCenturySchoolbookBold = 26
    NewCenturySchoolbookBoldItalic = 27
    PalatinoRoman = 28
    PalatinoItalic = 29
    PalatinoBold = 30
    PalatinoBoldItalic = 31
    Symbol = 32
    ZapfChanceryMediumItalic = 33
    ZapfDingbats = 34

    # join_style field (for lines)
    Miter = 0
    Bevel = 1
    Round = 2

    # cap_style (for lines, open splines and arcs only)
    Butt = 0
    Round = 1
    Projecting = 2

    # arrow_type (lines, arcs and open splines)
    Stick = 0
    Closed_triangle = 1
    Closed_indented_butt = 2
    Closed_pointed_butt = 3

    # The arrow_style field is defined for lines, arcs and open splines
    Hollow = 0
    Filled = 1

    # Colour values from 32 to 543 (512 total) are user colours and are defined
    # in colour pseudo-objects (type 0).  At the moment these are always used,
    # and the default colours never are.

    # XXX Need to check actual hex values in xfig source before inserting these
    # into the colors dictionary.

    #Default = (-1)
    from .piddle import black, white, red, green ,blue, darkblue, lightblue, \
         cyan, darkcyan, lightcyan, magenta, darkmagenta, yellow, gold
    default_colors = [
        (black, 0), (white, 7),
        (red, 4),# (darkRed, 18), (lightRed, 19), (lightestRed, 20),
        (green, 2),# (darkGreen, 12), (lightGreen, 13), (lightestGreen, 14),
        (blue, 1), #(darkestBlue, 8),
            (darkblue, 9), (lightblue, 10),
##             (lightestBlue, 11),
        (cyan, 3), (darkcyan, 15), (lightcyan, 16),# (lightestCyan, 17),
        (magenta, 5), (darkmagenta, 21),# (lightmagenta, 22),
##             (lightestMagenta, 23),
        (yellow, 6),# (darkBrown, 24), (lightBrown, 25), (lightestBrown, 26),
##         (darkestPink, 27), (darkPink, 28), (lightPink, 29), (lightestPink, 30),
        (gold, 31)]

    # We ignore the baroque system of fill styles, and rely on the normal color
    # system.

    # area fill field for white color
    NotFilled = -1
    Filled = 20
    # -1 = not filled
    # 0 = black
    # ...  values from 1 to 19 are shades of grey, from darker to lighter
    # 20 = white
    # 21-40 not used
    # 41-56 see patterns for colors, below

    # area fill field for black or default color
    # -1 = not filled
    # 0 = white
    # ...  values from 1 to 19 are shades of grey, from lighter to darker
    # 20 = black
    # 21-40 not used
    # 41-56 see patterns for colors, below

    # area fill field for all other colors
    # -1 = not filled
    # 0 = black
    # ...  values from 1 to 19 are "shades" of the color, from darker to lighter.
    # A shade is defined as the color mixed with black
    # 20 = full saturation of the color
    # ...  values from 21 to 39 are "tints" of the color from the color to white.
    # A tint is defined as the color mixed with white
    # 40 = white
    # 41 = 30 degree left diagonal pattern
    # 42 = 30 degree right diagonal pattern
    # 43 = 30 degree crosshatch
    # 44 = 45 degree left diagonal pattern
    # 45 = 45 degree right diagonal pattern
    # 46 = 45 degree crosshatch
    # 47 = bricks
    # 48 = circles
    # 49 = horizontal lines
    # 50 = vertical lines
    # 51 = crosshatch
    # 52 = fish scales
    # 53 = small fish scales
    # 54 = octagons
    # 55 = horizontal "tire treads"
    # 56 = vertical "tire treads"

    # depth
    # 0 ... 999, where larger value means object is deeper than (under) objects
    # with smaller depth

    # indices into font_map, below
    Normal = 0
    Bold = 1
    Italic = 2
    BoldItalic = 3

    font_map = {
        "times": (TimesRoman, TimesBold, TimesItalic, TimesBoldItalic),
        "serif": (TimesRoman, TimesBold, TimesItalic, TimesBoldItalic),
        "helvetica": (Helvetica, HelveticaBold, HelveticaOblique,
                      HelveticaBoldOblique),
        "sansserif": (Helvetica, HelveticaBold, HelveticaOblique,
                      HelveticaBoldOblique),
        "monospaced": (Courier, CourierBold, CourierOblique,
                       CourierBoldOblique),
        "courier": (Courier, CourierBold, CourierOblique, CourierBoldOblique),
        "avantgarde": (AvantGardeBook, AvantGardeDemi, AvantGardeBookOblique,
                       AvantGardeDemiOblique),
        "bookman": (BookmanLight, BookmanDemi, BookmanLightItalic, BookmanDemiItalic),
        "newcenturyschoolbook": (NewCenturySchoolbookRoman,
                                 NewCenturySchoolbookBold,
                                 NewCenturySchoolbookItalic,
                                 NewCenturySchoolbookBoldItalic),
        "palatino": (PalatinoRoman, PalatinoBold, PalatinoItalic,
                     PalatinoBoldItalic),
        "symbol": (Symbol, Symbol, Symbol, Symbol),
        "zapfchancery": (ZapfChanceryMediumItalic,
                         ZapfChanceryMediumItalic,
                         ZapfChanceryMediumItalic,
                         ZapfChanceryMediumItalic),
        "zapfdingbats": (ZapfDingbats, ZapfDingbats, ZapfDingbats,
                         ZapfDingbats)
        }
    defaultFace = "times"

    text_sub = re.compile(r"([\177-\377])")

    def __init__(self, size=(300,300), name='piddleFIG',
                 fontMapEncoding=PSFontMapLatin1Enc):
        Canvas.__init__(self, size, name)
        self.fontMapEncoding = fontMapEncoding
        self.size = size
        self.name = name
        self.color_code = []
        self.code = []
        # indexed by PIDDLE color instances, containing FIG color nr.
        self.colors = {}
        # indexed by PIL image instances, containing file names
        self.images = {}
        self.color_nr = 32  # first user-defined FIG color nr.
        self.fileNameCounter = -1  # for saving images

    def clear(self):
        """Reset canvas to its default state."""
        raise NotImplementedError("clear")

    def save(self, file=None, format=None):
        """Write the current document to a file or stream and close the file.

        The format argument is not used.

        """
        if file is None:
            file = self.name
            if not file.endswith(".fig"):
                file = file+".fig"
        with open(file, "w") as f:
            header = self.header_fmt % {
                "orientation": self.Portrait,
                "justification": self.CenterJust,
                # units only affects the rules displayed in xfig, not the internal
                # units used in the file format
                "units": self.Metric,
                "papersize": self.A4,
                "magnification": 100,
                "multiple-page": self.SinglePage,
                "transparent-color": self.BackgroundTransp
                }
            f.write(header)
            for line in self.color_code+self.code:
                f.write(line)
                f.write("\n")

    def drawLine(self, x1, y1, x2, y2, color=None, width=None):
        """

        x1: horizontal (right) coordinate of the starting point
        y1: vertical (down) coordinate of the starting point
        x2: horizontal (right) coordinate of the ending point
        y2: vertical (down) coordinate of the ending point
        color: Color of the line to draw; defaults to the Canvas's
         defaultLineColor
        width: width of the line to draw; defaults to the Canvas's
         defaultLineWidth

        """
        if color is None:
            color = self.defaultLineColor
        if width is None:
            width = self.defaultLineWidth
        pointlist = [(x1, y1), (x2, y2)]
        self._drawPolygon(pointlist, color, width, self.defaultFillColor, 0,
                          self.NotFilled)

    def drawPolygon(self, pointlist,
                    edgeColor=None, edgeWidth=None, fillColor=None, closed=0):
        """Draw a set of joined-up line segments.

        edgeColor: color of the polygon edges; defaults to the Canvas's
         defaultLineColor
        edgeWidth: width of the polygon edges; defaults to the Canvas's
         defaultLineWidth
        fillColor: color of the polygon interior; defaults to the Canvas's
         defaultFillColor
        closed: if 1, adds an extra segment smoothly connecting the first
         vertex to the last; defaults to 0

        """
        if edgeColor is None:
            edgeColor = self.defaultLineColor
        if edgeWidth is None:
            edgeWidth = self.defaultLineWidth
        if fillColor is None:
            fillColor = self.defaultFillColor
        self._drawPolygon(pointlist, edgeColor, edgeWidth, fillColor, closed,
                          self.Filled)

    def _drawPolygon(self, pointlist,
                     edgeColor, edgeWidth, fillColor, closed,
                     filled):
        if closed:
            line_type = self.Polygon
            nr_points = len(pointlist) + 1
        else:
            line_type = self.PolyLine
            nr_points = len(pointlist)
        fig_edgeColor = self._figColor(edgeColor)
        fig_fillColor = self._figColor(fillColor)
        if fillColor == transparent:
            fig_fillColor = 0
            filled = self.NotFilled
        if edgeColor == transparent:
            # XXX should use background color, which is what, in general?
            fig_edgeColor = 7  # white
        code = self.poly_fmt % {
            "line_type": line_type,
            "line_style": self.Solid,
            "thickness": edgeWidth*bp_width,  # 1/80 inch
            "pen_color": fig_edgeColor,
            "fill_color": fig_fillColor,
            "depth": 50,  # XXX
            "pen_style": 0,  # ignored
            "area_fill": filled,
            "style_val": 0,  # no meaning for solid lines
            "join_style": self.Miter,
            "cap_style": self.Projecting,
            "radius": 1,  # only meaningful for ArcBox
            "forward_arrow": 0,
            "backward_arrow": 0,
            "npoints": nr_points
            }
        self.code.append(code)
        line = []
        pointlist = list(map(lambda p, f=bp: (p[0]*bp, p[1]*bp), pointlist))
        for coords in pointlist:
            code = self.coord_fmt % coords
            line.append(code)
        if closed:
            coords = pointlist[0]
            line.append(self.coord_fmt % coords)
        self.code.append(" ".join(line))

    def _imageFileName(self):
        self.fileNameCounter = self.fileNameCounter + 1
        dir = os.path.splitext(self.name)[0]
        try:
            os.mkdir(dir)
        except OSError:
            # complain if directory already exists when saving first image
            if self.fileNameCounter == 0: raise
        return os.path.join(dir, "image%d.gif" % (self.fileNameCounter,))

    def drawImage(self, image, x1,y1, x2=None,y2=None):
        """Draw a bitmap image at specified coordinates.

        If x2 and y2 are omitted, they are calculated from image size.
        (x1,y1) is upper left of image, (x2,y2) is lower right of image in
        PIDDLE coordinates.

        image: a Python Imaging Library Image object
        x1: leftmost edge of destination rectangle
        y1: topmost edge of destination rectangle
        x2: rightmost edge of destination rectangle (defaults to x1 plus the
         image width)
        y2: bottom of destination rectangle (defaults to y1 plus the image
         height)

        """
        code = self.poly_fmt % {
            "line_type": self.BoundingBox,
            "line_style": self.DefaultLineStyle,  # no meaning
            "thickness": 0,  # no meaning
            "pen_color": 0,  # no meaning
            "fill_color": 0,  # no meaning
            "depth": 50,  # XXX
            "pen_style": 0,  # ignored
            "area_fill": self.NotFilled,
            "style_val": 0,  # no meaning
            "join_style": self.Miter,  # no meaning
            "cap_style": self.Butt,  # no meaning
            "radius": 1,  # no meaning
            "forward_arrow": 0,  # no meaning
            "backward_arrow": 0,  # no meaning
            "npoints": 5
            }
        self.code.append(code)
        # add the filename and bounding box in the reverse order to that
        # specified in the fig 3.2 standard, because xfig wants it to be that
        # way
        fileName = self.images.get(image)
        if fileName is None:
            fileName = self._imageFileName()
            image.save(fileName)
            self.images[image] = fileName
        code = "0 %s" % (fileName,)
        self.code.append(code)
        code = []
        pointlist = [(x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)]
        pointlist = list(map(lambda p, f=bp: (p[0]*bp, p[1]*bp), pointlist))
        for coords in pointlist:
            code.append(self.coord_fmt % coords)
        code = " ".join(code)
        self.code.append(code)

    def _figColor(self, color):
        if color == transparent:
            return None
        fig_color = self.colors.get(color)
        if fig_color is None:
            fig_color = self._makeCustomColor(color)
            self.colors[color] = fig_color
        return fig_color

    def _makeCustomColor(self, color):
        code = self.color_fmt % (
            self.color_nr,
            255*color.red, 255*color.green, 255*color.blue)
        self.color_nr = self.color_nr + 1
        self.color_code.append(code)
        return self.color_nr-1

    def _findExternalFontName(self, font):
        """Attempts to return proper font name.
        PDF uses a standard 14 fonts referred to
        by name. Default to self.defaultFont('Helvetica').
        The dictionary allows a layer of indirection to
        support a standard set of PIDDLE font names."""
        # lifted from piddlePDF via piddlePS
        piddle_font_map = {
            'Times':'Times',
            'times':'Times',
            'Courier':'Courier',
            'courier':'Courier',
            'helvetica':'Helvetica',
            'Helvetica':'Helvetica',
            'symbol':'Symbol',
            'Symbol':'Symbol',
            'monospaced':'Courier',
            'serif':'Times',
            'sansserif':'Helvetica',
            'ZapfDingbats':'ZapfDingbats',
            'zapfdingbats':'ZapfDingbats',
            'arial':'Helvetica'
            }

        try:
            face = piddle_font_map[string.lower(font.face)]
        except:
            return 'Helvetica'

        name = face + '-'
        if font.bold and face in ['Courier','Helvetica','Times']:
            name = name + 'Bold'
        if font.italic and face in ['Courier', 'Helvetica']:
            name = name + 'Oblique'
        elif font.italic and face == 'Times':
            name = name + 'Italic'

        if name == 'Times-':
            name = name + 'Roman'
        # symbol and ZapfDingbats cannot be modified!

        #trim and return
        if name[-1] == '-':
            name = name[0:-1]
        return name

    def stringWidth(self, s, font=None):
        "Return the logical width of the string if it were drawn \
        in the current font (defaults to self.font)."
        # lifted from piddlePS
        if not font:
            font = self.defaultFont
        fontname = self._findExternalFontName(font)
        return 0.001 * font.size * piddlePSmetrics.psStringWidth(
            s, fontname, self.fontMapEncoding["EncodingName"])

    def fontAscent(self, font=None):
        "Find the ascent (height above base) of the given font."
        # lifted from piddlePS.py
        if not font:
            font = self.defaultFont
        fontname = self._findExternalFontName(font)
        return piddlePSmetrics.ascent_descent[fontname][0] * 0.001 * font.size

    def fontDescent(self, font=None):
        "Find the descent (extent below base) of the given font."
        # lifted from piddlePS.py
        if not font:
            font = self.defaultFont
        fontname = self._findExternalFontName(font)
        return -piddlePSmetrics.ascent_descent[fontname][1] * 0.001 * font.size

    def drawString(self, s, x, y, font=None, color=None, angle=0):
        """Draw a string s at position x,y.

        The color argument is ignored.
        angle is in degrees?

        s: the string to draw
        x: horizontal (right) coordinate of the starting position for the text
        y: vertical (down) coordinate of the starting position for the text
        font: font face and style for drawing; defaults to the Canvas's
         defaultFont
        color: Color of the drawn text; defaults to the Canvas's
         defaultLineColor
        angle: angle (degrees counter-clockwise from +X) at which the text
         should be drawn; defaults to 0

        """
        if font is None:
            font = self.defaultFont
        if color is None:
            color = self.defaultLineColor
        ss = s.split("\n")
        for i in range(len(ss)):
            s = ss[i]
            self._drawString(s, x, y, font, color, angle, i)

    def _drawString(self, s, x, y, font, color, angle, line_nr):
        # units, where given below in comments, are what fig expects
        fig_color = self._figColor(color)
        if font.face is None:
            face = self.defaultFace
        else:
            face = font.face
        fig_font = self.font_map[face]
        if not (font.bold or font.italic):
            fig_font = fig_font[self.Normal]
        elif font.bold and not font.italic:
            fig_font = fig_font[self.Bold]
        elif font.italic and not font.bold:
            fig_font = fig_font[self.Italic]
        elif font.italic and font.bold:
            fig_font = fig_font[self.BoldItalic]

        def escape(x): return "\\%.3o" % ord(x.group(1))
        s = self.text_sub.sub(escape, s)

        width = self.stringWidth(s, font)
        height = self.fontHeight(font)
        offset = line_nr*height
        dx = offset*math.sin(angle*degrees)
        dy = offset*math.cos(angle*degrees)
        x, y = x+dx, y+dy
        code = self.text_fmt % {
            "justification": self.Left,
            "color": fig_color,
            "depth": 50,
            "pen_style": 0,  # ignored
            "font": fig_font,
            "font_size": font.size,  # points
            "angle": angle*degrees,  # radians
            "font_flags": self.Postscript,
            "height": height*pt,  # 1/1200 inch
            "length": width*pt,  # 1/1200 inch
            "x": x*bp,  # 1/1200 inch
            "y": y*bp,  # 1/1200 inch
            "text": s+"\\001"}  # XXX what is the \001 for??
        self.code.append(code)
        if font.underline:
            dy = self.fontDescent(font)
            st = math.sin(angle*degrees)
            ct = math.cos(angle*degrees)
            xoff = dy*st
            yoff = dy*ct
            x1 = x+xoff
            y1 = y+yoff
            x2 = (x+width)-width*(1.0-ct)+xoff
            y2 = y-width*st+yoff
            self.drawLine(x1,y1, x2,y2, color)
