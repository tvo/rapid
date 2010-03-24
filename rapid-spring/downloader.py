#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Tobi Vollebregt

from contextlib import closing
import ConfigParser
import os
import urllib2

################################################################################

timeout = 5     # change timeout here if desired

################################################################################

def atomic_write(filename, data):
	temp = filename + '.tmp'
	with open(temp, 'wb') as f:
		f.write(data)
	if os.path.exists(filename): # on Windows rename doesn't overwrite destination
		os.remove(filename)
	os.rename(temp, filename)


class NotModifiedHandler(urllib2.BaseHandler):

	def http_error_304(self, req, fp, code, message, headers):
		addinfourl = urllib2.addinfourl(fp, headers, req.get_full_url())
		addinfourl.code = code
		return addinfourl

################################################################################

class Downloader:
	__config = ConfigParser.RawConfigParser()
	_304 = False    # for unit tests

	def __init__(self, config_filename):
		#print ('reading configuration from ' + config_filename)
		self.__config_filename = config_filename
		self.__config.read(config_filename)

	def __write_config(self):
		#print ('writing configuration to ' + self.__config_filename)
		with open(self.__config_filename, 'wb') as f:
			self.__config.write(f)

	def __config_get(self, section, option):
		if self.__config.has_option(section, option):
			return self.__config.get(section, option)

	def __config_set(self, section, option, value):
		if value:
			if not self.__config.has_section(section):
				self.__config.add_section(section)
			self.__config.set(section, option, value)

	def onetime_get_request(self, url, filename):
		if os.path.exists(filename):
			return

		request = urllib2.Request(url, unverifiable=True)

		with closing(urllib2.urlopen(request, timeout = timeout)) as remote:
			atomic_write(filename, remote.read())

	def conditional_get_request(self, url, filename):
		section = url + ',' + filename
		etag = self.__config_get(section, 'etag')
		last_modified = self.__config_get(section, 'last_modified')

		request = urllib2.Request(url, unverifiable=True)

		if os.path.exists(filename):
			if etag:
				request.add_header('If-None-Match', etag)
			if last_modified:
				request.add_header('If-Modified-Since', last_modified)

		try:
			with closing(urllib2.build_opener(NotModifiedHandler()).open(request, timeout = timeout)) as remote:
				headers = remote.info()
				self.__config_set(section, 'etag', headers.getheader('ETag'))
				self.__config_set(section, 'last_modified', headers.getheader('Last-Modified'))
				self.__write_config()

				if hasattr(remote, 'code') and remote.code == 304:
					#print 'the file has not been modified'
					self._304 = True
					return

				atomic_write(filename, remote.read())

		except urllib2.URLError:
			if os.path.exists(filename):
				return
			raise

	def post(self, url, data):
		request = urllib2.Request(url, unverifiable=True)
		request.add_data(data)

		return urllib2.urlopen(request)

################################################################################

from StringIO import StringIO

class MockDownloader:
	def __init__(self):
		self.www = {}
		self.visited = set()
		self._304 = False

	def onetime_get_request(self, url, filename):
		atomic_write(filename, self.www[url])

	def conditional_get_request(self, url, filename):
		if url in self.visited:
			self._304 = True
			return

		atomic_write(filename, self.www[url])
		self.visited.add(url)

	def post(self, url, data):
		def info():
			return {'Content-Length': len(self.www[url])}
		remote = StringIO(self.www[url])
		remote.info = info
		return remote

################################################################################

import unittest, shutil

class TestDownloader(unittest.TestCase):
	test_dir = '.test-downloader'
	url = 'http://repos.caspring.org/repos.gz'
	test_file = os.path.join(test_dir, 'repos.gz')
	config_file = os.path.join(test_dir, 'test.cfg')

	def setUp(self):
		os.mkdir(self.test_dir)
		if False:   # change to test (Mock)Downloader
			self.downloader = Downloader(self.config_file)
		else:
			self.downloader = MockDownloader()
			self.downloader.www[self.url] = ''

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

if __name__ == '__main__':
	unittest.main()
