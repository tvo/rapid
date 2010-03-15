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
	pinned_tags = filter(lambda x: len(x)>0, config.get('tags', 'pinned').split(','))


#  Create rapid module.
rapid = rapid.Rapid()


def select(noun, searchterm, packages):
	""" Search for packages with searchterm in tag or name. Ask user for more
	    information depending on the number of results and return the selected
	    packages or exit if user canceled."""
	s = searchterm.lower()
	selected = filter(lambda p: s in p.tag.lower() or s in p.name.lower(), packages)

	if len(selected) == 0:
		print 'No %ss matching %s found.' % (noun, searchterm)
		sys.exit(1)

	if len(selected) >= 100:
		print '100 or more matching %ss found, please narrow your search.' % noun
		sys.exit(1)

	if len(selected) > 1:
		print 'Multiple %ss found:' % noun
		for i in range(len(selected)):
			p = selected[i]
			print '%2i.  %-30s (%s)' % (i + 1, p.tag, p.name)
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
		pinned_tags.append(tag)
	else:
		print 'Already pinned: ' + tag


def pin(searchterm):
	""" Pin all tags matching searchterm and install the corresponding packages."""
	for p in select('tag', searchterm, rapid.get_packages()):
		pin_single(p.tag)
		install_single(p)


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
	for p in select('pinned tag', searchterm, filter(lambda p: p.tag in pinned_tags, rapid.get_packages())):
		unpin_single(p.tag)


def install_single(p, dep = False):
	""" Install a single package and its dependencies."""
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
	for p in select('package', searchterm, rapid.get_packages()):
		install_single(p)


def uninstall_single(p):
	""" Uninstall and unpin a single package. Does not uninstall dependencies."""
	unpin_single(p.tag)
	print 'Uninstalling: ' + p.name
	p.uninstall()


def uninstall(searchterm):
	""" Uninstall all packages matching searchterm."""
	for p in select('package', searchterm, filter(lambda p: p.installed(), rapid.get_packages())):
		uninstall_single(p)


def list_packages(searchterm, available):
	""" List all packages whose name matches searchterm."""
	selected = filter(lambda p: searchterm in p.name, rapid.get_packages())
	print 'Installed packages:'
	for p in filter(lambda p: p.installed(), selected):
		print '  %-40s (%s)' % (p.name, ', '.join(filter(lambda t: t == p.tag, pinned_tags)))
	if available:
		print 'Available packages:'
		for p in filter(lambda p: not p.installed(), selected):
			print '  %-40s (%s)' % (p.name, p.tag)


def list_tags(searchterm, available):
	""" List all tags which match searchterm."""
	print 'Pinned tags:'
	for tag in filter(lambda t: searchterm.lower() in t.lower(), pinned_tags):
		packages = filter(lambda p: tag == p.tag, rapid.get_packages())
		for p in packages:
			print '  %-40s (%s)' % (p.tag, p.name)
		if len(packages) == 0:
			print '  %-40s [dangling tag]' % tag
	if available:
		print 'Available tags:'
		for p in filter(lambda p: searchterm.lower() in p.tag.lower() and not p.tag in pinned_tags, rapid.get_packages()):
			print '  %-40s (%s)' % (p.tag, p.name)


def upgrade(searchterm):
	""" Upgrade installed tags which match searchterm."""
	for tag in filter(lambda t: searchterm.lower() in t.lower(), pinned_tags):
		for p in filter(lambda p: tag == p.tag, rapid.get_packages()):
			install_single(p)


if len(sys.argv) < 2:
	usage()

verb = sys.argv[1]

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

if verb == 'pin':
	pin(req_arg())
elif verb == 'unpin':
	unpin(req_arg())
elif verb == 'install':
	install(req_arg())
elif verb == 'uninstall':
	uninstall(req_arg())
elif verb == 'list-packages':
	list_packages(opt_arg(), True)
elif verb == 'list-installed-packages':
	list_packages(opt_arg(), False)
elif verb == 'list-tags':
	list_tags(opt_arg(), True)
elif verb == 'list-pinned-tags':
	list_tags(opt_arg(), False)
elif verb == 'update' or verb == 'upgrade':
	upgrade(opt_arg())
else:
	print 'Unknown operation: ' + verb
	print
	usage()


# Write configuration.
config.set('tags', 'pinned', ','.join(pinned_tags))
with open(config_path, 'wb') as f:
	config.write(f)
