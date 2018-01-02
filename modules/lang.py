import re

RE_LETTER_CLUSTERS = re.compile(r'[a-z]+', re.IGNORECASE)

LANGUAGES = {
    'chi': ['Chinese'],
    'dan': ['Danish'],
    'dut': ['Dutch'],
    'eng': ['English', 'en'],
    'fin': ['Finnish'],
    'fre': ['French'],
    'ger': ['German'],
    'jpn': ['Japanese'],
    'nor': ['Norwegian'],
    'por': ['Portuguese'],
    'rus': ['Russian', 'ru'],
    'spa': ['Spanish'],
    'swe': ['Swedish'],
    'ukr': ['Ukrainian'],
    'und': [],
}
LANGUAGE_STRINGS = {}
for key, values in LANGUAGES.iteritems():
    for string in values + [key]:
        LANGUAGE_STRINGS[string.lower()] = key

def guess_language(filepath):
    found_languages = set()
    for string in RE_LETTER_CLUSTERS.findall(filepath.lower()):
        if string in LANGUAGE_STRINGS:
            found_languages.add(LANGUAGE_STRINGS[string])
    if len(found_languages) != 1:
        raise Exception(u"Unable to guess language of '{}'".format(filepath))
    return list(found_languages)[0]
