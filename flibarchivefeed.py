# -*- coding: utf-8 -*-
import pymysql
from flibdefs import *
from flibcommon import *
import base64
from PIL import Image
from io import BytesIO

BOOK_FEED_GENRE_TEMPLATE = '<a href="#" class="genre" name="%s">%s</a>'
BOOK_FEED_AUTHOR_TEMPLATE = '<a href="%s/a/%d">%s</a>'
BOOK_FEED_AUTHOR_NOLINK_TEMPLATE = '<a href="#">%s</a>'
BOOK_FEED_SEQUENCE_TEMPLATE = '<a href="%s/s/%d"><span class="h8">%s</span></a>'
BOOK_FEED_SEQUENCE_NUMBERED_TEMPLATE = '<a href="%s/s/%d"><span class="h8">%s</span></a> - %s'
BOOK_FEED_SEQUENCE_NOLINK_TEMPLATE = '<a href="#"><span class="h8">%s</span></a>'
BOOK_FEED_SEQUENCE_NOLINK_NUMBERED_TEMPLATE = '<a href="#"><span class="h8">%s</span></a> - %s'
BOOK_FEED_SEQUENCES_TEMPLATE = ' (%s)'
BOOK_FEED_TRANSLATORS_TEMPLATE = ' (пер. %s)'
BOOK_FEED_IMAGE_TEMPLATE_BASE64 = '<img src="data:image/jpeg;base64, %s "/>'
BOOK_FEED_IMAGE_TEMPLATE_FILE = '<img src=".data/%s"/>'
BOOK_FEED_MOREINFO_AUTHORBLOCK_TEMPLATE = '''
<p><b>%s</b></p><ul>
%s
</ul>
'''
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
<table><tr>
<td>
%s
<p>
Издание %s г.
</p>
</td>
<td>
%s
</td>
</tr></table>
<button class="collapsible">Оглавление</button>
<div class="content">
%s
</div>
<button class="collapsible">Авторы</button>
<div class="content">
%s
</div>
</div>
'''

PAGE_TEMPLATE = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ru" class="js" lang="ru"><head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>%s | Флибуста</title>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <link type="text/css" rel="stylesheet" media="all" href="../../css.css">
<style>
.collapsible {
  background-color: #777;
  color: white;
  cursor: pointer;
  width: 100%%;
  border: none;
  text-align: left;
  outline: none;
  font-size: 15px;
}

.active, .collapsible:hover {
  background-color: #555;
}

.content {
  padding: 0 18px;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease-out;
  background-color: #f1f1f1;
}
</style>
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

<script>
var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.maxHeight){
      content.style.maxHeight = null;
    } else {
      content.style.maxHeight = content.scrollHeight + "px";
    } 
  });
}
</script>

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


def update_and_get_more_info(book, cur, fs):
	cur.execute("SELECT Title FROM libbook WHERE BookId=%d" % book.id)
	if not cur.fetchone():
		authors = book.description.authors
		author_ids = [None for x in book.description.authors]
		translator_ids = [None for x in book.description.translators]
		seq_ids = [None for x in book.description.sequences]
		pseq_ids = [None for x in book.description.psequences]
		return book, fs, author_ids, translator_ids, seq_ids, pseq_ids
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

	author_books = []

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
	
	for aid in author_ids:
		current_author_books = []
		cur.execute("SELECT BookId FROM libavtor WHERE AvtorId=%d" % aid)
		rows = cur.fetchall()
		sorted_authors = []
		for row in rows:
			bid = row[0]
#			if bid == book.id:
#				continue
			cur.execute("SELECT realId FROM libjoinedbooks WHERE BadId=%d" % bid)
			if cur.fetchone():
				continue
			cur.execute("SELECT Title, Lang, FileType, Deleted, Pages FROM libbook WHERE BookId=%d" % bid)
			tmp = cur.fetchone()
			if not tmp:
				continue
			title, lang, filetype, deleted, tmp_pages = tmp
			if lang.lower() != 'ru':
				continue
			cur.execute("SELECT GenreId FROM libgenre WHERE BookId=%d" % bid)
			rows = cur.fetchall()
			temp_genres = []
			for row in rows:
				gid = row[0]
				cur.execute("SELECT GenreCode FROM libgenrelist WHERE GenreId=%d" % gid)
				genre = cur.fetchone()[0]
				temp_genres.append(genre)
			multiauthor = False
			cur.execute("SELECT AvtorId, Pos FROM libavtor WHERE BookId=%d" % bid)
			multiauthor = len(cur.fetchall()) > 2
	
			current_author_books.append((title, bid, filetype, temp_genres, multiauthor, tmp_pages))
		author_books.append(current_author_books)
	
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

	if not authors:
		authors = book.description.authors
		author_ids = [None for x in authors]
	if not translators:
		translators = book.description.translators
		translator_ids = [None for x in translators]
	if not authors:
		authors = book.description.authors
	if not sequences and not psequences:
		sequences = book.description.sequences
		psequences = book.description.psequences
		seq_ids = [None for x in sequences]
		pseq_ids = [None for x in psequences]
	description = Description(book.description.title, authors, translators, book.description.genres, sequences, psequences, book.description.lang, book.description.year)
	return Book(book.id, description, book.bodyhash, pages), filesize, author_ids, translator_ids, seq_ids, pseq_ids, author_books


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


def build_toc(toc_list):
	s = ''
	for title, children in toc_list:
		if not title:
			title = '...'
		s += '<li>%s</li>\n' % title
		s += build_toc(children)
	return '<ul>%s</ul>' % s

def write_cat_feed(content, cat_path, cat_name, genremap, flib_url, bookset):
	path = os.path.join(cat_path, 'feed.html')
	book_feeds = []
	with open(path, 'w') as feed:
		for book, filepath, anno, cover, toc, fsize, aids, tids, sids, psids, abooks in content:
			authors = ' - '.join([author_link(flib_url, aid, author_name(a)) for a, aid in zip(book.description.authors, aids)])
			genres = ', '.join([BOOK_FEED_GENRE_TEMPLATE % (g, genremap[g][0] if g in genremap.keys() else g) for g in book.description.genres])
			translators = ''
			if book.description.translators:
				translators = BOOK_FEED_TRANSLATORS_TEMPLATE % (','.join([author_link(flib_url, tid, author_name(a)) for a, tid in zip(book.description.translators, tids)]))
			sequences = ''
			if book.description.sequences or book.description.psequences:
				sequences = BOOK_FEED_SEQUENCES_TEMPLATE % (', '.join([sequence_link(flib_url, sid, s.name, s.number) for s, sid in zip(book.description.sequences + book.description.psequences, sids + psids)]))
			cover_str = ''
			if cover:
#				buf = BytesIO()
#				cover.save(buf, format="JPEG")
#				cover_str = BOOK_FEED_IMAGE_TEMPLATE_BASE64 % base64.b64encode(buf.getvalue()).decode("utf-8")
				data_path = os.path.join(cat_path, '.data')
				if not os.path.exists(data_path):
					os.makedirs(data_path)
				cover_name = '%d.jpg' % book.id
				cover = cover.convert('RGB')
				cover.save(os.path.join(data_path, cover_name))
				cover_str = BOOK_FEED_IMAGE_TEMPLATE_FILE % cover_name
			toc_block = build_toc(toc)
			more_block = ''
			for a, books in zip(book.description.authors, abooks):
				if not books:
					continue
				if 'коллектив авторов' in author_name(a).lower() or 'автор неизвестен' in author_name(a).lower():
					continue
				book_items = []
				for title, bid, filetype, b_genres, multiauthor, pages in sorted(books, key=lambda x: (x[4], x[0])):
					item = title
					if multiauthor:
						item = '[СБОРНИК] ' + item
					item += ' <small>(' + ', '.join([(genremap[g][0] if g in genremap.keys() else g) for g in b_genres]) + ')</small>'
					if filetype.lower() != 'fb2':
						item = '<span style="background-color:#ffcfcf;">%s (%s)</span>' % (item, filetype.lower())
					else:
						item += ' (%s стр)' % pages
					if bid in bookset:
						item = '<span style="background-color:#cfffcf;">%s</span>' % item
					if bid == book.id:
						item = '<i>%s</i>' % item
					book_items.append(item)
				book_block = '\n'.join(['<li>%s</li>' % item for item in book_items])
				author_block = BOOK_FEED_MOREINFO_AUTHORBLOCK_TEMPLATE % (author_name(a), book_block)
				more_block += author_block
			book_feed = BOOK_FEED_TEMPLATE % (genres, flib_url, book.id, book.description.title, translators, sequences, fsize / 1000, book.pages, filepath, authors, cover_str, book.description.year, anno, toc_block, more_block)
			book_feeds.append(book_feed)
		page = PAGE_TEMPLATE % (cat_name, cat_name, '\n'.join(book_feeds))
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
			tree, fs = read_book_zip(zfo)
			book = load_book_info(bookid, tree)
			anno = load_annotation(tree)
			cover = None
			try:
				cover_string = load_cover(tree)
				if cover_string:
					cover_bytes = base64.b64decode(cover_string)
					cover_stream = BytesIO(cover_bytes)
					cover = Image.open(cover_stream)
					if cover:
						cover.thumbnail((200,200), Image.ANTIALIAS)
			except Exception as e:
				cover = None
			toc = get_toc(tree)
			return book, anno, cover, toc, fs
	except Exception as e:
		print(e)
		return None, None, None

def process_cat(cat_path, cat_name, cur, genremap, flib_url, bookset):
	print(cat_path)
	content = []
	files = sorted([x for x in os.listdir(cat_path) if x.endswith('.fb2.zip') and os.path.isfile(os.path.join(cat_path, x))])
	for f in files:
		path = os.path.join(cat_path, f)
		book, file_anno, cover, toc, fs = read_file(path)
		if book:
			book, fsize, aids, tids, sids, psids, abooks = update_and_get_more_info(book, cur, fs)
#			anno = get_annotation(book.id, cur) #way too long
			anno = None
			content.append((book, path, anno if anno else file_anno if file_anno else '', cover, toc, fsize, aids, tids, sids, psids, abooks))
#	content.sort(key=lambda tup: tup[0].id)
	write_cat_feed(content, cat_path, cat_name, genremap, flib_url, bookset)

def process_feed(cur, feed_path, flib_url, bookset):
	genremap = load_genremap(cur)
	dirs = sorted([x for x in os.listdir(feed_path) if os.path.isdir(os.path.join(feed_path, x))])
	for d in dirs:
		process_cat(os.path.join(feed_path, d), d, cur, genremap, flib_url, bookset)

def gather_directory_ids(d, bookset):
	for book in d.books:
		bookset.add(book.id)
	for sd in d.subdirs:
		gather_directory_ids(sd, bookset)

def gather_library_ids(library, errors):
	bookset = set()
	for d in library.root.subdirs:
		gather_directory_ids(d, bookset)
	print('Число книг:', len(bookset))
	return bookset

def main():
	errors = []
	try:
		[dumpfile_path, flib_url, host, user, password, database, port] = \
			read_config_values(['DUMP_FILE_PATH', 'FLIB_URL', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE', 'MYSQL_PORT'],
			[str, str, str, str, str, str, int],
			errors)
		library = read_dump_compressed(dumpfile_path, errors)
		bookset = gather_library_ids(library, errors)
		connection = pymysql.connect(host=host, user=user, password=password, database=database, port=port)
		with connection.cursor() as cur:
			process_feed(cur, 'flibfeeds', flib_url, bookset)
		connection.close()
		print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()





