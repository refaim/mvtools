import json
from abc import ABCMeta, abstractmethod
from typing import List, Dict

from modules import cmd
from modules import platform
from modules.ffmpeg import Ffmpeg
from modules.formats import FileFormat, FieldOrder, AudioCodec, TrackType
from modules.misc import Struct


class Detector:
    __metaclass__ = ABCMeta

    @abstractmethod
    def is_container_format_supported(self, container_format):
        pass

    @abstractmethod
    def detect(self, path):
        pass

class GenericFileInfo(Struct):
    __metaclass__ = ABCMeta

    def describe(self):
        self.tracks_by_type = {}  # type: Dict[int, Dict[int, DetectedTrack]]
        for track_type in TrackType.list_definitions():
            self.tracks_by_type[track_type] = {}

class MiFileInfo(GenericFileInfo):
    def describe(self):
        super(MiFileInfo, self).describe()
        self.file_format = None

class FfmpegFileInfo(GenericFileInfo):
    pass

class DetectedTrack(Struct):
    def describe(self):
        self.id = None
        self.type = None

class FfmpegTrack(DetectedTrack):
    def describe(self):
        super(FfmpegTrack, self).describe()
        self.raw_data = None
        self.is_default = None

class FfmpegVideoTrack(FfmpegTrack):
    def describe(self):
        super(FfmpegVideoTrack, self).describe()
        self.type = TrackType.VID
        self.width = None
        self.height = None
        self.field_order = None

class MiVideoTrack(DetectedTrack):
    def describe(self):
        super(MiVideoTrack, self).describe()
        self.type = TrackType.VID
        self.field_order = None

class MiAudioTrack(DetectedTrack):
    def describe(self):
        super(MiAudioTrack, self).describe()
        self.type = TrackType.AUD
        self.codec = None

class FfmpegAudioTrack(FfmpegTrack):
    def describe(self):
        super(FfmpegAudioTrack, self).describe()
        self.type = TrackType.AUD

class FfmpegSubtitleTrack(FfmpegTrack):
    def describe(self):
        super(FfmpegSubtitleTrack, self).describe()
        self.type = TrackType.SUB

class MiDetector(Detector):
    # TODO write test that checks that every _supported_ FileFormat has association here
    _FILE_FORMATS = {
        ('AMR', None): FileFormat.AMR,
        ('AVI', 'OpenDML'): FileFormat.AVI,
        ('AVI', None): FileFormat.AVI,
        ('Chapters', None): FileFormat.CHA,
        ('E-AC-3', None): FileFormat.EAC3,
        ('FLAC', None): FileFormat.FLAC,
        ('Flash Video', None): FileFormat.FLV,
        ('Matroska', None): FileFormat.MKV,
        ('MPEG Audio', None): FileFormat.MP3,
        ('MPEG-4', '3GPP Media Release 4'): FileFormat.x3GP,
        ('MPEG-4', '3GPP Media Release 5'): FileFormat.x3GP,
        ('MPEG-4', 'Apple audio with iTunes info'): FileFormat.M4A,
        ('MPEG-4', 'Base Media / Version 2'): FileFormat.MP4,
        ('MPEG-4', 'Base Media'): FileFormat.MP4,
        ('MPEG-4', 'QuickTime'): FileFormat.MOV,
        ('MPEG-4', 'Sony PSP'): FileFormat.MP4,
        ('MPEG-4', None): FileFormat.MP4,
        ('MPEG-4', None, '.m4v'): FileFormat.M4V,
        ('MPEG-PS', None): FileFormat.MPG,
        ('MPEG-TS', None): FileFormat.TS,
        ('Ogg', None): FileFormat.OGG,
        ('PGS', None): FileFormat.SUP,
        ('RealMedia', None): FileFormat.RM,
        ('SubRip', None): FileFormat.SRT,
        ('Wave', None): FileFormat.WAV,
        ('WebM', None): FileFormat.WEBM,
        ('Windows Media', None): FileFormat.WMV,
    }

    _RAW_TRACK_TYPE_TO_ENUM = {
        'Video': TrackType.VID,
        'Audio': TrackType.AUD,
    }

    _FIELD_ORDERS = {
        ('Progressive', None): FieldOrder.PROGRESSIVE,
        ('Interlaced', 'TFF'): FieldOrder.INTERLACED_TOP,
        ('MBAFF', 'TFF'): FieldOrder.INTERLACED_TOP,
        (None, None): None,
    }

    _AUDIO_CODECS = {
        (('Format', 'AAC'), ('Format_AdditionalFeatures', 'LC'),): AudioCodec.AAC_LC,
        (('Format', 'AC-3'),): AudioCodec.AC3,
        (('Format', 'AMR'), ('Format_Profile', 'Narrow band'),): AudioCodec.AMR,
        (('Format', 'FLAC'),): AudioCodec.FLAC,
        (('Format', 'MPEG Audio'), ('Format_Profile', 'Layer 2'),): AudioCodec.MP2,
        (('Format', 'MPEG Audio'), ('Format_Profile', 'Layer 3'),): AudioCodec.MP3,
        (('Format', 'Opus'),): AudioCodec.OPUS,
        (('Format', 'PCM'), ('Format_Settings_Sign', 'Signed'), ('BitDepth', '16'), ('Format_Settings_Endianness', 'Little'),): AudioCodec.PCM_S16L,
        (('Format', 'Vorbis'),): AudioCodec.VORBIS,
        (('Format', 'WMA'), ('Format_Version', '2'),): AudioCodec.WMA_V2,
    }

    def _parse_generic_track(self, data, track):
        # type: (dict, DetectedTrack) -> DetectedTrack
        track.id = int(data['ID']) - 1 if 'ID' in data else None
        return track

    def _build_parse_video_track(self, data):
        # noinspection PyTypeChecker
        track = self._parse_generic_track(data, MiVideoTrack())  # type: MiVideoTrack
        track.field_order = self._FIELD_ORDERS[(data.get('ScanType'), data.get('ScanOrder'))]
        return track

    def _build_parse_audio_track(self, data):
        # noinspection PyTypeChecker
        track = self._parse_generic_track(data, MiAudioTrack())  # type: MiAudioTrack

        codec_key = []
        possible_parameters = ['Format', 'Format_Profile', 'Format_AdditionalFeatures']
        if data['Format'] == 'PCM':
            possible_parameters.extend(['Format_Settings_Sign', 'BitDepth', 'Format_Settings_Endianness'])
        elif data['Format'] == 'WMA':
            possible_parameters.extend(['Format_Version'])
        for parameter in possible_parameters:
            if parameter in data:
                codec_key.append((parameter, data[parameter]))
        track.codec = self._AUDIO_CODECS[tuple(codec_key)]

        return track

    def _build_parse_subtitle_track(self, data):
        pass

    def detect(self, path):
        result = MiFileInfo()

        for track_data in json.loads(platform.execute(u'mediainfo --Output=JSON {}'.format(cmd.quote(path))))['media']['track']:
            raw_track_type = track_data['@type']

            if raw_track_type == 'Menu':
                pass
            elif raw_track_type == 'General':
                key = [track_data.get('Format'), track_data.get('Format_Profile')]
                if platform.file_ext(path) == '.m4v':
                    key.append('.m4v')
                result.file_format = self._FILE_FORMATS[tuple(key)]
            else:
                track = None
                track_type = self._RAW_TRACK_TYPE_TO_ENUM[raw_track_type]
                if track_type == TrackType.VID:
                    track = self._build_parse_video_track(track_data)
                elif track_type == TrackType.AUD:
                    track = self._build_parse_audio_track(track_data)
                assert track is not None
                result.tracks_by_type[track_type][track.id] = track

                # TODO
                # if 'ES' in track_info.get('Format_Profile', ''):
                #     track.overwrite_codec(AudioCodec.DTS_ES)

                # TODO
                # if track_format is None:
                #     _, extension = os.path.splitext(media_path.lower())
                #     if extension == '.srt':
                #         track_format = 'SubRip'
                #     elif extension == '.sup':
                #         track_format = 'PGS'
                #     elif 'chapters' in media_path.lower():
                #         track_format = 'Chapters'
        return result

    def is_container_format_supported(self, container_format):
        return container_format != FileFormat.AC3


class FfmpegDetector(Detector):
    def __init__(self, ffmpeg):
        # type: (Ffmpeg) -> None
        self._ffmpeg = ffmpeg

    def _parse_generic_track(self, data, track):
        # type: (dict, FfmpegTrack) -> FfmpegTrack
        track.id = data['index']
        track.raw_data = data
        track.is_default = bool(data['disposition']['default'])
        return track

    def _build_parse_video_track(self, data):
        # noinspection PyTypeChecker
        track = self._parse_generic_track(data, FfmpegVideoTrack())  # type: FfmpegVideoTrack
        track.width = int(data['width'])
        track.height = int(data['height'])

        raw_field_order = data.get('field_order')
        if raw_field_order is not None:
            track.field_order = self._ffmpeg.parse_field_order(raw_field_order)

        return track

    def _build_parse_audio_track(self, data):
        # noinspection PyTypeChecker
        track = self._parse_generic_track(data, FfmpegAudioTrack())  # type: FfmpegAudioTrack
        return track

    def _build_parse_subtitle_track(self, data):
        # noinspection PyTypeChecker
        track = self._parse_generic_track(data, FfmpegSubtitleTrack())  # type: FfmpegSubtitleTrack
        return track

    def detect(self, path):
        command = [
            u'ffprobe',
            u'-v quiet',
            u'-print_format json',
            u'-probesize {}'.format(50 * 1024 * 1024),
            u'-analyzeduration {}'.format(int(3e+7)),
            u'-show_streams',
            cmd.quote(path),
        ]

        result = FfmpegFileInfo()
        for stream in json.loads(platform.execute(u' '.join(command)))['streams']:
            raw_track_type = stream['codec_type']
            if raw_track_type == 'data':
                pass
            else:
                track_type = self._ffmpeg.parse_track_type(raw_track_type)
                track = None
                if track_type == TrackType.VID:
                    track = self._build_parse_video_track(stream)
                elif track_type == TrackType.AUD:
                    track = self._build_parse_audio_track(stream)
                elif track_type == TrackType.SUB:
                    track = self._build_parse_subtitle_track(stream)
                assert track is not None
                result.tracks_by_type[track_type][track.id] = track

        return result

    def is_container_format_supported(self, container_format):
        return True
