# -*- coding: utf-8 -*-
import os
from flibdefs import *
from flibcommon import *

Dumpdata = namedtuple('Dumpdata', 'quick errors dump_path translit')

def read_file(path, old_dir, dumpdata):
	name = os.path.basename(path)
	mo = BOOKFILE_PATTERN.match(name)
	if not mo:
		dumpdata.errors.append('Пропущен файл: %s' % (path))
		return None
	try:
		bookid = int(mo.group(2))
		if old_dir:
			old_book = next((b for b in old_dir.books if b.id == bookid), None)
			if old_book:
				return old_book
		with open(path, 'rb') as zfo:
			tree, fs = read_book_zip(zfo)
			book = load_book_info(bookid, tree)
			print(' + %s' % os.path.join(os.path.dirname(os.path.relpath(path, dumpdata.dump_path)), build_filename(book, dumpdata.translit) + ".zip"))
			return book
	except Exception as e:
		dumpdata.errors.append('Ошибка при чтении файла: %s' % (path))
		return None

def read_directory(d, old_dir, dumpdata):
	if not dumpdata.quick:
		print(d)
	dirs = sorted([x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))])
	files = sorted([x for x in os.listdir(d) if os.path.isfile(os.path.join(d, x))])
	subdirs = []
	books = []
	for f in files:
		book = read_file(os.path.join(d, f), old_dir, dumpdata)
		if book:
			books.append(book)
	for sd in dirs:
		old_subdir = next((dd for dd in old_dir.subdirs if dd.name == sd), None) if old_dir else None
		subdir = read_directory(os.path.join(d, sd), old_subdir, dumpdata)
		if subdir:
			subdirs.append(subdir)
	if old_dir:
		for book in old_dir.books:
			if not next((b for b in books if b.id == book.id), None):
				print(' - %s' % os.path.join(os.path.relpath(d, dumpdata.dump_path), build_filename(book, dumpdata.translit) + ".zip"))
		for sd in old_dir.subdirs:
			if not next((dd for dd in subdirs if dd.name == sd.name), None) if old_dir else None:
				print(' - %s' % os.path.join(os.path.relpath(d, dumpdata.dump_path), sd.name))
	
	if subdirs or books:
		return Directory(os.path.basename(d), subdirs, sorted(books, key=lambda b: b.id))
	else:
		return None

def dump_library(old_library, dumpdata, dumpfile_path):
	print_header('ЧТЕНИЕ БИБЛИОТЕКИ')
	root = read_directory(dumpdata.dump_path, old_library.root if old_library else None, dumpdata)
	library = Library(root)
	write_dump_compressed(dumpfile_path, library)

def main():
	errors = []
	try:
		[dumpfile_path, read_path, quick, translit] = \
			read_config_values(['DUMP_FILE_PATH', 'DUMP_FROM_PATH', 'QUICK_DUMP', 'TRANSLIT'],
			[str, str, bool, bool],
			errors)
		if not os.path.exists(read_path):
			errors.append("Директория DUMP_FROM_PATH (%s) не найдена" % read_path)
		else:
			old_library = read_dump_compressed(dumpfile_path, []) if quick else None
			dumpdata = Dumpdata(old_library != None, errors, str(read_path), translit)
			if dumpdata.quick:
				print_header('РЕЖИМ БЫСТРОГО ОБНОВЛЕНИЯ')
			dump_library(old_library, dumpdata, dumpfile_path)
			print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()
