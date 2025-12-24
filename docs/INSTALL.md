# Installation

Note: This file describes the installation of the source release of BKChem. If you
have downloaded the binary release, please read `INSTALL.binary` instead.

## Before you start

Installation of BKChem is simple, but you must install the following first:

- Python. Get a distribution from [python.org](https://www.python.org/).
  Note that BKChem runs only on Python 2.6 or newer.
- pycairo (optional). This library is available only for Linux. It enables high
  quality export to PDF and PNG formats with support for antialiased unicode
  texts. It requires the cairo library. Both can be found at
  [cairographics snapshots](http://cairographics.org/snapshots/). The current
  tested version is 0.5.1.

## Single directory deployment

No installation is needed to run BKChem. You can run the program directly after
unpacking the downloaded sources.

Run `bkchem.py` located in the `bkchem-X.Y.Z/bkchem` directory, where `X.Y.Z` are
version numbers of the BKChem release.

Example on Unix:

```sh
cd "the dir where you have downloaded the BKChem package"
tar -xzf bkchem-X.X.X.tgz -C "the dir where you want to unpack BKChem"
cd "the dir where you have unpacked BKChem"/bkchem-X.Y.Z/bkchem
python bkchem.py
```

## System-wide install

On Linux and other Unix systems you can use a classic system install. The main
advantage is a `bkchem` program in your path, so you can run it from anywhere.

BKChem uses `distutils` for installation. Run `setup.py` from the `bkchem`
directory with the `install` argument:

```sh
python setup.py install
```

Note: You usually must be root to perform the install.

This installs:

- Python sources into a standard directory for third-party modules, usually
  something like `/usr/lib/python/site-packages`.
- Templates, pixmaps, and other assets into `prefix/share/bkchem`, where `prefix`
  is usually `usr` or `usr/local`.
- Documentation into `prefix/share/doc/bkchem`.
- A shell script at `prefix/bin/bkchem` so you can run BKChem from anywhere.

To influence the paths used during install (especially `prefix`), run:

```sh
python setup.py install --help
```

To see other install options, run:

```sh
python setup.py --help
```

## Feedback

Comments or reports on the installation process are especially welcome. This is
hard to test thoroughly on a single machine.
