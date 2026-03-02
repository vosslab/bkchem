#!/bin/sh

source source_me.sh
pytest tests/
pytest packages/oasa/tests/
pytest packages/bkchem-app/tests/
QT_QPA_PLATFORM=cocoa
pytest packages/bkchem-qt.app/tests/ -s
