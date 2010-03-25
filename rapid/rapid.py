#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Tobi Vollebregt

from bitarray import bitarray
from contextlib import closing
from hashlib import md5
from urlparse import urlparse
from StringIO import StringIO
import binascii, gzip, os, struct

from downloader import Downloader, atomic_write

################################################################################

# content_dir : Storage for temporary files (repos.gz, versions.gz)
# spring_dir  : Spring data directory
# pool_dir    : Where pool files are stored (visible to Spring)
# package_dir : Where package files are stored (visible to Spring)

master_url = 'http://repos.caspring.org/repos.gz'

def set_spring_dir(path):
	global spring_dir, pool_dir, package_dir, content_dir
	spring_dir = path
	pool_dir = os.path.join(spring_dir, 'pool')
	package_dir = os.path.join(spring_dir, 'packages')
	content_dir = os.path.join(spring_dir, 'rapid')

if os.name == 'posix':
	set_spring_dir(os.path.join(os.environ['HOME'], '.spring'))
#FIXME: elif os.name =='nt':
else:
	raise NotImplementedError('Unknown OS: %s' % os.name)

################################################################################

def mkdir(path):
	""" Create directory if it does not exist yet. """
	if not os.path.exists(path):
		os.mkdir(path)

def mkdir_p(path):
	""" Create directories if they do not exist yet. """
	if not os.path.exists(path):
		os.makedirs(path)

def psv(s):
	""" Split pipe separated value string into list of non-empty components."""
	return [x for x in s.split('|') if x]

def gzip_string(s):
	""" Gzip the string s."""
	fileobj = StringIO()
	with closing(gzip.GzipFile(mode = 'wb', fileobj = fileobj)) as f:
		f.write(s)
	return fileobj.getvalue()

################################################################################

class RapidException(Exception):
	""" Base class for other exceptions defined in this module."""
	pass


class PackageFormatException(RapidException):
	""" Raised when a .sdp package can not be read."""
	def __init__(self, field):
		self.field = field

	def __str__(self):
		return self.field


class StreamerFormatException(RapidException):
	""" Raised when the output of streamer.cgi can not be read."""
	def __init__(self, field):
		self.field = field

	def __str__(self):
		return self.field

################################################################################

class Rapid:
	""" Repository container."""
	def __init__(self):
		self.__repositories = None
		self.__packages = None
		self.__packages_by_tag = None
		self.master_url = master_url
		self.cache_dir = content_dir
		self.repos_gz = os.path.join(self.cache_dir, 'repos.gz')
		self.packages_gz = os.path.join(self.cache_dir, 'packages.gz')

		mkdir(spring_dir)
		mkdir(content_dir)
		mkdir(package_dir)

		if not os.path.exists(pool_dir):
			os.mkdir(pool_dir)
			for i in range(0, 256):
				os.mkdir(os.path.join(pool_dir, '%02x' % i))

		self.downloader = Downloader(os.path.join(content_dir, 'downloader.cfg'))

	def update(self):
		""" Update of the master list of repositories."""
		self.downloader.conditional_get_request(self.master_url, self.repos_gz)

	def get_repositories(self):
		""" Download and return list of repositories."""
		if self.__repositories:
			return self.__repositories

		self.update()
		with closing(gzip.open(self.repos_gz)) as f:
			unique = set([x.split(',')[1] for x in f])
			self.__repositories = [Repository(self, x) for x in unique]

		return self.__repositories

	def read_packages_gz(self):
		""" Reads global packages.gz into a dictionary of Packages.

			Contrary to versions.gz, packages.gz:
			- is normalised (i.e. every package occurs only once),
			- does not support '|' characters in tags (tags are '|' separated)
		"""
		def read_line(line):
			row = line[:-1].split(',')
			return (row[3], Package(tags         = psv(row[0]), hex  = row[1],
			                        dependencies = psv(row[2]), name = row[3]))

		if os.path.exists(self.packages_gz):
			with closing(gzip.open(self.packages_gz)) as f:
				return dict(map(read_line, f))
		return {}

	def write_packages_gz(self):
		# Write to temporary file
		tempfile = self.packages_gz + '.tmp'
		with closing(gzip.open(tempfile, 'wb')) as f:
			for p in self.__packages.itervalues():
				# tags, hex, dependencies, name
				f.write(','.join(['|'.join(p.tags), p.hex, '|'.join(p.dependencies), p.name]) + '\n')

		# Commit by moving temporary file over packages.gz
		if os.path.exists(tempfile):
			if os.path.exists(self.packages_gz):
				os.remove(self.packages_gz)
			os.rename(tempfile, self.packages_gz)

	def get_packages_by_name(self):
		""" Return package with given name or None if there isn't any."""
		if self.__packages:
			return self.__packages

		self.__packages = self.read_packages_gz()

		# FIXME: this is broken if a package is in repo1 with tag1 and in repo2 with tag2
		for r in self.get_repositories():
			self.__packages.update(r.get_packages())

		self.write_packages_gz()

		# Resolve dependencies and calculate reverse dependencies.
		# Dependencies missing in all repositories are silently discarded.
		for p in self.__packages.itervalues():
			p.dependencies = set([self.__packages[name] for name in p.dependencies if name in self.__packages])
			for d in p.dependencies:
				d.reverse_dependencies.add(p)

		return self.__packages

	def get_package_by_name(self, name):
		""" Return package with given name or None if there isn't any."""
		if name in self.get_packages_by_name():
			return self.__packages[name]

		return None

	def get_packages_by_tag(self):
		""" Return a dictionary mapping tag to Package."""
		if self.__packages_by_tag:
			return self.__packages_by_tag

		self.__packages_by_tag = {}
		for p in self.get_packages_by_name().itervalues():
			self.__packages_by_tag.update(dict([(t, p) for t in p.tags]))

		return self.__packages_by_tag

	def get_package_by_tag(self, tag):
		""" Return package with given tag or None if there isn't any."""
		if tag in self.get_packages_by_tag():
			return self.__packages_by_tag[tag]

		return None

	def get_packages(self):
		""" Return something that can iterate over all packages."""
		return self.get_packages_by_name().itervalues()

	def get_installed_packages(self):
		""" Return something that can iterate over all installed packages."""
		return filter(lambda p: p.installed(), self.get_packages())

	def get_not_installed_packages(self):
		""" Return something that can iterate over all not-installed packages."""
		return filter(lambda p: not p.installed(), self.get_packages())

################################################################################

class Repository:
	""" A rapid package repository."""
	def __init__(self, rapid, url):
		self.__packages = None
		self.rapid = rapid
		self.url = url
		self.cache_dir = os.path.join(self.rapid.cache_dir, urlparse(url).netloc)
		self.package_cache_dir = os.path.join(self.cache_dir, 'packages')
		self.versions_gz = os.path.join(self.cache_dir, 'versions.gz')

		mkdir(self.cache_dir)
		mkdir(self.package_cache_dir)

	def update(self):
		""" Update of the list of packages of this repository."""
		self.rapid.downloader.conditional_get_request(self.url + '/versions.gz', self.versions_gz)

	def read_versions_gz(self):
		""" Reads versions.gz-formatted file into a dictionary of Packages."""
		packages = {}

		def read_line(line):
			row = line[:-1].split(',')   # tag,hex,dependencies,name
			tag, hex, deps, name = row[0], row[1], psv(row[2]), row[3]
			if not name in packages:
				packages[name] = Package(hex, name, deps, repository = self)
			assert (packages[name].hex == hex)
			assert (packages[name].dependencies == deps)
			assert (packages[name].name == name)
			packages[name].tags.add(tag)

		with closing(gzip.open(self.versions_gz)) as f:
			map(read_line, f)

		return packages

	def get_packages(self):
		""" Download and return the list of packages offered. For these
		    packages dependencies have not been resolved to other Package
		    objects, because of cross-repository dependencies."""
		if self.__packages:
			return self.__packages

		self.update()
		self.__packages = self.read_versions_gz()
		return self.__packages

################################################################################

class Package:
	def __init__(self, hex, name, dependencies, tags = None, repository = None):
		self.__files = None
		self.hex = hex
		self.name = name
		self.dependencies = dependencies
		self.reverse_dependencies = set()
		self.tags = set(tags or [])
		self.repository = repository
		if repository:
			self.cache_file = os.path.join(repository.package_cache_dir, self.hex + '.sdp')

	def get_installed_path(self):
		""" Return the path at which the package would be visible to Spring."""
		return os.path.join(package_dir, self.hex + '.sdp')

	def download(self):
		""" Download the package from the repository."""
		self.repository.rapid.downloader.onetime_get_request(self.repository.url + '/packages/' + self.hex + '.sdp', self.cache_file)

	def get_files(self):
		""" Download .sdp file and return the list of files in it."""
		if self.__files:
			return self.__files
		self.__files = []

		self.download()
		with closing(gzip.open(self.cache_file)) as f:
			def really_read(n, field):
				data = f.read(n)
				if len(data) < n:
					raise PackageFormatException(field)
				return data

			while True:
				namelen = f.read(1)
				if namelen == '': break   # normal loop termination condition
				namelen = struct.unpack('B', namelen)[0]

				name  = really_read(namelen, 'name')
				md5   = really_read(16, 'md5')
				crc32 = really_read(4, 'crc32')
				size  = really_read(4, 'size')

				size = struct.unpack('>L', size)[0]
				self.__files.append(File(self, name, md5, crc32, size))

		return self.__files

	def download_files(self, requested_files, progress = None):
		""" Download requested_files using the streamer.cgi interface.

		    Progress is reported through the progress object, which must be
		    callable (with a single argument to indicate progress _increase_),
		    a setMaximum (int) setter and int maximum() getter

		    streamer.cgi works as follows:
		    * The client does a POST to /streamer.cgi?<hex>
		      Where hex = the name of the .sdp
		    * The client then sends a gzipped bitarray representing the files
		      it wishes to download. Bitarray is formated in the obvious way,
		      an array of characters where each file in the sdp is represented
		      by the (index mod 8) bit (shifted left) of the (index div 8) byte
		      of the array.
		    * streamer.cgi then responds with <big endian encoded int32 length>
		      <data of gzipped pool file> for all files requested. Files in the
		      pool are also gzipped, so there is no need to decompress unless
		      you wish to verify integrity.
		    * streamer.cgi also sets the Content-Length header in the reply so
		      you can implement a proper progress bar.

		"""
		# Determine which files to fetch. (as bitarray and list of files)
		requested_files = set(requested_files)
		bits = bitarray(map(lambda f: f in requested_files, self.get_files()), endian='little')
		expected_files = filter(lambda f: f in requested_files, self.get_files())
		if len(expected_files) == 0:
			return

		# Build HTTP POST data.
		postdata = gzip_string(bits.tostring())

		# Perform HTTP POST request and download and process the response.
		with closing(self.repository.rapid.downloader.post(self.repository.url + '/streamer.cgi?' + self.hex, postdata)) as remote:
			if not remote.info().has_key('Content-Length'):
				raise StreamerFormatException('Content-Length')

			if progress:
				progress.setMaximum( int(remote.info()['Content-Length']) )
				progress(0)

			for f in expected_files:
				size = remote.read(4)
				if size == '': raise StreamerFormatException('size')
				size = struct.unpack('>L', size)[0]

				data = remote.read(size)
				if len(data) < size: raise StreamerFormatException('data')

				# check md5 hash
				with closing(gzip.GzipFile(mode = 'rb', fileobj = StringIO(data))) as g:
					if md5(g.read()).digest() != f.md5:
						raise StreamerFormatException('md5')

				mkdir_p( os.path.dirname(f.get_pool_path()) )
				atomic_write(f.get_pool_path(), data)

				if progress:
					progress(4 + size)

	def get_missing_files(self):
		""" Return a list of files which are not locally available."""
		return filter(lambda f: not f.available(), self.get_files())

	def can_be_installed(self):
		""" Return true iff all dependencies are installed."""
		if not self.installed():
			for dep in self.dependencies:
				if not dep.installed():
					return False
		return True

	def install(self, progress = None):
		""" Install the package by hardlinking it into Spring dir."""
		if not self.installed() and self.can_be_installed():
			self.download_files(self.get_missing_files(), progress)
			#FIXME: Windows support
			os.link(self.cache_file, self.get_installed_path())
			if progress:
				progress(progress.maximum())

	def can_be_uninstalled(self):
		""" Return true iff no reverse dependencies are installed."""
		if self.installed():
			for rdep in self.reverse_dependencies:
				if rdep.installed():
					return False
		return True

	def uninstall(self):
		""" Uninstall the package by unlinking it from Spring dir."""
		if self.installed() and self.can_be_uninstalled():
			os.unlink(self.get_installed_path())

	def installed(self):
		""" Return true if the package is installed, false otherwise."""
		return os.path.exists(self.get_installed_path())

################################################################################

class File:
	def __init__(self, package, name, md5, crc32, size):
		self.package = package
		self.name = name
		self.md5 = md5
		self.crc32 = crc32
		self.size = size

	def get_pool_path(self):
		""" Return the physical path to the file in the pool."""
		md5 = binascii.hexlify(self.md5)
		return os.path.join(pool_dir, md5[:2], md5[2:]) + '.gz'

	def available(self):
		""" Return true iff the file is available locally."""
		return os.path.exists(self.get_pool_path())

################################################################################

import unittest, shutil, time
from downloader import MockDownloader

class TestRapid(unittest.TestCase):
	test_dir = os.path.realpath('.test-rapid')

	def setUp(self):
		set_spring_dir(self.test_dir)

		# Speed up the test because if pool is present the 256 pool
		# directories are created on demand instead of beforehand.
		mkdir_p(pool_dir)

		self.rapid = Rapid()

		if True:   # False to use real Downloader, True to use MockDownloader
			self.rapid.downloader = MockDownloader()
			www = self.rapid.downloader.www
			www[master_url] = gzip_string(',http://ts1,,\n')
			www['http://ts1/versions.gz'] = gzip_string('xta:latest,1234,dependency,XTA 9.6\n,5678,,dependency\n')
			www['http://ts1/packages/1234.sdp'] = gzip_string('\3foo' + binascii.unhexlify('d41d8cd98f00b204e9800998ecf8427e') + 8 * '\0')
			www['http://ts1/packages/5678.sdp'] = gzip_string('')
			www['http://ts1/streamer.cgi?1234'] = struct.pack('>L', len(gzip_string(''))) + gzip_string('')

	def tearDown(self):
		shutil.rmtree(self.test_dir)

	def test_get_repositories(self):
		self.rapid.get_repositories()

	def test_get_packages_by_name(self):
		self.rapid.get_packages_by_name()

	def test_get_package_by_name(self):
		self.assertFalse(self.rapid.get_package_by_name('XXXXXX'))
		self.assertTrue(self.rapid.get_package_by_name('XTA 9.6'))

	def test_get_packages_by_tag(self):
		self.rapid.get_packages_by_tag()

	def test_get_package_by_tag(self):
		self.assertFalse(self.rapid.get_package_by_tag('XXXXXX'))
		self.assertTrue(self.rapid.get_package_by_tag('xta:latest'))

	def test_get_packages(self):
		self.rapid.get_packages()

	def test_get_installed_packages(self):
		self.rapid.get_installed_packages()

	def test_get_not_installed_packages(self):
		self.rapid.get_not_installed_packages()

	def install(self, p):
		for d in p.dependencies:
			self.install(d)
		p.install()

	def test_install_uninstall(self):
		p = self.rapid.get_package_by_tag('xta:latest')
		self.install(p)
		self.assertFalse(p.get_missing_files())
		self.assertTrue(os.path.exists(p.get_files()[0].get_pool_path()))
		self.assertTrue(os.path.exists(os.path.join(package_dir, '1234.sdp')))
		p.uninstall()
		self.assertFalse(os.path.exists(os.path.join(package_dir, '1234.sdp')))

	def test_install_missing_dependency(self):
		p = self.rapid.get_package_by_tag('xta:latest')
		p.install()
		self.assertFalse(p.installed())   # install should have failed

	def test_uninstall_dependency_check(self):
		p = self.rapid.get_package_by_tag('xta:latest')
		self.install(p)
		d = self.rapid.get_package_by_name('dependency')
		d.uninstall()
		self.assertTrue(d.installed())   # uninstall should have failed

if __name__ == '__main__':
	unittest.main()
