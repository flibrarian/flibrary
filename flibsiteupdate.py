# -*- coding: utf-8 -*-
import os, urllib.request, urllib.error, urllib.parse, io, shutil
from flibdefs import *
from flibcommon import *

def load_site_book(book, flib_url, errors):
	link = flib_url + ("/" if flib_url[-1] != "/" else "") + "b/" + str(book.id) + "/head"
	print(link)
	head = None
	try:
		response = urllib.request.urlopen(link)
		head = str(response.read(), 'utf-8')
	except Exception as e:
		print('Ошибка сети:')
		print(e)
		errors.append(HEAD_ERROR_TEMPLATE % (link, 'Ошибка сети'))
		return None
	try:
		descr = re.search('(<description>.*?</description>)', head, re.DOTALL)
		if descr:
			descr = descr.group(1)
			fakebook = '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">%s</FictionBook>' % descr
			tree = read_book_xml(io.StringIO(fakebook))
			site_book = load_book_info(book.id, tree)
			return site_book
		else:
			print('Ошибка формата:')
			errors.append(HEAD_ERROR_TEMPLATE % (link, 'Ошибка формата'))
			return None
	except Exception as e:
		print('Ошибка формата:')
		print(e)
		errors.append(HEAD_ERROR_TEMPLATE % (link, 'Ошибка формата'))
		return None

def update_directory(d, flib_url, errors, missedbookids):
	books = []
	subdirs = []
	for book in d.books:
		books.append(update_book(book, flib_url, errors, missedbookids))
	for sd in d.subdirs:
		subdirs.append(update_directory(sd, flib_url, errors, missedbookids))
	return Directory(d.name, subdirs, books)


def update_book(book, flib_url, errors, missedbookids):
	if book.id in missedbookids:
		fl_book = load_site_book(book, flib_url, errors)
		if fl_book:
			if fl_book.description != book.description:
				print('Обновлено: %s' % fl_book.description.title)
			book = Book(book.id, fl_book.description, book.bodyhash, book.pages)
			return book
		else:
			return book
	else:
		return book

def update_library(library, flib_url, errors, missedbookids):
	root = update_directory(library.root, flib_url, errors, missedbookids)
	return Library(root)


def main():
	errors = []
	try:
		[dumpfile_path, flib_url] = read_config_values(
			['DUMP_FILE_PATH', 'FLIB_URL'],
			[str, str],
			errors)
		library = read_dump_compressed(dumpfile_path, errors)
		missedbookids = []
		with open('missedbookids.txt', 'r') as f:
			missedbookids = [int(x) for x in f.read().splitlines()]
		new_library = update_library(library, flib_url, errors, missedbookids)
		write_dump_compressed(dumpfile_path, new_library)
		print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()





