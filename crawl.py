from lxml import html
from lxml import etree
import re
import pickle

from web_getter import WebGetter

OUTPUT_FILENAME = 'unity.pkl'
LOG_FILENAME = 'crawl.log'
ENABLE_WEB_CACHE = True
EXCLUDE_INHERITED = True
EXCLUDE_INHERITED_STATIC = True

CLASS_RUNTIME_CLASSES = 'classRuntime'
CLASS_RUNTIME_ATTRIBUTES = 'attrRuntime'
CLASS_RUNTIME_ENUMERATIONS = 'enumRuntime'
CLASS_EDITOR_CLASSES = 'classEditor'
CLASS_EDITOR_ATTRIBUTES = 'attrEditor'
CLASS_EDITOR_ENUMERATIONS = 'enumEditor'

BASE_URL = 'http://docs.unity3d.com/Documentation/ScriptReference/'



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

webGetter = WebGetter(enableCache=ENABLE_WEB_CACHE)

### Class sections:
# Variables
# Constructors
# Functions
# Messages Sent
# Class Variables
# Class Functions
## Inherited members
# Inherited Variables
# Inherited Constructors
# Inherited Functions
# Inherited Messages Sent
# Inherited Class Variables
# Inherited Class Functions

### Attribute sections
# Constructors

### Enumeration sections
# Values

def getPage(url):
	return webGetter.getUrl(url)

def readTopList(domClass):
	page = html.fromstring(getPage(BASE_URL))
	classes = {}
	for link in page.xpath('//li[@class="' + domClass + '"]/a'):
		className = link.text.strip()
		classUrl = link.get('href')
		classes[className] = readClass(BASE_URL + classUrl, className)
	return classes

def readClass(url, name):
	logger.info('class: ' + name)
	page = html.fromstring(getPage(url))
	members = {}
	for sect in page.xpath('//div[@class="script-section-softheading"]'):
		sectName = sect.text.strip()
		members.update(readClassSection(sect, sectName))
	return members

def readClassSection(node, name):
	logger.info('  section: ' + name)
	if EXCLUDE_INHERITED and name.startswith('Inherited '):
		logger.info('    skipped (inherited)')
		return {}
	if EXCLUDE_INHERITED_STATIC and name.startswith('Inherited Class '):
		logger.info('    skipped (inherited static)')
		return {}
	members = {}
	for link in node.xpath('./following-sibling::table[position()=1]//td[@class="class-member-list-name"]/a'):
		funcName = link.text.strip()
		if funcName.startswith('operator '):
			continue
		funcUrl = link.get('href')
		if name in ['Variables', 'Class Variables', 'Inherited Variables', 'Inherited Class Variables', 'Values']:
			members[funcName] = None
		else:
			members[funcName] = readFunction(BASE_URL + funcUrl, funcName)
	return members

def readFunction(url, name):
	logger.info('    function: ' + name)
	page = html.fromstring(getPage(url))
	funcDefs = []
	for node in page.xpath('//div[@class="manual-entry"]/h3[position()=1]'):
		funcDefs.append(parseFuncDef(node.text_content().strip(), name))
	return funcDefs

def parseFuncDef(paramDef, name):
	logger.debug('      def: ' + paramDef)
	try:
		m = re.search(r'%s(\.<\S+>)?\s+\(\s*([^)]*)\s*\)\s*:\s*(\S+)' % re.escape(name), paramDef)
		if not m:
			raise Exception('Could not parse function definition: ' + paramDef)
		template = m.group(1)
		params = m.group(2).split(', ')
		if params == ['']: params = []
		params = map(parseParam, params)
		returnType = m.group(3)
		logger.info('      template: ' + str(template))
		logger.info('      params: ' + str(params))
		logger.info('      returnType: ' + returnType)
		return {
			'template': template,
			'params': params,
			'returnType': returnType
		}
	except Exception, e:
		logger.error('Could not parse function definition: ' + paramDef + ' (' + str(e) + ')')

def parseParam(param):
	name, type_ = re.split(r'\s*:\s*', param)
	typeParts = re.split(r'\s*=\s*', type_)
	if len(typeParts) == 2:
		type_, default = typeParts
	else:
		default = None
	return {
		'name': name,
		'type': type_,
		'default': default
	}


data = {}
data['Runtime Classes'] = readTopList(CLASS_RUNTIME_CLASSES)
data['Runtime Attributes'] = readTopList(CLASS_RUNTIME_ATTRIBUTES)
data['Runtime Enumerations'] = readTopList(CLASS_RUNTIME_ENUMERATIONS)
data['Editor Classes'] = readTopList(CLASS_EDITOR_CLASSES)
data['Editor Attributes'] = readTopList(CLASS_EDITOR_ATTRIBUTES)
data['Editor Enumerations'] = readTopList(CLASS_EDITOR_ENUMERATIONS)

pickle.dump(data, open(OUTPUT_FILENAME, 'wb'), pickle.HIGHEST_PROTOCOL)
