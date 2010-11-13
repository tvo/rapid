# Copyright (C) 2010 Tobi Vollebregt

import binascii
import os
import shutil
import struct
import unittest
import rapid.rapid as rapid
from rapid.rapid import DependencyException, DetachedPackageException, OfflineRepositoryException, \
	PinnedTags, Rapid, mkdir_p, set_spring_dir, gzip_string, master_url
from rapid.util.downloader import MockDownloader


class TestPinnedTags(unittest.TestCase):
	test_dir = os.path.realpath('.test-rapid')

	def setUp(self):
		set_spring_dir(self.test_dir)
		mkdir_p(rapid.content_dir)
		self.pt = PinnedTags()

	def tearDown(self):
		shutil.rmtree(self.test_dir)

	def test_add(self):
		self.pt.add('foo')
		self.assertTrue('foo' in PinnedTags())

	def test_add_duplicate(self):
		self.pt.add('foo')
		self.pt.add('foo')
		self.assertEqual(['foo'], list(PinnedTags()))

	def test_clear(self):
		self.pt.add('foo')
		self.pt.clear()
		self.assertEqual([], list(PinnedTags()))

	def test_remove(self):
		self.pt.add('foo')
		self.pt.remove('foo')
		self.assertFalse('foo' in PinnedTags())

	def test_remove_nonexisting(self):
		self.assertRaises(KeyError, lambda: self.pt.remove('foo'))

	def test_update(self):
		self.pt.update(['foo'])
		self.assertTrue('foo' in PinnedTags())


class TestRapid(unittest.TestCase):
	test_dir = os.path.realpath('.test-rapid')

	def setUp(self):
		set_spring_dir(self.test_dir)

		# Speed up the test because if pool is present the 256 pool
		# directories are created on demand instead of beforehand.
		mkdir_p(rapid.pool_dir)

		if True:   # False to use real Downloader, True to use MockDownloader
			self.downloader = MockDownloader()
			self.rapid = Rapid(self.downloader)
			www = self.downloader.www
			www[master_url] = gzip_string(',http://ts1,,\n')
			# The last two packages have an identical name. This should not
			# actually happen in practice (leaves no good way to normalize
			# versions.gz), though it did happen once. (#9)
			# So it's present here to test that rapid handles it properly.
			www['http://ts1/versions.gz'] = gzip_string('xta:latest,1234,dependency,XTA 9.6\n,5678,,dependency\n,90AB,,dependency\n')
			www['http://ts1/packages/1234.sdp'] = gzip_string('\3foo' + binascii.unhexlify('d41d8cd98f00b204e9800998ecf8427e') + 8 * '\0')
			www['http://ts1/packages/5678.sdp'] = gzip_string('')
			www['http://ts1/packages/90AB.sdp'] = gzip_string('')
			www['http://ts1/streamer.cgi?1234'] = struct.pack('>L', len(gzip_string(''))) + gzip_string('')
		else:
			self.downloader = Downloader()
			self.rapid = Rapid(self.downloader)

	def tearDown(self):
		shutil.rmtree(self.test_dir)

	def test_get_repositories(self):
		self.assertEqual(1, len(self.rapid.repositories))

	def test_get_package_by_name(self):
		self.assertRaises(KeyError, lambda: self.rapid.packages['XXXXXX'])
		self.assertTrue(self.rapid.packages['XTA 9.6'])

	def test_get_package_by_tag(self):
		self.assertRaises(KeyError, lambda: self.rapid.packages['XXXXXX'])
		self.assertTrue(self.rapid.packages['xta:latest'])

	def test_get_packages(self):
		self.assertEqual(2, len(self.rapid.packages))

	def test_get_tags(self):
		self.assertEqual(set(['xta:latest']), self.rapid.tags)

	def install(self, p):
		for d in p.dependencies:
			self.install(d)
		p.install()

	def test_install_uninstall(self):
		p = self.rapid.packages['xta:latest']
		self.install(p)
		self.assertFalse(p.missing_files)
		self.assertTrue(os.path.exists(p.files[0].pool_path))
		self.assertTrue(os.path.exists(os.path.join(rapid.package_dir, '1234.sdp')))
		p.uninstall()
		self.assertFalse(os.path.exists(os.path.join(rapid.package_dir, '1234.sdp')))

	def test_install_missing_dependency(self):
		p = self.rapid.packages['xta:latest']
		self.assertRaises(DependencyException, lambda: p.install())
		self.assertFalse(p.installed)   # install should have failed

	def test_uninstall_dependency_check(self):
		p = self.rapid.packages['xta:latest']
		self.install(p)
		d = self.rapid.packages['dependency']
		self.assertRaises(DependencyException, lambda: d.uninstall())
		self.assertTrue(d.installed)   # uninstall should have failed

	def test_detached_package(self):
		self.rapid.packages.load()
		self.setUp()   # re-initialise
		self.downloader.www['http://ts1/versions.gz'] = gzip_string('')
		p = self.rapid.packages['dependency']
		self.assertFalse(p.repository)
		self.assertFalse(hasattr(p, 'cache_file'))
		self.assertFalse(p.available)
		self.assertFalse(p.installable)
		self.assertRaises(DetachedPackageException, lambda: p.files)
		self.assertRaises(DetachedPackageException, lambda: p.install())

	def test_detached_package_repair(self):
		self.rapid.packages['dependency'].files
		self.setUp()   # re-initialise
		self.downloader.www['http://ts1/versions.gz'] = gzip_string('')
		p = self.rapid.packages['dependency']
		self.assertTrue(p.repository)
		self.assertTrue(hasattr(p, 'cache_file'))
		self.assertTrue(p.available)
		self.assertTrue(p.installable)
		p.files

	def test_disappeared_repo_sdp_cached(self):
		self.rapid.packages['xta:latest'].files
		self.setUp()   # re-initialise
		self.downloader.www[master_url] = gzip_string('')
		p = self.rapid.packages['xta:latest']
		p.files

	def test_disappeared_repo_sdp_not_cached(self):
		self.rapid.packages.load()
		self.setUp()   # re-initialise
		self.downloader.www[master_url] = gzip_string('')
		p = self.rapid.packages['xta:latest']
		self.assertFalse(p.installable)
		self.assertRaises(OfflineRepositoryException, lambda: p.files)

	def test_issue_9_duplicate_package_name(self):
		self.assertEqual('5678', self.rapid.packages['dependency'].hex)

	def test_installable(self):
		p = self.rapid.packages['xta:latest']
		self.assertTrue(p.installable)

	def test_installable_if_installed(self):
		p = self.rapid.packages['dependency']
		p.install()
		self.assertTrue(p.installable)

	def test_installable_all_cached(self):
		p = self.rapid.packages['dependency']
		p.install()
		p.uninstall()
		self.setUp()   # re-initialise
		self.downloader.www[master_url] = gzip_string('')
		p = self.rapid.packages['dependency']
		self.assertTrue(p.installable)


if __name__ == '__main__':
	unittest.main()
