# Troubleshooting

## GUI launch issues
- If BKChem fails to start with a Tk error, install a Python build with Tk
  support and retry. See [docs/INSTALL.md](docs/INSTALL.md).

## Missing Cairo output
- PNG or PDF export requires pycairo. Install it if cairo-based output fails.
  See [packages/oasa/README.md](packages/oasa/README.md).

## Batch mode scripts
- Batch and GUI smoke scripts require Tk even when running headless. See
  [tests/bkchem_batch_examples.py](tests/bkchem_batch_examples.py).

## Known gaps
- Add platform-specific troubleshooting steps once installer testing is done.
