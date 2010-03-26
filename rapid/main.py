#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Tobi Vollebregt

from ConfigParser import RawConfigParser as ConfigParser
from progressbar import ProgressBar
import rapid
import getopt, os, sys


def usage():
	print """Usage: %(progname)s <verb> [<argument>]

Where verb is one of:
 * update|upgrade: Install the latest package for all pinned tags.
 * pin: Pins a tag and installs the latest package for that tag.
 * unpin: Unpins a tag. Does not uninstall any packages.
 * install: Install a package. Does not pin any tags.
 * uninstall: Uninstall a package. Unpin its tag if any.
 * list-tags: List all tags that contain <argument>.
 * list-pinned-tags: Idem, but only pinned tags.
 * list-packages: List all packages whose name contains <argument>.
 * list-installed-packages: Idem, but only installed packages.
 * uninstall-unpinned: Keep only the pinned tags and all dependencies.
 * collect-pool: Remove pool files not needed by any installed package.

Examples:
%(progname)s pin xta:latest           # installs latest XTA
%(progname)s pin 's44:latest mutator' # installs latest Spring: 1944
%(progname)s upgrade                  # upgrade all pinned tags
""" % {'progname': sys.argv[0]}
	sys.exit(1)


#  Create rapid module.
pool_dir = rapid.pool_dir
rapid = rapid.Rapid()


def select(noun, needle, haystack):
	n = needle.lower()
	selected = filter(lambda s: n in str(s).lower(), haystack)

	if len(selected) == 0:
		print 'No %ss matching %s found.' % (noun, needle)
		sys.exit(1)

	if len(selected) >= 100:
		print '100 or more matching %ss found, please narrow your search.' % noun
		sys.exit(1)

	if len(selected) > 1:
		print 'Multiple %ss found:' % noun
		for i in range(len(selected)):
			print '%2i.  %s' % (i + 1, selected[i])
		which = raw_input("Which %s do you mean? (enter number or 'all')   " % noun)
		if which == 'all':
			return selected
		try:
			which = int(which) - 1
		except ValueError:
			sys.exit(1)
		return [selected[which]]

	return selected


def pin_single(tag):
	""" Pin a tag. This means any package having this tag will automatically be
	    installed and upgraded."""
	if not tag in rapid.pinned_tags():
		print 'Pinning: ' + tag
		rapid.pinned_tags().add(tag)
	else:
		print 'Already pinned: ' + tag


def pin(searchterm):
	""" Pin all tags matching searchterm and install the corresponding packages."""
	for t in select('tag', searchterm, rapid.tags()):
		pin_single(t)
		install_single(rapid.packages()[t])


def unpin_single(tag):
	""" Unpin a tag. This means packages having this tag will not be
	    automatically upgraded anymore. Does not uninstall anything."""
	if tag in rapid.pinned_tags():
		print 'Unpinning: ' + tag
		rapid.pinned_tags().remove(tag)
	else:
		print 'Not pinned: ' + tag


def unpin(searchterm):
	""" Unpin all tags matching searchterm."""
	for t in select('pinned tag', searchterm, rapid.pinned_tags()):
		unpin_single(t)


def install_single(p, dep = False):
	""" Install a single package and its dependencies."""
	if p:
		for d in p.dependencies:
			install_single(d, True)
		if not p.installed():
			print ['Installing: ', 'Installing dependency: '][int(dep)] + p.name
			p.install(ProgressBar())
			print
		elif not dep:
			print 'Already installed: ' + p.name


def install(searchterm):
	""" Install all packages matching searchterm."""
	for name in select('name', searchterm, [p.name for p in rapid.packages()]):
		install_single(rapid.packages()[name])


def uninstall_single(p):
	""" Uninstall and unpin a single package. Does not uninstall dependencies."""
	if p:
		if not p.can_be_uninstalled():
			print 'Can not uninstall because of dependencies: ' + p.name
			return
		for t in p.tags:
			unpin_single(t)
		print 'Uninstalling: ' + p.name
		p.uninstall()


def uninstall_single_plus_revdeps(p, dep = False):
	""" Uninstall and unpin a package and all packages that depend on it."""
	if p:
		for d in p.reverse_dependencies:
			uninstall_single_plus_revdeps(d, True)
		for t in p.tags:
			unpin_single(t)
		if p.installed():
			print ['Uninstalling: ', 'Uninstalling dependency: '][int(dep)] + p.name
			p.uninstall()
		elif not dep:
			print 'Already uninstalled: ' + p.name


def uninstall(searchterm):
	""" Uninstall all packages matching searchterm."""
	for name in select('name', searchterm, [p.name for p in rapid.get_installed_packages()]):
		uninstall_single(rapid.packages()[name])


def list_packages(searchterm, available):
	""" List all packages whose name matches searchterm."""
	s = searchterm.lower()
	print 'Installed packages:'
	for p in [p for p in rapid.packages() if p.installed() and s in p.name.lower()]:
		print '  %-40s (%s)' % (p.name, ', '.join(p.tags))
	if available:
		print 'Available packages:'
		for p in [p for p in rapid.packages() if not p.installed() and s in p.name.lower()]:
			print '  %-40s (%s)' % (p.name, ', '.join(p.tags))


def list_tags(searchterm, available):
	""" List all tags which match searchterm."""
	s = searchterm.lower()
	print 'Pinned tags:'
	for tag in filter(lambda t: s in t.lower(), rapid.pinned_tags()):
		p = rapid.packages()[tag]
		if p:
			print '  %-40s (%s)' % (tag, p.name)
		else:
			print '  %-40s [dangling tag]' % tag
	if available:
		print 'Available tags:'
		for tag in (set(rapid.tags()) - set(rapid.pinned_tags())):
			p = rapid.packages()[tag]
			print '  %-40s (%s)' % (tag, p.name)


def upgrade(searchterm):
	""" Upgrade installed tags which match searchterm."""
	for tag in filter(lambda t: searchterm.lower() in t.lower(), rapid.pinned_tags()):
		install_single(rapid.packages()[tag])


def uninstall_unpinned():
	""" Simple mark and sweep garbage collector. The root set consists of the
	    pinned tags. This does not touch pool files."""
	# Build set marked_packages that should be kept.
	marked_packages = set()
	new_packages = set([rapid.packages()[t] for t in rapid.pinned_tags() if t in rapid.tags()])
	while new_packages:
		marked_packages.update(new_packages)
		new_packages = sum([list(p.dependencies) for p in new_packages], [])

	# Build set of packages that will be removed.
	garbage = set(set([p for p in rapid.packages() if p.installed()]) - marked_packages)

	# Confirmation?
	if (not raw_input('Uninstall %s? [y/N]: ' % ', '.join([p.name for p in garbage])).startswith('y')):
		return

	# Uninstall all garbage.
	for p in garbage:
		if p.installed():
			uninstall_single_plus_revdeps(p)


def collect_pool():
	""" Simple mark and sweep garbage collector. The root set consists of the
	    installed packages. This touches only pool files."""
	# Build set marked_files that should be kept.
	installed_packages = [p for p in rapid.packages() if p.installed()]
	marked_files = reduce(lambda x, y: x + y.get_files(), installed_packages, [])
	marked_files = set([f.get_pool_path() for f in marked_files])

	def gc(really_remove):
		# Remove all files not in marked_files.
		count = 0
		size = 0
		for i in range(0, 256):
			d = os.path.join(pool_dir, '%02x' % i)
			for f in os.listdir(d):
				f = os.path.join(d, f)
				if not f in marked_files:
					count += 1
					size += os.path.getsize(f)
					if really_remove: os.unlink(f)
		return (count, size)

	count, size = gc(False)

	print '%.2f megabytes / %d files can be collected from the pool.' % (size / (1024.*1024.), count)
	if count == 0:
		return

	# Confirmation?
	print
	print '#' * 80
	print '# %-76s #' % 'Collecting pool files will delete the data from disk permantly.'.center(76)
	print '# %-76s #' % 'You will have to download the data again in case you need it.'.center(76)
	print '#' * 80
	print
	if (not raw_input('Delete %d pool files? [y/N]: ' % count).startswith('y')):
		return

	count, size = gc(True)
	print '%.2f megabytes / %d files deleted from the pool.' % (size / (1024.*1024.), count)


def req_arg():
	if len(sys.argv) < 3:
		print 'Not enough arguments to operation: ' + verb
		print
		usage()
	return sys.argv[2]

def opt_arg():
	if len(sys.argv) > 2:
		return sys.argv[2]
	return ''
