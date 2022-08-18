#!/bin/sh

cd "$(mktemp -d)"
python3 -m venv venv
source venv/bin/activate

echo "RSYNC"
rsync -rt ~/nsh/bkchem/* .

echo "BUILD"
python3 ./setup.py build

echo "INSTALL"
python3 ./setup.py install

echo "IMPORT"
python3 -c 'import bkchem'

echo "RUN MAIN"
cd bkchem
python3 main.py

echo "DONE"
deactivate
