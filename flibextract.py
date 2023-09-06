# -*- coding: utf-8 -*-
import os, urllib.request, urllib.error, urllib.parse, io, shutil
from lxml import etree
from flibdefs import *
from flibcommon import *

Extractdata = namedtuple('Extractdata', 'idmap quick errors absent_books extract_path dump_path cache_path translit failed_books')

def extract_book(book, tree, path, extractdata):
	update_book_info(tree, book)
	
	if not os.path.exists(path):
		os.makedirs(path)
	fb2_name = build_filename(book, extractdata.translit)
	fb2zip_name = "%s.zip" % fb2_name
	new_book_path = os.path.join(path, fb2zip_name)
	
	if os.path.exists(new_book_path):
		print(' ^ %s' % (fb2zip_name if not extractdata.quick else os.path.join(os.path.relpath(path, extractdata.extract_path), fb2zip_name)))
	else:
		print(' + %s' % (fb2zip_name if not extractdata.quick else os.path.join(os.path.relpath(path, extractdata.extract_path), fb2zip_name)))
	
	inside_name = build_filename(book, True)

	extractdata.failed_books.append(new_book_path)
	with zipfile.ZipFile(new_book_path, "w", zipfile.ZIP_DEFLATED) as zf:
		info = zipfile.ZipInfo(filename=inside_name, date_time=(1980, 1, 1, 0, 0, 0))
		info.compress_type = zipfile.ZIP_DEFLATED
		zf.writestr(info, etree.tostring(tree, encoding='utf-8', xml_declaration=True, pretty_print=True, method='xml'))
	del extractdata.failed_books[-1]

	if body_hash(tree) != book.bodyhash:
		try:
			with open(new_book_path, 'rb') as zfo:
				new_tree, fs = read_book_zip(zfo)
				if body_hash(new_tree) != book.bodyhash:
					extractdata.errors.append('Контрольная сумма не совпадает: %s' % new_book_path)
		except Exception:
			extractdata.errors.append('Контрольная сумма не совпадает: %s' % new_book_path)

def check_local_file(book, path, quick, translit):
	try:
		fb2zip_name = "%s.zip" % build_filename(book, translit)
		new_book_path = os.path.join(path, fb2zip_name)
		if not os.path.exists(new_book_path):
			return False
		if quick:
			return True
		with open(new_book_path, 'rb') as zfo:
			tree, fs = read_book_zip(zfo)
			local_book = load_book_info(book.id, tree)
			return compare_descriptions(book.description, local_book.description) and book.bodyhash == local_book.bodyhash
	except Exception as e:
		return False

def try_get_old_file(book, path):
	try:
		for name in os.listdir(path):
			if os.path.isfile(os.path.join(path, name)):
				mo = BOOKFILE_PATTERN.match(name)
				if mo and int(mo.group(2)) == book.id:
					with open(os.path.join(path, name), 'rb') as zfo:
						tree, fs = read_book_zip(zfo)
						local_book = load_book_info(book.id, tree)
						if local_book.bodyhash == book.bodyhash:
							return tree
	except Exception as e:
		return None
	return None

def clear_duplicates(book, path, extractdata):
	fb2zip_name = "%s.zip" % build_filename(book, extractdata.translit)
	for name in os.listdir(path):
		if name != fb2zip_name and os.path.isfile(os.path.join(path, name)):
			mo = BOOKFILE_PATTERN.match(name)
			if mo and int(mo.group(2)) == book.id:
				print(' - %s' % (name if not extractdata.quick else os.path.join(os.path.relpath(path, extractdata.extract_path), name)))
				os.remove(os.path.join(path, name))

def try_extract_book(book, directory, path, extractdata):
	fb2zip_name = "%s.zip" % build_filename(book, extractdata.translit)
	if check_local_file(book, path, extractdata.quick, extractdata.translit):
		return fb2zip_name
	if book.id in list(extractdata.idmap.keys()):
		arch = extractdata.idmap[book.id]
		with zipfile.ZipFile(arch, 'r') as zf:
			with zf.open("%d.fb2" % book.id) as f:
				tree = read_book_xml(f)
				extract_book(book, tree, path, extractdata)
				clear_duplicates(book, path, extractdata)
				return fb2zip_name
	else:
		tree = try_get_old_file(book, path)
		if tree:
			extract_book(book, tree, path, extractdata)
			clear_duplicates(book, path, extractdata)
			return fb2zip_name
		if extractdata.dump_path != extractdata.extract_path:
			dump_path = os.path.join(extractdata.dump_path, os.path.relpath(path, extractdata.extract_path))
			tree = try_get_old_file(book, dump_path)
			if tree:
				extract_book(book, tree, path, extractdata)
				return fb2zip_name
		extractdata.absent_books.append((book, path))
	return None

def remove_or_cache(name, path, extractdata):
	print(' - %s' % (name if not extractdata.quick else os.path.join(os.path.relpath(path, extractdata.extract_path), name)))
	mo = BOOKFILE_PATTERN.match(name)
	if mo and int(mo.group(2)) not in list(extractdata.idmap.keys()):
		try:
			shutil.move(os.path.join(path, name), os.path.join(extractdata.cache_path, name))
			return
		except Exception as e:
			pass
	try:
		os.remove(os.path.join(path, name))
	except Exception as e:
		pass	

def extract_directory(directory, path, extractdata):
	if not extractdata.quick:
		print(path)
	if not os.path.exists(path):
		os.makedirs(path)
	valid_files = []
	valid_dirs = []

	for book in directory.books:
		new_name = try_extract_book(book, directory, path, extractdata)
		if new_name:
			valid_files.append(new_name)

	for sd in directory.subdirs:
		extract_directory(sd, os.path.join(path, sd.name), extractdata)
		valid_dirs.append(sd.name)
	
	for name in os.listdir(path):
		if os.path.isfile(os.path.join(path, name)):
			if name not in valid_files:
				remove_or_cache(name, path, extractdata)
		elif os.path.isdir(os.path.join(path, name)):
			if name not in valid_dirs:
				if os.path.join(path, name) == extractdata.cache_path:
					continue
				for root, dirs, files in os.walk(os.path.join(path, name)):
					for filename in files:
						remove_or_cache(filename, root, extractdata)
				shutil.rmtree(os.path.join(path, name))
				print(' - %s' % (name if not extractdata.quick else os.path.join(os.path.relpath(path, extractdata.extract_path), name)))

def extract_library(library, extractdata):
	print_header('РАСПАКОВКА КНИГ')
	extract_directory(library.root,  extractdata.extract_path, extractdata)

def reuse_cached(extractdata):
	still_absent = []
	for book, path in extractdata.absent_books:
		tree = try_get_old_file(book, extractdata.cache_path)
		if tree:
			fb2zip_name = "%s.zip" % build_filename(book, extractdata.translit)
			extract_book(book, tree, path, extractdata)
		else:
			still_absent.append((book, path))
	del extractdata.absent_books[:]
	extractdata.absent_books.extend(still_absent)
	shutil.rmtree(extractdata.cache_path)

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

def download_book(link, book, path, extractdata):
	print('Загрузка: ' + link)
	try:
		response = urllib.request.urlopen(link)
		remote_name = response.geturl().split("/")[-1]
		if not BOOKFILE_PATTERN.match(remote_name):
			extractdata.errors.append(DOWNLOAD_ERROR_TEMPLATE % (link, path, 'Неожиданное имя файла: ' + remote_name))
			print('Неожиданное имя файла: ' + remote_name)
			return
		if not os.path.exists(path):
			os.makedirs(path)
		fo = io.BytesIO(response.read())
		tree, fs = read_book_zip(fo)
		extract_book(book, tree, path, extractdata)
	except Exception as e:
		print('Ошибка сети:')
		print(e)
		extractdata.errors.append(DOWNLOAD_ERROR_TEMPLATE % (link, path, 'Ошибка сети'))

def download_absent(flib_url, extractdata):
	if extractdata.absent_books:
		print_header('ЗАГРУЗКА ОТСУТСТВУЮЩИХ КНИГ')
		ans = yes_or_no("%d книг не найдено в архивах. Загрузить с сайта?" % len(extractdata.absent_books))
		n = 25
		for i in range(0, len(extractdata.absent_books), n):
			chunk = extractdata.absent_books[i:i + n]
			if ans:
				print('Загрузка книг %d-%d из %d' % (i + 1, i + len(chunk), len(extractdata.absent_books)))
			for book, path in chunk:
				link = flib_url + ("/" if flib_url[-1] != "/" else "") + "b/" + str(book.id) + "/fb2"
				if ans:
					download_book(link, book, path, extractdata)
				else:
					extractdata.errors.append(DOWNLOAD_ERROR_TEMPLATE % (link, path, 'Отменено пользователем'))
			ans = i + n < len(extractdata.absent_books) and ans and yes_or_no("Продолжить загрузку?")
			

def main():
	errors = []
	failed_books = []
	try:
		[dumpfile_path, arch_path, flib_url, extract_path, dump_path, quick, translit] = \
			read_config_values(['DUMP_FILE_PATH', 'ARCHIVE_PATH', 'FLIB_URL', 'EXTRACT_TO_PATH', 'DUMP_FROM_PATH', 'QUICK_EXTRACT', 'TRANSLIT'],
			[str,str,str,str,str,bool,bool],
			errors)
		if not os.path.exists(arch_path):
			errors.append("Директория ARCHIVE_PATH (%s) не найдена" % arch_path)
			return

		if not os.path.exists(extract_path):
			ans = yes_or_no("Директория EXTRACT_TO_PATH (%s) отсутствует.\r\nСоздать директорию и продолжить?" % extract_path)
			if not ans:
				return

		if os.path.exists(extract_path) and os.listdir(extract_path):
			ans = yes_or_no("Директория EXTRACT_TO_PATH (%s) не пуста.\r\nПосторонние файлы будут удалены! Продолжить?" % extract_path)
			if not ans:
				return
		else:
			quick = False

		if quick:
			print_header('РЕЖИМ БЫСТРОГО ОБНОВЛЕНИЯ')
		library = read_dump_compressed(dumpfile_path, errors)
		if library:
			idmap = load_archives(arch_path)
			if not idmap:
				ans = yes_or_no("Архивы не найдены. Продолжить без них?")
				if not ans:
					return		
			cache_dir = '.flib_cache_' + ini_path().replace('.', '_')
			cache_path = os.path.join(extract_path, cache_dir)
			if not os.path.exists(cache_path):
				os.makedirs(cache_path)
			extractdata = Extractdata(idmap, quick, errors, [], extract_path, dump_path,  cache_path, translit, failed_books)
			extract_library(library, extractdata)
			reuse_cached(extractdata)
			download_absent(flib_url, extractdata)
			print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		for path in failed_books:
			try:
				os.remove(path)
			except Exception:
				pass
		write_errors(log_filename(), errors)

main()
