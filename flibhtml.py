# -*- coding: utf-8 -*-
from lxml import etree
from flibdefs import *
from flibcommon import *

def calculate_size(directory):
	nb = 0
	nd = 0
	for f in directory.books:
		nb += 1
	for sd in directory.subdirs:
		snb, snd = calculate_size(sd)
		nb += snb
		nd += snd + 1
	return nb, nd

def authors_str(authors):
	al = []
	for a in authors:
		s = ''
		for part in (a.first, a.middle, a.last):
			if part:
				s += ' ' + part
		if s:
			al.append(s.strip())
	return ", ".join(al)
	
def write_level(data, flib_url):
	source = ''
	for subdir in sorted(data.subdirs):
		nb, nd = calculate_size(subdir)
		subdirsize = ' (%d кн. / %d дир.)' % (nb, nd) if nd else ' (%d кн.)' % nb
		title = "<b>%s</b>" % subdir.name + subdirsize
		source += HTML_DIRSTART_TEMPLATE % title
		source += ''
		source += write_level(subdir, flib_url)
		source += HTML_DIREND_TEMPLATE
	title_sort_map = {}
	title_display_map = {}
	for book in data.books:
		title_sort = book.description.title
		title_display = "<b>%s</b>" % book.description.title
		astr = authors_str(book.description.authors)
		if astr:
			title_sort += " -- %s" % astr
			title_display += " -- <i>%s</i>" % astr
		tstr = authors_str(book.description.translators)
		if tstr:
			title_sort += " (пер. %s)" % tstr
			title_display += ' <small><i style="font-stretch: ultra-condensed">(пер. %s)</i></small>' % tstr
		seq = get_display_sequence(book)
		if seq:
			title_sort = ('[%s - %02d] ' % (seq.name, int(seq.number))) + title_sort
			title_display = ('[%s - %02d] ' % (seq.name, int(seq.number))) + title_display
		title_sort_map[book.id] = title_sort
		title_display_map[book.id] = title_display
	for book in sorted(data.books, key=lambda x: title_sort_map[x.id]):
		link = flib_url + ("/" if flib_url[-1] != "/" else "") + "b/" + str(book.id)
		source += HTML_BOOKLINE_TEMPLATE % (link, title_display_map[book.id], " (%d стр.)" % book.pages)
	return source

def write_html(library, flib_url, name):
	with open(name, 'w', encoding="utf-8") as htmlf:
		source = write_level(library.root, flib_url)
		nb, nd = calculate_size(library.root)
		libsizestr = ' (%d кн. / %d дир.)' % (nb, nd)
		htmlf.write((HTML_TEMPLATE % (libsizestr, source)))

def main():
	errors = []
	try:
		[dumpfile_path, flib_url] = \
			read_config_values(['DUMP_FILE_PATH', 'FLIB_URL'],
			[str, str],
			errors)
		library = read_dump_compressed(dumpfile_path, errors)
		if library:
			write_html(library, flib_url, 'library.html')
			print_header('ВСЁ СДЕЛАНО')
	except BaseException as e:
		print_exception()
	finally:
		write_errors(log_filename(), errors)

main()
