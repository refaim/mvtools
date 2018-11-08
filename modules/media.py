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

    CONTAINER_TRACK_TYPES = {
        '*.ac3': (Track.AUD,),
        '*.ass': (Track.SUB,),
        '*.avi': (Track.VID, Track.AUD),
        '*.dts': (Track.AUD,),
        '*.dtshr': (Track.AUD,),
        '*.dtsma': (Track.AUD,),
        '*.eac3': (Track.AUD,),
        '*.flac': (Track.AUD,),
        '*.flv': (Track.VID, Track.AUD),
        '*.m4a': (Track.AUD,),
        '*.m4v': (Track.VID, Track.AUD, Track.SUB),
        '*.mka': (Track.AUD,),
        '*.mks': (Track.SUB),
        '*.mkv': (Track.VID, Track.AUD, Track.SUB),
        '*.mp4': (Track.VID, Track.AUD, Track.SUB),
        '*.mpg': (Track.VID, Track.AUD, Track.SUB),
        '*.srt': (Track.SUB,),
        '*.ssa': (Track.SUB,),
        '*.sup': (Track.SUB,),
        '*.ts': (Track.VID, Track.AUD, Track.SUB),
        '*.webm': (Track.VID, Track.AUD),
        '*.wma': (Track.AUD,),
        '*.wmv': (Track.VID, Track.AUD, Track.SUB),
        '*chapters*.txt': (Track.CHA,),
        '*chapters*.xml': (Track.CHA,),
    }

    @classmethod
    def possible_track_types(cls, file_path):
        for wildcard in cls.CONTAINER_TRACK_TYPES:
            if fnmatch.fnmatch(file_path, wildcard):
                return list(cls.CONTAINER_TRACK_TYPES[wildcard])
        return []

    def __init__(self, file_path):
        self._path = file_path
        self._tracks_by_type = None

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
                    self._tracks_by_type[track_type].append(track_class(self._path, track_data))
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
        self._media_paths = list(media_paths)
        self._media_files = None
        self._main_path = self._media_paths[0]
        self._ignore_languages = ignore_languages

    def _parse_media(self):
        sort_prefix = os.path.commonprefix([path for path in self._media_paths])
        self._media_paths.sort(key=functools.partial(self.sort_key, sort_prefix))
        self._media_files = [File(path) for path in self._media_paths]
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
        files_info = {}
        for track in self.tracks(Track.AUD):
            if track.codec_id() == AudioTrack.DTS:
                file_path = track.source_file()
                if file_path not in files_info:
                    files_info[file_path] = cmd.mediainfo(file_path)
                track_info = files_info[file_path][track.id()]
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
