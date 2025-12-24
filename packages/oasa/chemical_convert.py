#!/usr/bin/env python3
#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program

#--------------------------------------------------------------------------

# Standard Library
import argparse
import os
import sys
import time

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
if REPO_DIR not in sys.path:
	sys.path.insert(0, REPO_DIR)

# local repo modules
import oasa


RECODING = {
	's': 'smiles',
	'i': 'inchi',
	'm': 'molfile',
	'c': 'cdml',
}

OUTPUT_MODES = {'s', 'i', 'm'}


#============================================
def conversion_type(text):
	"""Validate the conversion code.

	Args:
		text (str): Two-letter conversion code.

	Returns:
		tuple: (input_mode, output_mode)
	"""
	if len(text) != 2:
		message = "Conversion code must be exactly two letters, for example 'sm' or 'is'."
		raise argparse.ArgumentTypeError(message)
	inmode = text[0]
	outmode = text[1]
	if inmode not in RECODING:
		message = "Input mode must be one of s,i,m,c (smiles, inchi, molfile, cdml)."
		raise argparse.ArgumentTypeError(message)
	if outmode not in OUTPUT_MODES:
		message = "Output mode must be one of s,i,m (smiles, inchi, molfile)."
		raise argparse.ArgumentTypeError(message)
	result = (inmode, outmode)
	return result


#============================================
def parse_args():
	"""Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	script_name = os.path.basename(sys.argv[0]) or "chemical_convert.py"
	examples = [
		f"{script_name} -c sm -i input.smi -o output.mol",
		f"{script_name} -c is -i input.inchi -o output.smi",
		f"{script_name} -c ms -i input.mol -o output.smi",
	]
	parser = argparse.ArgumentParser(
		description="Convert between SMILES, InChI, molfile, and CDML.",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="Examples:\n  " + "\n  ".join(examples),
	)
	parser.add_argument(
		'-c', '--conversion',
		dest='conversion',
		required=True,
		type=conversion_type,
		help="Two-letter conversion code, for example 'sm', 'is', or 'ms'.",
	)
	parser.add_argument(
		'--version',
		action='version',
		version=f"%(prog)s {oasa.__version__}",
	)
	parser.add_argument(
		'-i', '--input',
		dest='input_file',
		help="Input file path. Omit for interactive mode.",
	)
	parser.add_argument(
		'-o', '--output',
		dest='output_file',
		help="Output file path. Defaults to stdout.",
	)
	args = parser.parse_args()
	return args


#============================================
def write_exception_message(exc):
	"""Write a short error message for conversion failures."""
	sys.stderr.write(f"Error: {exc}\n")
	sys.stderr.write("If you are sure your input is OK, please send a bugreport to ")
	sys.stderr.write("beda@zirael.org\n")


#============================================
def convert_file(in_recoder, out_recoder, infile, outfile):
	"""Convert a file using the selected recoders."""
	start_time = time.time()
	try:
		mol = in_recoder.file_to_mol(infile)
		out_recoder.mol_to_file(mol, outfile)
	except Exception as exc:
		write_exception_message(exc)
		raise
	elapsed_ms = (time.time() - start_time) * 1000.0
	return elapsed_ms


#============================================
def convert_interactive(in_recoder, out_recoder, outfile, prompt):
	"""Run interactive conversion in a prompt loop."""
	while True:
		try:
			text = input(prompt)
		except EOFError:
			break
		if not text:
			break
		start_time = time.time()
		try:
			mol = in_recoder.text_to_mol(text)
			out_recoder.mol_to_file(mol, outfile)
		except Exception as exc:
			write_exception_message(exc)
		else:
			outfile.write("\n")
		elapsed_ms = (time.time() - start_time) * 1000.0
		sys.stderr.write(f"processing time {elapsed_ms:.2f} ms\n")


#============================================
def main():
	"""Run the conversion utility."""
	args = parse_args()
	inmode, outmode = args.conversion
	in_recoder = oasa.__dict__[RECODING[inmode]]
	out_recoder = oasa.__dict__[RECODING[outmode]]

	if args.input_file:
		with open(args.input_file, 'r', encoding='utf-8') as infile:
			if args.output_file:
				with open(args.output_file, 'w', encoding='utf-8') as outfile:
					elapsed_ms = convert_file(in_recoder, out_recoder, infile, outfile)
			else:
				elapsed_ms = convert_file(in_recoder, out_recoder, infile, sys.stdout)
		sys.stderr.write(f"processing time {elapsed_ms:.2f} ms\n")
		return

	if args.output_file:
		with open(args.output_file, 'w', encoding='utf-8') as outfile:
			convert_interactive(in_recoder, out_recoder, outfile, f"{RECODING[inmode]}: ")
	else:
		convert_interactive(in_recoder, out_recoder, sys.stdout, f"{RECODING[inmode]}: ")


if __name__ == '__main__':
	main()
