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

VARIABLES_SECTIONS = set(['Properties', 'Static Properties'])
MESSAGES_SECTIONS = set(['Messages', 'Delegates', 'Events'])
FUNCTIONS_SECTIONS = set(['Constructors', 'Public Methods', 'Static Methods', 'Protected Methods', 'Operators'])

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

	CLASS_LIST_JSON_FILE = 'ScriptReference/docdata/toc.json'
	REFERENCE_DIR = 'ScriptReference'

	BUG_WORKAROUNDS = {
		'Media.MediaState': 'WindowsPhone.Media.MediaState',
		'Packer.Execution': 'Sprites.Packer.Execution',
		'Asset.States': 'VersionControl.Asset.States',
		'Message.Severity': 'VersionControl.Message.Severity'
	}

	UNDOCUMENTED = [
		['Runtime Classes', 'GameObject', 'FindGameObjectWithTag', 'public static GameObject[] FindGameObjectWithTag(string tag);']
	]

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
		self.classListFile = os.path.join(self.baseDir, self.CLASS_LIST_JSON_FILE)
		self.refDir = os.path.join(self.baseDir, self.REFERENCE_DIR)

	def read(self):
		self.readClassList()
		self.readAllPages()
		self.addUndocumented()

	def readClassList(self):
		self.classLinks = []
		self.classDataBySection = dict([(sectionName, {}) for sectionName in OUTPUT_SECTIONS])
		classList = self.readClassListJson()
		self.traverseClassList(classList)
		logger.info('# classes={}'.format(len(self.classLinks)))

	def readClassListJson(self):
		classListJson = open(self.classListFile, 'r').read()
		return json.loads(classListJson)

	def traverseClassList(self, obj, hierarchy=[]):
		# logger.debug('traverse: link={} title={} children={} hierarchy={}'.format(obj['link'], obj['title'], 'yes' if obj['children'] else 'no', hierarchy))
		if obj['link'] != 'null' and obj['link'] != 'toc':
			if obj['link'] in self.BUG_WORKAROUNDS:
				link = self.BUG_WORKAROUNDS[obj['link']]
			else:
				link = obj['link']
			self.classLinks.append(self.ClassLink(name=obj['title'], category=hierarchy[-1], link=link, namespace=hierarchy[1]))
		if obj['children']:
			hierarchy.append(obj['title'])
			for child in obj['children']:
				self.traverseClassList(child, hierarchy)
			hierarchy.pop()

	def readAllPages(self):
		for classLink in self.classLinks:
			classData = self.readClass(classLink)
			self.classDataBySection[classLink.sectionName][classLink.name] = classData

	def addUndocumented(self):
		logger.info('Adding undocumented functions')
		for sectionName, className, funcName, funcDef in self.UNDOCUMENTED:
			logger.info('  Adding undocumented function: sectionName={} className={} funcName={}'.format(sectionName, className, funcName))
			if className not in self.classDataBySection[sectionName]:
				logger.warn('Undocumented class does not exist: {}'.format(className))
				self.classDataBySection[sectionName][className] = {}
			if funcName not in self.classDataBySection[sectionName][className]:
				# logger.debug('Undocumented function does not exist: {}.{}'.format(className, funcName))
				self.classDataBySection[sectionName][className][funcName] = []
			parsedFuncDef = self.parseFuncDef(funcDef, funcName)
			self.classDataBySection[sectionName][className][funcName].append(parsedFuncDef)

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
		try:
			pageText = open(pageFilename, 'r').read()
		except Exception, e:
			logger.error('Could not read class: {} error={}'.format(classLink.name, e))
			return {};
		page = html.fromstring(pageText)
		members = {}
		sectName = ''
		content = page.xpath('.//div[@class="content"]/div[@class="section"]')[0]
		for sect in self.iterSections(content):
			logger.info('  section: {}'.format(sect.name or '-'))
			if EXCLUDE_INHERITED:
				if sect.name == 'Inherited Members':
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
			fixedFuncDef = self.fixFuncDef(funcDef, url, className, funcName)
			if fixedFuncDef:
				funcDef = fixedFuncDef
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
		for node in page.xpath('//div[@class="signature-CS sig-block"]'):
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
		elif className == 'Array' and funcName == 'Unshift':
			return 'Unshift()'
		elif className == 'Font' and funcName == 'Font' and url == 'Font.TextureChangedDelegate.html':
			return 'Font()'
		elif className == 'StateMachineBehaviour':
			if funcName == 'OnStateEnter':
				return 'StateMachineBehaviour.OnStateEnter(Animator animator, AnimatorStateInfo animatorStateInfo, int layerIndex)'
			elif funcName == 'OnStateExit':
				return 'StateMachineBehaviour.OnStateExit(Animator animator, AnimatorStateInfo animatorStateInfo, int layerIndex)'
			elif funcName == 'OnStateIK':
				return 'StateMachineBehaviour.OnStateIK(Animator animator, AnimatorStateInfo animatorStateInfo, int layerIndex)'
			elif funcName == 'OnStateMove':
				return 'StateMachineBehaviour.OnStateMove(Animator animator, AnimatorStateInfo animatorStateInfo, int layerIndex)'
			elif funcName == 'OnStateUpdate':
				return 'StateMachineBehaviour.OnStateUpdate(Animator animator, AnimatorStateInfo animatorStateInfo, int layerIndex)'
		elif className == 'AssetPostprocessor' and funcName == 'OnPreprocessAnimation':
			return 'OnPreprocessAnimation()'
		elif className == 'LODGroup' and funcName == 'SetLODs':
			return 'SetLODs(LOD[] lods)'

		# missing parameter names
		elif className == 'AssetPostprocessor' and funcName == 'OnPostprocessAssetbundleNameChanged':
			return 'OnPostprocessAssetbundleNameChanged(string assetPath, stringpreviousAssetBundleName, string newAssetBundleName)'
		elif className == 'AssetPostprocessor' and funcName == 'OnPostprocessAudio':
			return 'OnPostprocessAudio(AudioClip clip)'
		elif className == 'AssetPostprocessor' and funcName == 'OnPostprocessSpeedTree':
			return 'OnPostprocessSpeedTree(GameObject go)'
		elif className == 'AssetPostprocessor' and funcName == 'OnPostprocessTexture':
			return 'OnPostprocessTexture(Texture2D texture)'
		elif className == 'MaterialEditor' and funcName == 'LightmapEmissionProperty':
			return 'LightmapEmissionProperty(int labelIndent)'
		elif className == 'StaticOcclusionCulling' and funcName == 'Compute':
			return 'Compute(float viewCellSize, float nearClipPlane, float farClipPlane, int memoryLimit, StaticOcclusionCullingMode mode)'
		elif className == 'TextureImporter' and funcName == 'ReadTextureImportInstructions':
			return 'ReadTextureImportInstructions(TextureImportInstructions instructions)'
		elif className == 'Array' and funcName == 'Array':
			return 'Array(int arrayLength)'
		elif className == 'AssetModificationProcessor' and funcName == 'IsOpenForEdit':
			return 'IsOpenForEdit(string assetPath, string message)'
		elif className == 'AssetModificationProcessor' and funcName == 'OnWillCreateAsset':
			return 'OnWillCreateAsset(string path)'
		elif className == 'AssetModificationProcessor' and funcName == 'OnWillDeleteAsset':
			return 'AssetDeleteResult OnWillDeleteAsset(string assetPath, RemoveAssetOptions option)'
		elif className == 'AssetModificationProcessor' and funcName == 'OnWillMoveAsset':
			return 'AssetMoveResult OnWillMoveAsset(string oldPath, string newPath)'
		elif className == 'AssetModificationProcessor' and funcName == 'OnWillSaveAssets':
			return 'string[] OnWillSaveAssets(string[] paths)'
		elif className == 'Hashtable':
			if funcName == 'Add':
				return 'Add(object key, object value)'
			elif funcName == 'Contains':
				return 'bool Contains(object key)'
			elif funcName == 'ContainsKey':
				return 'bool ContainsKey(object key)'
			elif funcName == 'ContainsValue':
				return 'bool ContainsValue(object value)'
			elif funcName == 'Remove':
				return 'Remove(object key)'
		elif className == 'Path':
			if funcName == 'Combine':
				return 'string Combine(String path1, string path2)'
			elif funcName == 'GetExtension':
				return 'string GetExtension(string path)'
			elif funcName == 'GetFileName':
				return 'string GetFileName(string path)'
			elif funcName == 'GetFileNameWithoutExtension':
				return 'string GetFileNameWithoutExtension(string path)'
		elif className == 'Collider':
			if funcName == 'OnCollisionEnter':
				return 'OnCollisionEnter(Collision collisionInfo)'
			elif funcName == 'OnTriggerExit':
				return 'OnTriggerExit(Collider other)'
			elif funcName == 'OnTriggerStay':
				return 'OnTriggerStay(Collider other)'
		elif className == 'Collider2D':
			if funcName == 'OnTriggerExit2D':
				return 'OnTriggerExit2D(Collider2D other)'
			elif funcName == 'OnTriggerStay2D':
				return 'OnTriggerStay2D(Collider2D other)'
		elif className == 'MonoBehaviour':
			if funcName == 'OnCollisionEnter':
				return 'OnCollisionEnter(Collision collisionInfo)'
			elif funcName == 'OnTriggerStay2D':
				return 'OnTriggerStay2D(Collider2D other)'

		return None

	@classmethod
	def parseFuncDef(cls, funcDef, funcName):
		logger.debug('        def: ' + funcDef)
		#              name .<temp>?     (   params     )   : returnType
		m = re.search(r'%s(\.?<\S+>)?\s*\(\s*([^)]*)\s*\)\s*:?\s*(\S+)?' % re.escape(funcName), funcDef)
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
		m = re.search(r'^((?:(?:out|ref|params) )?[\w\.,<>\[\]]+)(?:\s+(\w+)(?:\s*=\s*([\w\-\.\"]+))?)?$', param)
		if not m:
			raise Exception('Could not parse function param: ' + param)
		type_ = m.group(1)
		paramName = m.group(2)
		default = m.group(3)
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
