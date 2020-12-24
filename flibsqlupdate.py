# -*- coding: utf-8 -*-
import pymysql
from flibdefs import *
from flibcommon import *

def load_sql_book(book, cur, errors):
	cur.execute("SELECT Title FROM libbook WHERE BookId=%d" % book.id)
	if not cur.fetchone():
		return book
	cur.execute("SELECT Title, Lang, Year, Deleted, Pages FROM libbook WHERE BookId=%d" % book.id)
	title, lang, year, deleted, pages = cur.fetchone()
	title = title.decode('utf-8')
	lang = lang.decode('utf-8')
	year = None if year == 0 else str(year)
	if deleted == 1:
		errors.append(u'Книга #%d ("%s") была удалена из библиотеки' % (book.id, book.description.title ))
		
	cur.execute("SELECT realId FROM libjoinedbooks WHERE BadId=%d" % book.id)
	if cur.fetchone():
		errors.append(u'Книга #%d ("%s") была заменена на другую версию' % (book.id, book.description.title ))
	
	authors = []
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
		author = Author(*[x.decode('utf-8') if x else None for x in cur.fetchone()])
		sorted_authors.append((author, pos))
	authors = [a for a, _ in sorted(sorted_authors, key=lambda tup: tup[1])]
	
	cur.execute("SELECT TranslatorId, Pos FROM libtranslator WHERE BookId=%d" % book.id)
	rows = cur.fetchall()
	sorted_translators = []
	for row in rows:
		tid = row[0]
		pos = row[1]
		cur.execute("SELECT FirstName, MiddleName, LastName FROM libavtorname WHERE AvtorId=%d" % tid)
		author = Author(*[x.decode('utf-8') if x else None for x in cur.fetchone()])
		sorted_translators.append((author, pos))
	translators = [a for a, _ in sorted(sorted_translators, key=lambda tup: tup[1])]
	
	cur.execute("SELECT GenreId FROM libgenre WHERE BookId=%d" % book.id)
	rows = cur.fetchall()
	for row in rows:
		gid = row[0]
		cur.execute("SELECT GenreCode FROM libgenrelist WHERE GenreId=%d" % gid)
		genre = cur.fetchone()[0].decode('utf-8')
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
		sequence = Sequence(sq_tmp[0].decode('utf-8'), sn)
		if is_p:
			psequences.append(sequence)
		else:
			sequences.append(sequence)
	
	description = Description(title, authors, translators, genres, sequences, psequences, lang, year)
	if description != book.description:
		print u'Обновлено: %s' % title
	return Book(book.id, description, book.bodyhash, pages)
		
def update_directory(d, cur, errors):
	books = []
	subdirs = []
	for book in d.books:
		books.append(update_book(book, cur, errors))
	for sd in d.subdirs:
		subdirs.append(update_directory(sd, cur, errors))
	return Directory(d.name, subdirs, books)
	

def update_book(book, cur, errors):
	return load_sql_book(book, cur, errors)

def update_library(library, con, errors):
	with con.cursor() as cur:
		root = update_directory(library.root, cur, errors)
		return Library(root)


def main():
	errors = []
	try:
		[dumpfile_path, host, user, password, database, port] = read_config_values(
			['DUMP_FILE_PATH', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE', 'MYSQL_PORT'],
			[str, str, str, str, str, int],
			errors)
		connection = pymysql.connect(host, user, password, database, port)
		library = read_dump_compressed(dumpfile_path, errors)
		new_library = update_library(library, connection, errors)
		connection.close()
		write_dump_compressed(dumpfile_path, new_library)
		print_header(u'ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()





