# -*- coding: utf-8 -*-
import pymysql
from flibdefs import *
from flibcommon import *

BOOK_FEED_GENRE_TEMPLATE = '<a href="#" class="genre" name="%s">%s</a>'
BOOK_FEED_AUTHOR_TEMPLATE = '<a href="%s/a/%d">%s</a>'
BOOK_FEED_SEQUENCE_TEMPLATE = '<a href="%s/s/%d"><span class="h8">%s</span></a>'
BOOK_FEED_SEQUENCE_NUMBERED_TEMPLATE = '<a href="%s/s/%d"><span class="h8">%s</span></a> - %s'
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
скачать: <a href="%s">(fb2)</a> -
%s
<p></p>
%s
<p></p>
</div>
'''

PAGE_TEMPLATE = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ru" class="js" lang="ru"><head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>Последние поступления | Флибуста</title>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <link type="text/css" rel="stylesheet" media="all" href="../css.css">
</head>
<body id="second">
<div id="page" class="one-sidebar">
<div id="container" class=" withright clear-block">   
<div id="main-wrapper"><div id="main" class="clear-block">
<h1 class="title">Последние поступления</h1>
%s
<br>
</div></div>
<div id="sidebar-right" class="sidebar"></div>
</div>
<div id="footer">Fueled by Johannes Gensfleisch zur Laden zum Gutenberg</div>
</div>
</body></html>
'''

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
		return ''	#TODO: get from tree

def get_filesize(bookid, cur):
	cur.execute("SELECT FileSize FROM libbook WHERE BookId=%d" % bookid)
	return cur.fetchone()[0]


def update_and_get_more_info(book, cur):
	cur.execute("SELECT FileSize, Pages FROM libbook WHERE BookId=%d" % book.id)
	filesize, pages = cur.fetchone()

	authors = []
	author_ids = []
	translators = []
	translator_ids = []
	sequences = []
	psequences = []
	seq_ids = []
	pseq_ids = []
	

	cur.execute("SELECT AvtorId, Pos FROM libavtor WHERE BookId=%d" % book.id)
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
	
	cur.execute("SELECT TranslatorId, Pos FROM libtranslator WHERE BookId=%d" % book.id)
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
			pseq_ids.append(sid)
		else:
			sequences.append(sequence)
			seq_ids.append(sid)

	description = Description(book.description.title, authors, translators, book.description.genres, sequences, psequences, book.description.lang, book.description.year)
	return Book(book.id, description, book.bodyhash, pages), filesize, author_ids, translator_ids, seq_ids, pseq_ids


def author_name(a):
	s = ''
	for part in (a.first, a.middle, a.last):
		if part:
			s += ' ' + part
	return s

def write_cat_feed(content, cat_path, genremap, flib_url):
	path = os.path.join(cat_path, 'feed.html')
	book_feeds = []
	with open(path, 'w') as feed:
		for book, filepath, anno, fsize, aids, tids, sids, psids in content:
			authors = ' - '.join([BOOK_FEED_AUTHOR_TEMPLATE % (flib_url, aid, author_name(a)) for a, aid in zip(book.description.authors, aids)])
			genres = ', '.join([BOOK_FEED_GENRE_TEMPLATE % (g, genremap[g][0]) for g in book.description.genres])
			translators = ''
			if book.description.translators:
				translators = BOOK_FEED_TRANSLATORS_TEMPLATE % (','.join([BOOK_FEED_AUTHOR_TEMPLATE % (flib_url, tid, author_name(a)) for a, tid in zip(book.description.translators, tids)]))
			sequences = ''
			if book.description.sequences or book.description.psequences:
				sequences = BOOK_FEED_SEQUENCES_TEMPLATE % (', '.join([BOOK_FEED_SEQUENCE_NUMBERED_TEMPLATE % (flib_url, sid, s.name, s.number) if s.number else BOOK_FEED_SEQUENCE_TEMPLATE % (flib_url, sid, s.name) for s, sid in zip(book.description.sequences + book.description.psequences, sids + psids)]))
			book_feed = BOOK_FEED_TEMPLATE % (genres, flib_url, book.id, book.description.title, translators, sequences, fsize / 1000, book.pages, filepath, authors, anno)
			book_feeds.append(book_feed)
		page = PAGE_TEMPLATE % ('\n'.join(book_feeds))
		page = page.replace('//', '/')
		feed.write(page)

def read_file(path):
	name = os.path.basename(path)
	mo = BOOKFILE_PATTERN.match(name)
	if not mo:
		return None
	try:
		bookid = int(mo.group(2))
		with open(path, 'rb') as zfo:
			tree = read_book_zip(zfo)
			book = load_book_info(bookid, tree)
			return book
	except Exception as e:
		return None

def process_cat(cat_path, cur, genremap, flib_url):
	print(cat_path)
	content = []
	files = sorted([x for x in os.listdir(cat_path) if os.path.isfile(os.path.join(cat_path, x))])
	for f in files:
		path = os.path.join(cat_path, f)
		book = read_file(path)
		if book:
			book, fsize, aids, tids, sids, psids = update_and_get_more_info(book, cur)
			anno = get_annotation(book.id, cur)
			content.append((book, path, anno, fsize, aids, tids, sids, psids))
#	content.sort(key=lambda tup: tup[0].id)
	write_cat_feed(content, cat_path, genremap, flib_url)		

def process_feed(cur, feed_path, flib_url):
	genremap = load_genremap(cur)
	dirs = sorted([x for x in os.listdir(feed_path) if os.path.isdir(os.path.join(feed_path, x))])
	for d in dirs:
		process_cat(os.path.join(feed_path, d), cur, genremap, flib_url)


def main():
	errors = []
	try:
		[flib_url, host, user, password, database, port] = \
			read_config_values(['FLIB_URL', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE', 'MYSQL_PORT'],
			[str, str, str, str, str, int],
			errors)
		connection = pymysql.connect(host=host, user=user, password=password, database=database, port=port)
		with connection.cursor() as cur:
			process_feed(cur, 'flibfeeds', flib_url)
		connection.close()
		print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()




