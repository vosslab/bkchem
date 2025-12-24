from group import group
from textatom import textatom
from singleton_store import Store


def main(app):
\t# if nothing is selected the use all
\tselected = app.paper.selected or (
\t\tj for i in [m.vertices for m in app.paper.molecules] for j in i
\t)
\ttextatoms = [a for a in selected if isinstance(a, textatom)]

\ti = 0
\tfor atom in textatoms:
\t\tval = atom.occupied_valency
\t\tgr = atom.molecule.create_vertex(vertex_class=group)
\t\ttext = atom.symbol
\t\tprint(text)
\t\tif gr.set_name(text, occupied_valency=val):
\t\t\ti += 1
\t\t\tatom.copy_settings(gr)
\t\t\tatom.molecule.replace_vertices(atom, gr)
\t\t\tatom.delete()
\t\t\tgr.draw()

\tStore.log(_("%d textatoms were converted to groups") % i)

\tapp.paper.start_new_undo_record()
\tapp.paper.add_bindings()
