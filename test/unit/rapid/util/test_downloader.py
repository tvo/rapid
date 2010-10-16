# Copyright (C) 2010 Tobi Vollebregt

import unittest
import os, shutil
from rapid.util.downloader import Downloader, MockDownloader

class TestDownloader(unittest.TestCase):
	test_dir = '.test-downloader'
	url = 'http://repos.caspring.org/repos.gz'
	test_file = os.path.join(test_dir, 'repos.gz')
	config_file = os.path.join(test_dir, 'test.cfg')

	def setUp(self, factory = lambda: Downloader(TestDownloader.config_file)):
		os.mkdir(self.test_dir)
		self.downloader = factory()

	def tearDown(self):
		shutil.rmtree(self.test_dir)

	def test_onetime_get_request(self):
		self.downloader.onetime_get_request(self.url, self.test_file)

	def test_http_304_not_modified(self):
		self.downloader.conditional_get_request(self.url, self.test_file)
		self.assertFalse(self.downloader._304)
		self.downloader.conditional_get_request(self.url, self.test_file)
		self.assertTrue(self.downloader._304)

	def test_post(self):
		#TODO: implement test_post
		pass

class TestMockDownloader(TestDownloader):
	def setUp(self):
		TestDownloader.setUp(self, lambda: MockDownloader({self.url: ''}))

	def test_init(self):
		MockDownloader()   # test __init__ without arguments

if __name__ == '__main__':
	unittest.main()
