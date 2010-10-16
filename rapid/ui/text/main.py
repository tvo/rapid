# Author: Tobi Vollebregt

import os, re, sys
import logging
from optparse import OptionParser
from rapid.main import *
from .interaction import TextUserInteraction
from rapid.unitsync.api import get_writable_data_directory


USAGE = """Usage: %prog [options...] <verb>  [arguments...]

Where the different verbs and their arguments are:

 * `upgrade`: Install the latest package for all pinned tags.
 * `clean-upgrade`: Equivalent to 'upgrade' followed by 'uninstall-unpinned'.
 * `pin <tag(s)>`: Pins tags and installs the latest packages for those tags.
 * `unpin <tag(s)>`: Unpins tags. Does not uninstall any packages.
 * `install <package(s)>`: Install packages. Does not pin any tags.
 * `uninstall <package(s)>`: Uninstall packages. Unpins their tags if any.
 * `list-tags [tag]`: List all tags that match *tag*.
 * `list-pinned-tags [tag]`: Idem, but only pinned tags.
 * `list-packages [package]`: List all packages whose name contains *package*.
 * `list-installed-packages [package]`: Idem, but only installed packages.
 * `uninstall-unpinned`: Keep only the pinned tags and all dependencies.
 * `collect-pool`: Remove pool files not needed by any installed package.
 * `make-sdd <tag|package> <dir>`: Extract pool files of a package into
	`~/.spring/mods/<dir>`.

Examples:

  %prog pin xta:latest   # installs latest XTA
  %prog pin s44:latest   # installs latest Spring: 1944
  %prog upgrade          # upgrade all pinned tags

Other commands are for power users mostly, e.g.:

  %prog list-tags '^(?!ba).*:(latest|stable|test)$' --regex
    # This displays all tags ending with ':latest', ':stable' or ':test',
    # which do not start with the string 'ba'."""


def main():
	""" Commandline interface entry point."""
	logging.basicConfig(level = logging.INFO, stream = sys.stdout, format = '%(message)s')
	parser = OptionParser(usage=USAGE)

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
	parser.add_option('-r', '--regex',
		action='store_true', dest='regex',
		help='Use regular expressions instead of substring matches for '
		'pin, unpin, install, uninstall and all list-* commands.')
	parser.add_option('-y', '--yes',
		action='store_true', dest='force',
		help='Answer all confirmations with yes. MAY BE DANGEROUS!')

	(options, args) = parser.parse_args()

	def usage():
		""" Display usage and exit."""
		parser.print_usage()
		sys.exit(1)

	def req_arg():
		""" Returns the next positional argument or
		displays an error and exits if there are no arguments left."""
		if len(args) < 1:
			print 'Not enough arguments to operation.'
			print
			usage()
		return args.pop(0)

	def opt_arg():
		""" Returns the next positional argument or
		the empty string if there are no arguments left."""
		if len(args) >= 1:
			return args.pop(0)
		return ''

	if len(args) < 1:
		usage()

	verb = args.pop(0)

	ui = TextUserInteraction(options.force)

	if options.regex:
		ui._select_core = (lambda needle, haystack:
			[candidate for candidate in haystack if re.search(needle, str(candidate), re.I)])

	if options.datadir:
		init(options.datadir, ui)
	elif options.unitsync:
		init(get_writable_data_directory(), ui)
	elif os.name == 'posix':
		init(os.path.expanduser('~/.spring'), ui)
	else:
		print 'No data directory specified. Specify one using either --datadir or --unitsync.'
		print
		usage()

	# Loop conditions are at the end.
	handled = True
	while True:
		# Commands which are applied to all subsequent arguments.
		# (e.g. `pin tag1 tag2 tag3' pins all three tags..)
		if verb == 'pin':
			pin(req_arg())
		elif verb == 'unpin':
			unpin(req_arg())
		elif verb == 'install':
			install(req_arg())
		elif verb == 'uninstall':
			uninstall(req_arg())
		else:
			handled = False
			break

		# Unless we ran out of arguments, repeat the same operation
		# on the next argument.
		if len(args) == 0:
			break
		else:
			print '---'

	# Commands which have a fixed number of arguments.
	if verb == 'list-packages':
		list_packages(opt_arg(), True)
	elif verb == 'list-installed-packages':
		list_packages(opt_arg(), False)
	elif verb == 'list-tags':
		list_tags(opt_arg(), True)
	elif verb == 'list-pinned-tags':
		list_tags(opt_arg(), False)
	elif verb == 'update' or verb == 'upgrade':
		upgrade()
	elif verb == 'clean-update' or verb == 'clean-upgrade':
		clean_upgrade()
	elif verb == 'uninstall-unpinned':
		uninstall_unpinned()
	elif verb == 'collect-pool':
		collect_pool()
	elif verb == 'make-sdd':
		make_sdd(req_arg(), req_arg())
	elif not handled:
		print 'Unknown operation: ' + verb
		print
		usage()
