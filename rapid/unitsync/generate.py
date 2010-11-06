# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
#  more details.
#
# You should have received a copy of the GNU General Public License along
# with this program in the file licence.txt; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-
# 1307 USA
# You can find the licence also on the web at:
# http://www.opensource.org/licenses/gpl-license.php

import sys, os, time, traceback

baseScript = '''
import os, ctypes
from ctypes import c_bool, POINTER, c_ushort, c_char, c_char_p, c_int, c_uint, c_float, Structure, create_string_buffer, cast, pointer

class StartPos(Structure):
	_fields_ = [('x', c_int), ('y', c_int)]
	def __str__(self):
		return '(%i, %i)' % (self.x, self.y)

class MapInfo(Structure):
	def __init__(self):
		self.author = cast(create_string_buffer(200), c_char_p) # BUG: author field shows up as empty, probably something to do with the fact it's after the startpos structs
		self.description = cast(create_string_buffer(255), c_char_p)

	_fields_ = [('description', c_char_p),
			('tidalStrength', c_int),
			('gravity', c_int),
			('maxMetal', c_float),
			('extractorRadius', c_int),
			('minWind', c_int),
			('maxWind', c_int),
			('width', c_int),
			('height', c_int),
			('posCount', c_int),
			('StartPos', StartPos * 16),
			('author', c_char_p)]
'''.lstrip() # takes off the leading \n which is just for aesthetics here :)
classBase = '''
class Unitsync:
	def has(self, name):
		"""Query whether the loaded unitsync exports a particular procedure."""
		return hasattr(self.unitsync, name)

	def _init(self, name, restype):
		"""Load a procedure from unitsync and assign its return type."""
		if self.has(name):
			getattr(self.unitsync, name).restype = restype

	def __init__(self, location):
		"""Load unitsync from location and attempt to load all known procedures.
		Location must end with .so (Linux) or .dll (Windows)"""
		if location.endswith('.so'):
			self.unitsync = ctypes.cdll.LoadLibrary(location)
		elif location.endswith('.dll'):
			locationdir = os.path.dirname(location)
			# load devil first, to avoid dll conflicts
			ctypes.windll.LoadLibrary(locationdir + "/devil.dll" )
			# load other dependencies, in case the spring dir is not in PATH
			ctypes.windll.LoadLibrary(locationdir + "/ILU.dll" )
			ctypes.windll.LoadLibrary(locationdir + "/SDL.dll" )
			self.unitsync = ctypes.windll.LoadLibrary(location)
'''

argv = sys.argv
if len(argv) < 2:
	if os.path.isfile('./unitsync_api.h'):
		argv.append('./unitsync_api.h')
	else:
		print 'must be passed unitsync_api.h to generate bindings'
		print 'if on windows, you can simply drag the file onto this one'
		time.sleep(30)
		sys.exit(1)

name = argv[1]
if not os.path.isfile(name):
	print '%s is not a valid file' % name
	time.sleep(30)
	sys.exit(1)

f = open(name, 'r')
data = f.read()
f.close()

typeMap = {
	'char*':		'c_char_p',
	'char':			'c_char',
	'int':			'c_int',
	'int*':			'c_int', # pointer to an int, not sure if ctypes can just use this as a normal int
	'unsigned int': 'c_uint',
	'float':		'c_float',
	'bool':			'c_bool',
	'void*':		'c_char_p', 
	'void':			'', # makes the generated code return (self.unitsync.etc), which doesn't cast it as anything :)
	'unsigned short*': 'POINTER(c_ushort)'# used by minimap
}

def quickParse(data):
	return data.replace('const', '').strip()

def getType(data):
	if data in typeMap:
		return typeMap[data]
	else: # pass it as a pointer
		return 'pointer'

functions = []

for line in data.split('\n'):
	line = line.strip('\r')
	if line.startswith('EXPORT'):
		returnType, line = line.split('(',1)[1].split(')',1)
		function, args = line.split('(',1)

		args = args.split(')',1)[0]
		if args: args = [quickParse(arg) for arg in args.split(',')]
		else: args = []
		returnType = quickParse(returnType)
		function = quickParse(function)

		returnType = getType(returnType)
		newArgs = []
		for arg in args:
			argType, argName = arg.rsplit(' ',1)
			argType = getType(argType)
			newArgs.append((argType, argName))

		functions.append((function, returnType, newArgs))

		#print 'EXPORT(%s) %s(%s);' % (returnType, function, ', '.join(newArgs))

f = open('unitsync.py', 'w')
f.write(baseScript)
f.write(classBase)

for (name, returnType, args) in functions:
	if returnType:
		text = 'self._init("%s", %s)' % (name, returnType)
		f.write('\n\t\t%s'%text)

f.write('\n')

for (name, returnType, args) in functions:
	defTemp = []
	callTemp = []
	for argType, argName in args:
		defTemp.append(argName)
		if argType == 'pointer':
			callTemp.append('pointer(%s)'%argName)
		else:
			callTemp.append(argName)

	callArgs = ', '.join(callTemp)
	defArgs = ('self, '+', '.join(defTemp)) if defTemp else 'self'
	text = 'def %s(%s): return self.unitsync.%s(%s)' % (name, defArgs, name, callArgs)
	#text = 'def %s(%s): return %s(self.unitsync.%s(%s)).value' % (name, defArgs, returnType, name, callArgs)
	f.write('\n\t%s'%text)
f.close()
