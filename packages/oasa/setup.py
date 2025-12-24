#!/usr/bin/env python3

# Standard Library
from pathlib import Path

# PIP3 modules
from setuptools import setup

ROOT_DIR = Path(__file__).parent
README_PATH = ROOT_DIR / "README.md"
LONG_DESCRIPTION = README_PATH.read_text(encoding="utf-8")


setup(
	name='oasa',
	version='0.16beta',
	description="OASA is a free cheminformatics library written in Python",
	long_description=LONG_DESCRIPTION,
	long_description_content_type="text/markdown",
	author="Beda Kosata",
	author_email="beda@zirael.org",
	maintainer="Reinis Danne",
	maintainer_email="rei4dan@gmail.com",
	url="http://bkchem.zirael.org/oasa_en.html",
	project_urls={
		"Homepage": "https://bkchem.zirael.org/oasa_en.html",
		"BKChem": "https://bkchem.zirael.org/",
	},
	license="GPL-3.0-or-later",
	platforms=["Unix", "Windows", "other OSes able to run Python"],
	packages=['oasa', 'oasa.graph'],
	package_data={
		'oasa': [
			'*.txt',
			'*.txt.gz',
			'*.db',
		],
	},
	python_requires=">=3.10",
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: Science/Research",
		"License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
		"Operating System :: OS Independent",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.10",
		"Programming Language :: Python :: 3.11",
		"Programming Language :: Python :: 3.12",
		"Topic :: Scientific/Engineering :: Chemistry",
	],
)
