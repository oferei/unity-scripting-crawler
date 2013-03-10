DEFAULT_DIRNAME = 'webcache'
DEFAULT_BASE_TIMEOUT = 5
DEFAULT_TIMEOUT_FACTOR = 2
DEFAULT_NUM_RETRIES = 10

import os
import re
import string
import urllib2
import socket

class WebGetter(object):
	def __init__(self, enableCache=True, dirname=DEFAULT_DIRNAME,
				baseTimeout=DEFAULT_BASE_TIMEOUT, timeoutFactor=DEFAULT_TIMEOUT_FACTOR, numRetries=DEFAULT_NUM_RETRIES):
		self.enableCache = enableCache
		self.dirname = dirname
		self.baseTimeout = baseTimeout
		self.timeoutFactor = timeoutFactor
		self.numRetries = numRetries

		if self.enableCache:
			self.createCacheDir()

	def createCacheDir(self):
		if not os.path.isdir(self.dirname):
			os.makedirs(self.dirname)

	def getUrl(self, url):
		if self.enableCache:
			data = self.readCache(url)
			if data:
				return data
		timeout = self.baseTimeout
		for _i in xrange(self.numRetries):
			try:
				data = urllib2.urlopen(url, timeout=timeout).read()
				if self.enableCache:
					self.writeCache(url, data)
				return data
			except (urllib2.URLError, socket.timeout), e:
				# retry
				timeout *= self.timeoutFactor
		raise e

	def getCacheFilename(self, url):
		return os.path.join(self.dirname, self.slugify(url))

	def readCache(self, url):
		filename = self.getCacheFilename(url)
		if not os.path.isfile(filename):
			return None
		return open(filename, 'rb').read()

	def writeCache(self, url, data):
		filename = self.getCacheFilename(url)
		return open(filename, 'wb').write(data)

	VALID_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)

	@classmethod
	def slugify(cls, value):
		return re.sub('[^%s]' % cls.VALID_CHARS, '-', value)
		
