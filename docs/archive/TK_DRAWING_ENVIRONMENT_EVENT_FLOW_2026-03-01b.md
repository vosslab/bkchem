# Tkinter Main/Paper Evaluation for Qt Port

## Context

BKChem is a 2D chemistry structure editor being ported from Tkinter to Qt. The Tkinter version has a mature, well-organized codebase split across `main.py` + 4 mixins (~1,870 lines) and `paper.py` + 8 mixins (~2,224 lines). The Qt version already has solid infrastructure (menus, modes, canvas, models) but needs the interaction/editing layer fleshed out. This evaluation catalogs what to preserve, what to replace, and what the Qt version still needs.

---

## 1. Architecture overview: Tkinter version

### main.py + main_lib/ (~1,870 lines)

```
BKChem(MainTabsMixin, MainModesMixin, MainChemistryIOMixin, MainFileIOMixin, Tk)
```

| Module | Lines | Responsibility |
| --- | --- | --- |
| `main.py` | 828 | Root window, menu, init, status bar, preferences, singletons |
| `main_lib/main_tabs.py` | 206 | Tab lifecycle (add/close/switch papers) |
| `main_lib/main_modes.py` | 265 | Mode toolbar + submode ribbon construction |
| `main_lib/main_file_io.py` | 360 | CDML/SVG save/load, format plugins, recent files |
| `main_lib/main_chemistry_io.py` | 219 | SMILES/InChI/peptide import/export dialogs |

### paper.py + paper_lib/ (~2,224 lines)

```
chem_paper(PaperLayoutMixin, PaperPropertiesMixin, PaperCDMLMixin,
           PaperFactoriesMixin, PaperEventsMixin, PaperIdManagerMixin,
           PaperSelectionMixin, PaperTransformsMixin, PaperZoomMixin, Canvas)
```

| Module | Lines | Responsibility |
| --- | --- | --- |
| `paper.py` | 374 | Coordination: clipboard, undo, hex grid, queries |
| `paper_lib/paper_zoom.py` | 220 | Zoom in/out/fit/content, viewport centering |
| `paper_lib/paper_transforms.py` | 76 | Real-to-canvas coordinate mapping |
| `paper_lib/paper_selection.py` | 208 | Selection state, filters, delete, toggle |
| `paper_lib/paper_id_manager.py` | 41 | Tk canvas ID to object mapping |
| `paper_lib/paper_events.py` | 217 | All mouse/keyboard bindings, event dispatch to modes |
| `paper_lib/paper_factories.py` | 111 | Object creation (molecule, arrow, text, shapes) |
| `paper_lib/paper_cdml.py` | 216 | CDML serialization, ID sandboxing, version upgrade |
| `paper_lib/paper_properties.py` | 248 | Paper size/type, background, standard management |
| `paper_lib/paper_layout.py` | 512 | Alignment, overlap merge, coord regen, cleanup |

---

## 2. Business logic to preserve (toolkit-independent)

These are the "good stuff" algorithms and patterns that must survive the Qt port.

### 2.1 Selection system (paper_selection.py)

- **`selected_to_unique_top_levels()`**: Deduplicates selected atoms/bonds to their parent molecules. Selecting 3 atoms from the same molecule returns 1 molecule, not 3 atoms. Returns `(unique_tops, is_unique)` tuple.
- **Computed properties**: `selected_mols`, `selected_atoms`, `selected_bonds`, `groups_selected`, `one_mol_selected`, `two_or_more_selected` - efficient filter properties used everywhere.
- **`bonds_to_update()` / `atoms_to_update()` / `arrows_to_update()`**: Find objects adjacent to selection that need redraw after a move/edit.
- **`delete_selected()`**: Complex deletion with special handling for arrows (delete point vs whole arrow), bonds (remove from molecule graph), and molecule cleanup.

### 2.2 Geometry and layout (paper_layout.py)

- **`align_selected(mode)`**: 6-axis alignment (top/bottom/left/right/h-center/v-center). Extracts bboxes, computes reference coordinate, moves each item by offset.
- **`clean_selected()`**: Regenerates 2D coordinates via OASA's RDKit-backed `Compute2DCoords`. Locks selected atom positions, regenerates non-selected, detects and corrects mirror flips.
- **`handle_overlap()`**: Finds atoms within 2px of each other, merges overlapping molecules (flattens graph), preserves/deletes original atoms, tracks for undo.
- **`swap_sides_of_selected()`**: Mirror operation around vertical or horizontal axis.
- **`place_next_to_selected()` / `place_next_to_bbox()`**: Positioning relative to selection.

### 2.3 CDML serialization (paper_cdml.py)

- **ID sandboxing**: `onread_id_sandbox_activate()` / `onread_id_sandbox_finish()` - swaps global ID manager during paste/import to prevent collisions, then reassigns IDs.
- **Version upgrade**: `CDML_versions.transform_dom_to_version()` on read.
- **Round-trip structure**: Paper properties, viewport, standard, all objects, external data.
- **`get_cropping_bbox()`**: Computes SVG export crop region excluding background/grid.

### 2.4 Coordinate transforms (paper_transforms.py)

- Dual coordinate system: Real/model coordinates vs canvas/screen pixels.
- `real_to_canvas()` / `canvas_to_real()` with scale factor.
- `screen_to_real_coords()` / `real_to_screen_coords()` with transform matrices.
- Non-uniform scaling support via `_ratio = sqrt(ratio_x * ratio_y)`.

### 2.5 File I/O logic (main_file_io.py)

- **Format routing by extension**: `.cdml`, `.cdgz`, `.svg`, `.cdsvg` etc.
- **CDML namespace handling**: Complex XML parsing with namespace resolution.
- **Plugin system**: `format_loader.load_format_entries()` for import/export codecs.
- **Recent files tracking** and collision detection.

### 2.6 Tab management logic (main_tabs.py)

- Tab name generation and paper-to-tab mapping.
- File collision detection (`check_if_the_file_is_opened()`).
- Duplicate name counting (`check_number_of_opened_same_names()`).
- Event guard pattern preventing recursive tab selection.

### 2.7 Mode switching flow (main_modes.py)

- Settings copying between modes (`copy_settings()`).
- Submode group layout routing: row vs grid vs combobox.
- Default submode selection on mode change.
- Dynamic widget cleanup and reconstruction.

### 2.8 Chemistry I/O (main_chemistry_io.py)

- SMILES/InChI parsing with error mapping (unsupported InChI features).
- Peptide sequence validation.
- ID sandbox activation during chemistry imports.
- Result formatting for SMILES/InChI generation display.

### 2.9 Undo/redo integration (paper.py)

- Checkpoint creation with `before_undo_record()` / `after_undo_record()` hooks.
- Before-hook: runs chemistry checks (e.g., `check_linear_fragments()`).
- After-hook: updates scroll region if bbox changed.
- Lazy scroll region updates tied to geometry changes.

### 2.10 Clipboard management (paper.py)

- Internal clipboard as CDML DOM (separate from system clipboard).
- `selected_to_clipboard()`: Serialize selected to DOM with optional delete.
- `paste_clipboard()`: Deserialize with offset, ID regeneration, overlap handling.
- `selected_to_real_clipboard_as_SVG()`: System clipboard SVG export.

### 2.11 Paper properties (paper_properties.py)

- Paper type/orientation/size management (A4, Letter, custom).
- Background rectangle drawing and updates.
- Standard (drawing style) management: load/save personal standard.
- `apply_current_standard()`: Apply standard to objects with template awareness.

### 2.12 Object factories (paper_factories.py)

- Typed creation: `new_molecule()`, `new_arrow()`, `new_plus()`, `new_text()`, `new_rect()`, etc.
- `add_object_from_package()`: DOM element deserialization into typed objects (molecule, arrow, text, shapes, reaction).

---

## 3. Tkinter-specific code to replace

### 3.1 Widget infrastructure

| Tkinter | Qt equivalent | Notes |
| --- | --- | --- |
| `Tk.__init__()` | `QMainWindow.__init__()` | Already done in Qt |
| `ttk.Notebook` | `QTabWidget` | Tab management |
| `ttk.Frame` | `QWidget` / `QFrame` | Container widgets |
| `ttk.Button` | `QPushButton` | Buttons |
| `ttk.Radiobutton` | `QRadioButton` / `QActionGroup` | Mode selection |
| `ttk.Label` | `QLabel` | Text labels |
| `ttk.Combobox` | `QComboBox` | Dropdowns |
| `ttk.Scrollbar` | Built into `QGraphicsView` | Scrolling |
| `StringVar` | Qt properties + signals | Reactive state |
| `Frame.grid()` / `pack()` | `QHBoxLayout` / `QVBoxLayout` / `QGridLayout` | Layout |

### 3.2 Dialog replacements

| Tkinter | Qt equivalent |
| --- | --- |
| `askopenfilename()` | `QFileDialog.getOpenFileName()` |
| `asksaveasfilename()` | `QFileDialog.getSaveFileName()` |
| `messagebox.showerror()` | `QMessageBox.critical()` |
| `messagebox.askokcancel()` | `QMessageBox.question()` |
| `BkPromptDialog` | Custom `QDialog` with `QLineEdit` |
| `BkTextDialog` | Custom `QDialog` with `QTextEdit` |

### 3.3 Canvas operations

| Tkinter Canvas | Qt QGraphicsScene |
| --- | --- |
| `create_rectangle()` | `addRect()` / `QGraphicsRectItem` |
| `create_line()` | `addLine()` / `QGraphicsLineItem` |
| `coords(item_id)` | `item.setPos()` / `item.boundingRect()` |
| `itemconfig(id, fill=)` | `item.setBrush()` / `item.setPen()` |
| `delete(id)` | `removeItem(item)` |
| `scale(id, x0, y0, sx, sy)` | `QGraphicsView.setTransform()` |
| `find_overlapping()` | `items(rect)` |
| `find_withtag(tag)` | Custom item registry |
| `tag_bind(tag, event)` | Item-level event handlers |
| `canvasx()` / `canvasy()` | `mapToScene()` |
| `bbox(ALL)` | `itemsBoundingRect()` |
| `winfo_rgb(color)` | `QColor(color)` |

### 3.4 Event system

| Tkinter | Qt |
| --- | --- |
| `bind('<Button-1>', handler)` | `mousePressEvent()` override |
| `bind('<B1-Motion>', handler)` | `mouseMoveEvent()` override |
| `bind('<Key>', handler)` | `keyPressEvent()` override |
| `bind('<<selection-changed>>')` | Custom `selectionChanged` signal |
| `bind('<<zoom-changed>>')` | Custom `zoomChanged` signal |
| `after(ms, callback)` | `QTimer.singleShot()` |

### 3.5 Other Tk-specific patterns

- `tk_setPalette()`, `option_add()` --> Qt stylesheets / `QPalette`
- `protocol("WM_DELETE_WINDOW")` --> `QMainWindow.closeEvent()`
- `update_idletasks()` --> `QApplication.processEvents()` (rarely needed)
- `clipboard_clear()` / `clipboard_append()` --> `QApplication.clipboard()`

---

## 4. What the Qt version already has

| Capability | Qt status | Tk equivalent |
| --- | --- | --- |
| Main window + menus | Done (YAML-driven `MenuBuilder`) | `init_menu()` |
| Mode toolbar | Done (`ModeToolbar` widget) | `init_mode_buttons()` |
| Submode ribbon | Done (`SubModeRibbon` widget) | `_build_submode_row/grid()` |
| Edit ribbon | Done (`EditRibbon` widget) | `editPool` |
| Canvas scene | Done (`ChemScene`) | `chem_paper` Canvas |
| Canvas view + zoom | Done (`ChemView`) | `PaperZoomMixin` |
| Theme system | Done (YAML themes) | `theme_manager` |
| Document model | Done (`Document`) | Paper state |
| Molecule/atom/bond models | Done (composition) | Inheritance from OASA |
| CDML I/O | Done (`cdml_io.py`) | `PaperCDMLMixin` |
| SVG/PNG/PDF export | Done (`export.py`) | `format_loader` |
| Undo/redo | Done (`QUndoStack`) | `undo_manager` |
| Render ops painter | Done | `render_ops` |
| 20 mode skeletons | Done (structure only) | Fully implemented modes |

---

## 5. What the Qt version still needs from Tkinter

### 5.1 CRITICAL: Selection system

The Tk `PaperSelectionMixin` has sophisticated logic not yet in Qt:
- Multi-object selection with dedup to top-level containers
- Selection filters (atoms, bonds, molecules, groups)
- `delete_selected()` with arrow/bond/molecule special cases
- `bonds_to_update()` / `atoms_to_update()` for efficient adjacent redraws
- Selection-changed event propagation

### 5.2 CRITICAL: Clipboard / copy-paste

- Internal CDML clipboard (serialize selected --> DOM --> deserialize with offset)
- ID sandboxing during paste
- System clipboard SVG export
- Cut = copy + delete

### 5.3 HIGH: Layout and geometry operations

- Alignment (6-axis)
- Overlap detection and molecule merging
- Coordinate regeneration via OASA/RDKit
- Mirror/swap operations
- Stack reordering (lift/lower)

### 5.4 HIGH: Mode implementations

The Qt modes are skeletons. Each needs the interaction logic from Tk:
- **Draw mode**: Click-to-place atoms, drag bonds, smart angles, transoid placement
- **Edit mode**: Select, move, resize, marquee selection
- **Template mode**: Template preview, click-to-place, attachment points
- **Rotate mode**: Rotation around center
- **Arrow mode**: Arrow drawing with points
- **Text mode**: Text input on canvas

### 5.5 HIGH: Tab management

- Multi-document tabs (add/close/switch)
- Unsaved changes prompt on close
- File collision detection
- Duplicate name handling

### 5.6 MEDIUM: Chemistry I/O dialogs

- SMILES import/export with error handling
- InChI import/export with feature error mapping
- Peptide sequence import

### 5.7 MEDIUM: Paper properties

- Paper type/orientation/size dialog
- Background rectangle management
- Standard (drawing style) load/save/apply
- Scroll region management

### 5.8 LOW: Preferences

- Window geometry save/restore
- Recent files list
- Default directories
- Personal standard persistence

---

## 6. Drawing environment: how clicks become chemistry

This section traces the complete event-to-pixel pipeline for every major drawing interaction. This is the core behavior the Qt version must replicate.

### 6.1 Event dispatch architecture

```
Tkinter Canvas Event
  |
  v
paper_events.py handler (_pressed1, _drag1, _release1, _move)
  |  converts screen coords -> canvas coords via canvasx()/canvasy()
  |  looks up focused object via _id_2_object dict
  v
Store.app.mode.mouse_down/drag/up/click(event, modifiers)
  |  mode decides what to do based on focused object + submode
  v
Object model mutation (molecule.add_atom_to, bond.toggle_type, etc.)
  |
  v
Visual update (atom.draw(), bond.redraw(), paper.register_id())
  |
  v
paper.start_new_undo_record()  (captures state for undo)
```

**Key bindings in `paper_events.py`:**

| Tk binding | Handler | Dispatches to |
| --- | --- | --- |
| `<Button-1>` | `_pressed1()` | `mode.mouse_down(event, modifiers=[])` |
| `<B1-Motion>` | `_drag1()` | `mode.mouse_drag(event)` |
| `<ButtonRelease-1>` | `_release1()` | `mode.mouse_up(event)` |
| `<Button-3>` | `_n_pressed3()` | `mode.mouse_down3(event, modifiers)` |
| `<Motion>` | `_move()` | `mode.mouse_move()` + `enter_object()`/`leave_object()` |
| `<Key>` | `key_pressed()` | `mode.key_pressed(event)` |
| `<Delete>` | `key_pressed()` | `mode._delete_selected()` |
| `<Control-MouseWheel>` | zoom handler | `paper.zoom_in()` / `paper.zoom_out()` |

**Modifier tracking:** Shift, Ctrl, Alt are extracted from event state and passed as `modifiers` list. Modes use these for axis-locking (Ctrl=lock-X, Shift=lock-Y), multi-select (Shift+click), and delete (Ctrl+click).

**Hover/focus system (`_move` handler):**
- Tracks `paper._in` (currently hovered object) and `paper._in_id` (its canvas item ID)
- Calls `mode.enter_object(obj, event)` when mouse enters an object
- Calls `mode.leave_object(event)` when mouse leaves
- Modes use this to set `self.focused` for subsequent click operations

### 6.2 Drawing bonds (draw mode)

**Source:** `modes/draw_mode.py`

This is the most complex interaction. Three phases:

**Phase 1 - mouse_down:** Establish starting atom
```
Click on empty canvas:
  1. paper.new_molecule() -> creates BkMolecule, adds to paper.stack
  2. mol.create_new_atom(x, y) -> creates BkAtom at click position
     - atom.__init__() sets symbol='C', calls draw()
     - draw() creates invisible Tk line if show=False, or renders label via BkFtext
     - paper.register_id(item_id, atom) maps canvas ID to object
  3. atom.focus() -> draws blue highlight rectangle
  4. self.focused = atom

Click on existing atom:
  1. self.focused = that_atom (already registered from hover)
  2. atom.focus() -> highlight
```

**Phase 2 - mouse_drag:** Create bond + endpoint atom, drag to position
```
First drag event (threshold passed):
  1. self._start_atom = self.focused
  2. Create BkBond with current submode settings:
     - type = __mode_to_bond_type() -> 'n'/'w'/'h'/'s'/'o'/'a'/'b'/'d'
     - order = __mode_to_bond_order() -> 1/2/3
     - simple_double from submode[4]
  3. mol.add_atom_to(start_atom, bond_to_use=bond):
     - Finds position using geometry.point_on_circle()
     - Creates new BkAtom at calculated position
     - Calls mol.add_edge(a1, a2, bond) -> updates OASA graph
     - bond.draw() renders the bond on canvas
     - Returns (new_atom, bond)
  4. Block focus on new objects: paper._do_not_focus = [new_atom, bond]

Subsequent drag events:
  Fixed-length mode (default):
    - Calculate position on circle around start_atom
    - Resolution from submode (30deg, 15deg, free, etc.)
    - new_atom.move_to(x, y) updates position
    - bond.redraw() redraws connecting line

  Free-hand mode (submode[3]==1):
    - new_atom follows mouse cursor directly
    - Optional hex grid snap: oasa.hex_grid.snap_to_hex_grid()

  Snapping to existing atom:
    - If mouse hovers over another atom, new_atom snaps to its position
    - This sets up overlap detection on mouse_up
```

**Phase 3 - mouse_up:** Finalize, merge overlaps, undo checkpoint
```
  1. paper.handle_overlap() -> merges atoms at same position
     - Finds atoms within 2px of each other
     - Merges molecules if atoms from different molecules overlap
     - Returns (deleted_atoms, preserved_atoms)
  2. For each affected atom:
     - update_after_valency_change() -> recalculate H count
     - Check free_valency < 0 -> warn "valency exceeded"
     - reposition_bonds_around_atom() -> fix double bond placement
  3. paper.start_new_undo_record() -> captures state
  4. paper.add_bindings() -> re-enable hover events
```

### 6.3 Adding atom labels (atom mode)

**Source:** `modes/atom_mode.py` (via `editPool` text entry)

**Click on empty canvas:**
```
  1. Store.app.editPool.activate() -> shows text entry bar, returns typed text
  2. mol = paper.new_molecule()
  3. mol.create_vertex_according_to_text(None, name, interpret=True):
     - Parses text: "C", "N+", "CH3", "COOH", etc.
     - Creates appropriate atom subclass
     - Sets symbol, charge, hydrogens from parsed text
  4. atom.x = event.x, atom.y = event.y
  5. mol.insert_atom(atom)
  6. atom.draw() -> renders label via BkFtext rich text
  7. paper.start_new_undo_record()
```

**Click on existing atom (relabel):**
```
  1. editPool.activate(text=atom.symbol) -> prefills current symbol
  2. mol.create_vertex_according_to_text(old_atom, name) -> new atom
  3. old_atom.copy_settings(new_atom) -> transfers style (color, font, marks)
  4. mol.replace_vertices(old_atom, new_atom) -> graph topology update
  5. old_atom.delete() -> remove from canvas
  6. new_atom.draw() -> render new label
  7. Reposition adjacent bonds
  8. paper.start_new_undo_record()
```

### 6.4 Moving atoms and bonds (edit mode)

**Source:** `modes/edit_mode.py`

**Four drag types determined on first drag event:**

| Drag type | Condition | Behavior |
| --- | --- | --- |
| Type 1 | Focused object is in `paper.selected` | Move ALL selected objects together |
| Type 2 | Focused object is NOT selected | Move its container (whole molecule) |
| Type 3 | No focused object, rectangle_selection enabled | Draw marquee selection box |
| Type 4 | Focused object is `selection_rect` | Resize vector graphics |

**Type 1 (move selected) detail:**
```
mouse_down:
  - Record start position
  - self._shift, self._ctrl for axis locking

first drag event:
  - Gather bonds_to_update() (adjacent bonds not in selection)
  - Gather arrows_to_update() (arrows containing selected points)
  - Find snap anchor atom for hex grid

each drag event:
  - dx = event.x - startx (0 if Ctrl held = lock X axis)
  - dy = event.y - starty (0 if Shift held = lock Y axis)
  - If hex grid snap: compute snapped delta from anchor atom
  - [o.move(dx, dy) for o in paper.selected]
  - [o.redraw() for o in bonds_to_update]
  - [o.redraw() for o in arrows_to_update]
  - Update start position for next iteration

mouse_up:
  - Recalculate double bond positions (decide_pos)
  - Reposition marks on affected atoms
  - paper.handle_overlap() (merge if atoms overlap)
  - paper.start_new_undo_record()
```

**Type 3 (marquee selection) detail:**
```
first drag event:
  - If not Shift: paper.unselect_all()
  - Create Tk rectangle: paper.create_rectangle(x1, y1, x2, y2)

each drag event:
  - Update rectangle coords: paper.coords(rect, x1, y1, event.x, event.y)

mouse_up:
  - _end_of_empty_drag(x1, y1, x2, y2):
    - Find all canvas items in rectangle: paper.find_overlapping()
    - Convert IDs to objects: paper.id_to_object()
    - paper.select(found_objects)
  - Delete selection rectangle
```

### 6.5 Deleting atoms and bonds

**Triggers:** Delete key, BackSpace key, or Ctrl+click in edit mode

**Source:** `paper_selection.py` `delete_selected()`

```
1. Separate selected into: bonds, atoms, arrows, texts, shapes
2. For each molecule containing selected items:
   - mol.delete_items(items):
     a. Remove atoms from mol.vertices
     b. Disconnect bonds from graph via disconnect_edge()
     c. Remove orphaned atoms (degree 0 after bond deletion)
     d. If molecule fragments: create new molecule objects for each component
     e. Return (deleted_objects, new_molecules)
3. Replace fragmented molecules in paper.stack
4. Remove empty molecules from paper.stack
5. Delete canvas items: [o.delete() for o in deleted]
   - atom.delete(): unregister_id, paper.delete(item)
   - bond.delete(): unregister all items (item, second, third, items list)
6. Clear paper.selected
7. Check arrow references (clean up reaction pointers)
8. paper.start_new_undo_record()
```

### 6.6 Changing bond types

**Source:** `bond_type_control.py` `toggle_type()`, triggered by click on bond in draw mode

**Click on bond in draw mode:**
```
bond.toggle_type(to_type=current_submode_type, to_order=current_submode_order):

  Case 1: type differs from current -> switch type
    - bond.switch_to_type(type):
      - If entering wedge/hash/any: set wedge_width from standard
      - If leaving wedge/hash/any: set bond_width from standard
      - bond.type = new_type

  Case 2: same type, order=1 -> cycle order: 1 -> 2 -> 3 -> 1
    - Only if both atoms have free valency
    - bond.switch_to_order(new_order):
      - If order 3: force center=False
      - If order > 1: _decide_distance_and_center()

  Case 3: same type and order -> toggle properties:
    - Wedge: flip atom1/atom2 (reverses wedge direction)
    - Hash: toggle equithick, then flip atoms
    - Double: cycle center -> offset-left -> offset-right -> center

  bond.redraw()  (full visual update)
  Redraw adjacent atoms (H counts may change)
  Check free_valency warnings
```

**Bond type visual rendering** (`bond_render_ops.py`):

| Type char | Visual | Canvas items |
| --- | --- | --- |
| `n` | Normal line | `create_line()` |
| `w` | Solid wedge (3D out of plane) | `create_polygon()` filled triangle |
| `h` | Hashed wedge (3D into plane) | Multiple short `create_line()` dashes perpendicular to bond |
| `d` | Dashed line | `create_line()` with dash pattern |
| `o` | Dotted line | Multiple `create_oval()` dots along bond |
| `s` | Wavy/squiggly | `create_polygon()` snake shape |
| `a` | Any stereo (wavy) | Similar to `s` |
| `b` | Bold line | `create_polygon()` thick filled rectangle |
| `q` | Wide rectangle (Haworth) | `create_polygon()` thick rectangle |

**Double bond placement algorithm:**
```
_compute_sign_and_center():
  1. Count neighbors on each side of bond axis
  2. If in ring: place second line toward ring center
  3. If not in ring: place toward side with more neighbors
  4. Set bond_width sign (positive/negative) for side selection
  5. If center=True: draw second lines on both sides (equal offset)
  6. double_length_ratio controls second line length (default 0.75)
```

### 6.7 Rotating about a bond (rotate mode)

**Source:** `modes/rotate_mode.py`

**Three rotation submodes:**

| Submode | Behavior |
| --- | --- |
| 2D free rotation | Rotate entire molecule around its bbox center |
| 3D free rotation | Apply 3D rotation (X/Y axes from mouse dx/dy) |
| 3D fixed-bond rotation | Select a bond first, then rotate atoms on one side around that bond axis |

**2D rotation (drag):**
```
mouse_down:
  - Calculate molecule center from bbox
  - self._rotated_mol = focused.molecule

mouse_drag:
  - sig = which_side_of_point(center, start, event) -> rotation direction
  - angle = sig * (abs(dx) + abs(dy)) / 50.0
  - tr = Transform()
  - tr.set_move(-centerx, -centery)    # translate to origin
  - tr.set_rotation(angle)              # rotate
  - tr.set_move(centerx, centery)       # translate back
  - molecule.transform(tr)              # apply to all atoms
    -> Each atom: x,y = tr.transform_xy(x, y); move_to(x, y)
    -> Each bond: simple_redraw() (fast line-only update)
```

**3D fixed-bond rotation (drag):**
```
mouse_down:
  - self._fixed = selected bond (must be pre-selected)
  - self._rotated_atoms = atoms on ONE side of the bond

mouse_drag:
  - angle = sig * sqrt(dx^2 + dy^2) / 50.0
  - t = geometry.create_transformation_to_rotate_around_particular_axis(
      fixed_bond.atom2.xyz, fixed_bond.atom1.xyz, angle)
  - For each atom on rotation side:
    - x, y, z = t.transform_xyz(atom.x, atom.y, atom.z)
    - atom.move_to(x, y); atom.z = z
  - All bonds: simple_redraw()

mouse_up:
  - Full bond redraw with recalc_side=1
  - Reposition marks on all atoms
  - paper.start_new_undo_record()
```

### 6.8 Transformations (scale, flip, mirror)

**Source:** `paper_layout.py` (menu-triggered, not direct mouse interaction)

**Scale selected:**
```
paper.scale_selected(ratio_x, ratio_y, scale_font=1, fix_centers=0):
  For each top-level object:
    - paper.scale_object(obj, transform, ratio, scale_font):
      - Molecule: transform all atom coords; optionally scale font_size and bond_width
      - Arrow: transform all point coords
      - Text: transform position; optionally scale font_size
      - Rect/Oval: transform coords
```

**Mirror/flip (`swap_sides_of_selected`):**
```
swap_sides_of_selected(mode="vertical"):
  1. Get bbox of selected objects
  2. Create Transform with reflection:
     - vertical: negate X coords around bbox center
     - horizontal: negate Y coords around bbox center
  3. Apply transform to all atoms in selected molecules
  4. Redraw all bonds with recalc_side=1
```

**Alignment (`align_selected`):**
```
align_selected(mode):  # mode = 't','b','l','r','h','v'
  1. Get bbox of each selected top-level object
  2. Compute reference coordinate:
     - 't'op: min(all y1)
     - 'b'ottom: max(all y2)
     - 'l'eft: min(all x1)
     - 'r'ight: max(all x2)
     - 'h' center: avg(all center_x)
     - 'v' center: avg(all center_y)
  3. Move each object by offset to align with reference
  4. paper.start_new_undo_record()
```

### 6.9 The render ops pipeline (bond drawing detail)

**Source:** `bond_render_ops.py`, `bond_drawing.py`

The full pipeline from bond state to pixels:

```
bond.draw(automatic="none")
  |
  1. Normalize type ('l'/'r' -> 'h')
  |
  2. Auto-position double bonds if needed:
     _compute_sign_and_center() -> sets bond_width sign
  |
  3. 3D perspective (if any atom has z != 0):
     Apply perspective transform, draw, restore
  |
  4. Resolve endpoints:
     a1_xy = atom1.get_xy_on_paper()
     a2_xy = atom2.get_xy_on_paper()
     a1_bbox = atom1.bbox() (with font descent correction)
     a2_bbox = atom2.bbox()
     Clip bond endpoints to atom label boundaries
  |
  5. Build OASA render_ops:
     _build_bond_ops(start, end, type, order, width, ...)
     -> Returns list of render operation dicts
  |
  6. Convert to Tk canvas:
     _render_ops_to_tk_canvas(ops)
     -> For each op: paper.create_line/polygon/oval(...)
     -> Returns list of canvas item IDs
  |
  7. Store items:
     self.item = primary_id
     self.second = [secondary_ids]  (double bond lines)
     self.third = [tertiary_ids]    (triple bond lines)
     self.items = [decoration_ids]  (dashes, dots)
     self._render_item_ids = all_ids
  |
  8. Register all IDs with paper:
     paper.register_id(id, self) for each id
```

### 6.10 Focus and selection visual feedback

**Atom focus (hover):**
```
atom.focus():
  self.selector = paper.create_rectangle(x-3, y-3, x+3, y+3,
                                          outline=paper.highlight_color)
atom.unfocus():
  paper.delete(self.selector); self.selector = None
```

**Bond focus (hover):**
```
bond.focus():
  For each visible canvas item:
    paper.itemconfig(item, fill=highlight_color, width=line_width+1)
bond.unfocus():
  Restore original fill and width
```

**Selection (persistent):**
```
atom.select():
  Create selection rectangle around atom label
  Blue outline rectangle stays until unselect()

bond.select():
  Create selection rectangle at bond midpoint

paper.select(items):
  For each item: item.select()
  self.selected.append(item)
  event_generate("<<selection-changed>>")
```

### 6.11 Undo system mechanics

**Source:** `undo.py`

```
paper.start_new_undo_record(name=''):
  1. before_undo_record():
     - Run checks.check_linear_fragments()
  2. um.start_new_record(name):
     - Captures state_record of ALL objects on paper
     - state_record iterates paper.stack
     - For each object with meta__undo_properties:
       - Captures: position, type, bonds, valency, colors, etc.
       - Deep copies mutable data via meta__undo_copy
     - Appends record to undo stack
  3. after_undo_record():
     - Update scrollregion if bbox changed

paper.undo():
  1. um.undo():
     - Decrements position in undo stack
     - Restores previous state_record:
       - Deletes objects not in previous state
       - Creates objects present in previous state but not current
       - Updates properties of existing objects
  2. paper.unselect_all()
  3. event_generate("<<undo>>")
```

---

## 7. UI/UX design guidelines for Qt port

### 7.1 Design system (from ui-ux-pro-max analysis)

| Role | Recommendation |
| --- | --- |
| Primary color | `#0D9488` (teal) |
| Secondary | `#14B8A6` (lighter teal) |
| Action/CTA | `#F97316` (orange for active tools) |
| Background | `#F0FDFA` (light) / `#1E293B` (dark) |
| Text | `#134E4A` (light) / `#E2E8F0` (dark) |
| Font heading | Poppins (if web) or system sans-serif |
| Font body | Open Sans or system sans-serif |

### 7.2 Interaction principles for a desktop drawing tool

- **Hover feedback**: All clickable toolbar buttons and canvas objects must show hover state (color/opacity change, 150-300ms transition).
- **Cursor changes**: Different cursors for different modes (crosshair for draw, move arrows for edit, rotation cursor for rotate).
- **Focus states**: Visible focus rings on all interactive elements for keyboard navigation.
- **Confirmation dialogs**: Required before destructive actions (delete molecule, close unsaved document).
- **Success feedback**: Status bar messages after save, export, paste operations.
- **Active states**: Visual press/active feedback on toolbar buttons.
- **Keyboard shortcuts**: Match standard conventions (Ctrl+Z undo, Ctrl+C copy, etc.). Tab order matches visual layout.
- **Color contrast**: Minimum 4.5:1 ratio for all text. Don't use color alone to convey information (e.g., selection needs both color and visual indicator).
- **Error messages**: Show near the problem area, use both text and icon, announce via accessibility.
- **Reduced motion**: Respect `prefers-reduced-motion` for animation.

### 7.3 Canvas-specific UX

- **Zoom**: Cursor-centered zoom (already in Qt `ChemView`).
- **Pan**: Middle-click drag and Alt+left-click (already in Qt).
- **Grid snap**: Visual grid dots + togglable snap-to-grid.
- **Status bar**: Show cursor position, zoom level, current mode, selection info.

---

## 8. Recommended porting order

### Phase 1: Selection and interaction foundation
1. Port `PaperSelectionMixin` logic to Qt scene/view
2. Implement `delete_selected()` with all special cases
3. Wire selection-changed signals to menu state updates

### Phase 2: Edit mode (select/move/resize)
4. Implement marquee selection in edit mode
5. Implement click-to-select, shift-click multi-select
6. Implement drag-to-move selected objects
7. Port `bonds_to_update()` / `atoms_to_update()` for efficient redraws

### Phase 3: Clipboard and undo
8. Port internal CDML clipboard
9. Implement cut/copy/paste with ID sandboxing
10. Wire undo/redo commands for all operations

### Phase 4: Draw mode completion
11. Port atom/bond drawing interaction from Tk draw mode
12. Smart angle snapping, transoid placement
13. Template mode with attachment points

### Phase 5: Layout operations
14. Port alignment (6-axis)
15. Port overlap detection and molecule merging
16. Port coordinate regeneration
17. Port mirror/swap operations

### Phase 6: File I/O and tabs
18. Port tab management (add/close/switch)
19. Port file save/load dialogs
20. Port format plugin system
21. Port chemistry I/O (SMILES/InChI)

### Phase 7: Properties and preferences
22. Port paper properties dialog
23. Port standard management
24. Port preferences persistence
25. Port recent files

---

## 9. Key files to reference during port

### Tkinter source (preserve logic from these)

- `packages/bkchem-app/bkchem/paper_lib/paper_selection.py` - Selection algorithms
- `packages/bkchem-app/bkchem/paper_lib/paper_layout.py` - Geometry/alignment
- `packages/bkchem-app/bkchem/paper_lib/paper_cdml.py` - CDML serialization
- `packages/bkchem-app/bkchem/paper_lib/paper_events.py` - Event dispatch pattern
- `packages/bkchem-app/bkchem/paper_lib/paper_zoom.py` - Zoom/viewport logic
- `packages/bkchem-app/bkchem/paper_lib/paper_transforms.py` - Coordinate transforms
- `packages/bkchem-app/bkchem/paper_lib/paper_factories.py` - Object creation
- `packages/bkchem-app/bkchem/paper_lib/paper_properties.py` - Paper/standard mgmt
- `packages/bkchem-app/bkchem/main_lib/main_file_io.py` - File I/O logic
- `packages/bkchem-app/bkchem/main_lib/main_tabs.py` - Tab lifecycle
- `packages/bkchem-app/bkchem/main_lib/main_modes.py` - Mode/submode switching
- `packages/bkchem-app/bkchem/main_lib/main_chemistry_io.py` - Chemistry dialogs

### Qt destination (modify these)

- `packages/bkchem-qt.app/bkchem_qt/main_window.py` - Main window
- `packages/bkchem-qt.app/bkchem_qt/canvas/scene.py` - Scene (paper equivalent)
- `packages/bkchem-qt.app/bkchem_qt/canvas/view.py` - View (events/zoom)
- `packages/bkchem-qt.app/bkchem_qt/models/document.py` - Document model
- `packages/bkchem-qt.app/bkchem_qt/modes/*.py` - Mode implementations

---

## 10. Verification

- Run existing Qt tests: `source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/ -v`
- Run Tk tests for reference: `source source_me.sh && python -m pytest packages/bkchem-app/tests/ -v`
- Manual testing: Open Qt app, verify each ported feature matches Tk behavior
- Pyflakes lint: `source source_me.sh && python -m pytest tests/test_pyflakes_code_lint.py`
