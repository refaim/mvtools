import re

import misc

RE_LETTER_CLUSTERS = re.compile(r'[a-z]+', re.IGNORECASE)

LANGUAGES = {
    'ara': ['Arabic'],
    'bul': ['Bulgarian'],
    'chi': ['Chinese'],
    'cze': ['Czech'],
    'dan': ['Danish'],
    'dut': ['Dutch'],
    'eng': ['English', 'en'],
    'est': ['Estonian'],
    'fin': ['Finnish'],
    'fre': ['French'],
    'ger': ['German'],
    'gre': ['Greek'],
    'heb': ['Hebrew'],
    'hrv': ['Croatian'],
    'hun': ['Hungarian'],
    'ice': ['Icelandic'],
    'ind': ['Indonesian'],
    'jpn': ['Japanese'],
    'kor': ['Korean'],
    'lav': ['Latvian'],
    'lit': ['Lithuanian'],
    'nor': ['Norwegian'],
    'pol': ['Polish'],
    'por': ['Portuguese'],
    'rum': ['Romanian'],
    'rus': ['Russian', 'ru'],
    'slo': ['Slovak'],
    'slv': ['Slovenian'],
    'spa': ['Spanish'],
    'srp': ['Serbian'],
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
    # TODO parse 2xRus.Eng as und instead of eng
    for string in RE_LETTER_CLUSTERS.findall(filepath.lower()):
        if string in LANGUAGE_STRINGS:
            found_languages.add(LANGUAGE_STRINGS[string])
    return list(found_languages)
