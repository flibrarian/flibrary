# -*- coding: utf-8 -*-
import pymysql
from flibdefs import *
from flibcommon import *

GENRES_TO_IGNORE = ('love_short', 'love_sf', 'love_detective', 'love_hard', 'love_erotica', 'fanfiction', 'sf_litrpg', 'popadancy')
METAS_TO_SPLIT = ('Проза', 'Фантастика', 'Наука, Образование', 'Поэзия', 'Дом и семья', 'Детективы и Триллеры', 'Приключения', 'Документальная литература', 'Религия, духовность, эзотерика')

def load_archive(name):
	content = []
	with zipfile.ZipFile(name, 'r') as zf:
		for filename in zf.namelist():
			if FBARCH_BOOK_PATTERN.match(filename):
				n = int(filename[:-4])
				content.append(n)
	return content

def load_archives(directory):
	print_header('ЧТЕНИЕ АРХИВОВ')
	archs = [x for x in os.listdir(directory) if FBARCH_PATTERN.match(x)]
	idmap = {}
	print('%d архивов найдено' % len(archs))
	for arch in sorted(archs):
		arch = os.path.join(directory, arch)
		for n in load_archive(arch):
			idmap[n] = arch
	if archs:
		print('архивы прочитаны')
	return idmap


def gather_directory_ids(d, cur, authorset, bookset):
	for book in d.books:
		bookset.add(book.id)
		cur.execute("SELECT AvtorId FROM libavtor WHERE BookId=%d" % book.id)
		rows = cur.fetchall()
		if len(rows) > 3:
			continue
		for row in rows:
			authorset.add(row[0])
	for sd in d.subdirs:
		gather_directory_ids(sd, cur, authorset, bookset)


def gather_library_ids(library, cur, errors):
	authorset = set()
	bookset = set()
	for d in library.root.subdirs:
		gather_directory_ids(d, cur, authorset, bookset)
	print('Число книг:', len(bookset))
	print('Число авторов:', len(authorset))
	return authorset, bookset

def load_sql_book(book, cur, errors):
	cur.execute("SELECT Title FROM libbook WHERE BookId=%d" % book.id)
	if not cur.fetchone():
		return book, []
	cur.execute("SELECT Title, Lang, Year, Deleted, Pages FROM libbook WHERE BookId=%d" % book.id)
	title, lang, year, deleted, pages = cur.fetchone()
	title = title
	lang = lang
	year = None if year == 0 else str(year)
	if deleted == 1:
		errors.append('Книга #%d ("%s") была удалена из библиотеки' % (book.id, book.description.title ))
		
	cur.execute("SELECT realId FROM libjoinedbooks WHERE BadId=%d" % book.id)
	if cur.fetchone():
		return None, []
	
	authors = []
	authorids = []
	translators = []
	genres = []
	sequences = []
	psequences = []
	
	cur.execute("SELECT AvtorId, Pos FROM libavtor WHERE BookId=%d" % book.id)
	rows = cur.fetchall()
	sorted_authors = []
	for row in rows:
		aid = row[0]
		pos = row[1]
		cur.execute("SELECT FirstName, MiddleName, LastName FROM libavtorname WHERE AvtorId=%d" % aid)
		author = Author(*[x if x else None for x in cur.fetchone()])
		sorted_authors.append((author, pos))
		authorids.append(aid)
	authors = [a for a, _ in sorted(sorted_authors, key=lambda tup: tup[1])]
	
	cur.execute("SELECT TranslatorId, Pos FROM libtranslator WHERE BookId=%d" % book.id)
	rows = cur.fetchall()
	sorted_translators = []
	for row in rows:
		tid = row[0]
		pos = row[1]
		cur.execute("SELECT FirstName, MiddleName, LastName FROM libavtorname WHERE AvtorId=%d" % tid)
		author = Author(*[x if x else None for x in cur.fetchone()])
		sorted_translators.append((author, pos))
	translators = [a for a, _ in sorted(sorted_translators, key=lambda tup: tup[1])]
	
	cur.execute("SELECT GenreId FROM libgenre WHERE BookId=%d" % book.id)
	rows = cur.fetchall()
	for row in rows:
		gid = row[0]
		cur.execute("SELECT GenreCode FROM libgenrelist WHERE GenreId=%d" % gid)
		genre = cur.fetchone()[0]
		genres.append(genre)
	
	cur.execute("SELECT SeqId, SeqNumb, Type FROM libseq WHERE BookId=%d" % book.id)
	rows = cur.fetchall()
	for row in rows:
		sid = row[0]
		sn = row[1]
		is_p = row[2] != 0
		sn = None if sn == 0 else str(sn)
		cur.execute("SELECT SeqName FROM libseqname WHERE SeqId=%d" % sid)
		sq_tmp = cur.fetchone()
		if not sq_tmp:
			break
		sequence = Sequence(sq_tmp[0], sn)
		if is_p:
			psequences.append(sequence)
		else:
			sequences.append(sequence)
	if not authors:
		authors = book.description.authors
	if not translators:
		translators = book.description.translators
	if not genres:
		genres = book.description.genres
	if not sequences and not psequences:
		sequences = book.description.sequences
		psequences = book.description.psequences
	description = Description(title, authors, translators, genres, sequences, psequences, lang, year)
	return Book(book.id, description, book.bodyhash, pages), authorids

def load_genremap(cur):
	genremap = {}
	cur.execute("SELECT GenreCode, GenreDesc, GenreMeta FROM libgenrelist")
	rows = cur.fetchall()
	for row in rows:
		code = row[0]
		desc = row[1]
		meta = row[2]
		genremap[code] = (desc, meta)
	return genremap

def get_category(book, genremap):
	if not book.description.genres:
		return None
	for g in book.description.genres:
		if g not in genremap.keys():
			continue
		meta = genremap[g][1]
		if meta in METAS_TO_SPLIT:
			return '%s - %s' % (meta, genremap[g][0])
		else:
			return meta
	return None

def is_selfpub(tree):
	root = tree.getroot()
	nss = root.nsmap
	format3 = "%s/%s/%s"
	for s in root.findall(format3 % (DESCRIPTION_PATH, PUBLISH_INFO_TAG, 'publisher'), namespaces=nss):
		if s.text and ('selfpub' in s.text.lower() or 'самиздат' in s.text.lower()):
			return True
	for s in root.findall(format3 % (DESCRIPTION_PATH, TITLE_INFO_TAG, 'keywords'), namespaces=nss):
		if s.text:
			keywords = [x.strip().lower() for x in s.text.split(',')]
			if 'самиздат' in keywords:
				return True
	return False

def extract_book(book, tree, path, translit):
	update_book_info(tree, book)
	
	if not os.path.exists(path):
		os.makedirs(path)
	fb2_name = build_filename(book, translit)
	fb2zip_name = "%s.zip" % fb2_name
	new_book_path = os.path.join(path, fb2zip_name)
	
	inside_name = build_filename(book, True)

	with zipfile.ZipFile(new_book_path, "w", zipfile.ZIP_DEFLATED) as zf:
		zf.writestr(inside_name, etree.tostring(tree, encoding='utf-8', xml_declaration=True, pretty_print=True, method='xml'))

def process_books(idmap, cur, feed_path, translit, authorset, bookset, errors):
	genremap = load_genremap(cur)
	for n in sorted(idmap.keys()):
		print(n)
		if n in bookset:
			continue
		arch = idmap[n]
		with zipfile.ZipFile(arch, 'r') as zf:
			with zf.open("%d.fb2" % n) as f:
				tree = read_book_xml(f)
				book = load_book_info(n, tree)
				if not book:
					continue
				book, aids = load_sql_book(book, cur, errors)
				if not book:
					continue
				if book.description.lang != 'ru':
					continue
				ignore_book = False
				for g in GENRES_TO_IGNORE:
					if g in book.description.genres:
						ignore_book = True
						break
				if ignore_book:
					continue
				selfpub = is_selfpub(tree) or 'network_literature' in book.description.genres
				cat = get_category(book, genremap)
				if not cat:
					cat = 'Без категории'
				if selfpub:
					cat += ' (самиздат)'
				known_author = False
				if len(aids) <= 3:
					for aid in aids:
						if aid in authorset:
							known_author = True
							break
				if known_author:
					cat += ' [автор в библиотеке]'
				path = os.path.join(feed_path, cat)
				extract_book(book, tree, path, translit)
				

def main():
	errors = []
	try:
		[dumpfile_path, arch_path, translit, host, user, password, database, port] = \
			read_config_values(['DUMP_FILE_PATH', 'ARCHIVE_PATH', 'TRANSLIT', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE', 'MYSQL_PORT'],
			[str, str, bool, str, str, str, str, int],
			errors)
		if not os.path.exists(arch_path):
			errors.append("Директория ARCHIVE_PATH (%s) не найдена" % arch_path)
			return

		idmap = load_archives(arch_path)
		if not idmap:
			print("Архивы не найдены.")
			return
		library = read_dump_compressed(dumpfile_path, errors)
		connection = pymysql.connect(host=host, user=user, password=password, database=database, port=port)
		with connection.cursor() as cur:
			authorset, bookset = gather_library_ids(library, cur, errors)
			process_books(idmap, cur, 'flibfeeds', translit, authorset, bookset, errors)
		connection.close()
		print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()





