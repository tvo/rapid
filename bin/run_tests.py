#!/usr/bin/env python
# Author: Tobi Vollebregt

'''
Abstracts the way to run all unit tests so there is a consistent interface for
both python versions before 2.7 and python version 2.7 and later.

This script takes a single optional argument that gives the test set to run.
It can be one `functional', `integration' or `unit'. If no argument is given
all test sets are run.
'''

import os, sys

def main():
	which = 'test.' + sys.argv[1] if len(sys.argv) > 1 else 'test'
	args = ['discover', '-s', which, '-p', 'test_*.py', '-t', '.']
	if sys.hexversion < 0x02070000:
		args = ['unit2'] + args
	else:
		args = ['python', '-m', 'unittest'] + args
	os.execvpe(args[0], args, {'PYTHONPATH': 'src'})


if __name__ == '__main__':
	main()
