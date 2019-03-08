# coding: utf-8

import math
import re

import misc
import platform

class Track(object):
    AUD = 'audio'
    VID = 'video'
    SUB = 'subtitle'
    CHA = 'chapters'

    TYPE_FLAGS = {
        VID: (None, '-D'),
        AUD: ('--audio-tracks', '-A'),
        SUB: ('--subtitle-tracks', '-S'),
    }

    _CODEC_PROPS_IDX_NAME = 0
    _CODEC_PROPS_IDX_FEXT = 1

    def __init__(self, parent_path, parent_format, ffm_data, codec_props):
        self._parent_path = parent_path
        self._parent_format = parent_format
        self._ffm_data = ffm_data
        self._codec_props = codec_props
        self._duration = None

    def source_file(self):
        return self._parent_path

    def container_format(self):
        return self._parent_format

    def get_single_track_file_extension(self):
        result = self._codec_props[self.codec_id()][self._CODEC_PROPS_IDX_FEXT]
        assert result is not None
        return result

    def is_single(self):
        return platform.file_ext(self.source_file()) == self.get_single_track_file_extension()

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

    def codec_unknown(self):
        return self.codec_id() not in self._codec_props

    def codec_name(self):
        if self.codec_unknown():
            return self.codec_id()
        return self._codec_props[self.codec_id()][self._CODEC_PROPS_IDX_NAME]

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
        n = self._tags().get('NUMBER_OF_FRAMES-eng', None) or self._ffm_data.get('nb_frames', None)
        return misc.try_int(n)

    def is_forced(self):
        forced = self._ffm_data['disposition']['forced']
        return forced if forced is None else bool(forced)

    def set_forced(self, value):
        self._ffm_data['disposition']['forced'] = value

    def is_default(self):
        return bool(self._ffm_data['disposition']['default'])

class AudioTrack(Track):
    AAC_HE = 'aac_he_aac'
    AAC_LC = 'aac_lc'
    AC3 = 'ac3'
    AMR = 'amr_nb'
    DTS = 'dts_dts'
    DTS_ES = 'dts_dts_es'
    DTS_HRA = 'dts_dts_hd_hra'
    DTS_MA = 'dts_dts_hd_ma'
    EAC3 = 'eac3'
    FLAC = 'flac'
    MP2 = 'mp2'
    MP3 = 'mp3'
    OPUS = 'opus'
    PCM_S16L = 'pcm_s16le'
    SPEEX = 'speex'
    TRUE_HD = 'truehd'
    VORBIS = 'vorbis'
    WMAV2 = 'wmav2'

    _CODEC_PROPS = {
        AAC_HE: ['aac_he', '.aac'],
        AAC_LC: ['aac_lc', '.aac'],
        AC3: ['ac3', '.ac3'],
        AMR: ['amr', '.amr'],
        DTS: ['dts', '.dts'],
        DTS_ES: ['dts', '.dts'],
        DTS_HRA: ['dtshra', '.dtshr'],
        DTS_MA: ['dtsma', '.dts'],
        EAC3: ['eac3', '.eac3'],
        FLAC: ['flac', '.flac'],
        MP2: ['mp2', '.mp2'],
        MP3: ['mp3', '.mp3'],
        OPUS: ['opus', '.opus'],
        PCM_S16L: ['pcm', '.wav'],
        SPEEX: ['speex', '.spx'],
        TRUE_HD: ['thd', '.dts'],
        VORBIS: ['ogg', '.ogg'],
        WMAV2: ['wma', '.wma'],
    }

    def __init__(self, parent_path, parent_format, ffm_data):
        super(AudioTrack, self).__init__(parent_path, parent_format, ffm_data, self._CODEC_PROPS)

    def codec_id(self):
        profile = self._ffm_data.get('profile')
        result = self._ffm_data['codec_name']
        if profile:
            result += '_{}'.format(profile.replace('-', '_').replace(' ', '_'))
        return result.lower()

    def set_codec_id(self, value):
        self._ffm_data['profile'] = None
        self._ffm_data['codec_name'] = value

    def channels(self):
        return int(self._ffm_data['channels'])

    def delay(self):
        return int(self._ffm_data['start_pts'])

class VideoTrack(Track):
    PAL = 'not_ffmpeg_const_pal'
    NTSC = 'not_ffmpeg_const_ntsc'
    DEINT = 'not_ffmpeg_const_deinterlaced'

    YUV420P = 'yuv420p'
    YUVJ420P = 'yuvj420p'
    YUV420P10LE = 'yuv420p10le'
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

    def __init__(self, parent_path, parent_format, ffm_data):
        super(VideoTrack, self).__init__(parent_path, parent_format, ffm_data, {})
        self._crf = None
        self._field_order = None
        self._colors = Colors(self.width(), self.height(), self.standard(), self._ffm_data)

    def width(self):
        return self._ffm_data['width']

    def height(self):
        return self._ffm_data['height']

    def is_hd(self):
        return self.width() >= 1200 or self.height() >= 700

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
        def equals(x, y, p):
            return abs(x - y) <= p
        rate_string = self._ffm_data['r_frame_rate']
        a, b = [float(n) for n in rate_string.split('/')]
        rate_float = a / b
        if any(equals(rate_float, x, 0.1) for x in [23.976, 29.97]):
            return self.NTSC
        if equals(rate_float, 25, 0.1):
            return self.PAL
        if any(equals(rate_float, x, 0.1) for x in [50, 60]):
            return self.DEINT
        assert not self.is_hd()
        return None

    def field_order(self):
        if self._field_order is None:
            fo = self._ffm_data.get('field_order')
            if fo is None:
                fo = self.FO_PRG
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
    FCC = 'fcc'

    RANGE_PC = 'pc'
    RANGE_TV = 'tv'

    def __init__(self, w, h, standard, ffm_data):
        self._width = w
        self._height = h
        self._standard = standard
        self._ffm_data = ffm_data

    def range(self):
        result = self._ffm_data.get('color_range')
        if result is None and self._ffm_data['pix_fmt'] in (VideoTrack.YUV420P, VideoTrack.YUV420P10LE):
            result = self.RANGE_TV
        return result

    def is_hd(self):
        return self._width >= 1200 or self._height >= 700

    def correct_space(self):
        if self.is_hd():
            return self.BT_709
        if self._standard == VideoTrack.PAL:
            return self.BT_601_PAL
        if self._standard == VideoTrack.NTSC:
            return self.BT_601_NTSC
        assert not self.is_hd()
        return None

    def _guess_metric(self, metric):
        result = self._ffm_data.get(metric)
        if result is None:
            result = self.correct_space()
        assert result in (self.BT_709, self.BT_601_PAL, self.BT_601_NTSC, self.FCC)
        return result

    def space(self):
        if self._ffm_data.get('color_space') == self.FCC:
            return self.FCC
        return self._guess_metric('color_space')

    def trc(self):
        return self._guess_metric('color_transfer')

    def primaries(self):
        return self._guess_metric('color_primaries')

class SubtitleTrack(Track):
    _RE_SUB_CAPTIONS_NUM = re.compile(r', (?P<num>\d+) caption')

    ASS = 'ass'
    MOV = 'mov_text'
    PGS = 'hdmv_pgs_subtitle'
    SRT = 'subrip'
    VOBSUB = 'dvd_subtitle'

    _CODEC_PROPS = {
        ASS: ['ass', '.ass'],
        MOV: ['mov', '.ass'],
        PGS: ['pgs', '.sup'],
        SRT: ['srt', '.srt'],
        VOBSUB: ['vbs', None],
    }

    def __init__(self, parent_path, parent_format, ffm_data):
        super(SubtitleTrack, self).__init__(parent_path, parent_format, ffm_data, self._CODEC_PROPS)
        self._encoding = None

    def is_binary(self):
        return self.codec_id() in (self.PGS, self.VOBSUB)

    def is_text(self):
        return not self.is_binary()

    def encoding(self):
        return self._encoding

    def set_encoding(self, value):
        self._encoding = value

    def num_captions(self):
        match = self._RE_SUB_CAPTIONS_NUM.search(self.source_file())
        if match:
            return int(match.groupdict()['num'])
        return None

class ChaptersTrack(Track):
    def __init__(self, parent_path, parent_format, ffm_data):
        super(ChaptersTrack, self).__init__(parent_path, parent_format, ffm_data, {})

    def id(self):
        return id(self)
