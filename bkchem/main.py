#--------------------------------------------------------------------------
#     This file is part of BKchem - a chemical drawing program
#     Copyright (C) 2002, 2003 Beda Kosata <beda@zirael.org>

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


"""the main application class resides here"""

from Tkinter import *
from paper import chem_paper
import Pmw
from xml_writer import SVG_writer
from tkFileDialog import asksaveasfilename, askopenfilename
import os
import tkMessageBox
import xml.dom.minidom as dom
import data
import dom_extensions
import non_xml_writer
import import_checker
import dialogs
import export
import warnings
import plugins
import misc
from edit_pool import editPool
import pixmaps
import types
from temp_manager import template_manager
import modes
import interactors
import os_support
import pref_manager

import oasa_bridge
import plugins.plugin



class BKchem( Tk):


  def __init__( self):
    Tk.__init__( self)
    self.tk.call("tk", "useinputmethods", "1")
    #self.tk.call( "encoding", "system", "iso8859-2")
    #print self.tk.call( "encoding", "system")


  def initialize( self):
    self.in_batch_mode = 0
    self.init_basics()
    
    # main drawing part
    self.papers = []
    self.notebook = Pmw.NoteBook( self.main_frame,
                                  raisecommand=self.change_paper,
                                  borderwidth=data.border_width)
    self.add_new_paper()

    # template and group managers
    self.init_managers()

    # menu initialization
    self.init_menu()
    self.init_plugins_menu()

    # modes initialization
    self.init_modes()
    self.mode = 'draw' # this is normaly not a string but it makes things easier on startup
    self.init_mode_buttons()

    # edit pool
    self.editPool = editPool( self, self.main_frame, width=60)
    self.editPool.pack( anchor=W)

    # main drawing part packing
    self.notebook.pack( fill='both', expand=1)
    for p in self.papers:
      p.initialise()
    self.notebook.setnaturalsize()

    # init status bar
    self.init_status_bar()

    # 
    self.radiobuttons.invoke( self.mode)

    # protocol bindings
    self.protocol("WM_DELETE_WINDOW", self._quit)


    #self.start_server()




  def initialize_batch( self):
    self.in_batch_mode = 1
    self.init_basics()
    
    # main drawing part
    self.papers = []
    self.notebook = Pmw.NoteBook( self.main_frame,
                                  raisecommand=self.change_paper)
    self.add_new_paper()

    
    #self.paper = chem_paper( self.main_frame, app=self, width=640, height=480, scrollregion=(0,0,'210m','297m'),
    #                    background="grey", closeenough=5, file_name=self.get_name_dic("a"))

    # template and group managers
    self.init_managers()

    # menu initialization
    #self.init_menu()

    # modes initialization
    #self.init_modes()
    self.mode = 'draw' # this is normaly not a string but it makes things easier on startup
    #self.init_mode_buttons()

    # edit pool
    #self.editPool = editPool( self, self.main_frame, width=60)
    #self.editPool.pack( anchor=W)

    # main drawing part packing
    self.notebook.pack( fill='both', expand=1)
    for p in self.papers:
      p.initialise()
    self.notebook.setnaturalsize()


    self.papers.append( self.paper)

    # init status bar
    #self.init_status_bar()

    # 
    #self.radiobuttons.invoke( self.mode)

    # protocol bindings
    self.protocol("WM_DELETE_WINDOW", self._quit)


    #self.start_server()

    



  def init_menu( self):
    # defining menu
    menu = Frame( self.main_frame, relief=RAISED, bd=data.border_width)
    menu.pack( fill = X)

    helpButton = Menubutton( menu, text=_('Help'))
    helpButton.pack( side = RIGHT)
    
    helpMenu = Menu( helpButton, tearoff=0)
    helpButton['menu'] = helpMenu
    helpMenu.add( 'command', label=_('About'), command = self.about) 

    # file menu
    fileButton = Menubutton( menu, text=_('File'))
    fileButton.pack( side = LEFT)
    fileMenu = Menu( fileButton, tearoff=0)
    fileButton['menu'] = fileMenu
    fileMenu.add( 'command', label=_('New'), command = self.add_new_paper)
    fileMenu.add( 'command', label=_('Save'), command = self.save_CDML, accelerator='(C-x C-s)')
    fileMenu.add( 'command', label=_('Save As...'), command = self.save_as_CDML, accelerator='(C-x C-w)')
    fileMenu.add( 'command', label=_('Load'), command = self.load_CDML, accelerator='(C-x C-f)')
    fileMenu.add( 'command', label=_('Load to the same tab'), command = lambda : self.load_CDML( replace=1))
    fileMenu.add( 'separator')
    # export cascade
    self.export_menu = Menu( fileButton, tearoff=0)
    export_cascade = fileMenu.add( 'cascade', label=_('Export'), menu = self.export_menu)
    self.export_menu.add( 'command', label=_('SVG'), command = self.save_SVG)
    # import cascade
    self.import_menu = Menu( fileButton, tearoff=0)
    import_cascade = fileMenu.add( 'cascade', label=_('Import'), menu = self.import_menu)
    # file properties
    fileMenu.add( 'separator')
    fileMenu.add( 'command', label=_('File properties'), command=self.change_properties)
    fileMenu.add( 'separator')
    fileMenu.add( 'command', label=_('Close tab'), command = self.close_current_paper, accelerator='(C-x C-t)')
    fileMenu.add( 'command', label=_('Exit'), command = self._quit, accelerator='(C-x C-c)')


    # edit menu
    editButton = Menubutton( menu, text=_('Edit'))
    editButton.pack( side = LEFT)
    editMenu = Menu( editButton, tearoff=0)
    editButton['menu'] = editMenu
    editMenu.add( 'command', label=_('Undo'), command = lambda : self.paper.undo(), accelerator='(C-z)')
    editMenu.add( 'command', label=_('Redo'), command = lambda : self.paper.redo(), accelerator='(C-S-z)')
    editMenu.add( 'separator')
    editMenu.add( 'command', label=_('Cut'), command = lambda : self.paper.selected_to_clipboard( delete_afterwards=1), accelerator='(C-w)')
    editMenu.add( 'command', label=_('Copy'), command = lambda : self.paper.selected_to_clipboard(), accelerator='(A-w)')
    editMenu.add( 'command', label=_('Paste'), command = lambda : self.paper.paste_clipboard( None), accelerator='(C-y)')
    editMenu.add( 'separator')
    editMenu.add( 'command', label=_('Selected to clipboard as SVG'), command = lambda : self.paper.selected_to_real_clipboard_as_SVG())
    editMenu.add( 'separator')
    editMenu.add( 'command', label=_('Select all'), command = lambda : self.paper.select_all(), accelerator='(C-S-a)')
    
    alignButton = Menubutton( menu, text=_('Align'))
    alignButton.pack( side = LEFT)
    alignMenu = Menu( alignButton, tearoff=0)
    alignButton['menu'] = alignMenu
    alignMenu.add( 'command', label=_('Top'), command = lambda : self.paper.align_selected( 't'), accelerator='(C-a t)')
    alignMenu.add( 'command', label=_('Bottom'), command = lambda : self.paper.align_selected( 'b'), accelerator='(C-a b)')
    alignMenu.add( 'separator')
    alignMenu.add( 'command', label=_('Left'), command = lambda : self.paper.align_selected( 'l'), accelerator='(C-a l)')
    alignMenu.add( 'command', label=_('Right'), command = lambda : self.paper.align_selected( 'r'), accelerator='(C-a r)')
    alignMenu.add( 'separator')
    alignMenu.add( 'command', label=_('Center horizontaly'), command = lambda : self.paper.align_selected( 'h'), accelerator='(C-a h)')
    alignMenu.add( 'command', label=_('Center verticaly'), command = lambda : self.paper.align_selected( 'v'), accelerator="(C-a v)")

    scaleButton = Menubutton( menu, text=_('Object'))
    scaleButton.pack( side= 'left')
    scaleMenu = Menu( scaleButton, tearoff=0)
    scaleButton['menu'] = scaleMenu
    scaleMenu.add( 'command', label=_('Scale'), command = self.scale)
    scaleMenu.add( 'separator')
    scaleMenu.add( 'command', label=_('Bring to front'), command = lambda : self.paper.lift_selected_to_top(), accelerator='(C-o f)')
    scaleMenu.add( 'command', label=_('Send back'), command = lambda : self.paper.lower_selected_to_bottom(), accelerator='(C-o b)')
    scaleMenu.add( 'command', label=_('Swap on stack'), command = lambda : self.paper.swap_selected_on_stack(), accelerator='(C-o s)')
    scaleMenu.add( 'separator')
    scaleMenu.add( 'command', label=_('Vertical mirror'), command = lambda : self.paper.swap_sides_of_selected())
    scaleMenu.add( 'command', label=_('Horizontal mirror'), command = lambda : self.paper.swap_sides_of_selected('horizontal') )
    scaleMenu.add( 'separator')
    scaleMenu.add( 'command', label=_('Configure'), command = lambda : self.paper.config_selected(), accelerator='Mouse-3')
    scaleMenu.add( 'separator')
    scaleMenu.add( 'command', label=_('Set molecule name'), command = lambda : interactors.ask_name_for_selected( self.paper))
    scaleMenu.add( 'command', label=_('Set molecule ID'), command = lambda : interactors.ask_id_for_selected( self.paper))
    
    # for dev only

    # CHEMISTRY MENU
    chemistry_button = Menubutton( menu, text=_('Chemistry'))
    chemistry_button.pack( side= 'left')
    chemistry_menu = Menu( chemistry_button, tearoff=0)
    chemistry_button['menu'] = chemistry_menu
    chemistry_menu.add( 'command', label=_('Info'), command = lambda : self.paper.display_info_on_selected(), accelerator='(C-o i)')
    chemistry_menu.add( 'command', label=_('Check chemistry'), command = lambda : self.paper.check_chemistry_of_selected(), accelerator='(C-o c)')
    chemistry_menu.add( 'command', label=_('Expand groups'), command = lambda : self.paper.expand_groups(), accelerator='(C-o e)')
    chemistry_menu.add( 'separator')
    # oasa related stuff
    oasa_state = oasa_bridge.oasa_available and 'normal' or 'disabled'
    chemistry_menu.add( 'command', label=_('Read SMILES'), command = self.read_smiles, state=oasa_state)
    chemistry_menu.add( 'command', label=_('Read INChI'), command = self.read_inchi, state=oasa_state)
    chemistry_menu.add( 'separator')
    chemistry_menu.add( 'command', label=_('Generate SMILES'), command = self.gen_smiles, state=oasa_state)
    chemistry_menu.add( 'command', label=_('Generate INChI'), command = self.gen_inchi, state=oasa_state)
    #scaleMenu.add( 'command', label=_('Flush mol'), command = self.paper.flush_first_selected_mol_to_graph_file)
    
    # USER DEFINE TEMPLATES
    utm_button = Menubutton( menu, text=_('User templates'))
    utm_button.pack( side= 'left')
    self.utm_menu = Menu( utm_button, tearoff=0)
    utm_button['menu'] = self.utm_menu
    self.populate_utm_menu()

    # OPTIONS
    optionsButton = Menubutton( menu, text=_('Options'))
    optionsButton.pack( side= 'left')
    optionsMenu = Menu( optionsButton, tearoff=0)
    optionsButton['menu'] = optionsMenu
    optionsMenu.add( 'command', label=_('Standard'), command=self.standard_values)




  def init_basics( self):
    Pmw.initialise( self)
    import pixmaps
    if os.name == 'posix':
      try:
        self.option_add( "*font", ("-adobe-helvetica-medium-r-normal-*-12-*-*-*-p-*-iso10646-1"))
        ##self.option_add( "*font", ("-adobe-helvetica-medium-r-normal-*-*-100-*-*-*-*-*-*"))
      except:
        print "cannot init default font"
    else:
      self.option_add( "*font", ("Helvetica",10,"normal"))
    # colors
    #self.option_add( "*background", "#d0d0d0")
    #self.option_add( "*borderwidth", data.border_width)
    self.title( "BKchem")
    self.stat= StringVar()
    self.stat.set( "Idle")
    self.save_dir = '.'
    self.save_file = None
    self.svg_dir = '.'
    self.svg_file = ''

    self._clipboard = None
    self._clipboard_pos = None

    self._untitled_counter = 0
    self.__tab_name_2_paper = {}
    self.__last_tab = 0


    self._after = None

    self.balloon = Pmw.Balloon( self)
    self.main_frame = Frame( self)
    self.main_frame.pack( fill='both', expand=1)





  def init_plugins_menu( self):
    # PLUGINS
    if plugins.__all__:
      self.plugins = []
      for name in plugins.__all__:
        plugin = plugins.__dict__[ name]
        self.plugins.append( plugin)
        if ('importer' in  plugin.__dict__) and plugin.importer:
          self.import_menu.add( 'command',
                                label=plugin.name,
                                command = misc.lazy_apply( self.plugin_import, [self.plugins.index( plugin)]))
        if ('exporter' in plugin.__dict__) and plugin.exporter:
          self.export_menu.add( 'command',
                                label=plugin.name,
                                command = misc.lazy_apply( self.plugin_export, [self.plugins.index( plugin)]))





  def init_managers( self):
    # template_manager
    self.tm = template_manager( self)
    self.tm.add_template_from_CDML( "templates.cdml")

    # manager for user user defined templates
    self.utm = template_manager( self)
    self.read_user_templates()

    # groups manager
    self.gm = template_manager( self)
    self.gm.add_template_from_CDML( "groups.cdml")
    self.gm.add_template_from_CDML( "groups2.cdml")


    # preference manager
    self.pm = pref_manager.pref_manager( os_support.get_config_filename( "prefs.xml", level="personal", mode='r'))


  def init_modes( self):
    self.modes = { 'draw': modes.draw_mode( self),
                   'edit': modes.edit_mode( self),
                   'arrow': modes.arrow_mode( self),
                   'plus': modes.plus_mode( self),
                   'template': modes.template_mode( self),
                   'text': modes.text_mode( self),
                   'rotate': modes.rotate_mode( self),
                   'bondalign': modes.bond_align_mode( self),
                   'vector': modes.vector_mode( self),
                   'mark': modes.mark_mode( self),
                   'atom': modes.atom_mode( self)}
    self.modes_sort = [ 'edit', 'draw', 'template', 'atom', 'text', 'arrow', 'plus', 'rotate', 'bondalign', 'vector', 'mark']





  def init_mode_buttons( self):
    # mode selection panel     
    radioFrame = Frame( self.main_frame)
    radioFrame.pack( fill=X)
    self.radiobuttons = Pmw.RadioSelect(radioFrame,
                                        buttontype = 'button',
                                        selectmode = 'single',
                                        orient = 'horizontal',
                                        command = self.change_mode,
                                        hull_borderwidth = 0,
                                        padx = 0,
                                        pady = 0,
                                        hull_relief = 'flat',
                                        
             )
    self.radiobuttons.pack( side=LEFT)
    # Add some buttons to the radiobutton RadioSelect.
    for m in self.modes_sort:
      if m in pixmaps.images:
        recent = self.radiobuttons.add( m, image=pixmaps.images[m], text=self.modes[ m].name, activebackground='grey',
                                        relief='flat', borderwidth=data.border_width)
        self.balloon.bind( recent, self.modes[ m].name)
      else:
        self.radiobuttons.add( m, text=self.modes[ m].name, borderwidth=data.border_width)
    # sub-mode support
    self.subFrame = Frame( self.main_frame)
    self.subFrame.pack( fill=X)
    self.subbuttons = []
    # the remaining of sub modes support is now in self.change_mode





  def init_status_bar( self):
    status = Label( self.main_frame, relief=SUNKEN, bd=data.border_width, textvariable=self.stat, anchor='w', height=2, justify='l')
    status.pack( fill=X, side='bottom')





  def about( self):
    dialog = Pmw.MessageDialog(self,
                               title = _('About BKchem'),
                               defaultbutton = 0,
                               message_text = data.about_text)
    dialog.iconname('BKchem')
    dialog.activate()






  def change_mode( self, tag):
    if type( self.mode) != types.StringType:
      self.mode.cleanup()
    self.mode = self.modes[ tag]

    if self.subbuttons:
      for butts in self.subbuttons:
        butts.deleteall()
        butts.destroy()
    self.subbuttons = []
    m = self.mode
    for i in range( len( m.submodes)):
      self.subbuttons.append( Pmw.RadioSelect( self.subFrame,
                                               buttontype = 'button',
                                               selectmode = 'single',
                                               orient = 'horizontal',
                                               command = self.change_submode,
                                               hull_borderwidth = 0,
                                               padx = 0,
                                               pady = 0,
                                               hull_relief = 'ridge',
                                               ))
      if i % 2:
        self.subbuttons[i].pack( side=LEFT, padx=10)
      else:
        self.subbuttons[i].pack( side=LEFT)
      for sub in m.submodes[i]:
        if sub in pixmaps.images:
          recent = self.subbuttons[i].add( sub, image=pixmaps.images[sub], activebackground='grey', borderwidth=data.border_width)
          self.balloon.bind( recent, m.submodes_names[i][m.submodes[i].index(sub)])
        else:
          self.subbuttons[i].add( sub, text=m.submodes_names[i][m.submodes[i].index(sub)], borderwidth=data.border_width)
      # black magic???
      j = m.submodes[i][ m.submode[i]]
      self.subbuttons[i].invoke( j)
    self.paper.mode = self.mode
    self.update_status( _('mode changed to ')+self.modes[ tag].name)




  def change_submode( self, tag):
    self.mode.set_submode( tag)




  def update_status( self, signal, time=4):
    self.stat.set( signal)
    if self._after:
      self.after_cancel( self._after)
    self._after = self.after( time*1000, func=self.clear_status)




  def change_paper( self, name):
    if self.papers:
      i = self.notebook.index( name)
      self.paper = self.papers[i]
      self.paper.mode = self.mode




  def add_new_paper( self, name=''):
    # check if the same file is opened
    p = self.check_if_the_file_is_opened( name)
    if p:
      tkMessageBox.showerror( _("File already opened!"),_("Sorry but I cannot open one file twice."))
      return 0
    name_dic = self.get_name_dic( name=name)
    # create the tab
    _tab_name = self.get_new_tab_name()
    page = self.notebook.add( _tab_name, tab_text = chem_paper.create_window_name( name_dic))
    paper = chem_paper( page,
                        app=self,
                        width=640,
                        height=480,
                        scrollregion=(0,0,'210m','297m'),
                        background="grey",
                        closeenough=3,
                        file_name=name_dic)
    self.__tab_name_2_paper[ _tab_name] = paper
    # the scrolling
    scroll_y = Scrollbar( page, orient = VERTICAL, command = paper.yview, bd=data.border_width)
    scroll_x = Scrollbar( page, orient = HORIZONTAL, command = paper.xview, bd=data.border_width)
    paper.grid( row=0, column=0, sticky="news")
    page.grid_rowconfigure( 0, weight=1, minsize = 0)
    page.grid_columnconfigure( 0, weight=1, minsize = 0)
    scroll_x.grid( row=1, column=0, sticky='we')
    scroll_y.grid( row=0, column=1, sticky='ns')
    paper['yscrollcommand'] = scroll_y.set
    paper['xscrollcommand'] = scroll_x.set

    self.papers.append( paper)
    self.paper = paper
    self.notebook.selectpage( Pmw.END)
    self.paper.focus_set()


  def close_current_paper( self):
    return self.close_paper()


  def close_paper( self, paper=None):
    p = paper or self.paper

    if p.changes_made:
      name = p.file_name['name']
      dialog = Pmw.MessageDialog( self,
                                  title= _("Really close?"),
                                  message_text = _("There are unsaved changes in file %s, what should I do?") % name,
                                  buttons = (_('Close'),_('Save'),_('Cancel')),
                                  defaultbutton = _('Close'))
      result = dialog.activate()
      if result == _('Save'):
        self.save_CDML()
      elif result == _('Cancel'):
        return 0 # we skip away
    self.papers.remove( p)
    # find the name of the tab
    name = self.get_paper_tab_name( p)
    self.notebook.delete( name or Pmw.SELECT)
    return 1



  def clear_status( self):
    self.stat.set( '')



  def save_CDML( self, name=None):
    """saves content of self.paper (recent paper) under its filename,
    if the filename was automaticaly given by bkchem it will call save_as_CDML
    in order to ask for the name"""
    if not name:
      if self.paper.file_name['auto']:
        new_name = self.save_as_CDML()
        return
      else:
        a = os.path.join( self.paper.file_name['dir'], self.paper.file_name['name'])
        self._save_according_to_extension( a)
    else:
      self._save_according_to_extension( name)


  def save_as_CDML( self):
    """asks the user the name for a file and saves the current paper there,
    dir and name should be given as starting values"""
    dir = self.paper.file_name['dir']
    name = self.paper.file_name['name']
    a = asksaveasfilename( defaultextension = ".svg", initialdir = dir, initialfile = name,
                           title = _("Save As..."), parent = self,
                           filetypes=((_("CD-SVG file"),".svg"),
                                      (_("Gzipped CD-SVG file"),".svgz"),
                                      (_("CDML file"),".cdml"),
                                      (_("Gzipped CDML file"),".cdgz")))
    if a != '' and a!=():
      if self._save_according_to_extension( a):
        self.paper.file_name = self.get_name_dic( a)
        self.notebook.tab( self.get_paper_tab_name( self.paper)).configure( text = self.paper.file_name['name'])
        return self.paper.file_name
      else:
        return None
    else:
      return None
    
    


  def _save_according_to_extension( self, filename):
    """decides the format from the file extension and saves self.paper in it"""
    self.save_dir, save_file = os.path.split( filename)
    ext = os.path.splitext( filename)[1]
    if ext == '.cdgz':
      type = _('gzipped CDML')
      success = export.export_CDML( self.paper, filename, gzipped=1)
    elif ext == '.cdml':
      type = _('CDML')
      success = export.export_CDML( self.paper, filename, gzipped=0)        
    elif ext == '.svgz':
      type = _('gzipped CD-SVG')
      success = export.export_CD_SVG( self.paper, filename, gzipped=1)
    else:
      type = _('CD-SVG')
      success = export.export_CD_SVG( self.paper, filename, gzipped=0)
    if success:
      self.update_status( _("saved to %s file: %s") % (type, os.path.abspath( os.path.join( self.save_dir, save_file))))
      self.paper.changes_made = 0
      return 1
    else:
      self.update_status( _("failed to save to %s file: %s") % (type, save_file))
      return 0



  def set_file_name( self, name, check_ext=0):
    """if check_ext is true append a .svg extension if no is present"""
    if check_ext and not os.path.splitext( name)[1]:
      self.paper.file_name = self.get_name_dic( name + ".svg")
    else:
      self.paper.file_name = self.get_name_dic( name)
    self.notebook.tab( self.get_paper_tab_name( self.paper)).configure( text = self.paper.file_name['name'])




  def load_CDML( self, file=None, replace=0):
    if not file:
      if self.paper.changes_made and replace:
	if tkMessageBox.askokcancel( _("Forget changes?"),_("Forget changes in currently visiting file?"), default='ok', parent=self) == 0:
          return 0
      a = askopenfilename( defaultextension = "",
                           initialdir = self.save_dir,
                           title = _("Load"),
                           parent = self,
                           filetypes=((_("All native formats"), (".svg", ".svgz", ".cdml", ".cdgz")),
                                      (_("CD-SVG file"), ".svg"),
                                      (_("Gzipped CD-SVG file"), ".svgz"),
                                      (_("CDML file"),".cdml"),
                                      (_("CDGZ file"),".cdgz"),
                                      (_("Gzipped files"), ".gz"),
                                      (_("All files"),"*")))
    else:
      a = file
    if not a:
      return None
    if replace or (self.paper.file_name['auto'] and not self.paper.changes_made):
      self.close_paper()
    p = self.add_new_paper( name=a)
    if p != 0:
      self.paper.mode = self.mode # somehow the raise event does not work here
      return self._load_CDML_file( a)
    return 0



  def _load_CDML_file( self, a):
    if a != '':
      self.save_dir, save_file = os.path.split( a)
      ## try if the file is gzipped
      # try to open the file
      try:
        import gzip
        inp = gzip.open( a, "rb")
      except IOError:
        # can't read the file
        self.update_status( _("cannot open file ") + a)
        return None
      # is it a gzip file?
      it_is_gzip = 1
      try:
        str = inp.read()
      except IOError:
        # not a gzip file
        it_is_gzip = 0
      # if it's gzip file parse it
      if it_is_gzip:
        try:
          doc = dom.parseString( str)
        except:
          self.update_status( _("error reading file"))
          inp.close()
          return None
        inp.close()
        del gzip
        doc = doc.childNodes[0]
      else:
      ## otherwise it should be normal xml file
        ## try to parse it
        try:
          doc = dom.parse( a)
        except: 
          self.update_status( _("error reading file"))
          return None
        ## if it works check if its CDML of CD-SVG file
        doc = doc.childNodes[0]
      ## check if its CD-SVG or CDML
      if doc.nodeName == 'svg':
        ## first try if there is the right namespace
        docs = doc.getElementsByTagNameNS( data.cdml_namespace, 'cdml')
        if docs:
          doc = docs[0]
        else:
          # if not, try it without it
          docs = doc.getElementsByTagName( 'cdml')
          if docs:
            # ask if we should proceed with incorrect namespace
            proceed = tkMessageBox.askokcancel( _("Proceed?"),
						_("CDML data seem present in SVG but have wrong namespace. Proceed?"),
						default='ok',
						parent=self)
            if proceed:
              doc = docs[0]
            else:
              self.update_status(_("file not loaded"))
              return None
          else:
            ## sorry but there is no cdml in the svg file
            self.update_status(_("cdml data are not present in SVG or are corrupted!"))
            return None
      self.paper.clean_paper()
      self.paper.read_package( doc)
      self.update_status( _("loaded file: ")+self.paper.full_path)
      return 1



  def save_SVG( self, file_name=None):
    if not file_name:
      svg_file = self.paper.get_base_name()+".svg"
      a = asksaveasfilename( defaultextension = ".svg", initialdir = self.svg_dir, initialfile = svg_file,
                             title = _("Export SVG"), parent = self, filetypes=((_("SVG file"),"*.svg"),))
    else:
      a = file_name
    if a != '':
      self.svg_dir, svg_file = os.path.split( a)
      try:
        inp = open( a, "w")
      except IOError, x:
        raise "unable to open to file ", x
      exporter = SVG_writer( self.paper)
      exporter.construct_dom_tree( self.paper.top_levels)
      dom_extensions.safe_indent( exporter.document.childNodes[0])
      inp.write( unicode( exporter.document.toxml()).encode('utf-8'))
      inp.close()
      self.update_status( _("exported to SVG file: ")+svg_file)




  def _update_geometry( self, e):
    pass



  def scale( self):
    dialog = dialogs.scale_dialog( self)
    if dialog.result:
      x, y = dialog.result
      self.paper.scale_selected( x/100, y/100)


    
  def get_name_dic( self, name=''):
    if not name:
      name = 'untitled%d.svg' % self._untitled_counter
      name_dic = {'name':name, 'dir':self.save_dir, 'auto': 1, 'ord': 0}
      self._untitled_counter += 1
    else:
      dir, name = os.path.split( name)
      if not dir:
        dir = self.save_dir
      name_dic = {'name':name, 'dir':dir, 'auto': 0, 'ord': 0}
      i = self.check_number_of_opened_same_names( name_dic)
      name_dic['ord'] = i
    return name_dic



  def _quit( self):
    while self.papers:
      if not self.close_current_paper():
        return
    self.save_configuration()
    self.quit()


      
  def plugin_import( self, pl_id):
    plugin = self.plugins[ pl_id]
    if self.paper.changes_made:
      if tkMessageBox.askokcancel( _("Forget changes?"),_("Forget changes in currently visiting file?"), default='ok', parent=self) == 0:
        return 0
    types = []
    if 'extensions' in plugin.__dict__ and plugin.extensions:
      for e in plugin.extensions:
        types.append( (plugin.name+" "+_("file"), e))
    types.append( (_("All files"),"*"))
    a = askopenfilename( defaultextension = "",
                         initialdir = self.save_dir,
                         initialfile = self.save_file,
                         title = _("Load")+" "+plugin.name,
                         parent = self,
                         filetypes=types)
    if a:
      if plugin.importer.gives_molecule:
        # plugins returning molecule need paper instance for molecule initialization
        importer = plugin.importer( self.paper)
      else:
        importer = plugin.importer()
      if importer.on_begin():
        cdml = None
        # some importers give back a cdml dom object
        if importer.gives_cdml:
          cdml = 1
          try:
            doc = importer.get_cdml_dom( a)
          except plugins.plugin.import_exception, detail:
            tkMessageBox.showerror( _("Import error"), _("Plugin failed to import with following error:\n %s") % detail) 
            return
        # others give directly a molecule object
        elif importer.gives_molecule:
          cdml = 0
          try:
            doc = importer.get_molecule( a)
          except plugins.plugin.import_exception, detail:
            tkMessageBox.showerror( _("Import error"), _("Plugin failed to import with following error:\n %s") % detail) 
        self.paper.clean_paper()
        if cdml == 0:
          # doc is a molecule
          self.paper.set_paper_properties()
          self.paper.stack.append( doc)
          doc.draw()
          self.paper.add_bindings()
          self.paper.start_new_undo_record()
        elif cdml:
          self.paper.read_package( doc)
        self.update_status( _("loaded file: ")+a)



  def plugin_export( self, pl_id):
    plugin = self.plugins[ pl_id]
    exporter = plugin.exporter( self.paper)
    if not exporter.on_begin():
      return
    file_name = self.paper.get_base_name()
    types = []
    if 'extensions' in plugin.__dict__ and plugin.extensions:
      file_name += plugin.extensions[0]
      for e in plugin.extensions:
        types.append( (plugin.name+" "+_("file"), e))
    types.append( (_("All files"),"*"))
    a = asksaveasfilename( defaultextension = types[0][1],
                           initialdir = self.save_dir,
                           initialfile = file_name,
                           title = _("Export")+" "+plugin.name,
                           parent = self,
                           filetypes=types)
    if a != '':
      try:
        doc = exporter.write_to_file( a)
      except:
        tkMessageBox.showerror( _("Export error"), _("Plugin failed to export with following error:\n %s") % sys.exc_value)
        return
      self.update_status( _("exported file: ")+a)
  



  def change_properties( self):
    dial = dialogs.file_properties_dialog( self, self.paper)



  def standard_values( self):
    dial = dialogs.standard_values_dialog( self, self.paper.standard)
    if dial.change:
      old_standard = self.paper.standard
      self.paper.standard = dial.standard
      # apply all values or only the changed ones
      if dial.apply_all:
        old_standard = None
      if not dial.apply:
        return
      elif dial.apply == 2:
        [o.redraw() for o in self.paper.apply_current_standard( old_standard=old_standard)]
      elif dial.apply == 1:
        [o.redraw() for o in self.paper.apply_current_standard( objects=self.paper.selected, old_standard=old_standard)]
      self.paper.add_bindings()
      self.paper.start_new_undo_record()
  



  def request( self, type, **options):
    """used by submodules etc. for requests of application wide resources such as pixmaps etc."""
    import pixmaps
    if type == 'pixmap':
      if 'name' in options:
        name = options['name']
        if name in pixmaps.images:
          return pixmaps.images[ name]
        else:
          return None
      return None
    

  def read_smiles( self, smiles=None):
    if not oasa_bridge.oasa_available:
      return 
    lt = _("""Before you use this tool, be warned that not all features of SMILES are currently supported.
There is no support for stereo-related information, for the square brackets [] and a few more things.

Enter SMILES:""")
    if not smiles:
      dial = Pmw.PromptDialog( self,
			       title='Smiles',
			       label_text=lt,
			       entryfield_labelpos = 'n',
			       buttons=(_('OK'),_('Cancel')))
      res = dial.activate()
      if res == _('OK'):
	text = dial.get()
      else:
	return
    else:
      text = smiles

    if text:
      try:
	mol = oasa_bridge.read_smiles( text, self.paper)
      except :
	if not smiles:
	  tkMessageBox.showerror( _("Error processing %s") % 'SMILES',
				  _("The oasa library ended with error:\n%s") % sys.exc_value)
	return
      self.paper.stack.append( mol)
      mol.draw()
      self.paper.add_bindings()
      self.paper.start_new_undo_record()


  def read_inchi( self, inchi=None):
    if not oasa_bridge.oasa_available:
      return 
    lt = _("""Before you use his tool, be warned that not all features of INChI are currently supported.
There is no support for stereo-related information, isotopes and a few more things.
The IChI should be entered in the plain text form, e.g.- 1.0Beta/C7H8/1-7-5-3-2-4-6-7/1H3,2-6H

Enter IChI:""")
    text = None
    if not inchi:
      dial = Pmw.PromptDialog( self,
                               title='INChI',
                               label_text=lt,
                               entryfield_labelpos = 'n',
                               buttons=(_('OK'),_('Cancel')))
      res = dial.activate()
      if res == _('OK'):
        text = dial.get()
    else:
      text = inchi

    if text:
      try:
        mol = oasa_bridge.read_inchi( text, self.paper)
      except:
        if not inchi:
          tkMessageBox.showerror( _("Error processing %s") % 'INChI',
                                  _("The oasa library ended with error:\n%s") % sys.exc_value)
        return

      self.paper.stack.append( mol)
      mol.draw()
      self.paper.add_bindings()
      self.paper.start_new_undo_record()


  def gen_smiles( self):
    if not oasa_bridge.oasa_available:
      return
    u, i = self.paper.selected_to_unique_top_levels()
    sms = []
    for m in u:
      if m.object_type == 'molecule':
        try:
          sms.append( oasa_bridge.mol_to_smiles( m))
        except:
          tkMessageBox.showerror( _("Error generating %s") % 'SMILES',
                                  _("The oasa library ended with error:\n%s") % sys.exc_value)
          return
    text = '\n\n'.join( sms)
    dial = Pmw.TextDialog( self,
                           title='Generated SMILES',
                           buttons=(_('OK'),))
    dial.insert( 'end', text)
    dial.activate()
    

  def put_to_clipboard( self, xml, pos):
    self._clipboard = xml
    self._clipboard_pos = pos

  def get_clipboard( self):
    return self._clipboard

  def get_clipboard_pos( self):
    return self._clipboard_pos


##   def get_named_paper( self, name):
##     for p in self.papers:
##       if p.get_base_name() == name:
##         return p
##     return None


  def check_if_the_file_is_opened( self, name):
    for p in self.papers:
      if p.full_path == os.path.abspath( name):
        return p
    return None
      
  def check_number_of_opened_same_names( self, name):
    """checks if there are papers with same name and returns the highest value"""
    ps = [p.file_name['ord'] for p in self.papers if p.file_name['name'] == name['name']]
    if not ps:
      return 0
    else:
      return max( ps)+1



  def start_server( self):

    import http_server
    
    server_address = ('', 8008)
    httpd = http_server.bkchem_http_server( self, server_address, http_server.bkchem_http_handler)

    import threading

    t = threading.Thread( target=httpd.serve_forever, name='server')
    t.setDaemon( 1)
    t.start()



  def get_new_tab_name( self):
    self.__last_tab += 1
    return "tab"+str(self.__last_tab)

  def get_paper_tab_name( self, paper):
    for k in self.__tab_name_2_paper:
      if self.__tab_name_2_paper[ k] == paper:
        return k
    return None


  def read_user_templates( self):
    [self.utm.add_template_from_CDML( n) for n in os_support.get_local_templates()]



  def populate_utm_menu( self):
    for m in self.utm.get_template_names():
      self.utm_menu.add_radiobutton( label=m, command = misc.lazy_apply( self.select_user_template,  (m,)))
#    if self.utm.get_template_names():
#      self.utm_menu.invoke( 0)


  def select_user_template( self, name):
    self.radiobuttons.invoke( "template")
    self.subbuttons[0].invoke( "userdefined")
    self.mode._user_selected_template = name



  def process_batch( self, opts, files=None):
    import time
    
    f = None
    t = None
    o = None
    for opt in opts:
      if opt[0] == '-f':
        f = opt[1]
      elif opt[0] == '-t':
        t = opt[1]
      elif opt[0] == '-o':
        o = opt[1]
      elif opt[0] == '-l':
        if not files:
          files = []
          file_list = opt[1]
          file_file = open( file_list, 'r')
          for name in [l.strip() for l in file_file.xreadlines()]:
            if os.path.isfile( name):
              files.append( name)
              sys.stderr.write( " * added file from list: %s\n" % name)
        else:
          print "-l option is ignored when input file is given"

    # default values for input and output formats
    f = f or 'cdml'
    t = t or 'cd-svg'

    # processing of the files
    for file in files:
      # choose the output filename
      if not o:
        out = file+'.'+t
      else:
        out = o

      # read
      if f == 'cdml':
        sys.stderr.write( " * reading file: %s\n" % file)
        ret = self.load_CDML( file, replace=1)
        if not ret:
          sys.stderr.write( " !! failed, will not proceed.")
          return 

      # write
      start_time = time.time()
      if t == 'svg':
        self.save_SVG( out)
      elif t == 'cd-svg':
        self.save_CDML( o)
        sys.stderr.write( " * writing CD-SVG file: %s\n" % o)
        sys.stderr.write( " -- processing time: %.2fms\n" % (1000*(time.time()-start_time)))



  def gen_inchi( self):
    program = "/home/beda/inchi/cINChI11b"
    import tempfile
    
    if not oasa_bridge.oasa_available:
      return
    u, i = self.paper.selected_to_unique_top_levels()
    sms = []
    if not interactors.check_validity( self, u):
      return
    for m in u:
      if m.object_type == 'molecule':
        plugin = plugins.molfile
        exporter = plugin.exporter( self.paper)
        name = os.path.join( tempfile.gettempdir(), "gen_inchi.mol")
        file = open( name, 'w')
        oasa_bridge.write_molfile( m, file)
        file.close()

        in_name = os.path.join( tempfile.gettempdir(), "gen_inchi.temp")
        #print program, name, in_name

        os.spawnvp( os.P_WAIT, program, (program, name, in_name, "-AUXNONE"))

        in_file = open( in_name, 'r')
        [line for line in in_file.readlines()]
        sms.append( line[6:].strip())
        in_file.close()


    text = '\n\n'.join( sms)
    dial = Pmw.TextDialog( self,
                           title='Generated INChIs',
                           buttons=(_('OK'),))
    dial.insert( 'end', text)
    dial.activate()


  def save_configuration( self):
    self.pm.add_preference( 'geometry', self.winfo_geometry())
    f = os_support.get_opened_config_file( "prefs.xml", level="personal", mode="w")
    self.pm.write_to_file( f)
    f.close()

