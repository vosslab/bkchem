import os
import time
import tkinter.filedialog

import logger
import dialogs

from singleton_store import Store


def process_directory(app, fragment, directory):
\tfiles = 0
\tmatching = 0

\tdialog = dialogs.progress_dialog(app, title=_("Search progress"))

\tfiles_to_go = []
\tfor filename in os.listdir(directory):
\t\tpath = os.path.join(directory, filename)
\t\tif os.path.isfile(path) and os.path.splitext(path)[1] in (".svg", ".cdml"):
\t\t\tfiles_to_go.append(path)

\tfor f in files_to_go:
\t\t#print f
\t\tdialog.update(
\t\t\tfiles / len(files_to_go),
\t\t\ttop_text=os.path.split(f)[1],
\t\t\tbottom_text=_("Found: %d matching") % matching,
\t\t)
\t\tfiles += 1
\t\tapp.in_batch_mode = True
\t\tif app.add_new_paper(name=f):
\t\t\tif app._load_CDML_file(f, draw=False):
\t\t\t\tfound = False
\t\t\t\tfor mol in app.paper.molecules:
\t\t\t\t\tgen = mol.select_matching_substructures(
\t\t\t\t\t\tfragment,
\t\t\t\t\t\timplicit_freesites=True,
\t\t\t\t\t)
\t\t\t\t\ttry:
\t\t\t\t\t\tnext(gen)
\t\t\t\t\texcept StopIteration:
\t\t\t\t\t\tpass
\t\t\t\t\telse:
\t\t\t\t\t\tfound = True
\t\t\t\t\t\tmatching += 1
\t\t\t\t\t\tmol.clean_after_search(fragment)
\t\t\t\t\t\tbreak
\t\t\t\tif not found:
\t\t\t\t\tapp.close_current_paper()
\t\t\t\telse:
\t\t\t\t\tapp.in_batch_mode = False
\t\t\t\t\t[o.draw() for o in app.paper.stack]
\t\t\t\t\tapp.paper.set_bindings()
\t\t\t\t\tapp.paper.add_bindings()
\t\t\telse:
\t\t\t\tapp.close_current_paper()

\tapp.in_batch_mode = False
\tdialog.close()
\treturn files


def main(app):
\tt = time.time()
\tselected_mols = [
\t\to for o in app.paper.selected_to_unique_top_levels()[0]
\t\tif o.object_type == 'molecule'
\t]
\tif not selected_mols and len(app.paper.molecules) == 1:
\t\tselected_mols = app.paper.molecules

\tif len(selected_mols) > 1:
\t\tStore.log(_("Select only one molecule"), message_type="error")
\telif len(selected_mols) == 0:
\t\tStore.log(
\t\t\t_("Draw a molecule that you want to use as the fragment for search"),
\t\t\tmessage_type="error",
\t\t)
\telse:
\t\t# we may proceed
\t\tfragment = selected_mols[0]

\t\tdirectory = tkinter.filedialog.askdirectory(
\t\t\tparent=app,
\t\t\tinitialdir=app.save_dir or "./",
\t\t)

\t\tif directory:
\t\t\tStore.logger.handling = logger.ignorant
\t\t\tfiles = process_directory(app, fragment, directory)

\t\t\tt = time.time() - t
\t\t\t#print "%d files, %.2fs, %.2fms per file" % (files, t, 1000*(t/files))

\t\t\tStore.logger.handling = logger.normal
\t\t\tif files:
\t\t\t\tStore.log(
\t\t\t\t\t_("Searched %d files, %.2fs, %.2fms per file") %
\t\t\t\t\t(files, t, 1000 * (t / files)),
\t\t\t\t)
\t\t\telse:
\t\t\t\tStore.log(_("No files to search in were found"))
