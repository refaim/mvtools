# coding: utf-8

import math
import re

import misc
import platform

class Track(object):
    AUD = 'audio'
    VID = 'video'
    SUB = 'subtitle'

    TYPE_FLAGS = {
        VID: (None, '-D'),
        AUD: ('--audio-tracks', '-A'),
        SUB: ('--subtitle-tracks', '-S'),
    }

    def __init__(self, parent_path, ffm_data, codec_names):
        self._parent_path = parent_path
        self._ffm_data = ffm_data
        self._codec_names = codec_names
        self._duration = None

    def source_file(self):
        return self._parent_path

    def _tags(self):
        return self._ffm_data.setdefault('tags', {})

    def id(self):
        return self._ffm_data['index']

    def qualified_id(self):
        return (self.source_file(), self.id())

    def type(self):
        return self._ffm_data['codec_type']

    def codec_id(self):
        return self._ffm_data['codec_name']

    def codec_name(self):
        return self._codec_names[self.codec_id()]

    def name(self):
        return self._tags().get('title', '')

    def language(self):
        result = self._tags().get('language')
        if result in [None, 'non']:
            result = 'und'
        return result

    def set_language(self, value):
        self._tags()['language'] = value

    _DURATION_REGEXP = re.compile(r'(?P<hh>\d+):(?P<mm>\d+):(?P<ss>[\d\.]+)')

    def duration(self):
        if self._duration is None:
            duration_string = self._tags().get('DURATION-eng')
            if duration_string:
                match = self._DURATION_REGEXP.match(duration_string)
                value = match.groupdict()
                self._duration = (int(value['hh']) * 60 + int(value['mm'])) * 60 + float(value['ss'])
        return self._duration

    def frames_len(self):
        return misc.try_int(self._tags().get('NUMBER_OF_FRAMES-eng', None))

    def is_forced(self):
        return bool(self._ffm_data['disposition']['forced']) or \
            any(s in self.name().lower() for s in [u'forced', u'форсир'])

    def set_forced(self, value):
        self._ffm_data['disposition']['forced'] = value

    def is_default(self):
        return bool(self._ffm_data['disposition']['default'])

class AudioTrack(Track):
    AAC_HE = 'aac_he_aac'
    AAC_LC = 'aac_lc'
    AC3 = 'ac3'
    DTS = 'dts_dts'
    DTS_HD = 'dts_dts_hd_ma'
    FLAC = 'flac'
    MP2 = 'mp2'
    MP3 = 'mp3'
    PCM_S16L = 'pcm_s16le'

    CODEC_PROPS_IDX_NAME = 0
    CODEC_PROPS_IDX_FEXT = 1
    CODEC_PROPS = {
        AAC_HE: ['aac_he', '.m4a'],
        AAC_LC: ['aac_lc', '.m4a'],
        AC3: ['ac3', '.ac3'],
        DTS: ['dts', '.dts'],
        DTS_HD: ['dhm', None],
        FLAC: ['flac', '.flac'],
        MP2: ['mp2', '.mp2'],
        MP3: ['mp3', '.mp3'],
        PCM_S16L: ['pcm', '.wav'],
    }

    def __init__(self, parent_path, ffm_data):
        codec_names = { codec_id: props[self.CODEC_PROPS_IDX_NAME]
            for codec_id, props in self.CODEC_PROPS.iteritems() }
        super(AudioTrack, self).__init__(parent_path, ffm_data, codec_names)

    def get_single_track_file_extension(self):
        return self.CODEC_PROPS[self.codec_id()][self.CODEC_PROPS_IDX_FEXT]

    def is_single(self):
        return platform.file_ext(self.source_file()) == self.get_single_track_file_extension()

    def codec_id(self):
        profile = self._ffm_data.get('profile')
        result = self._ffm_data['codec_name']
        if profile:
            result += '_{}'.format(profile.replace('-', '_').replace(' ', '_'))
        return result.lower()

    def channels(self):
        return int(self._ffm_data['channels'])

class VideoTrack(Track):
    PAL = 'not_ffmpeg_const_pal'
    NTSC = 'not_ffmpeg_const_ntsc'
    _STANDARDS = {
        '13978/583': NTSC,
        '20327/813': PAL,
        '20877/835': PAL,
        '24000/1001': NTSC,
        '25/1': PAL,
        '2997/125': NTSC,
        '30000/1001': NTSC,
    }

    YUV420P = 'yuv420p'
    CODEC_H264 = 'h264'
    PROFILE_HIGH = 'High'
    LEVEL_41 = 41

    FO_PRG = 'progressive'
    FO_INT_TOP = 'tt'
    FO_INT_BOT = 'bb'

    @staticmethod
    def dimensions_correct(w, h):
        return w % 16 == h % 8 == 0

    @staticmethod
    def correct_dimensions(w, h, x, y):
        dw = w % 16
        dh = h % 8
        return (w - dw, h - dh, x + int(math.ceil(dw * 0.5)), y + int(math.ceil(dh * 0.5)))

    def __init__(self, parent_path, ffm_data):
        super(VideoTrack, self).__init__(parent_path, ffm_data, {})
        self._crf = None
        self._field_order = None
        self._colors = Colors(self.width(), self.height(), self.standard(), self._ffm_data)

    def width(self):
        p = self._ffm_data
        assert p['width'] == p['coded_width'] or p['coded_width'] == 0
        return p['width']

    def height(self):
        p = self._ffm_data
        assert p['height'] == p['coded_height'] or p['coded_height'] == 0
        return p['height']

    def profile(self):
        return self._ffm_data['profile']

    def level(self):
        return self._ffm_data['level']

    def pix_fmt(self):
        return self._ffm_data['pix_fmt']

    def crf(self):
        return self._crf

    def set_crf(self, value):
        self._crf = value

    def colors(self):
        return self._colors

    def standard(self):
        return self._STANDARDS[self._ffm_data['r_frame_rate']]

    def field_order(self):
        if self._field_order is None:
            fo = self._ffm_data.get('field_order')
            if fo is not None:
                assert fo in (self.FO_PRG, self.FO_INT_BOT, self.FO_INT_TOP)
                self._field_order = fo
        return self._field_order

    def set_field_order(self, value):
        self._field_order = value

class Colors(object):
    BT_709 = 'bt709'
    BT_601_PAL = 'bt470bg'
    BT_601_NTSC = 'smpte170m'

    RANGE_TV = 'tv'

    def __init__(self, w, h, standard, ffm_data):
        self._width = w
        self._height = h
        self._standard = standard
        self._ffm_data = ffm_data

    def range(self):
        result = self._ffm_data.get('color_range')
        if result is None and self._ffm_data['pix_fmt'] == VideoTrack.YUV420P:
            result = self.RANGE_TV
        return result

    def correct_space(self):
        result = None
        if self._height >= 700:
            result = self.BT_709
        elif self._standard == VideoTrack.PAL:
            result = self.BT_601_PAL
        elif self._standard == VideoTrack.NTSC:
            result = self.BT_601_NTSC
        return result

    def _guess_metric(self, metric):
        result = self._ffm_data.get(metric)
        if result is None:
            result = self.correct_space()
        assert result in (self.BT_709, self.BT_601_PAL, self.BT_601_NTSC)
        return result

    def space(self):
        return self._guess_metric('color_space')

    def trc(self):
        return self._guess_metric('color_transfer')

    def primaries(self):
        return self._guess_metric('color_primaries')

class SubtitleTrack(Track):
    _RE_SUB_CAPTIONS_NUM = re.compile(r', (?P<num>\d+) caption')

    ASS = 'ass'
    PGS = 'hdmv_pgs_subtitle'
    SRT = 'subrip'

    CODEC_NAMES = {
        ASS: 'ass',
        PGS: 'pgs',
        SRT: 'srt',
    }

    def __init__(self, parent_path, ffm_data):
        super(SubtitleTrack, self).__init__(parent_path, ffm_data, self.CODEC_NAMES)
        self._encoding = None

    def is_binary(self):
        return self.codec_id() == self.PGS

    def encoding(self):
        return self._encoding

    def set_encoding(self, value):
        self._encoding = value

    def num_captions(self):
        match = self._RE_SUB_CAPTIONS_NUM.search(self.source_file())
        if match:
            return int(match.groupdict()['num'])
        return None
