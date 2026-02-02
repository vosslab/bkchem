# Usage

## Install
- Install locally from the repo root:
  - `pip3 install .`

## Conversion script
- Preferred script: `chemical_convert.py`

Examples:
- `python3 chemical_convert.py -c sm -i input.smi -o output.mol`
- `python3 chemical_convert.py -c is -i input.inchi -o output.smi`
- `python3 chemical_convert.py -c ms -i input.mol -o output.smi`

## Haworth CLI
- Render Haworth projections from SMILES using
  [oasa_cli.py](../../oasa_cli.py).

Examples:
- `python3 oasa_cli.py haworth -s "C1CCOCC1" -o haworth.svg`
- `python3 oasa_cli.py haworth -s "C1CCOCC1" -o haworth.png`

## Smoke rendering test
- Requires `pycairo` in the active environment.
- Renders alpha-d-glucopyranose by default:
- `python3 tests/oasa_smoke_png.py -o output/glucose.png`

## Static checks
- Pyflakes: `tests/run_pyflakes.sh`
- Mypy: `tests/run_oasa_mypy.sh`

## Virtual install test
- Creates a temporary venv and installs the repo:
  - `tests/run_virtual_test.sh`
