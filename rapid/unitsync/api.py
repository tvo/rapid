#!/usr/bin/env python
# Copyright (C) 2010 Tobi Vollebregt

# This file contains the interface between rapid and unitsync,
# and the mechanism by which rapid can locate unitsync.

import os
import sys
from unitsync import Unitsync

class UnitsyncError(Exception):
	pass

def generate_linux_search_paths():
	"""Yield candidate unitsync paths for Linux (based?) systems."""
	ldpath = os.getenv('LDPATH')
	if ldpath:
		for path in ldpath.split(':'):
			yield path

	ld_library_path = os.getenv('LD_LIBRARY_PATH')
	if ld_library_path:
		for path in ld_library_path.split(':'):
			yield ld_library_path

	for prefix in ['/usr/local', '/usr/local/games', '/usr', '/usr/games']:
		yield os.path.join(prefix, 'lib/spring')
		yield os.path.join(prefix, 'lib64')
		yield os.path.join(prefix, 'lib')

def generate_windows_search_paths():
	"""Yield candidate unitsync paths for Windows systems."""
	program_files = os.getenv('ProgramFiles')
	if program_files:
		yield os.path.join(program_files, 'Spring')
		yield os.path.join(program_files, 'Games', 'Spring')

	yield os.getcwd()

	if sys.argv[0]:
		# check in folder in which rapid.exe lives and its parent
		path = os.path.dirname(os.path.abspath(sys.argv[0]))
		yield path
		yield os.path.normpath(os.path.join(path, '..'))

def generate_paths():
	"""Yield candidate unitsync paths for the current operating system."""
	if os.name == 'posix':
		return generate_linux_search_paths()
	elif os.name == 'nt':
		return generate_windows_search_paths()
	else:
		raise NotImplemented()

def generate_locations():
	"""Yields fully specified unitsync locations."""
	if os.name == 'posix':
		ext = '.so'
	elif os.name == 'nt':
		ext = '.dll'
	else:
		raise NotImplemented()

	for path in generate_paths():
		yield os.path.join(path, 'unitsync') + ext
		yield os.path.join(path, 'libunitsync') + ext

def locate_unitsync():
	"""Locate and instantiate unitsync, otherwise raise UnitsyncError.
	The unitsync library must export at least Init, UnInit and GetWritableDataDirectory."""
	for location in generate_locations():
		if os.path.isfile(location):
			unitsync = Unitsync(location)
			if (unitsync.has('Init') and
				unitsync.has('UnInit') and
				unitsync.has('GetWritableDataDirectory')):
				return unitsync
	raise UnitsyncError('suitable unitsync library not found')

def get_writable_data_directory():
	"""Acquire Springs `writable data directory' from unitsync, or raise UnitsyncError."""
	unitsync = locate_unitsync()
	if unitsync.Init(False, 0) == 1:
		data_directory = unitsync.GetWritableDataDirectory()
		unitsync.UnInit()
	else:
		raise UnitsyncError('unitsync.Init(...) failed')
	return data_directory

def test():
	# Quick test.
	for location in generate_locations():
		print location
	unitsync = locate_unitsync()
	# This is not available in older versions of unitsync.
	print 'Has GetMapDescription?', unitsync.has('GetMapDescription')
	# Test main interface.
	data_directory = get_writable_data_directory()
	print '===>', data_directory, '<==='


if __name__ == '__main__':
	test()
