#!/usr/bin/env python
# Copyright (C) 2010 Tobi Vollebregt

from bitarray import bitarray
from contextlib import closing
from hashlib import md5
from urlparse import urlparse
from StringIO import StringIO
import binascii, gzip, os, shutil, struct, weakref
import ConfigParser

from util.downloader import Downloader, atomic_write

# rapid hits the servers at worst once every..
MASTER_RATE_LIMIT = 60 * 60     # ..one hour
REPOSITORY_RATE_LIMIT = 5 * 60  # ..five minutes  

################################################################################

# content_dir : Storage for temporary files (repos.gz, versions.gz)
# spring_dir  : Spring data directory
# pool_dir    : Where pool files are stored (visible to Spring)
# package_dir : Where package files are stored (visible to Spring)

master_url = 'http://repos.springrts.com/repos.gz'

def set_spring_dir(path):
	global spring_dir, pool_dir, package_dir, content_dir
	spring_dir = path
	pool_dir = os.path.join(spring_dir, 'pool')
	package_dir = os.path.join(spring_dir, 'packages')
	content_dir = os.path.join(spring_dir, 'rapid')

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


class OfflineRepositoryException(RapidException):
	""" Raised when attempting to download something from an offline repository.
	    (i.e. the repository that has the package is not listed in repos.gz anymore.)"""
	pass


class DetachedPackageException(RapidException):
	""" Raised when attempting to download something from a detached package.
	    (i.e. it is not in any repositories' versions.gz)"""
	pass


class DependencyException(RapidException):
	""" Raised when install/uninstall fails because of dependencies."""
	pass

################################################################################

class RepositorySource(object):
	def __init__(self, cache_dir, downloader):
		self.__repositories = None
		self.cache_dir = cache_dir
		self.downloader = downloader
		self.repos_gz = os.path.join(cache_dir, 'repos.gz')

	def load(self):
		""" Download and return list of repositories."""

		# Collect OnlineRepositories
		self.downloader.conditional_get_request(master_url, self.repos_gz, MASTER_RATE_LIMIT)
		with closing(gzip.open(self.repos_gz)) as f:
			unique = set(x.split(',')[1] for x in f)
			self.__repositories = [OnlineRepository(os.path.join(self.cache_dir, urlparse(x).netloc), self.downloader, x) for x in unique]

		# Collect OfflineRepositories
		for dirent in os.listdir(self.cache_dir):
			path = os.path.join(self.cache_dir, dirent)
			if os.path.isdir(path) and path not in (r.cache_dir for r in self.__repositories):
				self.__repositories.append(OfflineRepository(path))

	@property
	def list(self):
		if not self.__repositories: self.load()
		return self.__repositories

	def __getitem__(self, key):
		return self.list[key]

	def __contains__(self, key):
		return key in self.list

	def __len__(self):
		return len(self.list)

	def __iter__(self):
		return self.list.__iter__()

################################################################################

class PackageSource(object):
	def __init__(self, cache_dir, repositories):
		self.__packages_dict = None
		self.__packages_list = None
		self.__tags = None
		self.cache_dir = cache_dir
		self.repositories = repositories
		self.packages_gz = os.path.join(cache_dir, 'packages.gz')

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
			for p in self:
				# tags, hex, dependencies, name
				f.write(','.join(['|'.join(p.tags), p.hex, '|'.join(p.dependencies), p.name]) + '\n')

		# Commit by moving temporary file over packages.gz
		if os.path.exists(tempfile):
			if os.path.exists(self.packages_gz):
				os.remove(self.packages_gz)
			os.rename(tempfile, self.packages_gz)

	def load(self):
		self.__packages_dict = self.read_packages_gz()
		# FIXME: this is broken if a package is in repo1 with tag1 and in repo2 with tag2
		for r in self.repositories:
			self.__packages_dict.update(r.packages)
		self.__packages_list = self.__packages_dict.values()
		self.write_packages_gz()

		# Resolve dependencies and calculate reverse dependencies.
		# Dependencies missing in all repositories are silently discarded.
		for p in self:
			p.dependencies = set(self[name] for name in p.dependencies if name in self)
			for d in p.dependencies:
				d.reverse_dependencies.add(p)

		# Try to 'repair' detached packages.
		# (This assumes package hex is (sufficiently) unique.)
		for p in self:
			if not p.repository:
				repos = [r for r in self.repositories if r.has_package(p)]
				if repos:
					self.__packages_dict[p.name] = Package(p.hex, p.name, p.dependencies, p.tags, repos[0])
		self.__packages_list = self.__packages_dict.values()

		# Create set of tags and mapping from tag to Package objects.
		self.__tags = set()
		for p in self:
			self.__packages_dict.update((t, p) for t in p.tags)
			self.__tags.update(p.tags)

		# Make __getitem__ idempotent.
		self.__packages_dict.update((p, p) for p in self)

	@property
	def list(self):
		if not self.__packages_list: self.load()
		return self.__packages_list

	@property
	def dict(self):
		if not self.__packages_dict: self.load()
		return self.__packages_dict

	@property
	def tags(self):
		if not self.__tags: self.load()
		return self.__tags

	def __getitem__(self, key):
		if type(key) in (int, slice):
			return self.list[key]
		return self.dict[key]

	def __contains__(self, key):
		return key in self.dict

	def __len__(self):
		return len(self.list)

	def __iter__(self):
		return self.list.__iter__()

################################################################################

class PinnedTags(object):
	def __init__(self):
		self.__config_path = os.path.join(content_dir, 'main.cfg')
		self.__config = ConfigParser.RawConfigParser()
		self.__config.read(self.__config_path)
		self.__pinned_tags = set()
		if not self.__config.has_section('tags'):
			self.__config.add_section('tags')
		if self.__config.has_option('tags', 'pinned'):
			self.__pinned_tags = set(s for s in self.__config.get('tags', 'pinned').split(',') if s)

	def write(self):
		# Write configuration.
		self.__config.set('tags', 'pinned', ','.join(self.__pinned_tags))
		with open(self.__config_path, 'wb') as f:
			self.__config.write(f)

	def add(self, tag):
		self.__pinned_tags.add(tag)
		self.write()

	def clear(self):
		self.__pinned_tags.clear()
		self.write()

	def remove(self, tag):
		self.__pinned_tags.remove(tag)
		self.write()

	def update(self, tags):
		self.__pinned_tags.update(tags)
		self.write()

	def __getitem__(self, key):
		return self.__pinned_tags[key]

	def __contains__(self, tag):
		return tag in self.__pinned_tags

	def __len__(self):
		return len(self.__pinned_tags)

	def __iter__(self):
		return self.__pinned_tags.__iter__();

################################################################################

class Rapid(object):
	def __init__(self, downloader = None):
		mkdir(spring_dir)
		mkdir(content_dir)
		mkdir(package_dir)

		if not os.path.exists(pool_dir):
			os.mkdir(pool_dir)
			for i in range(0, 256):
				os.mkdir(os.path.join(pool_dir, '%02x' % i))

		self.__downloader = downloader or Downloader(os.path.join(content_dir, 'downloader.cfg'))
		self.__repositories = RepositorySource(content_dir, self.__downloader)
		self.__packages = PackageSource(content_dir, self.__repositories)
		self.__pinned_tags = PinnedTags()

	@property
	def repositories(self):
		return self.__repositories

	@property
	def packages(self):
		return self.__packages

	@property
	def tags(self):
		return self.__packages.tags

	@property
	def pinned_tags(self):
		return self.__pinned_tags

################################################################################

class Repository(object):
	def __init__(self, cache_dir):
		self.__packages = None
		self.cache_dir = cache_dir
		self.package_cache_dir = os.path.join(self.cache_dir, 'packages')
		self.versions_gz = os.path.join(self.cache_dir, 'versions.gz')

		mkdir(self.cache_dir)
		mkdir(self.package_cache_dir)

	def has_package(self, p):
		""" Return true iff p belongs to this repository."""
		if p.repository:
			return p.repository == self
		return os.path.exists(os.path.join(self.package_cache_dir, p.hex + '.sdp'))

	def update(self):
		pass

	def read_versions_gz(self):
		""" Reads versions.gz-formatted file into a dictionary of Packages."""
		packages = {}

		def read_line(line):
			row = line[:-1].split(',')   # tag,hex,dependencies,name
			tag, hex, deps, name = row[0], row[1], psv(row[2]), row[3]
			if not name in packages:
				packages[name] = Package(hex, name, deps, repository = self)
			assert packages[name].name == name
			# Ignore package if the name was already present, but with
			# different hex or different dependencies. (#9)
			if (packages[name].hex == hex and
				packages[name].dependencies == deps and tag):
				packages[name].tags.add(tag)

		with closing(gzip.open(self.versions_gz)) as f:
			map(read_line, f)

		return packages

	@property
	def packages(self):
		""" Download and return the list of packages offered. For these
		    packages dependencies have not been resolved to other Package
		    objects, because of cross-repository dependencies."""
		if self.__packages:
			return self.__packages

		self.update()
		self.__packages = self.read_versions_gz()
		return self.__packages


class OfflineRepository(Repository):
	pass


class OnlineRepository(Repository):
	def __init__(self, cache_dir, downloader, url):
		Repository.__init__(self, cache_dir)
		self.downloader = downloader
		self.url = url

	def update(self):
		""" Update of the list of packages of this repository."""
		self.downloader.conditional_get_request(self.url + '/versions.gz', self.versions_gz, REPOSITORY_RATE_LIMIT)

################################################################################

class Package(object):
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

	def __str__(self):
		return self.name

	@property
	def installed_path(self):
		""" Return the path at which the package would be visible to Spring."""
		return os.path.join(package_dir, self.hex + '.sdp')

	def download(self):
		""" Download the package from the repository."""
		if not self.available:
			if not self.repository:
				raise DetachedPackageException()
			if not hasattr(self.repository, 'url'):
				raise OfflineRepositoryException()
			self.repository.downloader.onetime_get_request('%s/packages/%s.sdp' % (self.repository.url, self.hex), self.cache_file)

	@property
	def files(self):
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
				self.__files.append(File(name, md5, crc32, size))

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
		bits = bitarray(map(lambda f: f in requested_files, self.files), endian='little')
		expected_files = filter(lambda f: f in requested_files, self.files)
		if len(expected_files) == 0:
			return

		# Can not download from offline repository...
		if not hasattr(self.repository, 'url'):
			raise OfflineRepositoryException()

		# Build HTTP POST data.
		# NOTE: bitarray < 0.4.0 has only tostring()
		#       bitarray >= 0.4.0 has tobytes() and tostring(), but tostring()
		#       decodes the bits as 7-bit ascii, so many bytes trigger an error.
		postdata = bits.tobytes() if hasattr(bits, 'tobytes') else bits.tostring()
		postdata = gzip_string(postdata)

		# Perform HTTP POST request and download and process the response.
		url = '%s/streamer.cgi?%s' % (self.repository.url, self.hex)
		with closing(self.repository.downloader.post(url, postdata)) as remote:
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

				mkdir_p( os.path.dirname(f.pool_path) )
				atomic_write(f.pool_path, data)

				if progress:
					progress(4 + size)

	@property
	def missing_files(self):
		""" Return a list of files which are not locally available."""
		return filter(lambda f: not f.available, self.files)

	@property
	def can_be_installed(self):
		""" Return true iff all dependencies are installed."""
		if not self.installed:
			for dep in self.dependencies:
				if not dep.installed:
					return False
		return True

	def install(self, progress = None):
		""" Install the package by hardlinking it into Spring dir."""
		if not self.installed:
			if not self.can_be_installed:
				raise DependencyException()
			self.download_files(self.missing_files, progress)
			if hasattr(os, 'link'):
				os.link(self.cache_file, self.installed_path)
			else:
				shutil.copy(self.cache_file, self.installed_path)
			if progress:
				progress(progress.maximum())

	@property
	def can_be_uninstalled(self):
		""" Return true iff no reverse dependencies are installed."""
		if self.installed:
			for rdep in self.reverse_dependencies:
				if rdep.installed:
					return False
		return True

	def uninstall(self):
		""" Uninstall the package by unlinking it from Spring dir."""
		if self.installed:
			if not self.can_be_uninstalled:
				raise DependencyException()
			os.unlink(self.installed_path)

	@property
	def installed(self):
		""" Return true if the package is installed, false otherwise."""
		return os.path.exists(self.installed_path)

	@property
	def available(self):
		""" Return true iff the file list is available locally. This does not
		    imply the pool files are all available too."""
		return hasattr(self, 'cache_file') and os.path.exists(self.cache_file)

	@property
	def installable(self):
		""" Attempt to make a good guess at whether this package is installable.
			Contrary to can_be_installed this may return True if dependencies
			are not (yet) available. It checks that the package itself and all
			its dependencies are either installed already or can be downloaded
			from a repository.

			If this returns True, it is guaranteed no other method of this
			package or its dependencies raise an OfflineRepositoryException or
			a DetachedPackageException.

			Note that (obviously) there may still be other problems when
			actually installing the package. (e.g. network/server down)"""
		for dep in self.dependencies:
			if not dep.installable:
				return False
		return ((self.available and self.missing_files == []) or
				(self.repository and hasattr(self.repository, 'url')))

################################################################################

class File(object):
	""" Stores metadata about a pool file. Uses flyweight pattern to reduce
	    memory consumption. (Many pool files may be shared between packages.)"""

	__slots__ = ['pool_path', 'name', 'md5', 'crc32', 'size', '__weakref__']
	__files = weakref.WeakValueDictionary()

	def __new__(cls, name, md5, crc32, size):
		""" Factory participant of Flyweight pattern used to store huge amounts
		    of Files without requiring extraordinate amounts of memory."""
		# Get the physical path to the file in the pool.
		hex = binascii.hexlify(md5)
		pool_path = os.path.join(pool_dir, hex[:2], hex[2:]) + '.gz'

		# pool_path identifies the pool file, but name may differ per package.
		key = (pool_path, name)

		# If we got it already, return flyweight File object.
		if key in File.__files:
			f = File.__files[key]
			assert (f.pool_path == pool_path)
			assert (f.name == name)
			assert (f.md5 == md5)
			assert (f.crc32 == crc32)
			assert (f.size == size)
			return f

		# Use a local variable to ensure a strong ref exists until return!
		f = object.__new__(cls)
		f.pool_path = pool_path
		f.name = name
		f.md5 = md5
		f.crc32 = crc32
		f.size = size
		File.__files[key] = f
		return f

	@property
	def available(self):
		""" Return true iff the file is available locally."""
		return os.path.exists(self.pool_path)
