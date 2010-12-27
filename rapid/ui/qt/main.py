# Author: Tobi Vollebregt

from .gui import RapidGUI
from rapid.ui.text.interaction import TextUserInteraction
from optparse import OptionParser
from rapid.main import init
from rapid.unitsync.api import get_writable_data_directory
import os,threading
try:
	from PyQt4 import QtGui
except:
	import sys
	os.system("xmessage 'This application requires PyQt4 to be installed.\n" +
		"Please use your package manager to install PyQt4 and then run rapid-gui again.'")
	sys.exit(1)

def reloadAction(window):
	window.mainWidget.reloadModels.emit()

def main():
	""" PyQt4 GUI entry point."""
	#we could probably share this parser between cli and gui ...
	parser = OptionParser()

	parser.add_option('--datadir',
		action='store', dest='datadir',
		help='Override the default data directory. '
			'(~/.spring on Linux or the one reported by unitsync on Windows)')
	parser.add_option('--unitsync',
		action='store_true', dest='unitsync',
		help='Use unitsync to locate the data directory Spring uses.',
		default = (os.name == 'nt'))
	parser.add_option('--no-unitsync',
		action='store_false', dest='unitsync',
		help='Do not use unitsync.')

	(options, args) = parser.parse_args()

	# TODO: QtUserInteraction should be written and used here.
	# (+ some more refactors to allow a graphical progress bar too.)
	ui = TextUserInteraction()

	if options.datadir:
		init(options.datadir, ui)
	elif options.unitsync:
		init(get_writable_data_directory(), ui)
	elif os.name == 'posix':
		init(os.path.expanduser('~/.spring'), ui)
	else:
		print 'No data directory specified. Specify one using either --datadir or --unitsync.'
		print

	app = QtGui.QApplication(['RapidGUI'])
	window = RapidGUI()
	window.show()
	#poor man's threaded loading..
	t = threading.Timer( 1, reloadAction, [window] )
	t.start()
	app.exec_()
	
