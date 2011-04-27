#!/usr/bin/env python
# Copyright (C) 2010 Tobi Vollebregt

# This file contains the interface between rapid and unitsync,
# and the mechanism by which rapid can locate unitsync.

import os
import sys
from unitsync import Unitsync

class UnitsyncError(Exception):
	pass

def generate_locations():
	"""Yield possible unitsync paths for the current operating system."""
	if os.name == 'posix':
		filenames=["libunitsync.so", "unitsync.so"]
		for filename in filenames:
			ldpath = os.getenv('LDPATH')
			if ldpath:
				for path in ldpath.split(':'):
					yield os.path.join(path, filename)
		for filename in filenames:
			ld_library_path = os.getenv('LD_LIBRARY_PATH')
			if ld_library_path:
				for path in ld_library_path.split(':'):
					yield os.path.join(path, filename)
		for prefix in ['/usr/local', '/usr/local/games', '/usr', '/usr/games']:
			for filename in filenames:
				yield os.path.join(prefix, 'lib/spring', filename)
			for filename in filenames:
				yield os.path.join(prefix, 'lib64', filename)
			for filename in filenames:
				yield os.path.join(prefix, 'lib', filename)
	elif os.name == 'nt': #search for unitsync.dll on win32
		filenames=["unitsync.dll"]
		for filename in filenames:
			yield os.getcwd()
			if sys.argv[0]:
				# check in folder in which rapid.exe lives and its parent
				path = os.path.dirname(os.path.abspath(sys.argv[0]))
				yield os.path.join(path, filename)
				yield os.path.normpath(os.path.join(path, '..'))
		try:
			import _winreg
			key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r'Software\Spring')
			value, type = _winreg.QueryValueEx(key, r'SpringEngineHelper')
			_winreg.CloseKey(key)
			if type == _winreg.REG_SZ:
				yield value
			else:
				print 'key of unknown type'
		except WindowsError as e:
			print "Registry key not found: " + str(e)
		program_files = os.getenv('ProgramFiles')
		if program_files:
			for filename in filenames:
				yield os.path.join(program_files, 'Spring', filename)
			for filename in filenames:
				yield os.path.join(program_files, 'Games', 'Spring', filename)
	else:
		raise NotImplemented()

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
