# TKINTER WINDOW DEBUGGING

Lessons learned from debugging Tk Canvas zoom viewport drift in BKChem.

## The Bug

After zoom_out x3 + zoom_in x3, content bbox center shifted from
(1280, 960) to (815, 612) even though the scale correctly returned
to 4.0.  The zoom_to_content function became non-idempotent, producing
scale 1.0597 on the second call instead of the expected 4.0.

## Root Causes Found

### 1. Orphaned Canvas Items (atom.py -- primary cause)

For non-showing atoms (e.g. carbon in organic structures), the draw()
method called get_xy_on_paper() which creates a vertex_item, then
immediately created a separate self.item and set self.vertex_item =
self.item.  The vertex_item created by get_xy_on_paper() was orphaned
-- no reference kept, never deleted.

These orphaned items accumulated (6 per redraw for benzene), retained
stale canvas.scale() coordinates, and inflated the content bounding
box.

Fix: compute coordinates directly via real_to_canvas() instead of
calling get_xy_on_paper() in the non-showing atom path.

### 2. Stale vertex_item Coordinates (molecule.py -- secondary cause)

In molecule.redraw(), bonds are redrawn before atoms (for z-ordering).
Bonds call atom.get_xy_on_paper() which reads from vertex_item.  After
canvas.scale(ALL, ox, oy, factor, factor), vertex_items hold
canvas-scaled coordinates (offset by the zoom origin), not the correct
model_coord * scale values.  Atoms reset vertex_items later during
their own redraw, but by then bonds have already been drawn at wrong
positions.

Fix: reposition all vertex_items to model_coord * scale at the top of
molecule.redraw(), before bonds draw.

### 3. Viewport Centering After Scrollregion Update (paper.py -- minor)

update_scrollregion() changes the canvas-to-widget coordinate mapping.
After each zoom step, canvasx(winfo_width/2) returns a different canvas
coordinate, so the next zoom operates around a slightly different
origin.

Fix: add _center_viewport_on_canvas() helper and call it after
update_scrollregion() when center_on_viewport=True.

## Debugging Techniques That Worked

### Track Canvas Item Counts

Add n_items = len(paper.find_all()) to each diagnostic snapshot.
A growing count reveals leaked canvas items immediately.

### Diff Item Sets Before/After

    items_before = set(self.find_all())
    # ... operation ...
    items_after = set(self.find_all())
    new_items = items_after - items_before

For each leaked item, log its type, tags, and coords to identify what
created it and whether it belongs to atoms, bonds, or other objects.

### Per-Step Snapshots

Instead of only capturing state at the start and end of a zoom
sequence, capture after every individual zoom step.  This reveals
whether drift accumulates linearly (suggesting a per-step leak) or
compounds exponentially.

### Write Debug Output to a File

When tests run in subprocesses (common for Tk tests to avoid display
issues), print statements go to the subprocess stdout/stderr which may
be captured.  Write debug output to /tmp/debug.txt instead.

## Key Tk Canvas Concepts

### canvas.scale(ALL, ox, oy, fx, fy)

Transforms all canvas item coordinates around point (ox, oy).  Items
at (ox, oy) stay fixed.  Does NOT modify Python object attributes --
only Tk-level item coordinates.

### vertex_item Pattern

BKChem uses invisible canvas items (zero-length lines) as position
caches for atoms.  get_xy_on_paper() reads from these items.  When
canvas.scale() moves them, any code reading from them gets stale
positions until the owning object redraws.

### scrollregion and canvasx/canvasy

The scrollregion defines the total scrollable area.  canvasx(pixel)
maps widget pixel coordinates to canvas coordinates based on the
current scroll position and scrollregion.  Changing the scrollregion
changes this mapping, which can cause viewport drift if the scroll
position is not adjusted.

### redraw() Ordering Matters

When object A reads position from object B during redraw, B must have
correct positions before A draws.  In BKChem, bonds read atom positions
via vertex_items.  If atoms have not yet reset their vertex_items, bonds
get stale coordinates.

## Test Structure for Zoom

The test (tests/test_bkchem_gui_zoom.py) runs in a subprocess to
isolate Tk.  It draws benzene, performs zoom operations, and captures
snapshots of scale, bbox center, viewport center, and item count at
each step.  Key assertions:

- Scale round-trip: zoom_out x3 + zoom_in x3 restores original scale
- BBox stability: content bbox center unchanged after round-trip
  (50 px tolerance)
- Viewport stability: viewport center near original after round-trip
  (50 px tolerance)
- Idempotency: zoom_to_content produces same scale when called twice
  (5% tolerance)
- Scale clamping: zoom_out x50 clamps at ZOOM_MIN, zoom_in x50 at
  ZOOM_MAX
