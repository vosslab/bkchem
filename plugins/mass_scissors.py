from oasa.periodic_table import formula_dict


def main(app):
\tmols, _unique = app.paper.selected_to_unique_top_levels()

\tcolors = ["#cc0000", "#00ff00", "#0000ff", "#ff00ff", "#00ffff", "#ff5500"]

\tfor mol in mols:
\t\tif mol.object_type == "molecule":
\t\t\tcurrent_selected_bonds = set(mol.bonds) & set(
\t\t\t\tapp.paper.selected_bonds
\t\t\t)
\t\t\tif current_selected_bonds:
\t\t\t\tfor b in current_selected_bonds:
\t\t\t\t\tmol.temporarily_disconnect_edge(b)
\t\t\t\tfragments = list(mol.get_connected_components())
\t\t\t\tmol.reconnect_temporarily_disconnected_edges()
\t\t\t\tfor i, fragment in enumerate(fragments):
\t\t\t\t\tcolor = colors[i % len(colors)]
\t\t\t\t\tfrag_bonds = (
\t\t\t\t\t\tmol.vertex_subgraph_to_edge_subgraph(fragment) - current_selected_bonds
\t\t\t\t\t)
\t\t\t\t\tfor x in fragment | frag_bonds:
\t\t\t\t\t\tx.line_color = color
\t\t\t\t\t\tx.redraw()
\t\t\t\t\tformula = sum(
\t\t\t\t\t\t[atom.get_formula_dict() for atom in fragment],
\t\t\t\t\t\tformula_dict(),
\t\t\t\t\t)
\t\t\t\t\ttext = "%s: %.8f" % (
\t\t\t\t\t\tformula.get_html_repr_as_string(),
\t\t\t\t\t\tformula.get_exact_molecular_mass(),
\t\t\t\t\t)
\t\t\t\t\ttext_obj = app.paper.new_text(0, 0, text)
\t\t\t\t\ttext_obj.line_color = color
\t\t\t\t\ttext_obj.draw()
\t\t\t\t\tapp.paper.place_next_to_bbox(
\t\t\t\t\t\t"b",
\t\t\t\t\t\t"r",
\t\t\t\t\t\t10 + 20 * i,
\t\t\t\t\t\ttext_obj,
\t\t\t\t\t\tmol.bbox(),
\t\t\t\t\t)
