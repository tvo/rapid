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

Examples:
%(progname)s pin xta:latest           # installs latest XTA
%(progname)s pin 's44:latest mutator' # installs latest Spring: 1944
%(progname)s upgrade                  # upgrade all pinned tags
""" % {'progname': sys.argv[0]}
	sys.exit(1)


# Read configuration (i.e. list of pinned tags)
config_path = os.path.join(rapid.content_dir, 'main.cfg')
config = ConfigParser()
config.read(config_path)
pinned_tags = []

if not config.has_section('tags'):
	config.add_section('tags')
if config.has_option('tags', 'pinned'):
	pinned_tags = set([s for s in config.get('tags', 'pinned').split(',') if s])


#  Create rapid module.
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
	if not tag in pinned_tags:
		print 'Pinning: ' + tag
		pinned_tags.add(tag)
	else:
		print 'Already pinned: ' + tag


def pin(searchterm):
	""" Pin all tags matching searchterm and install the corresponding packages."""
	for t in select('tag', searchterm, rapid.get_packages_by_tag().iterkeys()):
		pin_single(t)
		install_single(rapid.get_package_by_tag(t))


def unpin_single(tag):
	""" Unpin a tag. This means packages having this tag will not be
	    automatically upgraded anymore. Does not uninstall anything."""
	if tag in pinned_tags:
		print 'Unpinning: ' + tag
		pinned_tags.remove(tag)
	else:
		print 'Not pinned: ' + tag


def unpin(searchterm):
	""" Unpin all tags matching searchterm."""
	for t in select('pinned tag', searchterm, pinned_tags):
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
	for name in select('name', searchterm, rapid.get_names().iterkeys()):
		install_single(rapid.get_package_by_name(name))


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


def uninstall(searchterm):
	""" Uninstall all packages matching searchterm."""
	for name in select('name', searchterm, [p.name for p in rapid.get_installed_packages()]):
		uninstall_single(rapid.get_package_by_name(name))


def list_packages(searchterm, available):
	""" List all packages whose name matches searchterm."""
	s = searchterm.lower()
	print 'Installed packages:'
	for p in filter(lambda p: s in p.name.lower(), rapid.get_installed_packages()):
		print '  %-40s (%s)' % (p.name, ', '.join(p.tags))
	if available:
		print 'Available packages:'
		for p in rapid.get_not_installed_packages():
			print '  %-40s (%s)' % (p.name, ', '.join(p.tags))


def list_tags(searchterm, available):
	""" List all tags which match searchterm."""
	s = searchterm.lower()
	print 'Pinned tags:'
	for tag in filter(lambda t: s in t.lower(), pinned_tags):
		p = rapid.get_package_by_tag(tag)
		if p:
			print '  %-40s (%s)' % (tag, p.name)
		else:
			print '  %-40s [dangling tag]' % tag
	if available:
		print 'Available tags:'
		for tag in (set(rapid.get_packages_by_tag()) - pinned_tags):
			p = rapid.get_package_by_tag(tag)
			print '  %-40s (%s)' % (tag, p.name)


def upgrade(searchterm):
	""" Upgrade installed tags which match searchterm."""
	for tag in filter(lambda t: searchterm.lower() in t.lower(), pinned_tags):
		install_single(rapid.get_package_by_tag(tag))


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
