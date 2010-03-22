#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Tobi Vollebregt

from binascii import hexlify
from bitarray import bitarray
from contextlib import closing
from hashlib import md5
from urlparse import urlparse
from StringIO import StringIO
import gzip, os, struct

from downloader import Downloader, atomic_write


# content_dir : Storage for temporary files (repos.gz, versions.gz)
# spring_dir  : Spring data directory
# pool_dir    : Where pool files are stored (visible to Spring)
# package_dir : Where package files are stored (visible to Spring)

if os.name == 'posix':
	home = os.environ['HOME']
	spring_dir = os.path.join(home, '.spring')
	pool_dir = os.path.join(spring_dir, 'pool')
	package_dir = os.path.join(spring_dir, 'packages')
	content_dir = os.path.join(spring_dir, 'rapid')
#FIXME: elif os.name =='nt':
else:
	raise NotImplementedError('Unknown OS: %s' % os.name)


def mkdir(path):
	""" Create directory if it does not exist yet. """
	if not os.path.exists(path):
		os.mkdir(path)


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


class Rapid:
	""" Repository container."""
	master_url = 'http://repos.caspring.org/repos.gz'
	cache_dir = content_dir
	__repositories = None
	__packages = None

	def __init__(self):
		mkdir(content_dir)
		mkdir(spring_dir)
		mkdir(package_dir)

		if not os.path.exists(pool_dir):
			os.mkdir(pool_dir)
			for i in range(0, 256):
				os.mkdir(os.path.join(pool_dir, '%02x' % i))

		self.downloader = Downloader(os.path.join(content_dir, 'downloader.cfg'))

	def update(self):
		""" Force an update of the master list of repositories."""
		path = os.path.join(content_dir, 'repos.gz')
		self.downloader.conditional_get_request(self.master_url, path)
		self.__repositories = None
		self.__packages = None
		return path

	def get_repositories(self):
		""" Download and return list of repositories."""
		if self.__repositories:
			return self.__repositories

		with closing(gzip.open(self.update())) as f:
			unique = set(map(lambda x: x.split(',')[1], f))
			self.__repositories = map(lambda x: Repository(self, x), unique)

		return self.__repositories

	def get_packages(self):
		""" Get combined list of packages published by all repositories."""
		if self.__packages:
			return self.__packages

		self.__packages = reduce(lambda x, y: x + y.get_packages(), self.get_repositories(), [])

		# Resolve dependencies.
		# Dependencies missing in all repositories are silently discarded.
		by_name = dict(map(lambda x: (x.name, x), self.__packages))
		for p in self.__packages:
			p.dependencies = map(lambda x: by_name[x], filter(lambda x: by_name.has_key(x), p.dependencies))

		return self.__packages


class Repository:
	""" A rapid package repository."""
	__packages = None

	def __init__(self, rapid, url):
		self.rapid = rapid
		self.url = url
		self.cache_dir = os.path.join(self.rapid.cache_dir, urlparse(url).netloc)
		self.package_cache_dir = os.path.join(self.cache_dir, 'packages')

		# Create cache directories
		mkdir(self.cache_dir)
		mkdir(self.package_cache_dir)

	def update(self):
		""" Force an update of the list of packages of this repository."""
		path = os.path.join(self.cache_dir, 'versions.gz')
		self.rapid.downloader.conditional_get_request(self.url + '/versions.gz', path)
		self.__packages = None
		return path

	def get_packages(self):
		""" Download and return the list of packages offered. For these
		    packages dependencies have not been resolved to other Package
		    objects, because of cross-repository dependencies."""
		if self.__packages:
			return self.__packages

		def read_line(line):
			row = line[:-1].split(',')   # tag,hex,dependencies,name
			deps = filter(lambda x: len(x)>0, row[2].split('|'))
			return Package(self, row[0], row[1], deps, row[3])

		with closing(gzip.open(self.update())) as f:
			self.__packages = map(read_line, f)

		return self.__packages


class Package:
	__files = None

	def __init__(self, repository, tag, hex, dependencies, name):
		self.repository = repository
		self.tag = tag
		self.hex = hex
		self.dependencies = dependencies
		self.name = name
		self.cache_file = os.path.join(repository.cache_dir, 'packages', self.hex + '.sdp')

	def get_installed_path(self):
		""" Return the path at which the package would be visible to Spring."""
		return os.path.join(package_dir, self.hex + '.sdp')

	def download(self):
		""" Download the package from the repository."""
		self.repository.rapid.downloader.onetime_get_request(self.repository.url + '/packages/' + self.hex + '.sdp', self.cache_file)
		return self.cache_file

	def get_files(self):
		""" Download .sdp file and return the list of files in it."""
		if self.__files:
			return self.__files
		self.__files = []

		#d = self.repository.rapid.downloader
		#d.onetime_get_request('packages/' + self.hex + '.sdp'

		with closing(gzip.open(self.download())) as f:
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
		    callable (with a single argument to indicate progress _increase_)
		    and have a max attribute.

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
		postdata = StringIO()
		with closing(gzip.GzipFile(mode = 'wb', fileobj = postdata)) as f:
			f.write(bits.tostring()) #bits.tofile(f) doesn't work here
		postdata = postdata.getvalue()

		# Perform HTTP POST request and download and process the response.
		with closing(self.repository.rapid.downloader.post(self.repository.url + '/streamer.cgi?' + self.hex, postdata)) as remote:
			if not remote.info().has_key('Content-Length'):
				raise StreamerFormatException('Content-Length')

			if progress:
				progress.max = int(remote.info()['Content-Length'])
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

				atomic_write(f.get_pool_path(), data)

				if progress:
					progress(4 + size)

	def get_missing_files(self):
		""" Return a list of files which are not locally available."""
		return filter(lambda f: not f.available(), self.get_files())

	def install(self, progress = None):
		""" Install the package by hardlinking it into Spring dir."""
		if not self.installed():
			for dep in self.dependencies:
				if not dep.installed():
					return False
			self.download_files(self.get_missing_files(), progress)
			#FIXME: Windows support
			os.link(self.cache_file, self.get_installed_path())
			progress(progress.max)
		return True

	def uninstall(self):
		""" Uninstall the package by unlinking it from Spring dir."""
		if self.installed():
			os.unlink(self.get_installed_path())

	def installed(self):
		""" Return true if the package is installed, false otherwise."""
		return os.path.exists(self.get_installed_path())


class File:
	def __init__(self, package, name, md5, crc32, size):
		self.package = package
		self.name = name
		self.md5 = md5
		self.crc32 = crc32
		self.size = size

	def get_pool_path(self):
		""" Return the physical path to the file in the pool."""
		md5 = hexlify(self.md5)
		return os.path.join(pool_dir, md5[:2], md5[2:]) + '.gz'

	def available(self):
		""" Return true iff the file is available locally."""
		return os.path.exists(self.get_pool_path())


if __name__ == '__main__':
	from progressbar import ProgressBar
	try:
		r = Rapid()
		"""for r in r.get_repositories():
			print(r)
			for p in r.get_packages():
				print(p.tag, p.hex, p.name)
				for d in p.dependencies:
					print (p.tag, p.name, type(d), str(d))"""
		"""for p in r.get_packages():
			print(p.tag, p.hex, p.name)"""
		for p in r.get_packages():
			if 'Spring: 1944' in p.name:
				print (p.name, len(p.get_files()), len(p.get_missing_files()))
				p.download_files(p.get_missing_files(), ProgressBar())
	except RapidException as e:
		print str(e)
		raise
