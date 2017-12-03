# coding: utf-8

from __future__ import print_function

import argparse
import codecs
import os
import pymediainfo
import re
import subprocess
import sys
import uuid

LANG_ORDER = ['und', 'jpn', 'eng', 'rus']
MUX_SCRIPT = 'mux.cmd'

TUNES_IDX_CRF = 0
TUNES_IDX_REAL_TUNE = 1
TUNES = {
    'animation': (18, 'animation'),
    'film': (22, 'film'),
    'trash': (23, 'film'),
    'supertrash': (25, 'film'),
}

def try_int(value):
    try:
        return int(value)
    except:
        return None

def is_windows():
    return 'win' in sys.platform

def quote(path):
    character = u"'"
    if is_windows() or '"' in path:
        character = u'"'
    return character + path + character

def process(command):
    cmd_encoding = 'cp1251' if is_windows() else 'utf-8'
    result_command = [arg.encode(cmd_encoding) for arg in command]
    p = subprocess.Popen(result_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0 or stderr:
        print(stderr, file=sys.stderr)
        raise Exception()
    return stdout

class Track(object):
    AUD = 'audio'
    VID = 'video'
    SUB = 'subtitles'

    def __init__(self, raw_params, media_info):
        self._data = raw_params
        self._media_info = media_info

    def id(self):
        return self._data['id']

    def type(self):
        return self._data['type']

    def name(self):
        return self._data.get('track_name', '')

    def language(self):
        return unicode(self._data['language'])

    def setLanguage(self, value):
        self._data['language'] = value

    def codecId(self):
        return unicode(self._data['codec_id']) # TODO enum

class AudioTrack(Track):
    def channels(self):
        return int(self._data['audio_channels'])

class VideoTrack(Track):
    def crf(self):
        match = re.search(r'crf=(?P<crf>[\d\.]+)', self._media_info.encoding_settings or '')
        if not match:
            return None
        return float(match.groupdict()['crf'])

    def is_interlaced(self):
        return self._media_info.scan_type == 'Interlaced'

class Movie(object):
    TRACK_CLASSES = {
        Track.AUD: AudioTrack,
        Track.VID: VideoTrack,
        Track.SUB: Track,
    }

    def __init__(self, path):
        self._path = path
        self._mkv_tracks = None

    def path(self):
        return self._path

    def _get_tracks(self):
        if self._mkv_tracks is None:
            mei_tracks_by_id = {}
            media_info = pymediainfo.MediaInfo.parse(self._path,
                library_file=os.path.join(os.path.dirname(__file__), 'MediaInfo.dll'))
            for track in media_info.tracks:
                if track.track_id is not None:
                    mei_tracks_by_id[int(track.track_id) - 1] = track

            track_objects = {}
            raw_strings = (line for line in process([u'mkvmerge', u'--identify-verbose', self._path]).splitlines() if line.startswith('Track'))
            for line in raw_strings:
                match = re.match(r'^Track ID (?P<id>\d+): (?P<type>[a-z]+).+$', line)
                gd = match.groupdict()
                raw_params = { 'id': int(gd['id']), 'type': gd['type'] }
                for raw_string in re.match(r'^.+?\[(.+?)\].*$', line).group(1).split():
                    k, v = raw_string.split(':')
                    if isinstance(v, str):
                        v = v.decode('utf-8').replace('\\s', ' ')
                    raw_params[k] = v
                track = Movie.TRACK_CLASSES[raw_params['type']](raw_params, mei_tracks_by_id[raw_params['id']])
                track_objects.setdefault(track.type(), [])
                track_objects[track.type()].append(track)
            self._mkv_tracks = track_objects
            assert len(self._mkv_tracks[Track.VID]) == 1
        return self._mkv_tracks

    def tracks(self, track_type):
        return self._get_tracks()[track_type]

    def video_track(self):
        return self.tracks(Track.VID)[0]

def mkvs(path):
    for root, dirs, files in os.walk(path):
        for filename in sorted(files):
            if filename.lower().endswith('.mkv'):
                yield os.path.join(root, filename)

def ffmpeg_command(src, dst, options):
    return u'ffmpeg -y -i {src} {options} {dst}'.format(
        src=quote(src), dst=quote(dst), options=u' '.join(options))

def cmd_string(bytestring):
    return bytestring.decode(sys.getfilesystemencoding())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', type=cmd_string, help='path to source directory') # TODO support not folder but list of files
    parser.add_argument('dst', type=cmd_string, help='path to destination directory')
    parser.add_argument('-al', nargs='*', choices=['rus', 'eng', 'jpn'], default=['eng', 'rus'], help='ordered list of audio languages to keep')
    parser.add_argument('-sl', nargs='*', choices=['rus', 'eng', 'jpn'], default=[], help='ordered list of subtitles languages to keep')
    parser.add_argument('-dm', default=False, action='store_true', help='downmix multi-channel audio to aac')
    parser.add_argument('-kv', default=False, action='store_true', help='keep video from re-encoding')
    parser.add_argument('-nf', type=cmd_string, default=None, help='path to names map file')
    args = parser.parse_args()

    filenames_map = None
    if args.nf and os.path.exists(args.nf):
        filenames_map = {}
        with open(args.nf) as fobj:
            for line in fobj:
                k, v = [os.path.normpath(s.strip()).replace('.mkv', '') for s in line.split('=')]
                filenames_map[k] = v

    movies = {}
    for filepath in mkvs(args.src):
        cur_name = os.path.normpath(os.path.relpath(filepath, args.src))
        new_name = cur_name
        if filenames_map is not None:
            raw_new_name_string = filenames_map[os.path.splitext(cur_name)[0]]
            new_name = None
            if raw_new_name_string == 'NO': continue
            elif raw_new_name_string == 'KEEP': new_name = cur_name
            else: new_name = '{}.mkv'.format(raw_new_name_string)
        movies[os.path.join(os.path.abspath(args.dst), new_name)] = Movie(os.path.abspath(filepath))

    output_track_types = {
        Track.VID: ['und'],
        Track.AUD: args.al,
        Track.SUB: args.sl,
    }

    try:
        os.remove(MUX_SCRIPT)
    except:
        pass

    for target_path, movie in sorted(movies.iteritems()):
        print(u'=== {} ==='.format(movie.path()))
        output_tracks = { track_type: [] for track_type in output_track_types }
        used_tracks = set()
        for track_type, lang_list in output_track_types.iteritems():
            for target_lang in lang_list:
                candidates = { track.id(): track for track in movie.tracks(track_type)
                    if track.id() not in used_tracks and (track.language() == target_lang or 'und' in (target_lang, track.language()))
                }
                if not candidates:
                    raise Exception('{} {} not found'.format(track_type, target_lang))

                chosen_track_id = None
                if len(candidates) == 1: chosen_track_id = list(candidates.keys())[0]
                if len(candidates) == 2:
                    comment_track_ids = [track_id for track_id, track
                        in candidates.iteritems() if re.search(r'(comment|коммент)', track.name().lower())]
                    if len(comment_track_ids) == 1:
                        chosen_track_id = list(set(candidates.keys()) - set(comment_track_ids))[0]

                while chosen_track_id not in candidates:
                    print(u'--- {}, {} ---'.format(track_type.capitalize(), target_lang.upper()))
                    for cand in sorted(candidates.itervalues(), key=lambda x: x.id()):
                        print(u'{} {} {} {}'.format(cand.id(), cand.language(), cand.codecId(), cand.name()))
                    chosen_track_id = try_int(raw_input(u'Enter track ID: ')) # TODO abort, retry, preview, undo, wtf

                used_tracks.add(chosen_track_id)
                chosen_track = candidates[chosen_track_id]
                chosen_track.setLanguage(target_lang)
                output_tracks[track_type].append(chosen_track)

        track_sources = {}
        for track_type, track_list in output_tracks.iteritems():
            track_list.sort(key=lambda t: LANG_ORDER.index(t.language()))
            for track in track_list:
                track_sources[track.id()] = [movie.path(), track.id()]

        result_commands = []
        encode_root = os.path.dirname(target_path)

        # TODO check if codec x264 and profile 4.1
        # TODO what if there is crf already?
        # TODO support crop
        video_track = movie.video_track()
        if video_track.crf() is None:
            enumerated_tunes = { i + 1: tune_id for i, tune_id in enumerate(sorted(TUNES.iterkeys())) }
            chosen_tune_id = None
            while chosen_tune_id not in enumerated_tunes:
                for tune_id, tune in sorted(enumerated_tunes.iteritems()):
                    print('{} {}'.format(tune_id, tune))
                chosen_tune_id = try_int(raw_input('Enter tune ID: '))
            tune_params = TUNES[enumerated_tunes[chosen_tune_id]]

            ffmpeg_options = ['-an', '-sn', '-dn']
            if video_track.is_interlaced():
                ffmpeg_options.append('-vf yadif=1:-1:0')
            ffmpeg_options.extend([
                '-c:v libx264', '-preset veryslow',
                '-tune {}'.format(tune_params[TUNES_IDX_REAL_TUNE]),
                '-profile:v high', '-level:v 4.1', '-crf {}'.format(tune_params[TUNES_IDX_CRF]),
                '-map_metadata -1', '-map_chapters -1',
            ])
            new_video_path = os.path.join(encode_root, u'{}.mkv'.format(uuid.uuid4()))
            result_commands.append(ffmpeg_command(movie.path(), new_video_path, ffmpeg_options))
            track_sources[video_track.id()] = [new_video_path, 0]

        # TODO convert PGS subtitles !!!!!!!!!!!!!!!!!!!!!!!!!!
        for track in output_tracks[Track.SUB]:
            # print(track._media_info)
            # exit()
            if True:
                pass
                # mkvextract tracks "!\!.!" 7:"!\!_rus.sup" 8:"!\!_eng.sup"
                # bdsup2sub -l ru -o "!\!.idx" "!\!.!"

        if args.dm:
            for track in output_tracks[Track.AUD]:
                if track.channels() > 2:
                    new_audio_path = os.path.join(encode_root, u'{}.m4a'.format(uuid.uuid4()))
                    decode = ffmpeg_command(movie.path(), '-', ['-f wav', '-acodec pcm_f32le', '-ac 2'])
                    qaac_options = ['--tvbr 63', '--quality 2', '--rate keep', '--ignorelength', '--no-delay']
                    encode = 'qaac {} - -o {}'.format(u' '.join(qaac_options), quote(new_audio_path))
                    result_commands.append(u'{} | {}'.format(decode, encode))
                    track_sources[track.id()] = [new_audio_path, 0]

        track_type_prefixes = {
            Track.VID: None,
            Track.AUD: 'audio',
            Track.SUB: 'subtitle',
        }

        mux = ['mkvmerge']
        mux.extend(['--output', quote(target_path)])
        mux.extend(['--no-track-tags', '--no-global-tags', '--disable-track-statistics-tags'])

        track_ids_by_files = {}
        for movie_track_id, (source_file, source_file_track_id) in track_sources.iteritems():
            track_ids_by_files.setdefault(source_file, {})[movie_track_id] = source_file_track_id

        source_file_ids = {}
        for i, (source_file, track_ids_map) in enumerate(track_ids_by_files.iteritems()):
            source_file_ids[source_file] = i
            for track_type, tracks_prefix in track_type_prefixes.iteritems():
                cur_file_tracks = [track for track in output_tracks[track_type] if track.id() in track_ids_map]
                if cur_file_tracks:
                    if tracks_prefix:
                        mux.append('--{}-tracks {}'.format(tracks_prefix, ','.join(str(track_ids_map[track.id()]) for track in cur_file_tracks)))
                    for track in cur_file_tracks:
                        default = track.id() == output_tracks[track_type][0].id()
                        mux.append('--track-name {0}:"" --language {0}:{1} --default-track {0}:{2}'.format(track_ids_map[track.id()], track.language(), 'yes' if default else 'no'))
            mux.append(quote(source_file))

        mux.append('--title ""')

        track_order = []
        for track_type in [Track.VID, Track.AUD, Track.SUB]:
            for track in output_tracks[track_type]:
                source_file, source_file_track_id = track_sources[track.id()]
                track_order.append('{}:{}'.format(source_file_ids[source_file], source_file_track_id))
        mux.append('--track-order {}'.format(','.join(track_order)))
        result_commands.append(u' '.join(mux))

        for source_file in source_file_ids.iterkeys():
            if source_file != movie.path():
                result_commands.append(u'del /q {}'.format(source_file))

        with codecs.open(MUX_SCRIPT, 'a', 'cp866') as fobj:
            for command in result_commands:
                fobj.write(u'{} || exit /b 1\r\n'.format(command.strip()))

    return 0

if __name__ == '__main__':
    sys.exit(main())
