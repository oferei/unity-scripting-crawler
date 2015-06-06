#!/usr/bin/python
import os
from lxml import html
# from lxml import etree
import re
import json
from itertools import izip
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
			members.update(self.readClassSubSection(classLink.name, sect))
			for subSect in self.iterSections(sect.elem):
				logger.info('    subsection: {}'.format(subSect.name))
				members.update(self.readClassSubSection(classLink.name, subSect))
		return members

	def readClassSubSection(self, className, subSect):
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
				members[funcName] = self.readFunction(funcUrl, className, funcName)
			else:
				raise Exception('Unknown section: {}'.format(subSect.name))
		return members

	def readFunction(self, url, className, funcName):
		logger.info('      function: ' + funcName)
		funcDefs = []
		for funcDef, funcParamNames in self.iterFuncDefs(url, funcName):
			# fixFuncDef works around bugs in documentation
			funcDef = self.fixFuncDef(funcDef, url, className, funcName)
			try:
				parsedFuncDef = self.parseFuncDef(funcDef, funcName)
				if parsedFuncDef['params'] and parsedFuncDef['params'][0]['name'] is None:
					if funcParamNames and len(parsedFuncDef['params']) == len(funcParamNames):
						for param, paramName in izip(parsedFuncDef['params'], funcParamNames):
							param['name'] = paramName
					else:
						logger.warn('Mismatch between function definition and length of parameters section: #params={} funcParamNames={}'.format(len(parsedFuncDef['params']), funcParamNames))
				funcDefs.append(parsedFuncDef)
			except Exception, e:
				logger.error('Could not parse function definition: {} error={}'.format(funcDef, e))
		return funcDefs

	def iterFuncDefs(self, url, funcName):
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
				topSect = self.getFuncDefSect(node)
				funcParamNames = self.getParamNames(topSect, funcName)
				yield funcDef, funcParamNames
		if not defFound:
			for node in page.xpath('//h1'):
				funcDef = node.text_content().strip().replace('\r\n', '').replace('\n', '')
				if funcDef:
					topSect = self.getHeaderSect(node)
					funcParamNames = self.getParamNames(topSect, funcName)
					yield self.convertHeaderToFuncDef(funcDef), funcParamNames

	@classmethod
	def isFunctionGeneric(cls, funcDefNode):
		descriptionNode = funcDefNode.xpath('./parent::div/parent::div[@class="subsection"]/following-sibling::div[@class="subsection"]/h2[text()="Description"]')
		if descriptionNode:
			description = descriptionNode[0].xpath('./following-sibling::p')[0].text
			return description and description.startswith('Generic version.')
		else:
			return False

	@classmethod
	def getFuncDefSect(cls, funcDefNode):
		funcDefSect = funcDefNode.xpath('./parent::div/parent::div[@class="subsection"]')[0]
		return funcDefSect

	@classmethod
	def getHeaderSect(cls, pageTitleNode):
		headerSect = pageTitleNode.xpath('./parent::div[contains(@class, "mb20")]')[0]
		return headerSect

	@classmethod
	def getParamNames(cls, topSect, funcName):
		try:
			paramsTitleNode = topSect.xpath('./following-sibling::div[@class="subsection"]/h2[text()="Parameters"]')
			paramNames = cls.parseParametersSection(paramsTitleNode)
			if paramNames:
				return paramNames

			exampleNode = topSect.xpath('./following-sibling::div[@class="subsection"]/pre[@class="codeExampleJS" or @class="codeExampleRaw"]')
			paramNames = cls.getFunctionParamNamesFromExample(exampleNode, funcName)
			return paramNames
		except Exception, e:
			logger.warn('Could not find function parameter names: {} error={}'.format(funcName, e))
			return None

	@classmethod
	def parseParametersSection(cls, paramsTitleNode):
		if paramsTitleNode:
			paramNames = paramsTitleNode[0].xpath('./following-sibling::table')[0].xpath('.//td[@class="name lbl"]/text()')
			return paramNames
		else:
			return None

	@classmethod
	def getFunctionParamNamesFromExample(cls, exampleNode, funcName):
		if exampleNode:
			example = exampleNode[0].text_content().strip().replace('\r\n', '').replace('\n', '')
			m = re.search(r'\b(%s\s*\(.+?)\s*\{' % re.escape(funcName), example)
			if not m:
				logger.debug('Function definition not found in example: ' + funcName)
				return None
			funcDef = m.group(1)
			parsedFuncDef = cls.parseFuncDef(funcDef, funcName)
			return [param['name'] for param in parsedFuncDef['params']]
		else:
			return None

	@classmethod
	def convertHeaderToFuncDef(cls, funcDef):
		if '(' not in funcDef:
			funcDef += '()'
		if '.' in funcDef:
			funcDef = re.sub(r'.+\.', '', funcDef)
		return funcDef

	@classmethod
	def fixFuncDef(cls, funcDef, url, className, funcName):
		if className == 'Vector4' and funcName == 'Vector2':
			return 'Vector2()'
		if className == 'Array' and funcName == 'Unshift':
			return 'Unshift()'
		if className == 'Font' and funcName == 'Font' and url == 'Font.TextureChangedDelegate.html':
			return 'Font()'
		if className == 'StateMachineBehaviour':
			if funcName == 'OnStateEnter':
				return 'StateMachineBehaviour.OnStateEnter(animator: Animator, animatorStateInfo: AnimatorStateInfo, layerIndex: int)'
			if funcName == 'OnStateExit':
				return 'StateMachineBehaviour.OnStateExit(animator: Animator, animatorStateInfo: AnimatorStateInfo, layerIndex: int)'
			if funcName == 'OnStateIK':
				return 'StateMachineBehaviour.OnStateIK(animator: Animator, animatorStateInfo: AnimatorStateInfo, layerIndex: int)'
			if funcName == 'OnStateMove':
				return 'StateMachineBehaviour.OnStateMove(animator: Animator, animatorStateInfo: AnimatorStateInfo, layerIndex: int)'
			if funcName == 'OnStateUpdate':
				return 'StateMachineBehaviour.OnStateUpdate(animator: Animator, animatorStateInfo: AnimatorStateInfo, layerIndex: int)'
		if className == 'AssetPostprocessor' and funcName == 'OnPreprocessAnimation':
			return 'OnPreprocessAnimation()'
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
