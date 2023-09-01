# -*- coding: utf-8 -*-
import pymysql
from flibdefs import *
from flibcommon import *

GENRES_TO_IGNORE = ('love_short', 'love_sf', 'love_detective', 'love_hard', 'love_erotica', 'fanfiction', 'sf_litrpg')
METAS_TO_SPLIT = ('Проза', 'Фантастика', 'Наука, Образование', 'Поэзия', 'Дом и семья', 'Детективы и Триллеры', 'Приключения', 'Документальная литература', 'Религия, духовность, эзотерика')

BOOK_FEED_GENRE_TEMPLATE = '<a href="#" class="genre" name="%s">%s</a>'
BOOK_FEED_AUTHOR_TEMPLATE = '<a href="%s/a/%d">%s</a>'
BOOK_FEED_AUTHOR_NOLINK_TEMPLATE = '<a href="#">%s</a>'
BOOK_FEED_SEQUENCE_TEMPLATE = '<a href="%s/s/%d"><span class="h8">%s</span></a>'
BOOK_FEED_SEQUENCE_NUMBERED_TEMPLATE = '<a href="%s/s/%d"><span class="h8">%s</span></a> - %s'
BOOK_FEED_SEQUENCE_NOLINK_TEMPLATE = '<a href="#"><span class="h8">%s</span></a>'
BOOK_FEED_SEQUENCE_NOLINK_NUMBERED_TEMPLATE = '<a href="#"><span class="h8">%s</span></a> - %s'
BOOK_FEED_SEQUENCES_TEMPLATE = ' (%s)'
BOOK_FEED_TRANSLATORS_TEMPLATE = ' (пер. %s)'
BOOK_FEED_TEMPLATE = '''
<div><p class="genre">
%s
</p>
<a href="%s/b/%d"><b>%s</b></a>
%s
%s
<span style="size">%dK, %d с.</span>
скачать: <a href="%s/b/%d/fb2">(fb2)</a> -
%s
<p></p>
%s
<p></p>
</div>
'''

PAGE_TEMPLATE = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ru" class="js" lang="ru"><head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>%s | Флибуста</title>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <link type="text/css" rel="stylesheet" media="all" href="../css.css">
</head>
<body id="second">
<div id="page" class="one-sidebar">
<div id="container" class=" withright clear-block">   
<div id="main-wrapper"><div id="main" class="clear-block">
<h1 class="title">%s</h1>
%s
<br>
</div></div>
<div id="sidebar-right" class="sidebar"></div>
</div>
<div id="footer">Fueled by Johannes Gensfleisch zur Laden zum Gutenberg</div>
</div>
</body></html>
'''

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

def get_annotation(bookid, cur):
	try:
		cur.execute("SELECT Body FROM libbannotations WHERE BookId=%d" % bookid)
		return cur.fetchone()[0]
	except Exception:
		return ''



def author_name(a):
	s = ''
	for part in (a.first, a.middle, a.last):
		if part:
			s += ' ' + part
	return s

def author_link(flib_url, aid, aname):
	if aid:
		return BOOK_FEED_AUTHOR_TEMPLATE % (flib_url, aid, aname)
	else:
		return BOOK_FEED_AUTHOR_NOLINK_TEMPLATE % (aname)

def sequence_link(flib_url, sid, sname, snumber):
	if sid:
		if snumber:
			return BOOK_FEED_SEQUENCE_NUMBERED_TEMPLATE % (flib_url, sid, sname, snumber)
		else:
			return BOOK_FEED_SEQUENCE_TEMPLATE % (flib_url, sid, sname)
	else:
		if snumber:
			return BOOK_FEED_SEQUENCE_NOLINK_NUMBERED_TEMPLATE % (sname, snumber)
		else:
			return BOOK_FEED_SEQUENCE_NOLINK_TEMPLATE % (sname)


def write_cat_feed(content, cat_path, cat_name, genremap, flib_url):
	path = os.path.join(cat_path, cat_name + '.html')
	book_feeds = []
	with open(path, 'w') as feed:
		for book, anno, fsize, aids, tids, sids, psids in content:
			authors = ' - '.join([author_link(flib_url, aid, author_name(a)) for a, aid in zip(book.description.authors, aids)])
			genres = ', '.join([BOOK_FEED_GENRE_TEMPLATE % (g, genremap[g][0] if g in genremap.keys() else g) for g in book.description.genres])
			translators = ''
			if book.description.translators:
				translators = BOOK_FEED_TRANSLATORS_TEMPLATE % (','.join([author_link(flib_url, tid, author_name(a)) for a, tid in zip(book.description.translators, tids)]))
			sequences = ''
			if book.description.sequences or book.description.psequences:
				sequences = BOOK_FEED_SEQUENCES_TEMPLATE % (', '.join([sequence_link(flib_url, sid, s.name, s.number) for s, sid in zip(book.description.sequences + book.description.psequences, sids + psids)]))
			book_feed = BOOK_FEED_TEMPLATE % (genres, flib_url, book.id, book.description.title, translators, sequences, fsize / 1000, book.pages, flib_url, book.id, authors, anno)
			book_feeds.append(book_feed)
		page = PAGE_TEMPLATE % (cat_name, cat_name, '\n'.join(book_feeds))
		page = page.replace('//', '/')
		feed.write(page)


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

def load_sql_book(n, cur):
	cur.execute("SELECT Title FROM libbook WHERE BookId=%d" % n)
	if not cur.fetchone():
		return None
	cur.execute("SELECT Title, Lang, Year, FileSize, keywords, Pages FROM libbook WHERE BookId=%d" % n)
	title, lang, year, filesize, keywords, pages = cur.fetchone()
	title = title
	lang = lang
	year = None if year == 0 else str(year)
	selfpub = 'самиздат' in keywords.lower()
	
	authors = []
	translators = []
	genres = []
	sequences = []
	psequences = []
	
	author_ids = []
	translator_ids = []
	seq_ids = []
	pseq_ids = []
	
	cur.execute("SELECT AvtorId, Pos FROM libavtor WHERE BookId=%d" % n)
	rows = cur.fetchall()
	sorted_authors = []
	for row in rows:
		aid = row[0]
		pos = row[1]
		cur.execute("SELECT FirstName, MiddleName, LastName FROM libavtorname WHERE AvtorId=%d" % aid)
		author = Author(*[x if x else None for x in cur.fetchone()])
		sorted_authors.append((author, pos, aid))
	authors = [a for a, _, _ in sorted(sorted_authors, key=lambda tup: tup[1])]
	author_ids = [i for _, _, i in sorted(sorted_authors, key=lambda tup: tup[1])]
	
	cur.execute("SELECT TranslatorId, Pos FROM libtranslator WHERE BookId=%d" % n)
	rows = cur.fetchall()
	sorted_translators = []
	for row in rows:
		tid = row[0]
		pos = row[1]
		cur.execute("SELECT FirstName, MiddleName, LastName FROM libavtorname WHERE AvtorId=%d" % tid)
		author = Author(*[x if x else None for x in cur.fetchone()])
		sorted_translators.append((author, pos, tid))
	translators = [a for a, _, _ in sorted(sorted_translators, key=lambda tup: tup[1])]
	translator_ids = [i for _, _, i in sorted(sorted_translators, key=lambda tup: tup[1])]

	cur.execute("SELECT GenreId FROM libgenre WHERE BookId=%d" % n)
	rows = cur.fetchall()
	for row in rows:
		gid = row[0]
		cur.execute("SELECT GenreCode FROM libgenrelist WHERE GenreId=%d" % gid)
		genre = cur.fetchone()[0]
		genres.append(genre)
	
	cur.execute("SELECT SeqId, SeqNumb, Type FROM libseq WHERE BookId=%d" % n)
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
			pseq_ids.append(sid)
		else:
			sequences.append(sequence)
			seq_ids.append(sid)
	
	description = Description(title, authors, translators, genres, sequences, psequences, lang, year)
	return Book(n, description, '', pages), filesize, author_ids, translator_ids, seq_ids, pseq_ids, selfpub

def write_feeds(cur, ids, feed_path, flib_url, authorset, bookset):
	genremap = load_genremap(cur)
	cats = {}
	for n in ids:
		book, fsize, aids, tids, sids, psids, selfpub = load_sql_book(n, cur)
		if book:
			ignore_book = False
			for g in GENRES_TO_IGNORE:
				if g in book.description.genres:
					ignore_book = True
					break
			if ignore_book:
				continue
			anno = get_annotation(book.id, cur)
			cat = get_category(book, genremap)
			selfpub = selfpub or 'network_literature' in book.description.genres
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
			if not cat in cats.keys():
				cats[cat] = []
			cats[cat].append((book, anno, fsize, aids, tids, sids, psids))
			print(book.id)
	for cat in cats.keys():
		write_cat_feed(cats[cat], feed_path, cat, genremap, flib_url)


def get_ids(cur, max_dump_n):
	cur.execute("SELECT BookId, Lang, FileType, Deleted FROM libbook WHERE BookId > %d ORDER BY BookId ASC" % max_dump_n)
	rows = cur.fetchall()
	ids = []
	for bid, lang, ft, dl in rows:
		if lang.lower() != 'ru' or ft.lower() != 'fb2' or int(dl) != 0:
			continue
		cur.execute("SELECT realId FROM libjoinedbooks WHERE BadId=%d" % bid)
		if cur.fetchone():
			continue
		ids.append(bid)
	return ids

def get_max_n(data):
	n = 0
	for subdir in sorted(data.subdirs):
		n = max(get_max_n(subdir), n)
	for book in data.books:
		n = max(book.id, n)
	return n


def main():
	errors = []
	try:
		[dumpfile_path, flib_url, host, user, password, database, port] = \
			read_config_values(['DUMP_FILE_PATH', 'FLIB_URL', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE', 'MYSQL_PORT'],
			[str, str, str, str, str, str, int],
			errors)
		connection = pymysql.connect(host=host, user=user, password=password, database=database, port=port)
		library = read_dump_compressed(dumpfile_path, errors)
		max_dump_n = get_max_n(library.root)
		with connection.cursor() as cur:
			authorset, bookset = gather_library_ids(library, cur, errors)
			ids = get_ids(cur, max_dump_n)
			write_feeds(cur, ids, 'flibfeeds', flib_url, authorset, bookset)
		connection.close()
		print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()





