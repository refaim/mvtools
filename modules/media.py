import ffmpeg
import lang
import platform

from tracks import Track, AudioTrack, VideoTrack, SubtitleTrack

class File(object):
    _TRACK_PROPS_IDX_CLASS = 0
    _TRACK_PROPS_IDX_FFMPEG_STREAM = 1
    _TRACK_PROPS = {
        Track.AUD: (AudioTrack, ffmpeg.STREAM_AUD),
        Track.SUB: (SubtitleTrack, ffmpeg.STREAM_SUB),
        Track.VID: (VideoTrack, ffmpeg.STREAM_VID),
    }

    EXTENSIONS = {
        '.ac3': (Track.AUD,),
        '.avi': (Track.VID, Track.AUD, Track.SUB),
        '.flv': (Track.VID, Track.AUD, Track.SUB),
        '.m4v': (Track.VID, Track.AUD, Track.SUB),
        '.mkv': (Track.VID, Track.AUD, Track.SUB),
        '.mp4': (Track.VID, Track.AUD, Track.SUB),
        '.mpg': (Track.VID, Track.AUD, Track.SUB),
        '.srt': (Track.SUB,),
        '.sup': (Track.SUB,),
        '.wmv': (Track.VID, Track.AUD, Track.SUB),
    }

    def __init__(self, file_path, file_id):
        self._path = file_path
        self._id = file_id
        self._tracks_by_type = None

    def id(self):
        return self._id

    def path(self):
        return self._path

    def _get_tracks(self):
        if self._tracks_by_type is None:
            tracks_data = {}
            for track_type in self.EXTENSIONS[platform.file_ext(self._path)]:
                stream_id = self._TRACK_PROPS[track_type][self._TRACK_PROPS_IDX_FFMPEG_STREAM]
                for track_id, track in ffmpeg.identify_tracks(self._path, stream_id).iteritems():
                    tracks_data.setdefault(track['codec_type'], {})[track_id] = track

            self._tracks_by_type = { track_type: [] for track_type in self._TRACK_PROPS.iterkeys() }
            for track_type, tracks_of_type in tracks_data.iteritems():
                for track_id, track_data in tracks_of_type.iteritems():
                    track_class = self._TRACK_PROPS[track_type][self._TRACK_PROPS_IDX_CLASS]
                    self._tracks_by_type[track_type].append(track_class(self._path, track_data))
                self._tracks_by_type[track_type].sort()
        return self._tracks_by_type

    def tracks(self, track_type):
        return self._get_tracks()[track_type]

class Movie(object):
    def __init__(self, media_files):
        self._media_files = list(sorted(media_files))
        assert len(list(self.tracks(Track.VID))) >= 1
        # TODO assert video tracks length
        self._set_languages()
        self._clear_wrong_forced_flags()
        self._set_forced_by_frame_length()
        self._set_forced_by_file_size()
        self._set_crf()

    def _set_languages(self):
        for media_file in self._media_files:
            for track_type in (Track.AUD, Track.SUB):
                type_tracks = list(media_file.tracks(track_type))
                file_tracks = []
                for file_track_type in (Track.AUD, Track.VID, Track.SUB):
                    file_tracks.extend(media_file.tracks(file_track_type))
                if len(file_tracks) == len(type_tracks) == 1:
                    track = file_tracks[0]
                    track.set_language(lang.guess_language(track.source_file()))

    def _clear_wrong_forced_flags(self):
        pass # TODO

    def _set_forced_by_frame_length(self):
        max_length = -1
        for track in self.tracks(Track.SUB):
            length = track.frames_len()
            if length is None:
                return
            max_length = max(float(length), max_length)
        if max_length <= 0:
            return

        forced_track_threshold = max_length / 100.0 * 50.0
        for track in self.tracks(Track.SUB):
            if (max_length - track.frames_len()) > forced_track_threshold:
                track.set_forced(True)

    def _set_forced_by_file_size(self):
        pass # TODO

    def _set_crf(self):
        for track in self.tracks(Track.VID):
            if track.crf() is None:
                track.set_crf(ffmpeg.detect_crf(track.source_file()))

    def tracks(self, track_type):
        for media_file in self._media_files:
            for track in media_file.tracks(track_type):
                yield track

    def track_index_in_type(self, track):
        return list(self.tracks(track.type())).index(track) + 1

    def main_path(self):
        return min(track.source_file() for track in self.tracks(Track.VID))

    def reference_duration(self):
        return any(track.duration() for track in self.tracks(Track.VID)) or None
