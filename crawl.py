import urllib2
from lxml import html
from lxml import etree
import re
import pickle

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
# Inherited Class variables
# Inherited Class Functions

## enums sections
# Values

URL_RUNTIME_CLASSES = 'http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.html'
URL_RUNTIME_ATTRIBUTES = 'http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Attributes.html'
URL_RUNTIME_ENUMERATIONS = 'http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Enumerations.html'
URL_EDITOR_CLASSES = 'http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Editor_Classes.html'
URL_EDITOR_ATTRIBUTES = 'http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Editor_Attributes.html'
URL_EDITOR_ENUMERATIONS = 'http://docs.unity3d.com/Documentation/ScriptReference/20_class_hierarchy.Editor_Enumerations.html'

BASE_URL = 'http://docs.unity3d.com/Documentation/ScriptReference/'

OUTPUT_FILENAME = 'unity.pkl'

def getPage(url, timeout=5, retries=10):
	for _i in xrange(retries):
		try:
			return urllib2.urlopen(url, timeout=timeout).read()
		except urllib2.URLError, e:
			pass # retry
	raise e

def readTopList(url):
	page = html.fromstring(getPage(url))
	classes = {}
	for link in page.xpath('//a[@class="classlink"]'):
		className = link.text.strip()
		classUrl = link.get('href')
		classes[className] = readClass(BASE_URL + classUrl, className)
	return classes

def readClass(url, name):
	print 'class: ' + name
	page = html.fromstring(urllib2.urlopen(url).read())
	members = {}
	for sect in page.xpath('//div[@class="script-section-softheading"]'):
		sectName = sect.text.strip()
		members.update(readClassSection(sect, sectName))
	return members

def readClassSection(node, name):
	print '  section: ' + name
	if name.startswith('Inherited '):
		print '    skipped (inherited)'
		return {}
	members = {}
	for link in node.xpath('./following-sibling::table[position()=1]//td[@class="class-member-list-name"]/a'):
		funcName = link.text.strip()
		funcName = funcName.replace('operator ', '')
		funcUrl = link.get('href')
		if name in ['Variables', 'Class Variables', 'Values']:
			members[funcName] = None
		else:
			members[funcName] = readFunction(BASE_URL + funcUrl, funcName)
	return members

def readFunction(url, name):
	print '    function: ' + name
	page = html.fromstring(urllib2.urlopen(url).read())
	funcDefs = []
	for node in page.xpath('//div[@class="manual-entry"]/h3[position()=1]'):
		text = node.text_content().strip()
		print '      def: ' + text
		m = re.search(r'%s(\.<\S+>)?\s+\(\s*([^)]*)\s*\)\s*:\s*(\S+)' % re.escape(name), text)
		if not m:
			raise Exception('Could not parse function definition: ' + text)
		template = m.group(1)
		params = re.split(r'\s*,\s*', m.group(2))
		if params == ['']: params = []
		# params = [parseParam(x) for x in params]
		params = map(parseParam, params)
		returnType = m.group(3)
		funcDef = {
			'template': template,
			'params': params,
			'returnType': returnType
		}
		print '      template: ' + str(template)
		print '      params: ' + str(params)
		print '      returnType: ' + returnType
		print '      funcDef: ' + str(funcDef)
		funcDefs.append(funcDef)
	return funcDefs

def parseParam(param):
	name, type_ = re.split(r'\s*:\s*', param)
	typeParts = re.split(r'\s*=\s*', type_)
	if len(typeParts) == 2:
		type_, default = typeParts
	else:
		default = None
	return (name, type_, default)


data = {}
data['Runtime Classes'] = readTopList(URL_RUNTIME_CLASSES)
data['Runtime Attributes'] = readTopList(URL_RUNTIME_ATTRIBUTES)
data['Runtime Enumerations'] = readTopList(URL_RUNTIME_ENUMERATIONS)
data['Editor Classes'] = readTopList(URL_EDITOR_CLASSES)
data['Editor Attributes'] = readTopList(URL_EDITOR_ATTRIBUTES)
data['Editor Enumerations'] = readTopList(URL_EDITOR_ENUMERATIONS)

pickle.dump(data, open(OUTPUT_FILENAME, 'wb'), pickle.HIGHEST_PROTOCOL)
