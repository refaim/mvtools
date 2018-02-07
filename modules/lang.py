import re

import misc

RE_LETTER_CLUSTERS = re.compile(r'[a-z]+', re.IGNORECASE)

LANGUAGES = {
    'chi': ['Chinese'],
    'cze': ['Czech'],
    'dan': ['Danish'],
    'dut': ['Dutch'],
    'eng': ['English', 'en'],
    'fin': ['Finnish'],
    'fre': ['French'],
    'ger': ['German'],
    'hun': ['Hungarian'],
    'ind': ['Indonesian'],
    'jpn': ['Japanese'],
    'kor': ['Korean'],
    'nor': ['Norwegian'],
    'pol': ['Polish'],
    'por': ['Portuguese'],
    'rus': ['Russian', 'ru'],
    'spa': ['Spanish'],
    'swe': ['Swedish'],
    'tha': ['Thai'],
    'tur': ['Turkish'],
    'ukr': ['Ukrainian'],
    'und': [],
}
LANGUAGE_STRINGS = misc.make_strings_dict(LANGUAGES)

ENCODINGS = {
    'CP1251': ['windows-1251'],
    'US-ASCII': ['ascii'],
    'UTF-8': ['utf8', 'utf-8-sig'],
}
ENCODING_STRINGS = misc.make_strings_dict(ENCODINGS)

def norm_lang(s):
    return LANGUAGE_STRINGS[s.lower()]

def norm_encoding(s):
    return ENCODING_STRINGS[s.lower()]

def guess(filepath):
    found_languages = set()
    for string in RE_LETTER_CLUSTERS.findall(filepath.lower()):
        if string in LANGUAGE_STRINGS:
            found_languages.add(LANGUAGE_STRINGS[string])
    return list(found_languages)
