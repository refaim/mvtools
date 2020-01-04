# coding: utf-8

import fnmatch
import functools
import os
import re

import cmd
import formats
import lang
import misc
import platform
from detectors import FfmpegFileInfo, MiFileInfo
from formats import TrackType
from tracks import AudioTrack, VideoTrack, SubtitleTrack, ChaptersTrack


class File(object):
    _TRACK_TYPE_TO_CLASS = {
        TrackType.VID: VideoTrack,
        TrackType.AUD: AudioTrack,
        TrackType.SUB: SubtitleTrack,
        TrackType.CHA: ChaptersTrack,
    }

    @classmethod
    def possible_track_types(cls, file_path):
        for wildcard, file_format in formats.FILE_FORMAT_FILENAME_WILDCARDS.iteritems():
            if fnmatch.fnmatch(file_path, wildcard):
                return formats.FILE_FORMAT_SUPPORTED_TRACK_TYPES[file_format]
        return set()

    def __init__(self, path, ff_info, mi_info):
        # type: (str, FfmpegFileInfo, MiFileInfo) -> None
        self._path = path
        self._format = mi_info.file_format
        self._ff_info = ff_info
        self._mi_info = mi_info
        self._tracks_by_type = None

    def path(self):
        return self._path

    def tracks(self, track_type):
        if self._tracks_by_type is None:
            self._tracks_by_type = {track_type: [] for track_type in TrackType.get_values()}

            for track_type, ff_tracks_of_type in self._ff_info.tracks_by_type.iteritems():
                file_tracks_of_type = []
                for track_id, ff_track in ff_tracks_of_type.iteritems():
                    print(self._mi_info.tracks_by_type)
                    mi_track = self._mi_info.tracks_by_type[track_type][track_id]
                    file_track = self._TRACK_TYPE_TO_CLASS[track_type](self._path, self._format, ff_track, mi_track)
                    file_tracks_of_type.append(file_track)
                self._tracks_by_type[track_type] = sorted(file_tracks_of_type, key=lambda t: t.qualified_id())

        return self._tracks_by_type[track_type]

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

    def __init__(self, media_paths, ignore_languages, detector_ffmpeg, detector_mi):
        self._ignore_languages = ignore_languages
        self._media_paths = list(media_paths)
        self._media_files = None
        self._main_path = self._media_paths[0]
        self._detector_ffmpeg = detector_ffmpeg
        self._detector_mi = detector_mi
        self._mi_file_info_cache = {}

    def _parse_media(self):
        sort_prefix = os.path.commonprefix([path for path in self._media_paths])
        self._media_paths.sort(key=functools.partial(self.sort_key, sort_prefix))
        self._media_files = []
        for path in self._media_paths:
            self._media_files.append(File(path, self._detector_ffmpeg.detect(path), self._detector_mi.detect(path)))
        assert len(list(self.tracks(TrackType.VID))) >= 1
        assert len(list(self.tracks(TrackType.CHA))) <= 1

    def _fill_metadata(self):
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
