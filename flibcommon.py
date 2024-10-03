# -*- coding: utf-8 -*-
import re, hashlib, zipfile, sys, os, configparser, traceback, platform
import simplejson as json
from collections import namedtuple
from lxml import etree
from flibdefs import *


def ini_path():
	if len(sys.argv) > 1:
		return sys.argv[1]
	return DEFAULT_INI_PATH

def read_config_values(keys, types, errors):
	config_path = ini_path()
	if not os.path.exists(config_path):
		errors.append('Конфигурационный файл (%s) не найден' % config_path)
	try:
		config = configparser.ConfigParser()
		config.read(config_path)
		values = []
		for k, t in zip(keys, types):
			if t == int:
				values.append(config.getint('FLIBCONFIG', k))
			elif t == float:
				values.append(config.getfloat('FLIBCONFIG', k))
			elif t == bool:
				values.append(config.getboolean('FLIBCONFIG', k))
			elif t == str:
				values.append(config.get('FLIBCONFIG', k))
			else:
				values.append(None)
		return values
	except Exception as e:	
		errors.append('Ошибка при чтении конфигурационного файла')
		raise e

def log_filename():
	script_filename = os.path.splitext(os.path.basename(sys.argv[0]))[0].replace('.', '_')
	if ini_path() == DEFAULT_INI_PATH:
		return '%s_errors.log' % (script_filename)
	ini_filename = os.path.splitext(os.path.basename(ini_path()))[0].replace('.', '_')
	return '%s_errors_%s.log' % (script_filename, ini_filename)
	
def namedtuple_from_json(d):
	for t in (Book, Description, Author, Sequence, Directory, Library):
		if set(t._fields) == set(d.keys()):
			return t(*[d[k] for k in t._fields])

def read_dump_compressed(name, errors):
	if not os.path.exists(name):
		errors.append('Дамп-файл отсутствует')
		return None
	generic_dump_error = 'Ошибка при чтении дамп-файла'
	try:
		with zipfile.ZipFile(name, 'r') as zf:
			if 'library.json' not in zf.namelist() or 'version' not in zf.namelist():
				raise Exception()
			with zf.open('library.json') as dumpf:
				library = json.loads(dumpf.read(), object_hook=lambda d: namedtuple_from_json(d))
				if library == None:
					raise Exception()
				with zf.open('version') as versf:
					version = versf.read().decode('utf-8').strip()
					if version != VERSION:
						errors.append('Версия дамп-файла "%s" не поддерживается' % version)
						return None
					return library
	except Exception:
		errors.append(generic_dump_error)
		return None

def write_dump_compressed(name, library):
	print_header('ПОДГОТОВКА ДАМП-ФАЙЛА')
	data = json.dumps(library, ensure_ascii=False, indent=1).encode("utf-8")
	print_header('ЗАПИСЬ ДАМП-ФАЙЛА, НЕ ПРЕРЫВАЙТЕ ПРОГРАММУ')
	with zipfile.ZipFile(name, "w", zipfile.ZIP_DEFLATED) as zf:
		zf.writestr("library.json", data)
		zf.writestr("version", "%s" % VERSION)

def body_hash(tree):
	root = tree.getroot()
	nss = root.nsmap
	bodies = ''
	for b in root.findall("./body", namespaces=nss):
		bodies += etree.tostring(b, encoding='unicode', method='xml')
	m = hashlib.md5()
	m.update(bodies.encode("utf-8"))
	return m.hexdigest()

def estimate_pages(tree):
	text_tags = ['p', 'v', 'subtitle', 'text-author']
	root = tree.getroot()
	nss = root.nsmap
	SYMBOLS_IN_LINE = 65
	LINES_IN_PAGE = 35
	parnum = 0
	elements = []
	for tag in text_tags:
		elements.extend(root.findall('.//%s' % tag, namespaces=nss))
	for element in elements:
		parlen = len(''.join(element.itertext()).strip())
		parnum += -(-parlen // SYMBOLS_IN_LINE)
	return -(-parnum // LINES_IN_PAGE)


def author_from_xml(element, nss):
	element_last = element.findall("./last-name", namespaces=nss)
	element_first = element.findall("./first-name", namespaces=nss)
	element_middle = element.findall("./middle-name", namespaces=nss)
	last = element_last[0].text if len(element_last) == 1 else None
	first = element_first[0].text if len(element_first) == 1 else None
	middle = element_middle[0].text if len(element_middle) == 1 else None
	if first or middle or last:
		return Author(first, middle, last)
	return None

def author_to_xml(tag, author):
	element = etree.Element(tag)
	if author.first:
		tmp = etree.Element("first-name")
		tmp.text = author.first
		element.append(tmp)
	if author.middle:
		tmp = etree.Element("middle-name")
		tmp.text = author.middle
		element.append(tmp)
	if author.last:
		tmp = etree.Element("last-name")
		tmp.text = author.last
		element.append(tmp)
	return element

def replace_elements(parent, element_name, new_elements, nss):
	old_elements = parent.findall(element_name, namespaces=nss)
	for element in old_elements:
		parent.remove(element)
	for element in new_elements:
		parent.append(element)

def read_book_xml(xfo):
	parser = etree.XMLParser(remove_blank_text=True)
	return etree.parse(xfo, parser)

def read_book_zip(fo):
	with zipfile.ZipFile(fo, 'r') as zfo:
		if len(zfo.namelist()) != 1:
			raise Exception()
		fs = zfo.getinfo(zfo.namelist()[0]).file_size
		with zfo.open(zfo.namelist()[0]) as xfo:
			return read_book_xml(xfo), fs

def load_book_info(bookid, tree):
	root = tree.getroot()
	nss = root.nsmap
	format3 = "%s/%s/%s"
	title_list = root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, BOOK_TITLE_TAG), namespaces=nss)
	if len(title_list) == 0:
		return None
	title = title_list[0].text
	
	authors = []
	for a in root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, AUTHOR_TAG), namespaces=nss):
		author = author_from_xml(a, nss)
		if author:
			authors.append(author)
	
	translators = []
	for a in root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, TRANSLATOR_TAG), namespaces=nss):
		author = author_from_xml(a, nss)
		if author:
			translators.append(author)
	
	genres = []
	for g in root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, GENRE_TAG), namespaces=nss):
		genres.append(g.text)
	
	sequences = []
	for s in root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, SEQUENCE_TAG), namespaces=nss):
		if s.get('name'):
			sequences.append(Sequence(s.get('name'), s.get('number')))

	psequences = []
	for s in root.findall(format3 % (DESCRIPTION_PATH, PUBLISH_INFO_TAG, SEQUENCE_TAG), namespaces=nss):
		if s.get('name'):
			psequences.append(Sequence(s.get('name'), s.get('number')))
	
	lang = "ru"
	lang_list = root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, LANG_TAG), namespaces=nss)
	if len(lang_list) > 0:
		lang = lang_list[0].text
	
	year = None
	year_list = root.findall(format3 % (DESCRIPTION_PATH, PUBLISH_INFO_TAG, YEAR_TAG), namespaces=nss)
	if len(year_list) > 0:
		year = year_list[0].text	
	
	return Book(bookid, Description(title, authors, translators, genres, sequences, psequences, lang, year), body_hash(tree), estimate_pages(tree))

def load_annotation(tree):
	root = tree.getroot()
	nss = root.nsmap
	format3 = "%s/%s/%s"
	
	anno_list = root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, ANNOTATION_TAG), namespaces=nss)
	if len(anno_list) == 0:
		return None
	return etree.tostring(anno_list[0], encoding='unicode', method='xml')

def load_cover(tree):
	root = tree.getroot()
	nss = root.nsmap
	format4 = "%s/%s/%s/%s"
	
	cover_list = root.findall(format4 % (DESCRIPTION_PATH, TITLE_INFO_TAG, COVER_TAG, IMAGE_TAG), namespaces=nss)
	if len(cover_list) == 0:
		return None
	for key in cover_list[0].keys():
		if 'href' in key:
			cover_name = cover_list[0].get(key)
			break
	if cover_name and cover_name[0] == '#':
		cover_name = cover_name[1:]
		binary_list = root.findall('binary', namespaces=nss)
		for b in binary_list:
			bid = b.get('id')
			btype = b.get('content-type')
			if bid == cover_name:
				return ''.join(b.itertext())
	return None

def get_toc_element_recursive(element, nss):
	title = ''
	children = []
	title_list = element.findall(TITLE_TAG, namespaces=nss)
	if title_list:
		title = ' '.join(title_list[0].itertext())
	section_list = element.findall(SECTION_TAG, namespaces=nss)
	for s in section_list:
		children.append(get_toc_element_recursive(s, nss))
	return title, children

def get_toc(tree):
	root = tree.getroot()
	nss = root.nsmap
	toc_root = []
	body_list = root.findall(BODY_PATH, namespaces=nss)
	section_list = body_list[0].findall(SECTION_TAG, namespaces=nss)
	for s in section_list:
		toc_root.append(get_toc_element_recursive(s, nss))
	return toc_root
			
#	section_list = root.findall(format2 % (BODY_PATH, SECTION_TAG), namespaces=nss)
	
	

def update_book_info(tree, book):
	root = tree.getroot()
	nss = root.nsmap
	format2 = "%s/%s"
	
	title_info = root.findall(format2 % (DESCRIPTION_PATH, TITLE_INFO_TAG), namespaces=nss)[0]
	publish_infos = root.findall(format2 % (DESCRIPTION_PATH, PUBLISH_INFO_TAG), namespaces=nss)
	publish_info = None
	if publish_infos:
		publish_info = publish_infos[0]
	else:
		publish_info = etree.Element(PUBLISH_INFO_TAG)
		root.findall(DESCRIPTION_PATH, namespaces=nss)[0].append(publish_info)

	new_title = etree.Element(BOOK_TITLE_TAG)
	new_title.text = book.description.title
	replace_elements(title_info, BOOK_TITLE_TAG, [new_title], nss)

	new_authors = []
	for a in book.description.authors:
		new_authors.append(author_to_xml(AUTHOR_TAG, a))
	replace_elements(title_info, AUTHOR_TAG, new_authors, nss)

	new_translators = []
	for a in book.description.translators:
		new_translators.append(author_to_xml(TRANSLATOR_TAG, a))
	replace_elements(title_info, TRANSLATOR_TAG, new_translators, nss)

	new_genres = []
	for g in book.description.genres:
		new_genre = etree.Element(GENRE_TAG)
		new_genre.text = g
		new_genres.append(new_genre)
	replace_elements(title_info, GENRE_TAG, new_genres, nss)

	new_sequences = []
	for s in book.description.sequences:
		new_sequence = etree.Element(SEQUENCE_TAG)
		new_sequence.set('name', s.name)
		if s.number:
			new_sequence.set('number', s.number)
		new_sequences.append(new_sequence)
	replace_elements(title_info, SEQUENCE_TAG, new_sequences, nss)

	new_psequences = []
	for s in book.description.psequences:
		new_psequence = etree.Element(SEQUENCE_TAG)
		new_psequence.set('name', s.name)
		if s.number:
			new_psequence.set('number', s.number)
		new_psequences.append(new_psequence)
	replace_elements(publish_info, SEQUENCE_TAG, new_psequences, nss)

	new_lang = etree.Element(LANG_TAG)
	if book.description.lang:
		new_lang.text = book.description.lang
	replace_elements(title_info, LANG_TAG, [new_lang], nss)

	new_year = etree.Element(YEAR_TAG)
	if book.description.year:
		new_year.text = book.description.year
	replace_elements(publish_info, YEAR_TAG, [new_year], nss)
	

def write_errors(filename, errors):
	try:
		os.remove(filename)
	except OSError:
		pass
	if errors:
		with open(filename, 'w', encoding="utf-8") as errf:
			for error in errors:
				errf.write(error + "\r\n")
		print('Были обнаружены проблемы: подробности в файле %s' % filename)
	if platform.system() == 'Windows':
		input('Нажмите ENTER для завершения программы.')

def process_characters(s, translit):
	trans = ''
	for ch in s:
		if ch.lower() in list(TRANSLIT_MAP.keys()):
			if not translit:
				trans += ch
			else:
				tmp = TRANSLIT_MAP[ch.lower()]
				if tmp:
					if ch.isupper():
						tmp = tmp[0].upper() + tmp[1:]
					trans += tmp
		elif ch in '1234567890':
			trans += ch
		elif ch.isalpha() and ord(ch) < 128:
			trans += ch
		elif not trans or trans[-1] != '-':
			trans += '-'
	return trans

def get_display_sequence(book):
	sequences_to_skip = ['любимые книги льва толстого']
	for seq in book.description.sequences + book.description.psequences:
		if seq.number and seq.number.isdigit() and int(seq.number) > 0:
			skip = False
			if seq.name.lower().startswith('антология ') and int(seq.number) > 1800:
				skip = True
				continue
			for ss in sequences_to_skip:
				if ss in seq.name.lower():
					skip = True
			if not skip:
				return seq
	return None

def cut_unicode(s, size):
	if len(s.encode('utf-8')) > size:
		while len(s.encode('utf-8')) > size - 2:
			s = s[:-1]
		s += '..'
	return s

def build_filename(book, translit):
	filename_parts = []
	
	author_part = None
	for a in book.description.authors:
		if a.last:
			author_part = a.last
			break
		if a.first:
			author_part = a.first
			break
		if a.middle:
			author_part = a.middle
			break
	if author_part and author_part.lower() != 'автор неизвестен' and author_part.lower() != 'автор' and author_part.lower() != 'неизвестен':
		filename_parts.append(author_part)

	seq = get_display_sequence(book)
	if seq:
		filename_parts.append(seq.name)
		filename_parts.append("%02d" % int(seq.number))
	
	filename_parts.append(book.description.title)
	base = '_'.join([process_characters(s, translit) for s in filename_parts])
	if len(base) > 1 and base[0] == '-':
		base = base[1:]
	base = cut_unicode(base, 240)
	return "%s.%d.fb2" % (base, book.id)

def compare_descriptions(descr1, descr2):
	if descr1 == descr2:
		return True
	descr1_sorted = Description(descr1.title, descr1.authors, descr1.translators, sorted(descr1.genres), sorted(descr1.sequences), sorted(descr1.psequences), descr1.lang, descr1.year)
	descr2_sorted = Description(descr2.title, descr2.authors, descr2.translators, sorted(descr2.genres), sorted(descr2.sequences), sorted(descr2.psequences), descr2.lang, descr2.year)
	return descr1_sorted == descr2_sorted

def yes_or_no(question):
	question = question + ' (y/n): '
#	question = question.encode(sys.stdout.encoding)
	while True:
		reply = str(input(question)).lower().strip()
		if reply and reply[0] == 'y':
			return True
		elif reply and reply[0] == 'n':
			return False

def print_exception():
	print_header('КРИТИЧЕСКАЯ ОШИБКА')
	traceback.print_exc()
			
def print_header(header):
	print()
	print("!" + header + "!")
	print("=" * (len(header)+2))


