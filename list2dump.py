# -*- coding: utf-8 -*-
import os, sys
from flibdefs import *
from flibcommon import *

def read_list(filename):
	data = [{}, []]
	with open(filename, encoding="utf-8") as l:
		for line in l.read().splitlines():
			parts = line.strip().split("/")
			if not parts:
				continue
			name_or_bookid = parts[-1]
			bookid = -1
			if name_or_bookid.isdigit():
				bookid = int(name_or_bookid)
			else:
				mo = BOOKFILE_PATTERN.match(name_or_bookid)
				if mo:
					bookid = int(mo.group(2))
			if bookid == -1:
				continue
			cur_data = data
			for part in parts[:-1]:
				part = part.strip()
				if part not in cur_data[0].keys():
					cur_data[0][part] = [{}, []]
				cur_data = cur_data[0][part]
			cur_data[1].append(bookid)
	return data

def dummy_book(bookid):
	return Book(bookid, Description('title', [], [], [], [], [], 'ru', None), '', 0)

def data_to_dir(data, name):
	subdirs = []
	books = []
	for subdata in sorted(list(data[0].keys())):
		sd = data_to_dir(data[0][subdata], subdata)
		if sd:
			subdirs.append(sd)
	for bookid in data[1]:
		books.append(dummy_book(bookid))
	if subdirs or books:
		return Directory(name, subdirs, sorted(books, key=lambda b: b.id))
	else:
		return None
				



def list_to_dump(listfile_path, dumpfile_path):
	data = read_list(listfile_path)
	root = data_to_dir(data, 'root')
	library = Library(root)
	write_dump_compressed(dumpfile_path, library)

def main():
	listfile_path = sys.argv[1]
	dumpfile_path = 'dummy.dump'
	list_to_dump(listfile_path, dumpfile_path)

main()
