import os.path


def main(app):
\tcrop_svg = app.paper.get_paper_property('crop_svg')
\tapp.paper.set_paper_properties(crop_svg=0)

\tname = app.paper.file_name['name']
\tname, ext = os.path.splitext(name)

\tn = app.paper.um.get_number_of_records()

\tfor _i in range(n):
\t\tapp.paper.undo()

\tfor i in range(n):
\t\tapp.save_CDML(name="%s-%02d%s" % (name, i, ext))
\t\tapp.paper.redo()

\tapp.paper.set_paper_properties(crop_svg=crop_svg)
