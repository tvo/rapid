#!/usr/bin/env python
# Copyright (C) 2010 Tobi Vollebregt

from contextlib import closing
import ConfigParser
import os
import time
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
	def __init__(self, config_filename):
		#print ('reading configuration from ' + config_filename)
		self.__config = ConfigParser.RawConfigParser()
		self._304 = False    # for unit tests
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

	def conditional_get_request(self, url, filename, rate_limit = None):
		section = url + ',' + filename
		etag = self.__config_get(section, 'etag')
		last_modified = self.__config_get(section, 'last_modified')
		last_requested = self.__config_get(section, 'last_requested')

		# rate limiting
		if (rate_limit and last_requested and
			time.time() - float(last_requested) <= rate_limit and
			os.path.exists(filename)):
			return

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
				self.__config_set(section, 'last_requested', time.time())
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
	def __init__(self, www = None):
		self.www = www or {}
		self.last_visited = {}
		self.request_count = 0
		self._304 = False

	def onetime_get_request(self, url, filename):
		if os.path.exists(filename):
			return

		self.request_count += 1
		atomic_write(filename, self.www[url])

	def conditional_get_request(self, url, filename, rate_limit = None):
		if (rate_limit and url in self.last_visited and
			time.time() - self.last_visited[url] <= rate_limit and
			os.path.exists(filename)):
			return

		self.request_count += 1

		if url in self.last_visited:
			self._304 = True
			return

		atomic_write(filename, self.www[url])
		self.last_visited[url] = time.time()

	def post(self, url, data):
		def info():
			return {'Content-Length': len(self.www[url])}
		remote = StringIO(self.www[url])
		remote.info = info
		return remote
