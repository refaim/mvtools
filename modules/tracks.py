# coding: utf-8

import math
import re

import misc
import platform
from ffmpeg import Ffmpeg
from formats import FieldOrder, PictureFormat, ColorRange, ColorSpace, VideoFpsStandard, \
    SubtitleCodec, VideoCodec, TrackType

class Track(object):
    # TODO move to mkvmerge class
    TYPE_FLAGS = {
        TrackType.VID: (None, '-D'),
        TrackType.AUD: ('--audio-tracks', '-A'),
        TrackType.SUB: ('--subtitle-tracks', '-S'),
    }

    _DURATION_REGEXP = re.compile(r'(?P<hh>\d+):(?P<mm>\d+):(?P<ss>[\d.]+)')

    def __init__(self, parent_path, parent_format, ffm_data, codec_props):
        self._parent_path = parent_path
        self._parent_format = parent_format
        self._ffm_data = ffm_data
        self._ffmpeg = Ffmpeg()  # TODO pass from outside
        self._duration = None

        self._codec_enums = {}
        self._codec_ids = {}
        self._codec_names = {}
        self._codec_file_extensions = {}
        for codec_enum, (codec_id, codec_name, codec_file_extension) in codec_props.iteritems():
            self._codec_enums[codec_id] = codec_enum
            self._codec_ids[codec_enum] = codec_id
            self._codec_names[codec_enum] = codec_name
            self._codec_file_extensions[codec_enum] = codec_file_extension

    def source_file(self):
        return self._parent_path

    def container_format(self):
        return self._parent_format

    def get_single_track_file_extension(self):
        return self._codec_file_extensions[self.codec()]

    def is_single(self):
        return platform.file_ext(self.source_file()) == self.get_single_track_file_extension()

    def _tags(self):
        return self._ffm_data.setdefault('tags', {})

    def id(self):
        return self._ffm_data['index']

    def qualified_id(self):
        return self.source_file(), self.id()

    def type(self):
        return self._ffm_data['codec_type']

    def codec(self):
        return self._codec_enums[self._codec_id()]

    def _codec_id(self):
        return self._ffm_data['codec_name']

    def codec_name(self):
        return self._codec_names[self.codec()]

    def name(self):
        return self._tags().get('title', '')

    def language(self):
        result = self._tags().get('language')
        if result in [None, 'non']:
            result = 'und'
        return result

    def set_language(self, value):
        self._tags()['language'] = value

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
    _CODEC_PROPS = {
        AudioCodec.AAC_HE: ['aac_he_aac', 'aac_he', '.aac'],
        AudioCodec.AAC_HE_V2: ['aac_he_aacv2', 'aac_he_aacv2', '.aac'],
        AudioCodec.AAC_LC: ['aac_lc', 'aac_lc', '.aac'],
        AudioCodec.AC3: ['ac3', 'ac3', '.ac3'],
        AudioCodec.ADPCM_IMA: ['adpcm_ima_wav', 'adpcm', '.wav'],
        AudioCodec.ADPCM_MS: ['adpcm_ms', 'adpcm', '.wav'],
        AudioCodec.ADPCM_SWF: ['adpcm_swf', 'adpcm', '.wav'],
        AudioCodec.AMR: ['amr_nb', 'amr', '.amr'],
        AudioCodec.ASAO: ['nellymoser', 'asao', '.flv'],
        AudioCodec.COOK: ['cook', 'cook', '.ra'],
        AudioCodec.DTS: ['dts_dts', 'dts', '.dts'],
        AudioCodec.DTS_ES: ['dts_dts_es', 'dts', '.dts'],
        AudioCodec.DTS_HRA: ['dts_dts_hd_hra', 'dtshra', '.dtshr'],
        AudioCodec.DTS_MA: ['dts_dts_hd_ma', 'dtsma', '.dts'],
        AudioCodec.EAC3: ['eac3', 'eac3', '.eac3'],
        AudioCodec.FLAC: ['flac', 'flac', '.flac'],
        AudioCodec.MP2: ['mp2', 'mp2', '.mp2'],
        AudioCodec.MP3: ['mp3', 'mp3', '.mp3'],
        AudioCodec.OPUS: ['opus', 'opus', '.opus'],
        AudioCodec.PCM_MULAW: ['pcm_mulaw', 'pcm', '.wav'],
        AudioCodec.PCM_S16L: ['pcm_s16le', 'pcm', '.wav'],
        AudioCodec.SMK: ['smackaudio', 'smk', '.smk'],
        AudioCodec.SPEEX: ['speex', 'speex', '.spx'],
        AudioCodec.TRUE_HD: ['truehd', 'thd', '.dts'],
        AudioCodec.VORBIS: ['vorbis', 'ogg', '.ogg'],
        AudioCodec.WMA_PRO: ['wmapro', 'wma', '.wma'],
        AudioCodec.WMA_V2: ['wmav2', 'wma', '.wma'],
    }

    def __init__(self, parent_path, parent_format, ffm_data):
        super(AudioTrack, self).__init__(parent_path, parent_format, ffm_data, self._CODEC_PROPS)
        self._codec_overwrite = None

    def _codec_id(self):
        if self._codec_overwrite is not None:
            return self._codec_ids[self._codec_overwrite]

        profile = self._ffm_data.get('profile')
        result = self._ffm_data['codec_name']
        if profile:
            result += '_{}'.format(profile.replace('-', '_').replace(' ', '_'))
        return result.lower()

    def overwrite_codec(self, value):
        self._codec_overwrite = value

    def channels(self):
        return int(self._ffm_data['channels'])

    def delay(self):
        return int(self._ffm_data['start_pts'])


class VideoTrack(Track):
    _CODECS_WITH_PROFILES_AND_LEVELS = {
        VideoCodec.H264,
        VideoCodec.H265,
    }

    _CODEC_PROPS = {
        VideoCodec.FLV1: ['flv1', 'flv', '.mkv'],
        VideoCodec.H263: ['h263', 'h263', '.mkv'],
        VideoCodec.H264: ['h264', 'h264', '.mkv'],
        VideoCodec.H265: ['hevc', 'h265', '.mkv'],
        VideoCodec.MJPEG: ['mjpeg', 'mjpeg', '.mkv'],
        VideoCodec.MPEG1: ['mpeg1video', 'mpeg1', '.mkv'],
        VideoCodec.MPEG2: ['mpeg2video', 'mpeg2', '.mkv'],
        VideoCodec.MPEG4: ['mpeg4', 'mpeg4', '.mkv'],
        VideoCodec.MSMPEG4V1: ['msmpeg4v1', 'mpeg4', '.mkv'],
        VideoCodec.MSMPEG4V2: ['msmpeg4v2', 'mpeg4', '.mkv'],
        VideoCodec.MSMPEG4V3: ['msmpeg4v3', 'mpeg4', '.mkv'],
        VideoCodec.RV30: ['rv30', 'rv30', '.mkv'],
        VideoCodec.RV40: ['rv40', 'rv40', '.mkv'],
        VideoCodec.SMK: ['smackvideo', 'smk', '.mkv'],
        VideoCodec.VC1: ['vc1', 'vc1', '.mkv'],
        VideoCodec.VP6: ['vp6', 'vp6', '.mkv'],
        VideoCodec.VP6F: ['vp6f', 'vp6f', '.mkv'],
        VideoCodec.VP8: ['vp8', 'vp8', '.mkv'],
        VideoCodec.WMV1_WMV7: ['wmv1', 'wmv', '.mkv'],
        VideoCodec.WMV2_WMV8: ['wmv2', 'wmv', '.mkv'],
        VideoCodec.WMV3_WMV9: ['wmv3', 'wmv', '.mkv'],
    }

    @staticmethod
    def dimensions_correct(w, h):
        return w % 16 == h % 8 == 0

    @staticmethod
    def correct_dimensions(w, h, x, y):
        dw = w % 16
        dh = h % 8
        return w - dw, h - dh, x + int(math.ceil(dw * 0.5)), y + int(math.ceil(dh * 0.5))

    def __init__(self, parent_path, parent_format, ffm_data):
        super(VideoTrack, self).__init__(parent_path, parent_format, ffm_data, self._CODEC_PROPS)
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
        if self.codec() not in self._CODECS_WITH_PROFILES_AND_LEVELS:
            return None
        return self._ffmpeg.parse_video_codec_profile(self._ffm_data['profile'])

    def level(self):
        if self.codec() not in self._CODECS_WITH_PROFILES_AND_LEVELS:
            return None
        return self._ffmpeg.parse_video_codec_level(self.codec(), self._ffm_data['level'])

    def pix_fmt(self):
        return self.colors().pix_fmt()

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
            return VideoFpsStandard.NTSC
        if equals(rate_float, 25, 0.1):
            return VideoFpsStandard.PAL
        if any(equals(rate_float, x, 1.0) for x in [15.0, 20.0, 27.3, 29.75, 35.0, 38.795, 125]):
            return VideoFpsStandard.WEBCAM
        if any(equals(rate_float, x, 0.1) for x in [30.3, 50, 120, 90000]) and self.is_hd():
            return VideoFpsStandard.PORN
        if any(equals(rate_float, x, 0.1) for x in [50, 60]):
            return VideoFpsStandard.DEINTERLACED
        assert not self.is_hd()
        return None

    def field_order(self):
        if self._field_order is None:
            raw = self._ffm_data.get('field_order')
            self._field_order = self._ffmpeg.parse_field_order(raw) if raw is not None else FieldOrder.PROGRESSIVE
        return self._field_order


class Colors(object):
    def __init__(self, w, h, standard, ffm_data):
        self._width = w
        self._height = h
        self._standard = standard
        self._ffm_data = ffm_data
        self._ffmpeg = Ffmpeg()

    # TODO move out
    def pix_fmt(self):
        return self._ffmpeg.parse_picture_format(self._ffm_data['pix_fmt'])

    def range(self):
        result = None
        raw = self._ffm_data.get('color_range')
        if raw is not None:
            result = self._ffmpeg.parse_color_range(raw)
        elif self.pix_fmt() in (PictureFormat.YUV420P, PictureFormat.YUV420P10LE):
            result = ColorRange.TV
        return result

    def is_hd(self):
        return self._width >= 1200 or self._height >= 700

    def correct_space(self):
        if self.is_hd():
            return ColorSpace.BT_709
        if self._standard == VideoFpsStandard.PAL:
            return ColorSpace.BT_601_PAL,
        if self._standard == VideoFpsStandard.NTSC:
            return ColorSpace.BT_601_NTSC
        assert not self.is_hd()
        return None

    def _guess_metric(self, metric):
        raw = self._ffm_data.get(metric)
        return self._ffmpeg.parse_color_space(raw) if raw is not None else self.correct_space()

    def space(self):
        raw = self._ffm_data.get('color_space')
        if raw is not None and self._ffmpeg.parse_color_space(raw) == ColorSpace.FCC:
            return ColorSpace.FCC
        return self._guess_metric('color_space')

    def trc(self):
        return self._guess_metric('color_transfer')

    def primaries(self):
        return self._guess_metric('color_primaries')


class SubtitleTrack(Track):
    _RE_SUB_CAPTIONS_NUM = re.compile(r', (?P<num>\d+) caption')

    _CODEC_PROPS = {
        SubtitleCodec.ASS: ['ass', 'ass', '.ass'],
        SubtitleCodec.MOV: ['mov_text', 'mov', '.ass'],
        SubtitleCodec.PGS: ['hdmv_pgs_subtitle', 'pgs', '.sup'],
        SubtitleCodec.SRT: ['subrip', 'srt', '.srt'],
        SubtitleCodec.VOBSUB: ['dvd_subtitle', 'vbs', None],
    }

    def __init__(self, parent_path, parent_format, ffm_data):
        super(SubtitleTrack, self).__init__(parent_path, parent_format, ffm_data, self._CODEC_PROPS)
        self._encoding = None

    def is_binary(self):
        return self.codec() in (SubtitleCodec.PGS, SubtitleCodec.VOBSUB)

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
