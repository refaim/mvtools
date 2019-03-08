# coding: utf-8

import fnmatch
import functools
import os
import re

import cmd
import lang
import misc
import platform

from tracks import Track, AudioTrack, VideoTrack, SubtitleTrack, ChaptersTrack

class File(object):
    _TRACK_PROPS_IDX_CLASS = 0
    _TRACK_PROPS_IDX_FFMPEG_STREAM = 1
    _TRACK_PROPS = {
        Track.VID: (VideoTrack, cmd.FFMPEG_STREAM_VID),
        Track.AUD: (AudioTrack, cmd.FFMPEG_STREAM_AUD),
        Track.SUB: (SubtitleTrack, cmd.FFMPEG_STREAM_SUB),
        Track.CHA: (ChaptersTrack, None),
    }

    FORMAT_3GP = '3gp'
    FORMAT_AC3 = 'ac3'
    FORMAT_AMR = 'amr'
    FORMAT_AVI = 'avi'
    FORMAT_CHA = 'cha'
    FORMAT_EAC3 = 'eac3'
    FORMAT_FLAC = 'flac'
    FORMAT_FLV = 'flv'
    FORMAT_M4A = 'm4a'
    FORMAT_M4V = 'm4v'
    FORMAT_MKV = 'mkv'
    FORMAT_MOV = 'mov'
    FORMAT_MP3 = 'mp3'
    FORMAT_MP4 = 'mp4'
    FORMAT_MPG = 'mpg'
    FORMAT_SRT = 'srt'
    FORMAT_SSA = 'ssa'
    FORMAT_SUP = 'sup'
    FORMAT_WAV = 'wav'
    FORMAT_WEBM = 'webm'
    FORMAT_WMV = 'wmv'

    _FORMATS_INFO = {
        FORMAT_3GP: (['*.3gp'], [Track.VID, Track.AUD], [('MPEG-4', '3GPP Media Release 4'), ('MPEG-4', '3GPP Media Release 5')]),
        FORMAT_AC3: (['*.ac3'], [Track.AUD], [('AC-3', None)]),
        FORMAT_AMR: (['*.amr'], [Track.AUD], [('AMR', None)]),
        FORMAT_AVI: (['*.avi'], [Track.VID, Track.AUD], [('AVI', None), ('AVI', 'OpenDML')]),
        FORMAT_CHA: (['*chapters*.txt', '*chapters*.xml'], [Track.CHA], [('Chapters', None)]),
        FORMAT_EAC3: (['*.eac3'], [Track.AUD], [('E-AC-3', None)]),
        FORMAT_FLAC: (['*.flac'], [Track.AUD], [('FLAC', None)]),
        FORMAT_FLV: (['*.flv'], [Track.VID, Track.AUD], [('Flash Video', None)]),
        FORMAT_M4A: (['*.m4a'], [Track.AUD], [('MPEG-4', 'Apple audio with iTunes info')]),
        # TODO Add signature
        FORMAT_M4V: (['*.m4v'], [Track.VID, Track.AUD, Track.SUB], []),
        FORMAT_MKV: (['*.mkv'], [Track.VID, Track.AUD, Track.SUB], [('Matroska', None)]),
        FORMAT_MOV: (['*.mov'], [Track.VID, Track.AUD, Track.SUB], [('MPEG-4', 'QuickTime')]),
        FORMAT_MP3: (['*.mp3'], [Track.AUD], [('MPEG Audio', None)]),
        FORMAT_MP4: (['*.mp4'], [Track.VID, Track.AUD, Track.SUB], [('MPEG-4', 'Base Media'), ('MPEG-4', 'Base Media / Version 2')]),
        FORMAT_MPG: (['*.mpg', '*.mpeg'], [Track.VID, Track.AUD, Track.SUB], [('MPEG-PS', None)]),
        FORMAT_SRT: (['*.srt'], [Track.SUB], [('SubRip', None)]),
        FORMAT_SSA: (['*.ssa', '*.ass'], [Track.SUB], []),
        FORMAT_SUP: (['*.sup'], [Track.SUB], [('PGS', None)]),
        FORMAT_WAV: (['*.wav'], [Track.AUD], [('Wave', None)]),
        FORMAT_WEBM: (['*.webm'], [Track.VID, Track.AUD], [('WebM', None)]),
        FORMAT_WMV: (['*.wma', '*.wmv'], [Track.VID, Track.AUD, Track.SUB], [('Windows Media', None)]),
    }
    _format_signatures = None

    # TODO move to _FORMATS_INFO
    # '*.dts': (Track.AUD,),
    # '*.dtshr': (Track.AUD,),
    # '*.dtsma': (Track.AUD,),
    # '*.mka': (Track.AUD,),
    # '*.mks': (Track.SUB),
    # '*.ts': (Track.VID, Track.AUD, Track.SUB),

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
                if track_type == Track.CHA:
                    tracks_data.setdefault(Track.CHA, {})[-1] = {}
                else:
                    stream_id = self._TRACK_PROPS[track_type][self._TRACK_PROPS_IDX_FFMPEG_STREAM]
                    for track_id, track in cmd.ffprobe(self._path, stream_id).iteritems():
                        tracks_data.setdefault(track['codec_type'], {})[track_id] = track

            self._tracks_by_type = { track_type: [] for track_type in self._TRACK_PROPS.iterkeys() }
            for track_type, tracks_of_type in tracks_data.iteritems():
                for track_id, track_data in tracks_of_type.iteritems():
                    track_class = self._TRACK_PROPS[track_type][self._TRACK_PROPS_IDX_CLASS]
                    self._tracks_by_type[track_type].append(track_class(self._path, self._format, track_data))
                self._tracks_by_type[track_type].sort(key=lambda track: track.qualified_id())
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
        assert len(list(self.tracks(Track.VID))) >= 1
        assert len(list(self.tracks(Track.CHA))) <= 1

    def _fill_metadata(self):
        self._set_codecs()
        self._set_languages()
        self._set_forced()
        self._set_crf()

    def _single_file_tracks(self, track_type):
        for media_file in self._media_files:
            type_tracks = list(media_file.tracks(track_type))
            file_tracks = []
            for file_track_type in (Track.AUD, Track.VID, Track.SUB):
                file_tracks.extend(media_file.tracks(file_track_type))
            if len(file_tracks) == len(type_tracks) == 1:
                yield file_tracks[0]

    def _set_codecs(self):
        for track in self.tracks(Track.AUD):
            if track.codec_id() == AudioTrack.DTS:
                track_info = self._get_file_info(track.source_file())['tracks'][track.id()]
                if 'ES' in track_info.get('Format_Profile', ''):
                    track.set_codec_id(AudioTrack.DTS_ES)

    def _set_languages(self):
        if self._ignore_languages:
            for track_type in (Track.AUD, Track.SUB):
                for track in self.tracks(track_type):
                    track.set_language('und')

        for track_type in (Track.AUD, Track.SUB):
            for track in self._single_file_tracks(track_type):
                if track.language() == 'und':
                    guessed = lang.guess(track.source_file())
                    if len(guessed) == 1:
                        track.set_language(guessed[0])

        for track in self._single_file_tracks(Track.SUB):
            if not track.is_binary() and (track.language() == 'und' or track.encoding() is None):
                encoding_data = platform.detect_encoding(track.source_file())
                if encoding_data['confidence'] >= 0.8:
                    new_lang = lang.alpha3(encoding_data['language'] or 'und')
                    if new_lang != 'und':
                        track.set_language(new_lang)
                    track.set_encoding(track.encoding() or lang.norm_encoding(encoding_data['encoding']))

    def _set_forced(self):
        for track_type in (Track.AUD, Track.VID):
            for track in self.tracks(track_type):
                track.set_forced(False)

        strings_forced = [u'forced', u'forsed', u'форсир', u'только надписи', u'tolko nadpisi']
        for track in self._single_file_tracks(Track.SUB):
            if not track.is_binary():
                track.set_forced(None)
            name_string = u''.join(c.lower() for c in track.source_file() if c.isalpha() or c.isspace())
            if u'normal' not in name_string and any(s in name_string for s in strings_forced):
                track.set_forced(True)

        strings_forced.append(u'caption')
        strings_full = [u'sdh']
        for track in self.tracks(Track.SUB):
            key = track.name().lower()
            if any(s in key for s in strings_forced):
                track.set_forced(True)
            elif any(s in key for s in strings_full):
                track.set_forced(False)

        relevant_tracks = [track for track in self.tracks(Track.SUB)
            if not track.is_forced() and track.language() != 'chi' and 'sdh' not in track.name().lower()]
        track_groups = []
        track_groups.append([track for track in relevant_tracks if track.is_binary()])
        track_groups.append([track for track in relevant_tracks if track.is_text()])
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
        for track in self.tracks(Track.VID):
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
        tracks = list(self.tracks(Track.CHA))
        return tracks[0].source_file() if tracks else None

    def reference_duration(self):
        durations = [track.duration() for track in self.tracks(Track.VID)]
        return durations[0] or None
