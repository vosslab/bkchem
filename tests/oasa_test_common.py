#!/usr/bin/env python3

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "oasa"))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

import oasa.common as common


#============================================
def main():
	print("Running test_common checks...")
	result = common.is_uniquely_sorted([1, 2, 3])
	assert result is True

	result = common.is_uniquely_sorted([1, 2, 2, 3])
	assert result is False
	print("test_common passed.")


if __name__ == '__main__':
	main()
