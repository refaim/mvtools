import os
import re

import misc

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
    'hin': ['Hindi'],
    'hrv': ['Croatian'],
    'hun': ['Hungarian'],
    'ice': ['Icelandic'],
    'ind': ['Indonesian'],
    'ita': ['Italian'],
    'jpn': ['Japanese'],
    'kaz': ['Kazakh'],
    'kor': ['Korean'],
    'lav': ['Latvian'],
    'lit': ['Lithuanian'],
    'may': ['Malay'],
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
    'vie': ['Vietnamese'],
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

def guess(file_path):
    found_languages = set()
    file_name = re.sub(r'\dx', r'', os.path.splitext(os.path.basename(file_path))[0].lower())
    for string in re.findall(r'[a-z]+', file_name, re.IGNORECASE):
        if string in LANGUAGE_STRINGS:
            found_languages.add(LANGUAGE_STRINGS[string])
    return list(found_languages)
