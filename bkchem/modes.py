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
#
#
#
#--------------------------------------------------------------------------

"""the modes in which the paper operates (such as edit, draw etc.) reside here"""

import misc
from warnings import warn
import operator
import geometry
import math
import transform, transform3d
import time
import data
import string
import dialogs
import xml.sax, xml.sax.saxutils
import tkMessageBox
import helper_graphics as hg
import dom_extensions

class mode:
  """abstract parent for all modes. No to be used for inheritation because the more specialized
  edit mode has all the methods for editing - just override what you need to change"""
  def __init__( self, paper):
    self.name = 'mode'
    self.paper = paper
    self.submodes = []
    self.submode = []
    self._key_sequences = {}
    self._recent_key_seq = ''
    self._specials_pressed = { 'C':0, 'A':0, 'M':0, 'S':0} # C-A-M-S
    
  def mouse_down( self, event, modifiers = []):
    pass

  def mouse_up( self, event):
    pass

  def mouse_click( self, event):
    pass

  def mouse_drag( self, event):
    pass

  def enter_object( self, object, event):
    pass

  def leave_object( self, event):
    pass

  def mouse_move( self, event):
    pass

  def key_pressed( self, event):
    key = event_to_key( event)
    # first filter off specials (CAMS)
    if len( key) == 1 and key in 'CAMS':
      self._specials_pressed[ key] = 1
    else:
      # then if key is not CAMS update the recent key sequence
      # CAMS modificators first
      first = 1 # to separate each step with ' '
      for a in 'CAMS':
        if self._specials_pressed[ a]:
          if self._recent_key_seq:
            if first:
              self._recent_key_seq += ' ' + a
            else:
              self._recent_key_seq += '-' + a
          else:
            self._recent_key_seq = a
          first = 0
      # then the key itself 
      if self._recent_key_seq:
        if first:
          first = 0
          self._recent_key_seq += ' ' + key
        else:
          self._recent_key_seq += '-' + key
      else:
        self._recent_key_seq = key
      # look if the keysequence is registered
      if self._recent_key_seq in self._key_sequences:
        self.paper.signal_to_app( self._recent_key_seq)
        self._key_sequences[ self._recent_key_seq]()
        self._recent_key_seq = ''
      else:
        # or its a prefix of some registered sequence
        for key in self._key_sequences.keys():
          if not string.find( key, self._recent_key_seq):
            self.paper.signal_to_app( self._recent_key_seq)
            return None
        # if we get here it means that the key is neither used nor a prefix
        self._recent_key_seq = ''
      
  def key_released( self, event):
    key = event_to_key( event)
    if len( key) == 1 and key in 'CAMS':
      self._specials_pressed[ key] = 0

  def clean_key_query( self):
    """cleans status of all special keys;
    needed because especially after C-x C-f the C-release is grabed by dialog
    and never makes it to paper, therefor paper calls this after a file was read"""
    for key in self._specials_pressed.keys():
      self._specials_pressed[ key] = 0

  def get_name( self):
    return self.name

  def get_submode( self, i):
    if i < len( self.submodes):
      return self.submodes[i][ self.submode[i]]
    raise "invalid submode index"

  def set_submode( self, name):
    for sms in self.submodes:
      if name in sms:
        i = self.submodes.index( sms)
        self.submode[i] = sms.index( name)

  def register_key_sequence( self, sequence, function, use_warning = 1):
    """registers a function with its coresponding key sequence
    when use_warning is true (default) than issues warning about overriden
    or shadowed bindings. In most cases its good idea to let it check the bindings."""
    if use_warning and sequence in self._key_sequences:
      warn( "binding of sequence %s to function %s overrides its binding to function %s" %
            (sequence, function.__name__, self._key_sequences[ sequence].__name__),
            UserWarning, 2)
    elif use_warning:
      for key in self._key_sequences.keys():
        if not string.find( key, sequence):
          warn( "binding of sequence %s to function %s shadows %s (binded to %s)" %
                (sequence, function.__name__, key, self._key_sequences[ key].__name__),
                UserWarning, 2)
    self._key_sequences[ sequence] = function

  def register_key_sequence_ending_with_number_range( self, sequence_base, function, numbers=[]):
    for i in numbers:
      if sequence_base and sequence_base[-1] != ' ':
        b = sequence_base+' '
      else:
        b = sequence_base
      self.register_key_sequence( b+str(i), misc.lazy_apply( function, (i,)))



### -------------------- EDIT MODE --------------------

class edit_mode( mode):
  """basic editing mode, also good as parent for more specialized modes"""
  def __init__( self, paper):
    mode.__init__( self, paper)
    self.name = _('edit')
    self._dragging = 0
    self._dragged_molecule = None
    self._block_leave_event = 0
    self._moving_selected_arrow = None
    self.focused = None
    # responses to key events
    self.register_key_sequence( 'Delete', self._delete_selected)
    self.register_key_sequence( ' ', self._set_name_to_selected)
    self.register_key_sequence( 'Return', lambda : self.paper.set_name_to_selected( self.paper.app.editPool.text)) 
    # align
    self.register_key_sequence( 'C-a t', lambda : self.paper.align_selected( 't'))
    self.register_key_sequence( 'C-a b', lambda : self.paper.align_selected( 'b'))
    self.register_key_sequence( 'C-a l', lambda : self.paper.align_selected( 'l'))
    self.register_key_sequence( 'C-a r', lambda : self.paper.align_selected( 'r'))
    self.register_key_sequence( 'C-a h', lambda : self.paper.align_selected( 'h'))
    self.register_key_sequence( 'C-a v', lambda : self.paper.align_selected( 'v'))
    # other
    self.register_key_sequence( 'C-x c', self.paper.toggle_center_for_selected)
    self.register_key_sequence( 'C-d w', self.paper.display_weight_of_selected)
    self.register_key_sequence( 'C-d i', self.paper.display_info_on_selected)
    # object related key bindings
    self.register_key_sequence( 'C-o i', self.paper.display_info_on_selected)
    self.register_key_sequence( 'C-o c', self.paper.check_chemistry_of_selected)
    self.register_key_sequence( 'C-o e', self._expand_groups)
    # emacs like key bindings
    self.register_key_sequence( 'C-x C-s', self.paper.app.save_CDML)
    self.register_key_sequence( 'C-x C-w', self.paper.app.save_as_CDML)
    self.register_key_sequence( 'C-x C-f', self.paper.app.load_CDML)
    self.register_key_sequence( 'C-x C-c', self.paper.app._quit)
    self.register_key_sequence( 'A-w', self.paper.selected_to_clipboard)
    self.register_key_sequence( 'M-w', self.paper.selected_to_clipboard)
    self.register_key_sequence( 'C-w', lambda : self.paper.selected_to_clipboard( delete_afterwards=1))
    self.register_key_sequence( 'C-y', self._paste_clipboard)
    self.register_key_sequence( 'C-/', self.paper.undo)
    self.register_key_sequence( 'C-S-?', self.paper.redo) #note that 'S-/' => 'S-?'  !!!
    # windows style key bindings
    self.register_key_sequence( 'C-s', self.paper.app.save_CDML)
    self.register_key_sequence( 'C-c', self.paper.selected_to_clipboard)
    self.register_key_sequence( 'C-v', self._paste_clipboard)
    self.register_key_sequence( 'C-z', self.paper.undo)
    self.register_key_sequence( 'C-S-z', self.paper.redo)
    # 'C-x' from windoze is in use - 'C-k' instead
    self.register_key_sequence( 'C-k', lambda : self.paper.selected_to_clipboard( delete_afterwards=1))
    # 'C-a' from windoze is in use - 'C-S-a' instead
    self.register_key_sequence( 'C-S-a', self.paper.select_all)
    # debuging
    #self.register_key_sequence( 'A-i', self._debug_info_for_focused)
    #self.register_key_sequence( 'A-d c', self.paper._open_debug_console)
    # arrow moving
    self.register_key_sequence( 'Up', lambda : self._move_selected( 0, -1))
    self.register_key_sequence( 'Down', lambda : self._move_selected( 0, 1))
    self.register_key_sequence( 'Left', lambda : self._move_selected( -1, 0))
    self.register_key_sequence( 'Right', lambda : self._move_selected( 1, 0))
    # manipulation of the paper.stack
    self.register_key_sequence( 'C-o f', self.paper.lift_selected_to_top)
    self.register_key_sequence( 'C-o b', self.paper.lower_selected_to_bottom)
    self.register_key_sequence( 'C-o s', self.paper.swap_selected_on_stack)
    # chains (C-d as draw)
    self.register_key_sequence_ending_with_number_range( 'C-d', self.add_chain, numbers=range(2,10))
    
  def _debug_info_for_focused( self):
    print self.focused
    print self.focused.__dict__
    
  def mouse_down( self, event, modifiers = []):
    self._shift = 'shift' in modifiers
    self._ctrl = 'ctrl' in modifiers
    self._alt = 'alt' in modifiers
    if self.focused and isinstance( self.focused, hg.selection_square):
      # we will need that later to fix the right corner of the selection_square
      self._startx, self._starty = self.focused.get_fix()
    else:
      self._startx, self._starty = event.x, event.y
    self._block_leave_event = 1

  def mouse_down3( self, event, modifiers = []):
    if self.focused:
      if self.focused not in self.paper.selected:
        self.paper.select( [self.focused])
      dialog = dialogs.config_dialog( self.paper.app, self.paper.selected[:])
      if dialog.changes_made:
        self.paper.start_new_undo_record()
      self.paper.add_bindings()
      
  def mouse_up( self, event):
    self._block_leave_event = 0
    # this strange thing makes the moving of selected arrows and polygons possible - the problem is
    # that these objects are not in self.paper.selected (only their points) and thus ...
    if self._moving_selected_arrow:
      self.paper.select( [self._moving_selected_arrow])
      self._moving_selected_arrow = None
    if not self._dragging:
      self.mouse_click( event)
    else:
      if self._dragging == 3:
        self.paper.select( filter( lambda o: o,\
                                   map( self.paper.id_to_object,\
                                        self.paper.find_enclosed( self._startx, self._starty, event.x, event.y))))
        self.paper.delete( self._selection_rect)
      elif self._dragging == 1:
        # repositioning of atoms and double bonds
        atoms = reduce( operator.add, [o.molecule.atoms_bound_to( o) for o in self.paper.selected if o.object_type == 'atom'], [])
        atoms = misc.filter_unique( [o for o in self.paper.selected if o.object_type == 'atom'] + atoms)
        [o.decide_pos() for o in atoms]
        [o.redraw() for o in atoms]
        [self.reposition_bonds_around_bond( o) for o in self._bonds_to_update]
        self.paper.handle_overlap()
        self.paper.start_new_undo_record()
      elif self._dragging == 2:
        self.paper.handle_overlap()
        self.paper.start_new_undo_record()
      elif self._dragging == 4:
        if self.focused:
          # the unfocus will otherwise not happen and cursor won't be restored
          self.focused.unfocus()
          self.focused = None
        self.paper.start_new_undo_record()
      self._dragging = 0
      self.paper.add_bindings()
    
  def mouse_click( self, event):
    if not self._shift:
      self.paper.unselect_all()
    if self.focused:
#      if self.focused.object_type == 'arrow':
#        self.paper.select( self.focused.points)
#      else:
        if self.focused in self.paper.selected:
          self.paper.unselect( [self.focused])
        elif (self.focused.object_type == 'selection_rect') and (self.focused.object in self.paper.selected):
          self.paper.unselect( [self.focused.object])
        else:
          if self.focused.object_type == 'selection_rect':
            self.paper.select( [self.focused.object])
          else:
            self.paper.select( [self.focused])
    self.paper.add_bindings()

  def mouse_drag( self, event):
    if not self._dragging:
      if self.focused and (self.focused.object_type == 'arrow' or self.focused.object_type == 'polygon'):
        for p in self.focused.points:
          if p in self.paper.selected:
            self._moving_selected_arrow = self.focused
            self.paper.unselect( self.focused.points)
            break
      if self.focused and self.focused.object_type == 'selection_rect':
        # resizing of vector graphics
        self._dragging = 4
        self._dragged_molecule = self.focused
      elif self.focused and (self.focused in self.paper.selected) or self._moving_selected_arrow:
        ### move all selected
        self._dragging = 1
        self.paper.select( self.paper.atoms_to_update())
        self._bonds_to_update = self.paper.bonds_to_update()
        self._arrows_to_update = self.paper.arrows_to_update()
        self.focused.unfocus()
        self.focused = None
      elif self.focused:
        ### move container of focused item
        self._dragging = 2
        if self.focused.object_type == 'point':
          self._dragged_molecule = self.focused.arrow
        elif self.focused.object_type in ('atom', 'bond'):
          self._dragged_molecule = self.focused.molecule
        else:
          self._dragged_molecule = self.focused
        self.focused.unfocus()
        self.focused = None
      else:
        ### select everything in selection rectangle
        if not self._shift:
          self.paper.unselect_all()
        self._dragging = 3
        self._selection_rect = self.paper.create_rectangle( self._startx, self._starty, event.x, event.y)
    if self._dragging == 1:
      dx = event.x-self._startx
      dy = event.y-self._starty
      [o.move( dx, dy) for o in self.paper.selected]
      if self._moving_selected_arrow:
        self._moving_selected_arrow.move( dx, dy)
      [o.redraw() for o in self._bonds_to_update]
      [o.redraw() for o in self._arrows_to_update]
      self._startx, self._starty = event.x, event.y
    elif self._dragging == 2:
      self._dragged_molecule.move( event.x-self._startx, event.y-self._starty)
      self._startx, self._starty = event.x, event.y
    elif self._dragging == 3:
      self.paper.coords( self._selection_rect, self._startx, self._starty, event.x, event.y)
    elif self._dragging == 4:
      self._dragged_molecule.drag( event.x, event.y, fix=(self._startx, self._starty))
      self.paper.signal_to_app( '%i, %i' % ( event.x-self._startx, event.y-self._starty))
      
  def enter_object( self, object, event):
    if not self._dragging:
      if self.focused:
        self.focused.unfocus()
      self.focused = object
      if self.focused.object_type == 'selection_rect':
        self.focused.focus( item= self.paper.find_withtag( 'current')[0])
      else:
        self.focused.focus()

  def leave_object( self, event):
    if self._block_leave_event:
      return
    if not self._dragging:
      if self.focused:
        self.focused.unfocus()
        self.focused = None

  def reposition_bonds_around_atom( self, a):
    bs = a.molecule.atoms_bonds( a)
    [b.redraw( recalc_side = 1) for b in bs if b.type == 2]
    a.reposition_marks()

  def reposition_bonds_around_bond( self, b):
    bs = misc.filter_unique( b.molecule.atoms_bonds( b.atom1) +  b.molecule.atoms_bonds( b.atom2))
    [b.redraw( recalc_side = 1) for b in bs if b.type == 2]
    # all atoms to update
    as = misc.filter_unique( reduce( operator.add, [[b.atom1,b.atom2] for b in bs], []))
    [a.reposition_marks() for a in as]


  ## METHODS FOR KEY EVENTS RESPONSES

  def _delete_selected( self):
    if self.focused and self.focused.object_type == 'selection_rect' and self.focused.object in self.paper.selected:
      self.focused.unfocus()
      self.focused = None
    self.paper.delete_selected()
    if self.focused and not self.paper.is_registered_object( self.focused):
      # focused object was deleted
      self.focused = None
    self.paper.add_bindings()

  def _paste_clipboard( self):
    self.paper.unselect_all()
    xy = (self.paper.canvasx( self.paper.winfo_pointerx() -self.paper.winfo_rootx()),
          self.paper.canvasy( self.paper.winfo_pointery() -self.paper.winfo_rooty()))
    if xy[0] > 0 and xy[1] > 0:
      self.paper.paste_clipboard( xy)

  def _set_name_to_selected( self):
    if self.paper.selected:
      name = self.paper.app.editPool.activate()
      if not name or dom_extensions.isOnlyTags( name):
        return
      # i really don't know if I should call the unicode first
      # i also don't understand how could it have worked without the encode
      name = unicode( name).encode('utf-8')
      try:
        xml.sax.parseString( "<a>%s</a>" % name, xml.sax.ContentHandler())
      except xml.sax.SAXParseException:
        name = xml.sax.saxutils.escape( name)
        # the second round of try: except: should catch problems not related to XML wellfomedness but rather to encoding
        try:
          xml.sax.parseString( "<a>%s</a>" % name, xml.sax.ContentHandler())
        except xml.sax.SAXParseException:        
          self.paper.bell()
          tkMessageBox.showerror( _("Parse Error"), _("Unable to parse the text-\nprobably error with input encoding!"))
          return
      self.paper.set_name_to_selected( name)
      [self.reposition_bonds_around_bond( o) for o in self.paper.bonds_to_update()]
      self.paper.add_bindings()

  def _move_selected( self, dx, dy):
    self.paper.select( self.paper.atoms_to_update())
    _bonds_to_update = self.paper.bonds_to_update()
    _arrows_to_update = self.paper.arrows_to_update()

    [o.move( dx, dy) for o in self.paper.selected]
    [o.redraw() for o in _bonds_to_update]
    [o.redraw() for o in _arrows_to_update]
    if self.paper.um.get_last_record_name() == "arrow-key-move":
      self.paper.um.delete_last_record()
    self.paper.start_new_undo_record( name="arrow-key-move")

  def _expand_groups( self):
    if self.focused:
      self.focused.unfocus()
      self.focused = None
    self.paper.expand_groups()

  def add_chain( self, n):
    if not self.focused:
      return
    a = self.focused
    mol = a.molecule
    for i in range( n):
      a, b = mol.add_atom_to( a) #, bond_type=self.__mode_to_bond_type())[0]]
      self.paper.select( [a])
    self.paper.start_new_undo_record()
    self.paper.add_bindings()
    

### -------------------- DRAW MODE --------------------

class draw_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('draw')
    self._moved_atom = None
    self._start_atom = None
    self.submodes = [['30','18','6','1'],['simple','double','triple'],
                     ['normal','wedge','hatch','adder','bbold'],['fixed','freestyle']]
    self.submodes_names = [[_('30'),_('18'),_('6'),_('1')],[_('simple'),_('double'),_('triple')],
                           [_('normal'),_('wedge'),_('hatch'),_('adder'),_('bold')],
                           [_('fixed length'),_('freestyle')]]
    self.submode = [0, 0, 0, 0]
    
  def mouse_down( self, event, modifiers = []):
    edit_mode.mouse_down( self, event, modifiers = modifiers)
    self.paper.unselect_all()
    if not self.focused:
      mol = self.paper.new_molecule()
      a = mol.create_new_atom( event.x, event.y)
      a.focus()
      self.focused = a
    #self.paper.add_bindings()
    
  def mouse_up( self, event):
    if not self._dragging:
      self.mouse_click( event)
      self.paper.handle_overlap()
    else:
      if self._moved_atom:
        self.paper.select( [self._moved_atom])
      self.paper.handle_overlap() # should be done before repositioning for ring closure to take effect
      # repositioning of double bonds
      if self._start_atom:
        # warn when valency is exceeded
        if self._start_atom.get_free_valency() < 0:
          self.paper.signal_to_app( _("maximum valency exceeded!"))
        # adding more than one bond to group
        if self._start_atom.type == "group":
          self.paper.signal_to_app( _("groups could have valency of 1 only! Atom was transformed to text!"))
          self._start_atom.type = "text"
        self.reposition_bonds_around_atom( self._start_atom)
      self._dragging = 0
      self._start_atom = None
      self._moved_atom = None
      self.paper.add_bindings()
      self.paper.start_new_undo_record()

  def mouse_click( self, event):
    if not self.focused:
      #print "it should not get here!!!"
      mol = self.paper.new_molecule()
      a = mol.create_new_atom( event.x, event.y)
      self.paper.add_bindings()
      self.paper.select( [mol.add_atom_to( a, bond_type=self.__mode_to_bond_type())[0]])
      self.focused = a
    else:
      if self.focused.object_type == 'atom':
        a, b = self.focused.molecule.add_atom_to( self.focused, bond_type=self.__mode_to_bond_type())
        # warn when valency is exceeded
        if self.focused.get_free_valency() < 0:
          self.paper.signal_to_app( _("maximum valency exceeded!"))
        # adding more than one bond to group
        if self.focused.type == "group":
          self.paper.signal_to_app( _("groups could have valency of 1 only! Atom was transformed to text!"))
          self.focused.type = "text"
        # repositioning of double bonds
        self.reposition_bonds_around_bond( b)
        self.paper.select( [a])
      elif self.focused.object_type == 'bond':
        if self._shift:
          self.focused.toggle_type( only_shift = 1, to_type=self.submodes[1][ self.submode[1]])
          self.focused.focus() # refocus
        else:
          self.focused.toggle_type( to_type=self.submodes[1][ self.submode[1]])
          # warn when valency is exceeded
          if self.focused.atom1.get_free_valency() < 0 or self.focused.atom2.get_free_valency() < 0:
            self.paper.signal_to_app( _("maximum valency exceeded!"))
          self.focused.focus() # refocus
    self.paper.start_new_undo_record()
    self.paper.add_bindings()

  def mouse_drag( self, event):
    if not self._dragging:
#      if abs(self._starty - event.y)+ abs(self._startx - event.x) > 1: ## threshhold for dragging
      self._dragging = 1
#      else:
#        return
      if self.focused and self.focused.object_type == "atom":
        self._start_atom = self.focused
        if self.submode[2] == 1:
          self._moved_atom, self._bonds_to_update = self.focused.molecule.add_atom_to( self.focused,  bond_type=self.__mode_to_bond_type(), pos=(event.x, event.y))
        else:
          self._moved_atom, self._bonds_to_update = self.focused.molecule.add_atom_to( self.focused,  bond_type=self.__mode_to_bond_type())
    if self._start_atom:
      if self.focused and self.focused != self._start_atom and self.focused.object_type == 'atom':
        x, y = self.focused.get_xy()
      elif self.submode[2] == 1:
        x, y = event.x, event.y
      else:
        dx = event.x - self._startx
        dy = event.y - self._starty
        x0, y0 = self._start_atom.get_xy()
        x,y = geometry.point_on_circle( x0, y0, self.paper.any_to_px( self.paper.standard.bond_length),
                                        direction = (dx, dy),
                                        resolution = int( self.submodes[0][ self.submode[ 0]]))
      self._moved_atom.move_to( x, y)
      self._bonds_to_update.redraw()

  def enter_object( self, object, event):
    if self.focused:
      self.focused.unfocus()
    self.focused = object
    self.focused.focus()
    #if self._dragging:
     # self.mouse_drag( event)
    ### this is here to help moving moved atom to get focused as soon as it is entered
    ### but it breakes it when button is released, therefor its commented
      
  def leave_object( self, event):
    if self.focused:
      self.focused.unfocus()
      self.focused = None
    else:
      pass #warn( "leaving NONE", UserWarning, 2)

  def __mode_to_bond_type( self):
    """maps bond type submode to bond_type number"""
    order = self.submode[1]+1
    type = self.submodes[2][ self.submode[2]][0]
    type = "%s%d" % (type, order) 
    #print type
##     if type == 'normal':
##       type = 1
##     else:
##      type = data.bond_types.index( type)
    return order



## -------------------- ARROW MODE --------------------

class arrow_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('arrow')
    self._start_point = None
    self._moved_point = None
    self._arrow_to_update = None
    self.submodes = [['30','18','6','1'],['fixed','freestyle'],['anormal','spline']]
    self.submodes_names = [[_('30'),_('18'),_('6'),_('1')], [_('fixed length'),_('freestyle')],
                           [_('normal'),_('spline')]]
    self.submode = [0, 0, 0]
    self.__nothing_special = 0 # to easy determine whether new undo record should be started

  def mouse_down( self, event, modifiers = []):
    edit_mode.mouse_down( self, event, modifiers = modifiers)
    self.paper.unselect_all()
    if not self.focused:
      spline = (self.get_submode( 2) == 'spline')
      arr = self.paper.new_arrow( spline=spline)
      self._start_point = arr.create_new_point( event.x, event.y)
      self._start_point.focus()
      self.focused = self._start_point
      self._arrow_to_update = arr
      #arr.draw()
    elif self.focused.object_type == 'point' and self.focused.arrow.object_type == 'arrow':
      self._start_point = self.focused
      self._arrow_to_update = self._start_point.arrow
    elif self.focused.object_type == 'arrow':
      self._arrow_to_update = self.focused
      self._start_point = None
    else:
      self.__nothing_special = 1
    self._block_leave_event = 0
    self.paper.add_bindings()

  def mouse_drag( self, event):
    if self._start_point:
      if not self._dragging:
        self._dragging = 1
        # update the spline-notspline in case it differs from the set submode
        spline = (self.get_submode( 2) == 'spline')
        if self._arrow_to_update.spline != spline:
          self._arrow_to_update.spline = spline
        if self._start_point == self._arrow_to_update.points[-1]:
          pos = -1
        else:
          pos = self._arrow_to_update.points.index( self._start_point)
        self._moved_point = self._start_point.arrow.create_new_point( event.x, event.y, position=pos)
      if self.submode[1] == 1:
        x, y = event.x, event.y
      else:
        dx = event.x - self._startx
        dy = event.y - self._starty
        x0, y0 = self._start_point.get_xy()
        x,y = geometry.point_on_circle( x0, y0,
                                        self.paper.any_to_px( self.paper.standard.arrow_length),
                                        direction = (dx, dy),
                                        resolution = int( self.submodes[0][ self.submode[ 0]]))
      self._moved_point.move_to( x, y)
      self._arrow_to_update.redraw()

  def mouse_up( self, event):
    if not self._dragging:
      # update the spline-notspline in case it differs from the set submode
      spline = (self.get_submode( 2) == 'spline')
      if self._arrow_to_update and self._arrow_to_update.spline != spline:
        self._arrow_to_update.spline = spline
        self._arrow_to_update.redraw()
      # change the arrow direction only if the spline was not changed
      elif self._arrow_to_update and not self._start_point:
        self._arrow_to_update.change_direction()
      # add point
      elif self._arrow_to_update:
        x0, y0 = self._start_point.get_xy()
        if self._start_point == self._arrow_to_update.points[-1]:
          pos = -1
        else:
          pos = self._arrow_to_update.points.index( self._start_point)
        pnt = self._arrow_to_update.create_new_point( x0+self.paper.any_to_px( self.paper.standard.arrow_length),
                                                      y0, position=pos)
        self.paper.select( [pnt])
        self._arrow_to_update.redraw()
      #self.mouse_click( event)
    else:
      if self._moved_point:
        self.paper.select( [self._moved_point])
      self._dragging = 0
    self._start_point = None
    self._moved_point = None
    self._arrow_to_update = None
    if self.__nothing_special:
      self.__nothing_special = 0
    else:
      self.paper.start_new_undo_record()
    self.paper.add_bindings()

  def mouse_click( self, event):
    pass

  def enter_object( self, object, event):
    if self.focused:
      self.focused.unfocus()
    self.focused = object
    if self.focused.object_type == 'selection_rect':
      self.focused.focus( item= self.paper.find_withtag( 'current')[0])
    else:
      self.focused.focus()


  def leave_object( self, event):
    if self.focused:
      self.focused.unfocus()
      self.focused = None
    else:
      warn( "leaving NONE", UserWarning, 2)



class plus_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('plus')
    self._start_point = None
    self._moved_point = None

  def mouse_down( self, event, modifiers = []):
    edit_mode.mouse_down( self, event, modifiers = modifiers)
    self.paper.unselect_all()

  def mouse_drag( self, event):
    if not self._dragging:
      self._dragging = 1

  def mouse_up( self, event):
    if not self._dragging:
      self.mouse_click( event)
    self._dragging = 0

  def mouse_click( self, event):
    if not self.focused:
      pl = self.paper.new_plus( event.x, event.y)
      self.paper.select( [pl])
    else:
      pass
    self.paper.start_new_undo_record()
    self.paper.add_bindings()

  def leave_object( self, event):
    if self.focused:
      self.focused.unfocus()
      self.focused = None
    else:
      warn( "leaving NONE", UserWarning, 2)



class template_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('template')
    self.submodes = [self.paper.tm.get_template_names()]
    self.submodes_names = self.submodes
    self.submode = [0]
    self.register_key_sequence( 'C-t 1', self._mark_focused_as_template_atom_or_bond)
    
  def mouse_click( self, event):
    self.paper.unselect_all()
    if not self.focused:
      t = self.paper.tm.get_transformed_template( self.submode[0], (event.x, event.y), type='empty')
    else:
      if self.focused.object_type == 'atom':
        if self.focused.z != 0:
          self.paper.signal_to_app( _("Sorry, it is not possible to append a template to an atom with non-zero Z coordinate, yet."))
          return
        if len( self.focused.molecule.atoms_bound_to( self.focused)) == 1:
          x1, y1 = self.focused.molecule.atoms_bound_to( self.focused)[0].get_xy()
          x2, y2 = self.focused.get_xy()
          t = self.paper.tm.get_transformed_template( self.submode[0], (x1,y1,x2,y2), type='atom1')
        else:
          x1, y1 = self.focused.get_xy()
          x2, y2 = self.focused.molecule.find_place( self.focused, self.paper.any_to_px( self.paper.standard.bond_length))
          t = self.paper.tm.get_transformed_template( self.submode[0], (x1,y1,x2,y2), type='atom2')
      elif self.focused.object_type == 'bond':
        x1, y1 = self.focused.atom1.get_xy()
        x2, y2 = self.focused.atom2.get_xy()
        #find right side of bond to append template to
        atms = self.focused.molecule.atoms_bound_to( self.focused.atom1) + self.focused.molecule.atoms_bound_to( self.focused.atom2)
        atms = misc.difference( atms, [self.focused.atom1, self.focused.atom2])
        coords = [a.get_xy() for a in atms]
        if reduce( operator.add, [geometry.on_which_side_is_point( (x1,y1,x2,y2), xy) for xy in coords]) > 0:
          x1, y1, x2, y2 = x2, y2, x1, y1
        t = self.paper.tm.get_transformed_template( self.submode[0], (x1,y1,x2,y2), type='bond')
        if not t:
          return # the template was not meant to be added to a bond
      else:
        return
    self.paper.add_molecule( t)
    t.draw()
    self.paper.signal_to_app( _("Added molecule from template: ")+self.paper.tm.get_template_names()[ self.submode[0]].encode('utf-8'))
    self.paper.select( [o for o in t])
    self.paper.handle_overlap()
    # checking of valency
    if self.focused:
      if (self.focused.object_type == "bond") and (self.focused.atom1.get_free_valency() < 0 or self.focused.atom2.get_free_valency() < 0):
        self.paper.signal_to_app( _("maximum valency exceeded!"))
      elif (self.focused.object_type == "atom") and self.focused.get_free_valency() < 0:
        self.paper.signal_to_app( _("maximum valency exceeded!"))

    self.paper.start_new_undo_record()
    self.paper.add_bindings()

  def _mark_focused_as_template_atom_or_bond( self):
    if self.focused and self.focused.object_type == 'atom':
      self.focused.molecule.t_atom = self.focused
      self.paper.signal_to_app( _("focused atom marked as 'template atom'")) 
    elif self.focused and self.focused.object_type == 'bond':
      atms = self.focused.molecule.atoms_bound_to( self.focused.atom1) + self.focused.molecule.atoms_bound_to( self.focused.atom2)
      atms = misc.difference( atms, [self.focused.atom1, self.focused.atom2])
      coords = [a.get_xy() for a in atms]
      line = self.focused.atom1.get_xy() + self.focused.atom2.get_xy()
      if reduce( operator.add, [geometry.on_which_side_is_point( line, xy) for xy in coords]) > 0:
        self.focused.molecule.t_bond_first = self.focused.atom1
        self.focused.molecule.t_bond_second = self.focused.atom2
      else:
        self.focused.molecule.t_bond_first = self.focused.atom2
        self.focused.molecule.t_bond_second = self.focused.atom1
      self.paper.signal_to_app( _("focused bond marked as 'template bond'")) 



##--------------------TEXT MODE--------------------

class text_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('text')
    self._start_point = None
    self._moved_point = None

  def mouse_down( self, event, modifiers = []):
    edit_mode.mouse_down( self, event, modifiers = modifiers)
    self.paper.unselect_all()

  def mouse_drag( self, event):
    if not self._dragging:
      self._dragging = 1

  def mouse_up( self, event):
    if not self._dragging:
      self.mouse_click( event)
    self._dragging = 0

  def mouse_click( self, event):
    if not self.focused:
      name = self.paper.app.editPool.activate()
      ## catch not well-formed text
      try:
        xml.sax.parseString( "<a>%s</a>" % name, xml.sax.ContentHandler())
      except xml.sax.SAXParseException:
        name = xml.sax.saxutils.escape( name)
        # the second round of try: except: should catch problems not
        # related to XML wellfomedness but rather to encoding
        try:
          xml.sax.parseString( "<a>%s</a>" % name, xml.sax.ContentHandler())
        except xml.sax.SAXParseException:        
          tkMessageBox.showerror( _("Parse Error"), _("Unable to parse the text-\nprobably problem with input encoding!"))
          self.paper.bell()
          return
      self.paper.set_name_to_selected( name)

      if name and not dom_extensions.isOnlyTags( name):
        txt = self.paper.new_text( event.x, event.y, text=name)
        txt.draw()
        self.paper.select( [txt])
        self.paper.add_bindings()
        self.paper.start_new_undo_record()        
    else:
      if self.focused.object_type == 'text':
        self.paper.select( [self.focused])
        name = self.paper.app.editPool.activate( text = self.focused.get_text())
        if name and not dom_extensions.isOnlyTags( name):
          self.paper.set_name_to_selected( name)
          self.paper.add_bindings()
      elif self.focused.object_type == 'atom':
        self.paper.select( [self.focused])
        name = self.paper.app.editPool.activate( text = self.focused.get_text())
        if name and not dom_extensions.isOnlyTags( name):
          self.paper.set_name_to_selected( name)
          self.paper.add_bindings()

  def leave_object( self, event):
    if self.focused:
      self.focused.unfocus()
      self.focused = None
    else:
      warn( "leaving NONE", UserWarning, 2)


class rotate_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('rotate')
    self._rotated_mol = None
    self.submodes = [['2D','3D']]
    self.submodes_names = [[_('2D'),_('3D')]]
    self.submode = [0]


  def mouse_down( self, event, modifiers = []):
    edit_mode.mouse_down( self, event, modifiers = modifiers)
    # blocking is not necessary in rotate mode
    self._block_leave_event = 0
    self.paper.unselect_all()
    if self.focused and (self.focused.object_type == 'atom' or self.focused.object_type == 'bond'):
      self._rotated_mol = self.focused.molecule
      x1, y1, x2, y2 = self.paper.list_bbox( [o.item for o in self._rotated_mol.atoms_map])
      self._centerx = x1+(x2-x1)/2.0
      self._centery = y1+(y2-y1)/2.0
    if self.focused:
      self.focused.unfocus()
      self.focused = None
    
  def mouse_up( self, event):
    if not self._dragging:
      self.mouse_click( event)
    else:
      self._dragging = 0
      self._moved_atom = None
      if self._rotated_mol:
        [b.redraw( recalc_side=1) for b in self._rotated_mol.bonds]
        [a.reposition_marks() for a in self._rotated_mol.atoms_map]
        self._rotated_mol = None
        self.paper.start_new_undo_record()
    self.paper.add_bindings()

  def mouse_drag( self, event):
    if not self._dragging:
      self._dragging = 1
    if self._rotated_mol:
      dx0 = event.x - self._centerx
      dy0 = event.y - self._centery
      dx1 = event.x - self._startx
      dy1 = event.y - self._starty
      sig = -geometry.on_which_side_is_point( (self._centerx, self._centery, self._startx, self._starty), (event.x, event.y))
      self._startx, self._starty = event.x, event.y
      if self.submode[0] == 0:
        # 2D rotation
        angle = round( sig * (abs( dx1) +abs( dy1)) / 50.0, 2)
        tr = transform.transform()
        tr.set_move( -self._centerx, -self._centery)
        tr.set_rotation( angle)
        tr.set_move( self._centerx, self._centery)
        for a in self._rotated_mol.atoms_map:
          x, y = a.get_xy()
          x, y = tr.transform_xy( x, y)
          a.move_to( x, y)
          # its no very time-optimal (it would be better to recalculate the position of marks using the
          # rotation calculation) but it works and takes only 0.1 ms per turn step on 800 MHz
          a.reposition_marks()
        for a in self._rotated_mol.bonds:
          a.redraw()
      else:
        # 3D rotation
        angle1 = round( dx1 / 50.0, 2)
        angle2 = round( dy1 / 50.0, 2)
        tr = transform3d.transform3d()
        tr.set_move( -self._centerx, -self._centery, 0)
        tr.set_rotation( angle2, angle1, 0)
        tr.set_move( self._centerx, self._centery, 0)
        for a in self._rotated_mol.atoms_map:
          x, y, z = a.x, a.y, a.z
          x, y, z = tr.transform_xyz( x, y, z)
          a.move_to( x, y)
          a.z = z
        for a in self._rotated_mol.bonds:
          a.simple_redraw()

  def mouse_click( self, even):
    pass


class name_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('name')
    self.submodes = [['id','name']]
    self.submodes_names = [[_('id'), _('name')]]
    self.submode = [0]


  def mouse_click( self, event):
    if self.focused and (self.focused.object_type == 'atom' or self.focused.object_type == 'bond'):
      mol = self.focused.molecule
      name = self.paper.app.editPool.activate( text=mol.__dict__[ self.submodes[0][ self.submode[0]]])
      if name:
        mol.__dict__[ self.submodes[0][ self.submode[0]]] = name
        self.paper.signal_to_app( _('%s %s was set to molecule') % (self.submodes_names[0][ self.submode[0]], name))
        self.paper.start_new_undo_record()


class vector_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('vector graphics')
    self.submodes = [['rectangle','square','oval', 'circle', 'polygon']]
    self.submodes_names = [[_('rectangle'),_('square'),_('oval'),_('circle'),_('polygon')]]
    self.submode = [0]
    self._polygon_points = []
    self._polygon_line = None
    self._current_obj = None
##1    self._x_label = None

  def mouse_down( self, event):
    edit_mode.mouse_down( self, event)
    if self.submode[0] == 4:
      self.paper.unselect_all()
      self._block_leave_event = 0
      self._polygon_points += [event.x, event.y]

  def mouse_drag( self, event):
    if self.submode[0] == 4:
      self.mouse_move( event)
      return
    if not self.focused and not self._dragging:
      self._dragging = 5
      self.paper.unselect_all()
      if self.submode[0] == 0:
        self._current_obj = self.paper.new_rect( (self._startx, self._starty, event.x, event.y))
      elif self.submode[0] == 1:
        self._current_obj = self.paper.new_square( (self._startx, self._starty, event.x, event.y))
      elif self.submode[0] == 2:
        self._current_obj = self.paper.new_oval( (self._startx, self._starty, event.x, event.y))
      elif self.submode[0] == 3:
        self._current_obj = self.paper.new_circle( (self._startx, self._starty, event.x, event.y))
      self._current_obj.draw()
    elif not self.focused and self._dragging and self._current_obj:
      self._current_obj.resize( (self._startx, self._starty, event.x, event.y), fix=( self._startx, self._starty))
      self.paper.signal_to_app( '%i, %i' % ( abs( self._startx-event.x), abs( self._starty-event.y)))
##1       if self._x_label:
##1         self.paper.delete( self._x_label)
##1       self._x_label = self.paper.create_text( self._startx, self._starty+10, text='%i' % (dx*(self._startx-event.x)))
    elif self.focused or self._dragging in (1,2):
      edit_mode.mouse_drag( self, event)

  def mouse_up( self, event):
    if self.submode[0] == 4:
      if not self._polygon_line:
        self._polygon_line = self.paper.create_line( tuple( self._polygon_points + [event.x, event.y]), fill='black')
      else:
        self.paper.coords( self._polygon_line, tuple( self._polygon_points + [event.x, event.y]))
      return
    self._block_leave_event = 0
    if self._dragging == 5:
      self._dragging = 0
      if self._current_obj:
        if self._current_obj.object_type != 'selection_rect':
          self.paper.select( [self._current_obj])
        self._current_obj = None
      self.paper.start_new_undo_record()
      self.paper.add_bindings()
##1      if self._x_label:
##1        self.paper.delete( self._x_label)
    elif self._dragging:
      edit_mode.mouse_up( self, event)
    else:
      self.mouse_click( event)

  def mouse_down3( self, event, modifiers = []):
    if self.submode[0] == 4 and self._polygon_line:
      self.paper.delete( self._polygon_line)
      if len( self._polygon_points) > 2:
        poly = self.paper.new_polygon( tuple( self._polygon_points + [event.x, event.y]))
        poly.draw()
        self.paper.select( [poly])
      self._polygon_points = []
      self._polygon_line = None
      self.paper.start_new_undo_record()
      self.paper.add_bindings()
    else:
      edit_mode.mouse_down3( self, event, modifiers=modifiers)

  def mouse_move( self, event):
    if self.submode[0] == 4 and self._polygon_points:
      if not self._polygon_line:
        self._polygon_line = self.paper.create_line( tuple( self._polygon_points + [event.x, event.y]), fill='black')
      else:
        self.paper.coords( self._polygon_line, tuple( self._polygon_points + [event.x, event.y]))
    

class mark_mode( edit_mode):

  def __init__( self, paper):
    edit_mode.__init__( self, paper)
    self.name = _('mark')
    self.submodes = [['radical','biradical','electronpair','plusincircle','minusincircle']]
    self.submodes_names = [[_('radical'), _('biradical'), _('electron pair'),
                            _('plus'), _('minus')]]
    self.submode = [0]

  def mouse_click( self, event):
    a = ['radical','biradical','electronpair','plus','minus']
    if self.focused and self.focused.object_type == 'atom':
      self.focused.set_mark( mark=a[ self.submode[0]])
      self.paper.start_new_undo_record()
    self.paper.add_bindings()




def event_to_key( event):
  key = event.keysym
  # 2 hacks to prevent ' ' -> 'space', '.' -> 'period' and other conversions
  # first is dealing with "strange keys" (see data.strange_key_symbols for more info)
  if key in data.strange_key_symbols:
    key = data.strange_key_symbols[ key]
  # second is for keys that are more consistent in their behavior (char is not changing with Ctrl)
  elif len(key) > 1 and string.lower( key) == key:
    key = event.char
  # now special keys as Ctrl, Alt etc.
  elif key in data.special_key_symbols:
    key = data.special_key_symbols[ key]
  else:
    # normal keys should be lowercase, specials uppercase
    if len( key) == 1:
      key = string.lower( key)
  if key:
    return key
  else:
    warn( 'how did we get here?!?', UserWarning, 2)
    return ''