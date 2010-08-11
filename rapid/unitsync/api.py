#!/usr/bin/env python
# Copyright (C) 2010 Tobi Vollebregt

# This file contains the interface between rapid and unitsync,
# and the mechanism by which rapid can locate unitsync.

import os
import sys
from unitsync import Unitsync

class UnitsyncError(Exception):
	pass

def generate_linux_paths():
	"""Yield candidate unitsync locations for Linux (based?) systems."""
	yield '/usr/lib/libunitsync.so'
	yield '/usr/local/lib/libunitsync.so'
	yield '/opt/spring/lib/libunitsync.so'

def generate_windows_paths():
	"""Yield candidate unitsync locations for Windows systems."""
	yield r'c:\Program Files\Spring\unitsync.dll'
	#FIXME: add more common locations?

def generate_paths():
	"""Yield candidate unitsync locations for the current operating system."""
	if os.name == 'posix':
		return generate_linux_paths()
	elif os.name == 'nt':
		return generate_windows_paths()

def locate_unitsync():
	"""Locate and instantiate unitsync, otherwise raise UnitsyncError.
	The unitsync library must export at least Init, UnInit and GetWritableDataDirectory."""
	for path in generate_paths():
		try:
			unitsync = Unitsync(path)
		except OSError:
			continue
		if (unitsync.has('Init') and
			unitsync.has('UnInit') and
			unitsync.has('GetWritableDataDirectory')):
			return unitsync
	raise UnitsyncError('suitable unitsync library not found')

def get_writable_data_directory():
	"""Acquire Springs `writable data directory' from unitsync, or raise UnitsyncError."""
	if unitsync.Init(False, 0) == 1:
		data_directory = unitsync.GetWritableDataDirectory()
		unitsync.UnInit()
	else:
		raise UnitsyncError('unitsync.Init(...) failed')
	return data_directory


if __name__ == '__main__':
	# Quick test.
	unitsync = locate_unitsync()
	# This is not available in older versions of unitsync.
	print 'Has GetMapDescription?', unitsync.has('GetMapDescription')
	# Test main interface.
	data_directory = get_writable_data_directory()
	print '===>', data_directory, '<==='
