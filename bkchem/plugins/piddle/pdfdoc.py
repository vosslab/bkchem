# -*- coding: iso-8859-1 -*-
#pdfdoc.py
"""
PDFgen is a library to generate PDF files containing text and graphics.  It is the
foundation for a complete reporting solution in Python.

The module pdfdoc.py handles the 'outer structure' of PDF documents, ensuring that
all objects are properly cross-referenced and indexed to the nearest byte.  The
'inner structure' - the page descriptions - are presumed to be generated before
each page is saved.
pdfgen.py calls this and provides a 'canvas' object to handle page marking operators.
piddlePDF calls pdfgen and offers a high-level interface.

(C) Copyright Andy Robinson 1998-1999
"""



import os
import sys
import string
import time
import tempfile
try:
    from io import StringIO as cStringIO
except ImportError:
    import io
from types import *
from math import sin, cos, pi, ceil

Log = sys.stderr  # reassign this if you don't want err output to console

try:
    import zlib
except:
    Log.write("zlib not available, page compression not available\n")

import pdfutils
import pdfmetrics
from pdfutils import LINEEND   # this constant needed in both
from pdfgeom import bezierArc

##############################################################
#
#            Constants and declarations
#
##############################################################

StandardEnglishFonts = [
    'Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique',
    'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique',
    'Helvetica-BoldOblique',
    'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic',
    'Symbol','ZapfDingbats']

PDFError = 'PDFError'
AFMDIR = '.'

A4 = (595.27,841.89)   #default page size



class PDFDocument(object):
    """Responsible for linking and writing out the whole document.
    Builds up a list of objects using add(key, object).  Each of these
    must inherit from PDFObject and be able to write itself into the file.
    For cross-linking, it provides getPosition(key) which tells you where
    another object is, or raises a KeyError if not found.  The rule is that
    objects should only refer ones previously written to file.
    """
    def __init__(self):
        self.objects = []
        self.objectPositions = {}

        self.fonts = MakeType1Fonts()

        #mapping of Postscriptfont names to internal ones;
        #needs to be dynamically built once we start adding
        #fonts in.
        self.fontMapping = {}
        for i in range(len(StandardEnglishFonts)):
            psname = StandardEnglishFonts[i]
            pdfname = '/F%d' % (i+1)
            self.fontMapping[psname] = pdfname


        self.pages = []
        self.pagepositions = []

        # position 1
        cat = PDFCatalog()
        cat.RefPages = 3
        cat.RefOutlines = 2
        self.add('Catalog', cat)

        # position 2 - outlines
        outl = PDFOutline()
        self.add('Outline', outl)

        # position 3 - pages collection
        self.PageCol = PDFPageCollection()
        self.add('PagesTreeRoot',self.PageCol)

        # positions 4-16 - fonts
        fontstartpos = len(self.objects) + 1
        for font in self.fonts:
            self.add('Font.'+font.keyname, font)
        self.fontdict = MakeFontDictionary(fontstartpos, len(self.fonts))

        # position 17 - Info
        self.info = PDFInfo()  #hang onto it!
        self.add('Info', self.info)
        self.infopos = len(self.objects)  #1-based, this gives its position


    def add(self, key, obj):
        self.objectPositions[key] = len(self.objects)  # its position
        self.objects.append(obj)
        obj.doc = self
        return len(self.objects) - 1  # give its position

    def getPosition(self, key):
        """Tell you where the given object is in the file - used for
        cross-linking; an object can call self.doc.getPosition("Page001")
        to find out where the object keyed under "Page001" is stored."""
        return self.objectPositions[key]

    def setTitle(self, title):
        "embeds in PDF file"
        self.info.title = title

    def setAuthor(self, author):
        "embedded in PDF file"
        self.info.author = author

    def setSubject(self, subject):
        "embeds in PDF file"
        self.info.subject = subject


    def printXref(self):
        self.startxref = sys.stdout.tell()
        Log.write('xref\n')
        Log.write("%s %s" % (0,len(self.objects) + 1) )
        Log.write('0000000000 65535 f')
        for pos in self.xref:
            Log.write( '%0.10d 00000 n\n' % pos)

    def writeXref(self, f):
        self.startxref = f.tell()
        f.write('xref' + LINEEND)
        f.write('0 %d' % (len(self.objects) + 1) + LINEEND)
        f.write('0000000000 65535 f' + LINEEND)
        for pos in self.xref:
            f.write('%0.10d 00000 n' % pos + LINEEND)


    def printTrailer(self):
        print('trailer')
        print('<< /Size %d /Root %d 0 R /Info %d 0 R>>' % (len(self.objects) + 1, 1, self.infopos))
        print('startxref')
        print(self.startxref)

    def writeTrailer(self, f):
        f.write('trailer' + LINEEND)
        f.write('<< /Size %d /Root %d 0 R /Info %d 0 R>>' % (len(self.objects) + 1, 1, self.infopos)  + LINEEND)
        f.write('startxref' + LINEEND)
        f.write(str(self.startxref)  + LINEEND)

    def SaveToFile(self, filename):
        with open(filename, 'wb') as f:
            self.SaveToFileObject(f)

    def SaveToFileObject(self, fileobj):
        """Open a file, and ask each object in turn to write itself to
        the file.  Keep track of the file position at each point for
        use in the index at the end"""
        f = fileobj
        i = 1
        self.xref = []
        f.write("%PDF-1.2" + LINEEND)  # for CID support
