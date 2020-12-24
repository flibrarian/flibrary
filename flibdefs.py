# -*- coding: utf-8 -*-
import re
from collections import namedtuple

VERSION = "1.0"

DEFAULT_INI_PATH = "flibconfig.ini"

DESCRIPTION_PATH = "./description"

TITLE_INFO_TAG = "title-info"
PUBLISH_INFO_TAG = "publish-info"

BOOK_TITLE_TAG = "book-title"
AUTHOR_TAG = "author"
TRANSLATOR_TAG = "translator"
GENRE_TAG = "genre"
SEQUENCE_TAG = "sequence"
LANG_TAG = "lang"
YEAR_TAG = "year"

Directory = namedtuple('Directory', 'name subdirs books')
Book = namedtuple('Book', 'id description bodyhash pages')
Description = namedtuple('Description', 'title authors translators genres sequences psequences lang year')
Author = namedtuple('Author', 'first middle last')
Sequence = namedtuple('Sequence', 'name number')
Library = namedtuple('Library', 'root')

BOOKFILE_PATTERN = re.compile("(.*?)\.([0-9]+?)\.fb2\.zip$")
FBARCH_PATTERN = re.compile("^((f|d)\.)?fb2-[0-9]+-[0-9]+\.zip$")
FBARCH_BOOK_PATTERN = re.compile("^[0-9]+\.fb2$")

TRANSLIT_MAP = {}
TRANSLIT_MAP[u'а'] = 'a'
TRANSLIT_MAP[u'б'] = 'b'
TRANSLIT_MAP[u'в'] = 'v'
TRANSLIT_MAP[u'г'] = 'g'
TRANSLIT_MAP[u'д'] = 'd'
TRANSLIT_MAP[u'е'] = 'e'
TRANSLIT_MAP[u'ё'] = 'yo'
TRANSLIT_MAP[u'ж'] = 'zh'
TRANSLIT_MAP[u'з'] = 'z'
TRANSLIT_MAP[u'и'] = 'i'
TRANSLIT_MAP[u'й'] = 'y'
TRANSLIT_MAP[u'к'] = 'k'
TRANSLIT_MAP[u'л'] = 'l'
TRANSLIT_MAP[u'м'] = 'm'
TRANSLIT_MAP[u'н'] = 'n'
TRANSLIT_MAP[u'о'] = 'o'
TRANSLIT_MAP[u'п'] = 'p'
TRANSLIT_MAP[u'р'] = 'r'
TRANSLIT_MAP[u'с'] = 's'
TRANSLIT_MAP[u'т'] = 't'
TRANSLIT_MAP[u'у'] = 'u'
TRANSLIT_MAP[u'ф'] = 'f'
TRANSLIT_MAP[u'х'] = 'h'
TRANSLIT_MAP[u'ц'] = 'c'
TRANSLIT_MAP[u'ч'] = 'ch'
TRANSLIT_MAP[u'ш'] = 'sh'
TRANSLIT_MAP[u'щ'] = 'shch'
TRANSLIT_MAP[u'ъ'] = ''
TRANSLIT_MAP[u'ы'] = 'y'
TRANSLIT_MAP[u'ь'] = ''
TRANSLIT_MAP[u'э'] = 'e'
TRANSLIT_MAP[u'ю'] = 'yu'
TRANSLIT_MAP[u'я'] = 'ya'

HTML_TEMPLATE = u'''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta http-equiv="content-type" content="text/html; charset=utf-8"/>
<style>
ul, #myUL {
  list-style-type: none;
}

#myUL {
  margin: 0;
  padding: 0;
}

.caret {
  cursor: pointer;
  -webkit-user-select: none; /* Safari 3.1+ */
  -moz-user-select: none; /* Firefox 2+ */
  -ms-user-select: none; /* IE 10+ */
  user-select: none;
}

.caret::before {
  content: "+";
  color: black;
  display: inline-block;
}

.caret-down::before {
  content: "−";
  color: black;
  display: inline-block;
}

.nested {
  display: none;
}

.active {
  display: block;
}

li{
  margin: 10px 0;
}
</style>
</head>
<body>

<h2>Библиотека%s</h2>

<ul id="myUL">
  %s
</ul>

<script>
var toggler = document.getElementsByClassName("caret");
var i;

for (i = 0; i < toggler.length; i++) {
  toggler[i].addEventListener("click", function() {
    this.parentElement.querySelector(".nested").classList.toggle("active");
    this.classList.toggle("caret-down");
  });
}
</script>

</body>
</html>'''

HTML_BOOKLINE_TEMPLATE = '<li><a href="%s">%s</a>%s</li>\n'
HTML_DIRSTART_TEMPLATE = '<li><span class="caret">%s</span>\n<ul class="nested">\n'
HTML_DIREND_TEMPLATE = '</ul>\n</li>\n'

DOWNLOAD_ERROR_TEMPLATE = u'Ошибка при загрузке %s в %s : %s'


