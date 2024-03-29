# coding: utf-8

import fnmatch
import functools
import os
import re

import cmd
import lang
import misc
import platform
from ffmpeg import Ffmpeg
from formats import AudioCodec, FileFormat, TrackType
from tracks import AudioTrack, VideoTrack, SubtitleTrack, ChaptersTrack

class File(object):
    _TRACK_PROPS_IDX_CLASS = 0
    _TRACK_PROPS_IDX_FFMPEG_STREAM = 1
    _TRACK_PROPS = {
        TrackType.VID: (VideoTrack, Ffmpeg.STREAM_ARGUMENT_VID),
        TrackType.AUD: (AudioTrack, Ffmpeg.STREAM_ARGUMENT_AUD),
        TrackType.SUB: (SubtitleTrack, Ffmpeg.STREAM_ARGUMENT_SUB),
        TrackType.CHA: (ChaptersTrack, None),
    }

    _FORMATS_INFO = {
        FileFormat.x3GP: (['*.3gp'], [TrackType.VID, TrackType.AUD], [('MPEG-4', '3GPP Media Release 4'), ('MPEG-4', '3GPP Media Release 5')]),
        FileFormat.AC3: (['*.ac3'], [TrackType.AUD], [('AC-3', None)]),
        FileFormat.AMR: (['*.amr'], [TrackType.AUD], [('AMR', None)]),
        FileFormat.AVI: (['*.avi'], [TrackType.VID, TrackType.AUD], [('AVI', None), ('AVI', 'OpenDML')]),
        FileFormat.CHA: (['*chapters*.txt', '*chapters*.xml'], [TrackType.CHA], [('Chapters', None)]),
        FileFormat.DTS: (['*.dts', '*.dtshr'], [TrackType.AUD], [('DTS', None)]),
        FileFormat.EAC3: (['*.eac3'], [TrackType.AUD], [('E-AC-3', None)]),
        FileFormat.FLAC: (['*.flac'], [TrackType.AUD], [('FLAC', None)]),
        FileFormat.FLV: (['*.flv'], [TrackType.VID, TrackType.AUD], [('Flash Video', None)]),
        FileFormat.M4A: (['*.m4a'], [TrackType.AUD], [('MPEG-4', 'Apple audio with iTunes info')]),
        FileFormat.M4V: (['*.m4v'], [TrackType.VID, TrackType.AUD, TrackType.SUB], []),
        FileFormat.MKV: (['*.mkv'], [TrackType.VID, TrackType.AUD, TrackType.SUB], [('Matroska', None)]),
        FileFormat.MOV: (['*.mov'], [TrackType.VID, TrackType.AUD, TrackType.SUB], [('MPEG-4', 'QuickTime')]),
        FileFormat.MP3: (['*.mp3'], [TrackType.AUD], [('MPEG Audio', None)]),
        FileFormat.MP4: (['*.mp4'], [TrackType.VID, TrackType.AUD, TrackType.SUB], [('MPEG-4', None), ('MPEG-4', 'Base Media'), ('MPEG-4', 'Base Media / Version 2'), ('MPEG-4', 'Sony PSP')]),
        FileFormat.MPG: (['*.mpg', '*.mpeg', '*.vob'], [TrackType.VID, TrackType.AUD, TrackType.SUB], [('MPEG-PS', None)]),
        FileFormat.RM: (['*.rm', '*.rmvb'], [TrackType.VID, TrackType.AUD], [('RealMedia', None)]),
        FileFormat.SMK: (['*.smk'], [TrackType.VID, TrackType.AUD], [(None, None)]),
        FileFormat.SRT: (['*.srt'], [TrackType.SUB], [('SubRip', None)]),
        FileFormat.SSA: (['*.ssa', '*.ass'], [TrackType.SUB], []),
        FileFormat.SUP: (['*.sup'], [TrackType.SUB], [('PGS', None)]),
        FileFormat.TS: (['*.ts'], [TrackType.VID, TrackType.AUD, TrackType.SUB], [('MPEG-TS', None)]),
        FileFormat.WAV: (['*.wav'], [TrackType.AUD], [('Wave', None)]),
        FileFormat.WEBM: (['*.webm'], [TrackType.VID, TrackType.AUD], [('WebM', None)]),
        FileFormat.WMV: (['*.asf', '*.wma', '*.wmv'], [TrackType.VID, TrackType.AUD, TrackType.SUB], [('Windows Media', None)]),
    }
    _format_signatures = None

    @classmethod
    def possible_track_types(cls, file_path):
        for file_format, (wildcards, track_types, signatures) in cls._FORMATS_INFO.iteritems():
            for wildcard in wildcards:
                if fnmatch.fnmatch(file_path, wildcard):
                    return track_types
        return []

    def __init__(self, file_path, container_format, container_format_profile):
        self._path = file_path
        self._tracks_by_type = None
        self._ffmpeg = Ffmpeg()  # TODO singleton

        if File._format_signatures is None:
            formats = {}
            for file_format, (_, _, signatures) in self._FORMATS_INFO.iteritems():
                for signature in signatures:
                    formats[signature] = file_format
            File._format_signatures = formats
        self._format = File._format_signatures[(container_format, container_format_profile)]

    def path(self):
        return self._path

    def _get_tracks(self):
        if self._tracks_by_type is None:
            tracks_data = {}
            for track_type in File.possible_track_types(self._path):
                if track_type == TrackType.CHA:
                    tracks_data.setdefault(TrackType.CHA, {})[-1] = {}
                else:
                    stream_id = self._TRACK_PROPS[track_type][self._TRACK_PROPS_IDX_FFMPEG_STREAM]
                    for track_id, track in cmd.ffprobe(self._path, stream_id).iteritems():
                        tracks_data.setdefault(self._ffmpeg.parse_track_type(track['codec_type']), {})[track_id] = track

            self._tracks_by_type = {track_type: [] for track_type in self._TRACK_PROPS.iterkeys()}
            for track_type, tracks_of_type in tracks_data.iteritems():
                for track_id, track_data in tracks_of_type.iteritems():
                    track_class = self._TRACK_PROPS[track_type][self._TRACK_PROPS_IDX_CLASS]
                    self._tracks_by_type[track_type].append(track_class(self._path, self._format, track_data))
                self._tracks_by_type[track_type].sort(key=lambda t: t.qualified_id())
        return self._tracks_by_type

    def tracks(self, track_type):
        return self._get_tracks()[track_type]

class Movie(object):
    RE_SUB_CAPTIONS_NUM = re.compile(r', (?P<num>\d+) caption')

    @staticmethod
    def sort_key(prefix, path):
        result = []
        for cluster in path[len(prefix):].split():
            if cluster.isdigit():
                cluster = cluster.zfill(2)
            result.append(cluster)
        return u' '.join(result)

    def __init__(self, media_paths, ignore_languages):
        self._ignore_languages = ignore_languages
        self._media_paths = list(media_paths)
        self._media_files = None
        self._main_path = self._media_paths[0]
        self._file_info_cache = {}

    def _get_file_info(self, path):
        if path not in self._file_info_cache:
            self._file_info_cache[path] = cmd.mediainfo(path)
        return self._file_info_cache[path]

    def _parse_media(self):
        sort_prefix = os.path.commonprefix([path for path in self._media_paths])
        self._media_paths.sort(key=functools.partial(self.sort_key, sort_prefix))
        self._media_files = []
        for path in self._media_paths:
            info = self._get_file_info(path)['general']
            self._media_files.append(File(path, info['format'], info['format_profile']))
        assert len(list(self.tracks(TrackType.VID))) >= 1
        assert len(list(self.tracks(TrackType.CHA))) <= 1

    def _fill_metadata(self):
        self._set_codecs()
        self._set_languages()
        self._set_forced()
        self._set_crf()

    def _single_file_tracks(self, track_type):
        for media_file in self._media_files:
            type_tracks = list(media_file.tracks(track_type))
            file_tracks = []
            for file_track_type in (TrackType.AUD, TrackType.VID, TrackType.SUB):
                file_tracks.extend(media_file.tracks(file_track_type))
            if len(file_tracks) == len(type_tracks) == 1:
                yield file_tracks[0]

    def _set_codecs(self):
        for track in self.tracks(TrackType.AUD):
            if track.codec() == AudioCodec.DTS:
                track_info = self._get_file_info(track.source_file())['tracks'][track.id()]
                if 'ES' in track_info.get('Format_Profile', ''):
                    track.overwrite_codec(AudioCodec.DTS_ES)

    def _set_languages(self):
        if self._ignore_languages:
            for track_type in (TrackType.AUD, TrackType.SUB):
                for track in self.tracks(track_type):
                    track.set_language('und')

        for track_type in (TrackType.AUD, TrackType.SUB):
            for track in self._single_file_tracks(track_type):
                if track.language() == 'und':
                    guessed = lang.guess(track.source_file())
                    if len(guessed) == 1:
                        track.set_language(guessed[0])

        for track in self._single_file_tracks(TrackType.SUB):
            if not track.is_binary() and (track.language() == 'und' or track.encoding() is None):
                encoding_data = platform.detect_encoding(track.source_file())
                if encoding_data['confidence'] >= 0.8:
                    new_lang = lang.alpha3(encoding_data['language'] or 'und')
                    if new_lang != 'und':
                        track.set_language(new_lang)
                    track.set_encoding(track.encoding() or lang.norm_encoding(encoding_data['encoding']))

    def _set_forced(self):
        for track_type in (TrackType.AUD, TrackType.VID):
            for track in self.tracks(track_type):
                track.set_forced(False)

        strings_forced = [u'forced', u'forsed', u'форсир', u'только надписи', u'tolko nadpisi']
        for track in self._single_file_tracks(TrackType.SUB):
            if not track.is_binary():
                track.set_forced(None)
            name_string = u''.join(c.lower() for c in track.source_file() if c.isalpha() or c.isspace())
            if u'normal' not in name_string and any(s in name_string for s in strings_forced):
                track.set_forced(True)

        strings_forced.append(u'caption')
        strings_full = [u'sdh']
        for track in self.tracks(TrackType.SUB):
            key = track.name().lower()
            if any(s in key for s in strings_forced):
                track.set_forced(True)
            elif any(s in key for s in strings_full):
                track.set_forced(False)

        relevant_tracks = [track for track in self.tracks(TrackType.SUB) if not track.is_forced() and track.language() != 'chi' and 'sdh' not in track.name().lower()]
        track_groups = [
            [track for track in relevant_tracks if track.is_binary()],
            [track for track in relevant_tracks if track.is_text()],
        ]
        metrics = ((lambda t: t.frames_len(), 50.0), (lambda t: t.num_captions(), 50.0))
        for value_getter, threshold_percentage in metrics:
            for track_group in track_groups:
                max_value = misc.safe_unsigned_max(value_getter(track) for track in track_group)
                if max_value is not None:
                    forced_threshold = max_value / 100.0 * threshold_percentage
                    for track in track_group:
                        if (max_value - value_getter(track)) > forced_threshold:
                            track.set_forced(True)

    def _set_crf(self):
        for track in self.tracks(TrackType.VID):
            if track.crf() is None:
                track.set_crf(cmd.detect_crf(track.source_file()))

    def _setup_media(self):
        if self._media_files is None:
            self._parse_media()
            self._fill_metadata()

    def media_files(self):
        self._setup_media()
        return self._media_files

    def tracks(self, track_type):
        self._setup_media()
        for media_file in self._media_files:
            for track in media_file.tracks(track_type):
                yield track

    def track_index_in_type(self, track):
        return list(self.tracks(track.type())).index(track) + 1

    def main_path(self):
        return self._main_path

    def chapters_path(self):
        tracks = list(self.tracks(TrackType.CHA))
        return tracks[0].source_file() if tracks else None

    def reference_duration(self):
        durations = [track.duration() for track in self.tracks(TrackType.VID)]
        return durations[0] or None
