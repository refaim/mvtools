# coding: utf-8

import os
import re

import misc

_ISO_639_LANGUAGE_SUBSET = {
    'aar': ['aa', ['Afar']],
    'abk': ['ab', ['Abkhazian']],
    'ace': [None, ['Achinese']],
    'ach': [None, ['Acoli']],
    'ada': [None, ['Adangme']],
    'ady': [None, ['Adyghe', 'Adygei']],
    'afa': [None, ['Afro-Asiatic']],
    'afh': [None, ['Afrihili']],
    'afr': ['af', ['Afrikaans']],
    'ain': [None, ['Ainu']],
    'aka': ['ak', ['Akan']],
    'akk': [None, ['Akkadian']],
    'alb': ['sq', ['Albanian']],
    'ale': [None, ['Aleut']],
    'alg': [None, ['Algonquian']],
    'alt': [None, ['Southern Altai']],
    'amh': ['am', ['Amharic']],
    'anp': [None, ['Angika']],
    'apa': [None, ['Apache']],
    'ara': ['ar', ['Arabic']],
    'arg': ['an', ['Aragonese']],
    'arm': ['hy', ['Armenian']],
    'arn': [None, ['Mapudungun', 'Mapuche']],
    'arp': [None, ['Arapaho']],
    'art': [None, ['Artificial']],
    'arw': [None, ['Arawak']],
    'asm': ['as', ['Assamese']],
    'ast': [None, ['Asturian', 'Bable', 'Leonese', 'Asturleonese']],
    'ath': [None, ['Athapascan']],
    'aus': [None, ['Australian']],
    'ava': ['av', ['Avaric']],
    'ave': ['ae', ['Avestan']],
    'awa': [None, ['Awadhi']],
    'aym': ['ay', ['Aymara']],
    'aze': ['az', ['Azerbaijani']],
    'bad': [None, ['Banda']],
    'bai': [None, ['Bamileke']],
    'bak': ['ba', ['Bashkir']],
    'bal': [None, ['Baluchi']],
    'bam': ['bm', ['Bambara']],
    'ban': [None, ['Balinese']],
    'baq': ['eu', ['Basque']],
    'bas': [None, ['Basa']],
    'bat': [None, ['Baltic']],
    'bej': [None, ['Beja', 'Bedawiyet']],
    'bel': ['be', ['Belarusian']],
    'bem': [None, ['Bemba']],
    'ben': ['bn', ['Bengali']],
    'ber': [None, ['Berber']],
    'bho': [None, ['Bhojpuri']],
    'bih': ['bh', ['Bihari']],
    'bik': [None, ['Bikol']],
    'bin': [None, ['Bini', 'Edo']],
    'bis': ['bi', ['Bislama']],
    'bla': [None, ['Siksika']],
    'bnt': [None, ['Bantu']],
    'bos': ['bs', ['Bosnian']],
    'bra': [None, ['Braj']],
    'bre': ['br', ['Breton']],
    'btk': [None, ['Batak']],
    'bua': [None, ['Buriat']],
    'bug': [None, ['Buginese']],
    'bul': ['bg', ['Bulgarian']],
    'bur': ['my', ['Burmese']],
    'byn': [None, ['Blin', 'Bilin']],
    'cad': [None, ['Caddo']],
    'cai': [None, ['Central American Indian']],
    'car': [None, ['Galibi Carib']],
    'cat': ['ca', ['Catalan', 'Valencian']],
    'cau': [None, ['Caucasian']],
    'ceb': [None, ['Cebuano']],
    'cel': [None, ['Celtic']],
    'cha': ['ch', ['Chamorro']],
    'chb': [None, ['Chibcha']],
    'che': ['ce', ['Chechen']],
    'chg': [None, ['Chagatai']],
    'chi': ['zh', ['Chinese']],
    'chk': [None, ['Chuukese']],
    'chm': [None, ['Mari']],
    'chn': [None, ['Chinook jargon']],
    'cho': [None, ['Choctaw']],
    'chp': [None, ['Chipewyan', 'Dene Suline']],
    'chr': [None, ['Cherokee']],
    'chu': ['cu', ['Church Slavic', 'Old Slavonic', 'Church Slavonic', 'Old Bulgarian', 'Old Church Slavonic']],
    'chv': ['cv', ['Chuvash']],
    'chy': [None, ['Cheyenne']],
    'cmc': [None, ['Chamic']],
    'cop': [None, ['Coptic']],
    'cor': ['kw', ['Cornish']],
    'cos': ['co', ['Corsican']],
    'cre': ['cr', ['Cree']],
    'crh': [None, ['Crimean Tatar', 'Crimean Turkish']],
    'crp': [None, ['Creoles and pidgins']],
    'csb': [None, ['Kashubian']],
    'cus': [None, ['Cushitic']],
    'cze': ['cs', ['Czech']],
    'dak': [None, ['Dakota']],
    'dan': ['da', ['Danish']],
    'dar': [None, ['Dargwa']],
    'day': [None, ['Land Dayak']],
    'del': [None, ['Delaware']],
    'den': [None, ['Athapascan']],
    'dgr': [None, ['Dogrib']],
    'din': [None, ['Dinka']],
    'div': ['dv', ['Divehi', 'Dhivehi', 'Maldivian']],
    'doi': [None, ['Dogri']],
    'dra': [None, ['Dravidian']],
    'dsb': [None, ['Lower Sorbian']],
    'dua': [None, ['Duala']],
    'dut': ['nl', ['Dutch', 'Flemish']],
    'dyu': [None, ['Dyula']],
    'dzo': ['dz', ['Dzongkha']],
    'efi': [None, ['Efik']],
    'eka': [None, ['Ekajuk']],
    'elx': [None, ['Elamite']],
    'eng': ['en', ['English', 'EN']],
    'epo': ['eo', ['Esperanto']],
    'est': ['et', ['Estonian']],
    'ewe': ['ee', ['Ewe']],
    'ewo': [None, ['Ewondo']],
    'fan': [None, ['Fang']],
    'fao': ['fo', ['Faroese']],
    'fat': [None, ['Fanti']],
    'fij': ['fj', ['Fijian']],
    'fil': [None, ['Filipino', 'Pilipino']],
    'fin': ['fi', ['Finnish']],
    'fiu': [None, ['Finno-Ugrian']],
    'fon': [None, ['Fon']],
    'fre': ['fr', ['French']],
    'frr': [None, ['Northern Frisian']],
    'frs': [None, ['Eastern Frisian']],
    'fry': ['fy', ['Western Frisian']],
    'ful': ['ff', ['Fulah']],
    'fur': [None, ['Friulian']],
    'gaa': [None, ['Ga']],
    'gay': [None, ['Gayo']],
    'gba': [None, ['Gbaya']],
    'gem': [None, ['Germanic']],
    'geo': ['ka', ['Georgian']],
    'ger': ['de', ['German']],
    'gez': [None, ['Geez']],
    'gil': [None, ['Gilbertese']],
    'gla': ['gd', ['Gaelic', 'Scottish Gaelic']],
    'gle': ['ga', ['Irish']],
    'glg': ['gl', ['Galician']],
    'glv': ['gv', ['Manx']],
    'gon': [None, ['Gondi']],
    'gor': [None, ['Gorontalo']],
    'got': [None, ['Gothic']],
    'grb': [None, ['Grebo']],
    'gre': ['el', ['Greek']],
    'grn': ['gn', ['Guarani']],
    'gsw': [None, ['Swiss German', 'Alemannic', 'Alsatian']],
    'guj': ['gu', ['Gujarati']],
    'gwi': [None, ['Gwich\'in']],
    'hai': [None, ['Haida']],
    'hat': ['ht', ['Haitian', 'Haitian Creole']],
    'hau': ['ha', ['Hausa']],
    'haw': [None, ['Hawaiian']],
    'heb': ['he', ['Hebrew']],
    'her': ['hz', ['Herero']],
    'hil': [None, ['Hiligaynon']],
    'him': [None, ['Himachali', 'Western Pahari']],
    'hin': ['hi', ['Hindi']],
    'hit': [None, ['Hittite']],
    'hmn': [None, ['Hmong', 'Mong']],
    'hmo': ['ho', ['Hiri Motu']],
    'hrv': ['hr', ['Croatian']],
    'hsb': [None, ['Upper Sorbian']],
    'hun': ['hu', ['Hungarian']],
    'hup': [None, ['Hupa']],
    'iba': [None, ['Iban']],
    'ibo': ['ig', ['Igbo']],
    'ice': ['is', ['Icelandic']],
    'ido': ['io', ['Ido']],
    'iii': ['ii', ['Sichuan Yi', 'Nuosu']],
    'ijo': [None, ['Ijo']],
    'iku': ['iu', ['Inuktitut']],
    'ile': ['ie', ['Interlingue', 'Occidental']],
    'ilo': [None, ['Iloko']],
    'ina': ['ia', ['Interlingua']],
    'inc': [None, ['Indic']],
    'ind': ['id', ['Indonesian']],
    'ine': [None, ['Indo-European']],
    'inh': [None, ['Ingush']],
    'ipk': ['ik', ['Inupiaq']],
    'ira': [None, ['Iranian']],
    'iro': [None, ['Iroquoian']],
    'ita': ['it', ['Italian']],
    'jav': ['jv', ['Javanese']],
    'jbo': [None, ['Lojban']],
    'jpn': ['ja', ['Japanese']],
    'jpr': [None, ['Judeo-Persian']],
    'jrb': [None, ['Judeo-Arabic']],
    'kaa': [None, ['Kara-Kalpak']],
    'kab': [None, ['Kabyle']],
    'kac': [None, ['Kachin', 'Jingpho']],
    'kal': ['kl', ['Kalaallisut', 'Greenlandic']],
    'kam': [None, ['Kamba']],
    'kan': ['kn', ['Kannada']],
    'kar': [None, ['Karen']],
    'kas': ['ks', ['Kashmiri']],
    'kau': ['kr', ['Kanuri']],
    'kaw': [None, ['Kawi']],
    'kaz': ['kk', ['Kazakh']],
    'kbd': [None, ['Kabardian']],
    'kha': [None, ['Khasi']],
    'khi': [None, ['Khoisan']],
    'khm': ['km', ['Central Khmer']],
    'kho': [None, ['Khotanese', 'Sakan']],
    'kik': ['ki', ['Kikuyu', 'Gikuyu']],
    'kin': ['rw', ['Kinyarwanda']],
    'kir': ['ky', ['Kirghiz', 'Kyrgyz']],
    'kmb': [None, ['Kimbundu']],
    'kok': [None, ['Konkani']],
    'kom': ['kv', ['Komi']],
    'kon': ['kg', ['Kongo']],
    'kor': ['ko', ['Korean']],
    'kos': [None, ['Kosraean']],
    'kpe': [None, ['Kpelle']],
    'krc': [None, ['Karachay-Balkar']],
    'krl': [None, ['Karelian']],
    'kro': [None, ['Kru']],
    'kru': [None, ['Kurukh']],
    'kua': ['kj', ['Kuanyama', 'Kwanyama']],
    'kum': [None, ['Kumyk']],
    'kur': ['ku', ['Kurdish']],
    'kut': [None, ['Kutenai']],
    'lad': [None, ['Ladino']],
    'lah': [None, ['Lahnda']],
    'lam': [None, ['Lamba']],
    'lao': ['lo', ['Lao']],
    'lat': ['la', ['Latin']],
    'lav': ['lv', ['Latvian']],
    'lez': [None, ['Lezghian']],
    'lim': ['li', ['Limburgan', 'Limburger', 'Limburgish']],
    'lin': ['ln', ['Lingala']],
    'lit': ['lt', ['Lithuanian']],
    'lol': [None, ['Mongo']],
    'loz': [None, ['Lozi']],
    'ltz': ['lb', ['Luxembourgish', 'Letzeburgesch']],
    'lua': [None, ['Luba-Lulua']],
    'lub': ['lu', ['Luba-Katanga']],
    'lug': ['lg', ['Ganda']],
    'lui': [None, ['Luiseno']],
    'lun': [None, ['Lunda']],
    'luo': [None, ['Luo']],
    'lus': [None, ['Lushai']],
    'mac': ['mk', ['Macedonian']],
    'mad': [None, ['Madurese']],
    'mag': [None, ['Magahi']],
    'mah': ['mh', ['Marshallese']],
    'mai': [None, ['Maithili']],
    'mak': [None, ['Makasar']],
    'mal': ['ml', ['Malayalam']],
    'man': [None, ['Mandingo']],
    'mao': ['mi', ['Maori']],
    'map': [None, ['Austronesian']],
    'mar': ['mr', ['Marathi']],
    'mas': [None, ['Masai']],
    'may': ['ms', ['Malay']],
    'mdf': [None, ['Moksha']],
    'mdr': [None, ['Mandar']],
    'men': [None, ['Mende']],
    'mic': [None, ['Mi\'kmaq', 'Micmac']],
    'min': [None, ['Minangkabau']],
    'mis': [None, ['Uncoded']],
    'mkh': [None, ['Mon-Khmer']],
    'mlg': ['mg', ['Malagasy']],
    'mlt': ['mt', ['Maltese']],
    'mnc': [None, ['Manchu']],
    'mni': [None, ['Manipuri']],
    'mno': [None, ['Manobo']],
    'moh': [None, ['Mohawk']],
    'mon': ['mn', ['Mongolian']],
    'mos': [None, ['Mossi']],
    'mul': [None, ['Multiple']],
    'mun': [None, ['Munda']],
    'mus': [None, ['Creek']],
    'mwl': [None, ['Mirandese']],
    'mwr': [None, ['Marwari']],
    'myn': [None, ['Mayan']],
    'myv': [None, ['Erzya']],
    'nah': [None, ['Nahuatl']],
    'nai': [None, ['North American Indian']],
    'nap': [None, ['Neapolitan']],
    'nau': ['na', ['Nauru']],
    'nav': ['nv', ['Navajo', 'Navaho']],
    'ndo': ['ng', ['Ndonga']],
    'nds': [None, ['Low German', 'Low Saxon', 'German, Low', 'Saxon, Low']],
    'nep': ['ne', ['Nepali']],
    'new': [None, ['Nepal Bhasa', 'Newari']],
    'nia': [None, ['Nias']],
    'nic': [None, ['Niger-Kordofanian']],
    'niu': [None, ['Niuean']],
    'nno': ['nn', ['Norwegian Nynorsk', 'Nynorsk, Norwegian']],
    'nob': ['nb', ['Bokmål, Norwegian', 'Norwegian Bokmål']],
    'nog': [None, ['Nogai']],
    'non': [None, ['Norse, Old']],
    'nor': ['no', ['Norwegian']],
    'nqo': [None, ['N\'Ko']],
    'nso': [None, ['Pedi', 'Sepedi', 'Northern Sotho']],
    'nub': [None, ['Nubian']],
    'nwc': [None, ['Classical Newari', 'Old Newari', 'Classical Nepal Bhasa']],
    'nya': ['ny', ['Chichewa', 'Chewa', 'Nyanja']],
    'nym': [None, ['Nyamwezi']],
    'nyn': [None, ['Nyankole']],
    'nyo': [None, ['Nyoro']],
    'nzi': [None, ['Nzima']],
    'oci': ['oc', ['Occitan']],
    'oji': ['oj', ['Ojibwa']],
    'ori': ['or', ['Oriya']],
    'orm': ['om', ['Oromo']],
    'osa': [None, ['Osage']],
    'oss': ['os', ['Ossetian', 'Ossetic']],
    'oto': [None, ['Otomian']],
    'paa': [None, ['Papuan']],
    'pag': [None, ['Pangasinan']],
    'pal': [None, ['Pahlavi']],
    'pam': [None, ['Pampanga', 'Kapampangan']],
    'pan': ['pa', ['Panjabi', 'Punjabi']],
    'pap': [None, ['Papiamento']],
    'pau': [None, ['Palauan']],
    'per': ['fa', ['Persian']],
    'phi': [None, ['Philippine']],
    'phn': [None, ['Phoenician']],
    'pli': ['pi', ['Pali']],
    'pol': ['pl', ['Polish']],
    'pon': [None, ['Pohnpeian']],
    'por': ['pt', ['Portuguese']],
    'pra': [None, ['Prakrit']],
    'pus': ['ps', ['Pushto', 'Pashto']],
    'qaa': [None, ['Reserved for local use: qaa']],
    'qad': [None, ['Reserved for local use: qad']],
    'que': ['qu', ['Quechua']],
    'raj': [None, ['Rajasthani']],
    'rap': [None, ['Rapanui']],
    'rar': [None, ['Rarotongan', 'Cook Islands Maori']],
    'roa': [None, ['Romance']],
    'roh': ['rm', ['Romansh']],
    'rom': [None, ['Romany']],
    'rum': ['ro', ['Romanian', 'Moldavian', 'Moldovan']],
    'run': ['rn', ['Rundi']],
    'rup': [None, ['Aromanian', 'Arumanian', 'Macedo-Romanian']],
    'rus': ['ru', ['Russian', 'RU']],
    'sad': [None, ['Sandawe']],
    'sag': ['sg', ['Sango']],
    'sah': [None, ['Yakut']],
    'sai': [None, ['South American Indian']],
    'sal': [None, ['Salishan']],
    'sam': [None, ['Samaritan Aramaic']],
    'san': ['sa', ['Sanskrit']],
    'sas': [None, ['Sasak']],
    'sat': [None, ['Santali']],
    'scn': [None, ['Sicilian']],
    'sco': [None, ['Scots']],
    'sel': [None, ['Selkup']],
    'sem': [None, ['Semitic']],
    'sgn': [None, ['Sign']],
    'shn': [None, ['Shan']],
    'sid': [None, ['Sidamo']],
    'sin': ['si', ['Sinhala', 'Sinhalese']],
    'sio': [None, ['Siouan']],
    'sit': [None, ['Sino-Tibetan']],
    'sla': [None, ['Slavic']],
    'slo': ['sk', ['Slovak']],
    'slv': ['sl', ['Slovenian']],
    'sma': [None, ['Southern Sami']],
    'sme': ['se', ['Northern Sami']],
    'smi': [None, ['Sami']],
    'smj': [None, ['Lule Sami']],
    'smn': [None, ['Inari Sami']],
    'smo': ['sm', ['Samoan']],
    'sms': [None, ['Skolt Sami']],
    'sna': ['sn', ['Shona']],
    'snd': ['sd', ['Sindhi']],
    'snk': [None, ['Soninke']],
    'sog': [None, ['Sogdian']],
    'som': ['so', ['Somali']],
    'son': [None, ['Songhai']],
    'sot': ['st', ['Sotho, Southern']],
    'spa': ['es', ['Spanish', 'Castilian']],
    'srd': ['sc', ['Sardinian']],
    'srn': [None, ['Sranan Tongo']],
    'srp': ['sr', ['Serbian']],
    'srr': [None, ['Serer']],
    'ssa': [None, ['Nilo-Saharan']],
    'ssw': ['ss', ['Swati']],
    'suk': [None, ['Sukuma']],
    'sun': ['su', ['Sundanese']],
    'sus': [None, ['Susu']],
    'sux': [None, ['Sumerian']],
    'swa': ['sw', ['Swahili']],
    'swe': ['sv', ['Swedish']],
    'syc': [None, ['Classical Syriac']],
    'syr': [None, ['Syriac']],
    'tah': ['ty', ['Tahitian']],
    'tai': [None, ['Tai']],
    'tam': ['ta', ['Tamil']],
    'tat': ['tt', ['Tatar']],
    'tel': ['te', ['Telugu']],
    'tem': [None, ['Timne']],
    'ter': [None, ['Tereno']],
    'tet': [None, ['Tetum']],
    'tgk': ['tg', ['Tajik']],
    'tgl': ['tl', ['Tagalog']],
    'tha': ['th', ['Thai']],
    'tib': ['bo', ['Tibetan']],
    'tig': [None, ['Tigre']],
    'tir': ['ti', ['Tigrinya']],
    'tiv': [None, ['Tiv']],
    'tkl': [None, ['Tokelau']],
    'tlh': [None, ['Klingon', 'tlhIngan-Hol']],
    'tli': [None, ['Tlingit']],
    'tmh': [None, ['Tamashek']],
    'ton': ['to', ['Tonga']],
    'tpi': [None, ['Tok Pisin']],
    'tsi': [None, ['Tsimshian']],
    'tsn': ['tn', ['Tswana']],
    'tso': ['ts', ['Tsonga']],
    'tuk': ['tk', ['Turkmen']],
    'tum': [None, ['Tumbuka']],
    'tup': [None, ['Tupi']],
    'tur': ['tr', ['Turkish']],
    'tut': [None, ['Altaic']],
    'tvl': [None, ['Tuvalu']],
    'twi': ['tw', ['Twi']],
    'tyv': [None, ['Tuvinian']],
    'udm': [None, ['Udmurt']],
    'uga': [None, ['Ugaritic']],
    'uig': ['ug', ['Uighur', 'Uyghur']],
    'ukr': ['uk', ['Ukrainian']],
    'umb': [None, ['Umbundu']],
    'und': [None, ['Undetermined']],
    'urd': ['ur', ['Urdu']],
    'uzb': ['uz', ['Uzbek']],
    'vai': [None, ['Vai']],
    'ven': ['ve', ['Venda']],
    'vie': ['vi', ['Vietnamese']],
    'vol': ['vo', ['Volapük']],
    'vot': [None, ['Votic']],
    'wak': [None, ['Wakashan']],
    'wal': [None, ['Wolaitta', 'Wolaytta']],
    'war': [None, ['Waray']],
    'was': [None, ['Washo']],
    'wel': ['cy', ['Welsh']],
    'wen': [None, ['Sorbian']],
    'wln': ['wa', ['Walloon']],
    'wol': ['wo', ['Wolof']],
    'xal': [None, ['Kalmyk', 'Oirat']],
    'xho': ['xh', ['Xhosa']],
    'yao': [None, ['Yao']],
    'yap': [None, ['Yapese']],
    'yid': ['yi', ['Yiddish']],
    'yor': ['yo', ['Yoruba']],
    'ypk': [None, ['Yupik']],
    'zap': [None, ['Zapotec']],
    'zbl': [None, ['Blissymbols', 'Blissymbolics', 'Bliss']],
    'zen': [None, ['Zenaga']],
    'zgh': [None, ['Standard Moroccan Tamazight']],
    'zha': ['za', ['Zhuang', 'Chuang']],
    'znd': [None, ['Zande']],
    'zul': ['zu', ['Zulu']],
    'zun': [None, ['Zuni']],
    'zza': [None, ['Zaza', 'Dimili', 'Dimli', 'Kirdki', 'Kirmanjki', 'Zazaki']],
}
_LANGUAGE_STRINGS = misc.make_strings_dict({alpha3: value[1] for alpha3, value in _ISO_639_LANGUAGE_SUBSET.iteritems()})
LANGUAGES = set(_ISO_639_LANGUAGE_SUBSET.iterkeys())

_ENCODINGS = {
    'CP1251': ['windows-1251'],
    'US-ASCII': ['ascii'],
    'UTF-8': ['utf8', 'utf-8-sig'],
    'UTF-16': ['utf-16'],
}
_ENCODING_STRINGS = misc.make_strings_dict(_ENCODINGS)

def alpha3(s):
    return _LANGUAGE_STRINGS[s.lower()]

def alpha2(s):
    return _ISO_639_LANGUAGE_SUBSET[alpha3(s)][0]

def norm_encoding(s):
    return _ENCODING_STRINGS[s.lower()]

def guess(file_path):
    found_languages = set()
    file_name = re.sub(r'\dx', r'', os.path.splitext(os.path.basename(file_path))[0].lower())
    for string in re.findall(r'[a-z]+', file_name, re.IGNORECASE):
        if string in _LANGUAGE_STRINGS:
            found_languages.add(_LANGUAGE_STRINGS[string])
    return list(found_languages)
