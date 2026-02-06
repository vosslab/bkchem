#!/usr/bin/env python3

"""Check translation files for formatting consistency."""

# Standard Library
import os
import subprocess


#============================================
def get_repo_root():
	"""Get repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
	)
	if result.returncode == 0:
		return result.stdout.strip()
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


repo_root = get_repo_root()
locale_dir = os.path.join(repo_root, "packages", "bkchem", "bkchem_data", "locale")

for lang in os.listdir( locale_dir):
    print("-- language:", lang)
    filename = os.path.join( locale_dir, lang, 'BKChem.po')
    try:
        f = open(filename, 'r')
    except IOError:
        print("Could not open the file %s" % filename)
        continue
    msgid = ""
    msgstr = ""
    i = 0
    with f:
        for line in f:
            if line.startswith( "msgid"):
                msgid = line
            elif line.startswith( "msgstr"):
                msgstr = line
                if msgstr != 'msgstr ""\n' and msgid.count("%") != msgstr.count("%"):
                    # if msgstr == 'msgstr ""\n', it is not translated
                    print("!! line %d: %s vs. %s" % (i, msgid, msgstr))
            i += 1

