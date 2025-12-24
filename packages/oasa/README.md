OASA is a free python library for manipulating and analyzing chemical
structures and is distributed under GNU GPL. The program is provided as is
without warranty of any kind. For details see the file "LICENSE" in main oasa
directory.
More info can be found on the [OASA project page](https://bkchem.zirael.org/oasa_en.html).
BKChem, the primary consumer of this library, is documented on the
[BKChem homepage](https://bkchem.zirael.org/).
Usage notes are in [docs/USAGE.md](docs/USAGE.md).
Current version: 0.16beta.

INSTALL
--------------------------------------------------
OASA needs Python 3.10 or higher to run properly. Tested with Python 3.12.
To use it, you can either copy the oasa directory inside your projects directory
or you may use

pip3 install .

to make a system-wide install

To use OASA from a python program use "import oasa"


TESTING
--------------------------------------------------
Run static checks from the repo root:
- tests/run_pyflakes.sh
- tests/run_mypy.sh


STATUS
--------------------------------------------------
Bellow are summarized the limitations of the library. It does by no means mean that there
are no other limitations, however, for these it has no sense to write bugreports :)


OVERALL:
- no documentation beyond the source code is available
- stereochemistry support is limited to cis/trans stereochemistry on double bonds
  and only in some formats
- not much effort was invested into optimalization of the code, it may be pretty slow sometimes
- the API might be unstable


SMILES:
- cis/trans stereochemistry is supported, some attempt were made to make tetrahedral stereochemistry
  work, but it is not very much tested


InChI:
- reading is done natively by OASA
- for writing the original InChI program is needed (cInChI, cInChI.exe)


MOLFILE
- not all data in the properties block (after the bond block) are supported
  (this means that molfiles containing a properties block might not be read properly)


COORDS GENERATOR:
- coords for molecules like calix[4]arene and similar do not give a very nice picture
- tetrahedral stereochemistry is not taken into account


CAIRO_OUT:
- pycairo is required to make use of cairo_out functionality
- PNG, PDF and SVG export is supported now
