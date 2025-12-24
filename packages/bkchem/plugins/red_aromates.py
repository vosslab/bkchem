def main(app):
\t# at first we cancel all selections
\tapp.paper.unselect_all()

\t# app.paper is the current paper
\t# app.paper.molecules is a list of all molecules on this paper
\tfor mol in app.paper.molecules:
\t\t# the aromaticity of bonds is not checked by default
\t\t# therefore we must at first call the mark_aromatic_bonds() method
\t\tmol.mark_aromatic_bonds()

\t\t# then we can loop over all the bonds
\t\t# and change the color of all the aromatic ones
\t\tfor b in mol.bonds:
\t\t\tif b.aromatic:
\t\t\t\tb.line_color = "#aa0000"
\t\t\t\tb.redraw()
