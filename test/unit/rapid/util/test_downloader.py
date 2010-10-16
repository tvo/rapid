# Copyright (C) 2010 Tobi Vollebregt

import unittest
import os, shutil
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from rapid.util.downloader import Downloader, MockDownloader


class MockHTTPRequestHandler(BaseHTTPRequestHandler):
	def log_request(self, code, size = None):
		pass

	def do_GET(self):
		'''handle GET request'''
		self.server.request_count += 1
		etag = self.headers.getheader('If-None-Match')
		date = self.headers.getheader('If-Modified-Since')
		if etag == 'hi' and date == 'now':
			self.send_response(304)
		else:
			self.send_response(200)
			self.send_header('Etag', 'hi')
			self.send_header('Last-Modified', 'now')
			self.end_headers()
			self.wfile.write('Hello world')

	def do_POST(self):
		'''handle POST request by echoing it'''
		self.server.request_count += 1
		length = int(self.headers.getheader('Content-Length', 0))
		self.send_response(200)
		self.send_header('Content-Length', length)
		self.end_headers()
		self.wfile.write(self.rfile.read(length))


class MockHTTPServerThread(Thread, HTTPServer):
	port = 8000

	def __init__(self):
		Thread.__init__(self)
		MockHTTPServerThread.port += 1
		HTTPServer.__init__(self, ('', self.port), MockHTTPRequestHandler)
		# Thread
		self.daemon = True
		# HTTPServer
		self.timeout = 0.5
		# self
		self.keep_going = True
		self.request_count = 0
		self.start()

	def run(self):
		while self.keep_going:
			self.handle_request()

	def shutdown(self):
		self.keep_going = False


class TestDownloaderCore(object):
	test_dir = '.test-downloader'
	test_file = os.path.join(test_dir, 'hello')
	config_file = os.path.join(test_dir, 'test.cfg')

	def setUp(self, downloader):
		if os.path.exists(self.test_dir):
			shutil.rmtree(self.test_dir)
		os.mkdir(self.test_dir)
		self.downloader = downloader

	def tearDown(self):
		shutil.rmtree(self.test_dir)

	def test_onetime_get_request(self):
		self.downloader.onetime_get_request(self.url, self.test_file)
		self.downloader.onetime_get_request(self.url, self.test_file)
		self.assertTrue(os.path.exists(self.test_file),
			'downloaded file should exist')
		self.assertEqual('Hello world', file(self.test_file).read(),
			'downloaded file should have expected contents')
		self.assertEqual(1, self.get_request_count(),
			'exactly one HTTP request should have been made')

	def test_http_304_not_modified(self):
		self.downloader.conditional_get_request(self.url, self.test_file)
		self.assertFalse(self.downloader._304,
			'first request should be 200 OK')
		self.downloader.conditional_get_request(self.url, self.test_file)
		self.assertTrue(self.downloader._304,
			'second request should be 304 Not Modified')
		self.assertEqual(2, self.get_request_count(),
			'exactly two HTTP requests should have been made')

	def test_post(self):
		remote = self.downloader.post(self.url + 'POST', 'payload')
		self.assertEqual('payload', remote.read())


class TestDownloader(unittest.TestCase, TestDownloaderCore):
	'''test the Downloader class against the MockHTTPServerThread'''

	def setUp(self):
		TestDownloaderCore.setUp(self, Downloader(TestDownloader.config_file))
		self.httpd = MockHTTPServerThread()
		self.url = 'http://localhost:%d/' % self.httpd.port

	def tearDown(self):
		self.httpd.shutdown()
		TestDownloaderCore.tearDown(self)

	def get_request_count(self):
		return self.httpd.request_count


class TestMockDownloader(unittest.TestCase, TestDownloaderCore):
	'''test the MockDownloader'''

	def setUp(self):
		self.url = '/'
		TestDownloaderCore.setUp(self, MockDownloader({
			'/': 'Hello world',
			'/POST': 'payload'
		}))

	def get_request_count(self):
		return self.downloader.request_count

	def test_init(self):
		MockDownloader()   # test __init__ without arguments


if __name__ == '__main__':
	unittest.main()
