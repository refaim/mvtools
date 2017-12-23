import ffmpeg
from tracks import Track

class MediaFile(object):
    def __init__(self, file_path, file_id):
        self._path = file_path
        self._id = file_id
        self._tracks_by_type = None
        # TODO set video track crf !!!!!!!!!!!!!!!!!!!!!!

        # if self._field_order is None:
        #     orders = (self.FO_PRG, self.FO_INT_BOT, self.FO_INT_TOP)
        #     fo = self._ffm_data.get('field_order') or \
        #         ask_to_select(u'Specify field order', sorted(orders))
        #     assert fo in orders
        #     self._field_order = fo
        # return self._field_order in (self.FO_INT_BOT, self.FO_INT_TOP)

    def id(self):
        return self._id

    def path(self):
        return self._path

    def _get_tracks(self):
        if self._tracks_by_type is None:
            tracks_data = {}
            for track_id, track in ffmpeg.identify_tracks(self._path).iteritems():
                tracks_data.setdefault(track['codec_type'], {})[track_id] = track

            self._tracks_by_type = { type_id: [] for type_id in self.TRACK_CLASSES.iterkeys() }
            for track_type, tracks_of_type in tracks_data.iteritems():
                self._tracks_by_type.setdefault(track_type, [])
                for track_id, track_data in tracks_of_type.iteritems():
                    track = Movie.TRACK_CLASSES[track_type](self._path, track_data)
                    self._tracks_by_type[track_type].append(track)

        return self._tracks_by_type

    def tracks(self, track_type):
        return self._get_tracks()[track_type]

    def track_index_in_type(self, track):
        return list(self.tracks(track.type())).index(track) + 1

class Movie(object):
    def __init__(self, media_files):
        self._media_files = media_files
        self._set_languages()
        self._set_forced_by_frame_length()
        self._set_forced_by_file_size()

    def _set_languages(self):
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

    def tracks(self, track_type):
        for media_file in self._media_files:
            for track in media_file.tracks(track_type):
                yield track

# class Movie(MediaFile):
#     TRACK_CLASSES = {
#         Track.AUD: AudioTrack,
#         Track.VID: VideoTrack,
#         Track.SUB: SubtitleTrack,
#     }

#     def __init__(self, path):
#         self._path = path
#         self._tracks_by_type = None

#     def path(self):
#         return self._path

#     def _ffprobe(self):
#         tracks = {}
#         for stream_specifier in ('a', 'V', 's'):
#             stdout = process(
#                 u'ffprobe -v quiet -print_format json -show_streams -select_streams {} {}'.format(
#                     stream_specifier, quote(self._path)))
#             for stream in json.loads(stdout)['streams']:
#                 tracks[stream['index']] = stream
#         return tracks

#     def _get_tracks(self):
#         if self._tracks_by_type is None:
#             ffprobe_data = self._ffprobe()
#             tracks_data = {}
#             for track_id, track in ffprobe_data.iteritems():
#                 tracks_data.setdefault(track['codec_type'], {})[track_id] = track
#             assert len(tracks_data[Track.VID]) == 1

#             frame_lengths = {}
#             for track_id, track_data in tracks_data.get(Track.SUB, {}).iteritems():
#                 track_length = track_data.get('tags', {}).get('NUMBER_OF_FRAMES-eng', None)
#                 if track_length is None:
#                     frame_lengths = None
#                     break
#                 frame_lengths[track_id] = int(track_length)
#             if frame_lengths:
#                 max_length = max(frame_lengths.itervalues())
#                 forced_track_threshold = max_length / 100.0 * 50.0
#                 for track_id, track_length in frame_lengths.iteritems():
#                     if (max_length - track_length) > forced_track_threshold:
#                         tracks_data[Track.SUB][track_id]['disposition']['forced'] = True

#             self._tracks_by_type = {}
#             for track_type, tracks_of_type in tracks_data.iteritems():
#                 self._tracks_by_type.setdefault(track_type, [])
#                 for track_id, track_data in tracks_of_type.iteritems():
#                     track = Movie.TRACK_CLASSES[track_type](self._path, track_data)
#                     self._tracks_by_type[track_type].append(track)

#         return self._tracks_by_type

#     def tracks(self, track_type):
#         return self._get_tracks()[track_type]

#     def video_track(self):
#         return self.tracks(Track.VID)[0]

#     def track_index_in_type(self, track):
#         return list(self.tracks(track.type())).index(track) + 1
