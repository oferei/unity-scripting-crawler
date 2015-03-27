#!/usr/bin/python
import os
from lxml import html
# from lxml import etree
import re
import json
import pickle

OUTPUT_FILENAME = 'unity.pkl'
LOG_FILENAME = 'crawl.log'
EXCLUDE_INHERITED = True

BASE_DIR = '/Applications/Unity/Documentation/en'

OUTPUT_SECTIONS = set(('Runtime Classes', 'Runtime Interfaces', 'Runtime Enumerations', 'Runtime Attributes', 'Editor Classes', 'Editor Interfaces', 'Editor Enumerations', 'Editor Attributes', 'Other Classes'))

VARIABLES_SECTIONS = set(['Variables', 'Static Variables'])
MESSAGES_SECTIONS = set(['Messages', 'Delegates'])
FUNCTIONS_SECTIONS = set(['Constructors', 'Public Functions', 'Static Functions', 'Protected Functions', 'Operators'])

with open(LOG_FILENAME, 'w'): pass
import logging
# create logger
logger = logging.getLogger('unity_crawl_application')
logger.setLevel(logging.DEBUG)
# create file handler
fh = logging.FileHandler(LOG_FILENAME)
fh.setLevel(logging.DEBUG)
# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

### Class sections:
# Variables
# Static Variables
# Constructors
# Functions
# Static Functions
# Operators
# Messages
# Class Variables
# Class Functions
## Inherited members
# Variables
# Static Variables
# Constructors
# Functions
# Static Functions
# Operators
# Messages
# Class Variables
# Class Functions

### Attribute sections
# Constructors

### Enumeration sections
# Values


class ScriptReferenceReader(object):

	CLASS_LIST_JS_FILE = 'ScriptReference/docdata/toc.js'
	REFERENCE_DIR = 'ScriptReference'

	BUG_WORKAROUNDS = {
		'Media.MediaState': 'WindowsPhone.Media.MediaState',
		'Packer.Execution': 'Sprites.Packer.Execution',
		'Asset.States': 'VersionControl.Asset.States',
		'Message.Severity': 'VersionControl.Message.Severity'
	}

	class ClassLink:
		def __init__(self, name, category, link, namespace):
			# logger.debug('toc-link: name={} category={} link={} namespace={}'.format(name, category, link, namespace))
			self.name = name
			self.category = category
			self.link = link
			self.namespace = namespace

		@property
		def sectionName(self):
			logger.debug('class info: namespace={} category={}'.format(self.namespace, self.category))
			if self.namespace.startswith('UnityEngine'):
				namespace = 'Runtime'
			elif self.namespace.startswith('UnityEditor'):
				namespace = 'Editor'
			elif self.namespace == 'Other':
				namespace = 'Other'
			else:
				raise Exception('Unknown namespace: {}'.format(self.namespace))
			sectionName = namespace + ' ' + self.category
			logger.debug('sectionName: {}'.format(sectionName))

			if sectionName not in OUTPUT_SECTIONS:
				raise Exception('Insanity detected, unexpected section name: {}'.format(sectionName))

			return sectionName

	def __init__(self, baseDir):
		self.baseDir = baseDir
		self.classLinks = None
		self.classDataBySection = None
		self.classListFile = os.path.join(self.baseDir, self.CLASS_LIST_JS_FILE)
		self.refDir = os.path.join(self.baseDir, self.REFERENCE_DIR)

	def read(self):
		self.readClassList()
		self.readAllPages()

	def readClassList(self):
		self.classLinks = []
		self.classDataBySection = dict([(sectionName, {}) for sectionName in OUTPUT_SECTIONS])
		classList = self.readClassListJson()
		self.traverseClassList(classList)
		logger.info('# classes={}'.format(len(self.classLinks)))

	def readClassListJson(self):
		classListJs = open(self.classListFile, 'r').read()
		# remove bit of javascript code
		classListJson = classListJs.replace('var toc = ', '')
		return json.loads(classListJson)

	def traverseClassList(self, obj, hierarchy=[]):
		# logger.debug('traverse: link={} title={} children={} hierarchy={}'.format(obj['link'], obj['title'], 'yes' if obj['children'] else 'no', hierarchy))
		if obj['link'] != 'null' and obj['link'] != 'toc':
			if obj['link'] in self.BUG_WORKAROUNDS:
				link = self.BUG_WORKAROUNDS[obj['link']]
			else:
				link = obj['link']
			self.classLinks.append(self.ClassLink(name=obj['title'], category=hierarchy[-1], link=link, namespace=hierarchy[-2]))
		if obj['children']:
			hierarchy.append(obj['title'])
			for child in obj['children']:
				self.traverseClassList(child, hierarchy)
			hierarchy.pop()

	def readAllPages(self):
		for classLink in self.classLinks:
			classData = self.readClass(classLink)
			self.classDataBySection[classLink.sectionName][classLink.name] = classData

	@classmethod
	def iterSections(cls, elem):
		class Section:
			def __init__(self, name, elem, table):
				self.name = name
				self.elem = elem
				self.table = table

		for div in elem.xpath('./div[@class="subsection"]'):
			titleElement = div.xpath('./h2')
			title = titleElement[0].text.strip() if titleElement else None
			tableElement = div.xpath('./table[@class="list"]')
			table = tableElement[0] if tableElement else None
			yield Section(name=title, elem=div, table=table)

	def readClass(self, classLink):
		logger.info('class: ' + classLink.name)
		pageFilename = os.path.join(self.refDir, classLink.link) + '.html'
		pageText = open(pageFilename, 'r').read()
		page = html.fromstring(pageText)
		members = {}
		sectName = ''
		content = page.xpath('.//div[@class="content"]/div[@class="section"]')[0]
		for sect in self.iterSections(content):
			logger.info('  section: {}'.format(sect.name or '-'))
			if EXCLUDE_INHERITED:
				if sect.name == 'Inherited members':
					logger.info('    skipped (inherited)')
					continue
			members.update(self.readClassSubSection(sect))
			for subSect in self.iterSections(sect.elem):
				logger.info('    subsection: {}'.format(subSect.name))
				members.update(self.readClassSubSection(subSect))
		return members

	def readClassSubSection(self, subSect):
		if subSect.table is None:
			return {}

		members = {}
		for link in subSect.table.xpath('.//td[@class="lbl"]/a'):
			funcName = link.text.strip()
			if funcName.startswith('operator '):
				continue
			funcUrl = link.get('href')
			if subSect.name in VARIABLES_SECTIONS:
				logger.info('      member: ' + funcName)
				# TODO: handle e.g. "this[string]" (Animation page)
				members[funcName] = None
			elif subSect.name in FUNCTIONS_SECTIONS or subSect.name in MESSAGES_SECTIONS:
				members[funcName] = self.readFunction(funcUrl, funcName)
			else:
				raise Exception('Unknown section: {}'.format(subSect.name))
		return members

	def readFunction(self, url, funcName):
		logger.info('      function: ' + funcName)
		funcDefs = []
		for funcDef in self.iterFuncDefs(url):
			# fixFuncDef works around bugs in documentation
			funcDef = self.fixFuncDef(funcDef, url, funcName)
			try:
				funcDefs.append(self.parseFuncDef(funcDef, funcName))
			except Exception, e:
				logger.error('Could not parse function definition: {} error={}'.format(funcDef, e))
		return funcDefs

	def iterFuncDefs(self, url):
		pageFilename = os.path.join(self.refDir, url)
		pageText = open(pageFilename, 'r').read()
		page = html.fromstring(pageText)
		defFound = False
		for node in page.xpath('//div[@class="signature-JS sig-block"]'):
			funcDef = node.text_content().strip().replace('\r\n', '').replace('\n', '')
			if funcDef:
				defFound = True
				if self.isFunctionGeneric(node):
					funcDef = funcDef.replace('(', '.<T>(', 1)
				yield funcDef
		if not defFound:
			for node in page.xpath('//h1'):
				funcDef = node.text_content().strip().replace('\r\n', '').replace('\n', '')
				if funcDef:
					yield self.convertHeaderToFuncDef(funcDef)

	@classmethod
	def isFunctionGeneric(cls, funcDefNode):
		descriptionNode = funcDefNode.xpath('./parent::div/parent::div[@class="subsection"]/following-sibling::div[@class="subsection"]/h2[text()="Description"]')
		if descriptionNode:
			description = descriptionNode[0].xpath('./following-sibling::p')[0].text
			return description and description.startswith('Generic version.')
		else:
			return False

	@classmethod
	def convertHeaderToFuncDef(cls, funcDef):
		if '(' not in funcDef:
			funcDef += '()'
		if '.' in funcDef:
			funcDef = re.sub(r'.+\.', '', funcDef)
		return funcDef

	@classmethod
	def fixFuncDef(cls, funcDef, url, funcName):
		if funcName == 'Vector3' and url == 'Vector4-operator_Vector4.html':
			return 'Vector3()'
		if funcName == 'Unshift' and url == 'Array.Unshift.html':
			return 'Unshift()'
		return funcDef

	@classmethod
	def parseFuncDef(cls, funcDef, funcName):
		logger.debug('        def: ' + funcDef)
		#              name .<temp>?    (   params     )   : returnType
		m = re.search(r'%s(\.<\S+>)?\s*\(\s*([^)]*)\s*\)\s*:?\s*(\S+)?' % re.escape(funcName), funcDef)
		if not m:
			raise Exception('Function definition structure does not match: ' + funcDef)
		template = m.group(1)
		# split by commas but ignore: "[,,,,]"
		# allow commas inside <> and inside []
		params = re.findall(r'[^,<\[]+(?:\<[^>]*\>)?(?:\[[^\]]*\])?[^,]*', m.group(2))
		if params == ['']: params = []
		params = map(str.strip, params)
		params = map(cls.parseParam, params)
		returnType = m.group(3)
		logger.info('           template: ' + str(template))
		logger.info('           params: ' + str(params))
		logger.info('           returnType: ' + str(returnType))
		return {
			'template': template,
			'params': params,
			'returnType': returnType
		}

	@classmethod
	def parseParam(cls, param):
		try:
			paramName, type_ = re.split(r'\s*:\s*', param)
		except Exception, e:
			m = re.search(r'^([\w\[\]]+)$', param)
			if m: # parameter type without name
				paramName = None
				type_ = m.group(1)
			else:
				raise Exception('Could not parse function param: ' + param)
		typeParts = re.split(r'\s*=\s*', type_)
		if len(typeParts) == 2:
			type_, default = typeParts
		else:
			default = None
		return {
			'name': paramName,
			'type': type_,
			'default': default
		}

	def save(self, filename):
		pickle.dump(self.classDataBySection, open(filename, 'wb'), pickle.HIGHEST_PROTOCOL)		

reader = ScriptReferenceReader(baseDir=BASE_DIR)
reader.read()
reader.save(OUTPUT_FILENAME)
