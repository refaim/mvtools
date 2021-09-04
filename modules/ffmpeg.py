from formats import PictureFormat, ColorSpace, ColorRange, VideoCodec, VideoCodecProfile, VideoCodecLevel, FieldOrder, \
    TrackType
from misc import flip_dict

class Ffmpeg(object):
    STREAM_ARGUMENT_AUD = 'a'
    STREAM_ARGUMENT_SUB = 's'
    STREAM_ARGUMENT_VID = 'V'

    _TRACK_TYPE_RAW_TO_ENUM = {
        'video': TrackType.VID,
        'audio': TrackType.AUD,
        'subtitle': TrackType.SUB,
        'chapters': TrackType.CHA,
    }

    _VIDEO_ENCODING_LIBRARY_ENUM_TO_ARGUMENT = {
        VideoCodec.H264: 'libx264',
        VideoCodec.H265: 'libx265',
    }

    _VIDEO_CODEC_PROFILE_RAW_TO_ENUM = {
        'Baseline': VideoCodecProfile.BASELINE,
        'Constrained Baseline': VideoCodecProfile.BASELINE,
        'High': VideoCodecProfile.HIGH,
        'High 10': VideoCodecProfile.HIGH_10,
        'Main': VideoCodecProfile.MAIN,
        'Main 10': VideoCodecProfile.MAIN_10,
    }

    _VIDEO_CODEC_PROFILE_ENUM_TO_ARGUMENT = {
        VideoCodec.H264: {
            VideoCodecProfile.BASELINE: 'baseline',
            VideoCodecProfile.HIGH: 'high',
            VideoCodecProfile.MAIN: 'main',
        },
        VideoCodec.H265: {
            VideoCodecProfile.MAIN: 'main',
        }
    }

    _VIDEO_CODEC_LEVEL_RAW_TO_ENUM = {
        VideoCodec.H264: {
            10: VideoCodecLevel.L10,
            11: VideoCodecLevel.L11,
            12: VideoCodecLevel.L12,
            13: VideoCodecLevel.L13,
            20: VideoCodecLevel.L20,
            21: VideoCodecLevel.L21,
            22: VideoCodecLevel.L22,
            30: VideoCodecLevel.L30,
            31: VideoCodecLevel.L31,
            32: VideoCodecLevel.L32,
            40: VideoCodecLevel.L40,
            41: VideoCodecLevel.L41,
            42: VideoCodecLevel.L42,
            50: VideoCodecLevel.L50,
            51: VideoCodecLevel.L51,
            52: VideoCodecLevel.L52,
            60: VideoCodecLevel.L60,
            61: VideoCodecLevel.L61,
            62: VideoCodecLevel.L62,
        },
        VideoCodec.H265: {
            # VideoCodecLevel.L10,
            # VideoCodecLevel.L20,
            # VideoCodecLevel.L21,
            # VideoCodecLevel.L30,
            # VideoCodecLevel.L31,
            120: VideoCodecLevel.L40,
            150: VideoCodecLevel.L50,
            153: VideoCodecLevel.L51,
            156: VideoCodecLevel.L52,
            180: VideoCodecLevel.L60,
            183: VideoCodecLevel.L61,
            186: VideoCodecLevel.L62,
        }
    }

    _PICTURE_FORMAT_RAW_TO_ENUM = {
        'pal8': PictureFormat.PAL8,
        'yuv420p': PictureFormat.YUV420P,
        'yuvj420p': PictureFormat.YUVJ420P,
        'yuv420p10le': PictureFormat.YUV420P10LE,
    }

    _COLOR_SPACE_RAW_TO_ENUM = {
        'bt2020nc': ColorSpace.BT_2020,
        'bt470bg': ColorSpace.BT_601_PAL,
        'bt709': ColorSpace.BT_709,
        'fcc': ColorSpace.FCC,
        'smpte170m': ColorSpace.BT_601_NTSC,
    }
    _COLOR_TRC_RAW_TO_ENUM = _COLOR_SPACE_RAW_TO_ENUM
    _COLOR_PRIMARIES_RAW_TO_ENUM = _COLOR_SPACE_RAW_TO_ENUM

    _COLOR_RANGE_RAW_TO_ENUM = {
        'pc': ColorRange.PC,
        'tv': ColorRange.TV,
    }

    _FIELD_ORDER_RAW_TO_ENUM = {
        'progressive': FieldOrder.PROGRESSIVE,
        'tt': FieldOrder.INTERLACED_TOP,
        'bb': FieldOrder.INTERLACED_BOT,
    }

    def __init__(self):
        self._video_codec_level_enum_to_argument = {}
        for codec, levels in self._VIDEO_CODEC_LEVEL_RAW_TO_ENUM.iteritems():
            self._video_codec_level_enum_to_argument[codec] = flip_dict(levels)

        h265_levels = {}
        for level, argument in self._video_codec_level_enum_to_argument[VideoCodec.H265].iteritems():
            h265_levels[level] = int(argument / 3)
        self._video_codec_level_enum_to_argument[VideoCodec.H265] = h265_levels

        self._picture_format_enum_to_argument = flip_dict(self._PICTURE_FORMAT_RAW_TO_ENUM)
        self._color_range_enum_to_argument = flip_dict(self._COLOR_RANGE_RAW_TO_ENUM)
        self._color_space_enum_to_argument = flip_dict(self._COLOR_SPACE_RAW_TO_ENUM)
        self._color_primaries_enum_to_argument = flip_dict(self._COLOR_PRIMARIES_RAW_TO_ENUM)
        self._color_trc_enum_to_argument = flip_dict(self._COLOR_TRC_RAW_TO_ENUM)
        self._color_trc_enum_to_argument[ColorSpace.BT_601_PAL] = 'gamma28'
        self._field_order_enum_to_argument = flip_dict(self._FIELD_ORDER_RAW_TO_ENUM)

    def parse_track_type(self, value):
        return self._TRACK_TYPE_RAW_TO_ENUM[value]

    def build_video_encoding_library_argument(self, codec):
        return self._VIDEO_ENCODING_LIBRARY_ENUM_TO_ARGUMENT[codec]

    def parse_video_codec_profile(self, value):
        return self._VIDEO_CODEC_PROFILE_RAW_TO_ENUM[value]
    def build_video_codec_profile_argument(self, codec, profile):
        return self._VIDEO_CODEC_PROFILE_ENUM_TO_ARGUMENT[codec][profile]

    def parse_video_codec_level(self, codec, value):
        return self._VIDEO_CODEC_LEVEL_RAW_TO_ENUM[codec][value]
    def build_video_codec_level_argument(self, codec, level):
        return self._video_codec_level_enum_to_argument[codec][level]

    def parse_picture_format(self, value):
        return self._PICTURE_FORMAT_RAW_TO_ENUM[value]
    def build_picture_format_argument(self, value):
        return self._picture_format_enum_to_argument[value]

    def parse_color_space(self, value):
        return self._COLOR_SPACE_RAW_TO_ENUM[value]
    def build_color_space_argument(self, value):
        return self._color_space_enum_to_argument[value]

    def parse_color_trc(self, value):
        return self._COLOR_TRC_RAW_TO_ENUM[value]
    def build_color_trc_argument(self, value):
        return self._color_trc_enum_to_argument[value]

    def parse_color_primaries(self, value):
        return self._COLOR_PRIMARIES_RAW_TO_ENUM[value]
    def build_color_primaries_argument(self, value):
        return self._color_primaries_enum_to_argument[value]

    def parse_color_range(self, value):
        return self._COLOR_RANGE_RAW_TO_ENUM[value]
    def build_color_range_argument(self, value):
        return self._color_range_enum_to_argument[value]

    def parse_field_order(self, value):
        return self._FIELD_ORDER_RAW_TO_ENUM[value]
    def build_field_order(self, value):
        return self._field_order_enum_to_argument[value]
