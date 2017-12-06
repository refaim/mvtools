# coding: utf-8

from __future__ import print_function

import argparse
import codecs
import json
import math
import os
import re
import subprocess
import sys
import uuid

LANG_ORDER = ['und', 'jpn', 'eng', 'rus']
MUX_SCRIPT = 'mux.cmd'

TUNES_IDX_SORT_KEY = 0
TUNES_IDX_CRF = 1
TUNES_IDX_REAL_TUNE = 2
TUNES = {
    'animation': (1, 18, 'animation'),
    'film': (2, 22, 'film'),
    'trash': (3, 23, 'film'),
    'supertrash': (4, 25, 'film'),
}

LANGUAGES_IDX_SUB_LANG = 0
LANGUAGES = {
    'rus': ('ru',),
    'eng': ('en',),
    'jpn': ('jp',),
}

def try_int(value):
    try:
        return int(value)
    except:
        return None

def is_windows():
    return 'win' in sys.platform

def quote(path):
    character = ''
    if ' ' in path:
        character = u"'"
        if is_windows() or '"' in path:
            character = u'"'
    return character + path + character

def process(command):
    cmd_encoding = 'cp1251' if is_windows() else 'utf-8'
    if isinstance(command, list):
        result_command = [arg.encode(cmd_encoding) for arg in command]
    else:
        result_command = command.encode(cmd_encoding)
    p = subprocess.Popen(result_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    if p.returncode != 0 or stderr:
        print(stderr, file=sys.stderr)
        raise Exception()
    return stdout

class Track(object):
    AUD = 'audio'
    VID = 'video'
    SUB = 'subtitles'

    TYPE_FLAGS = {
        VID: (None, '-D'),
        AUD: ('--audio-tracks', '-A'),
        SUB: ('--subtitle-tracks', '-S'),
    }

    def __init__(self, parent_path, raw_params):
        self._parent_path = parent_path
        self._data = raw_params

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
        return unicode(self._data['codec_id'])

class VideoTrack(Track):
    FO_PRG = 'progressive'
    FO_INT_TOP = 'tt'
    FO_INT_BOT = 'bb'
    _KNOWN_FO = set([FO_PRG, FO_INT_BOT, FO_INT_TOP])

    def __init__(self, parent_path, raw_params):
        super(VideoTrack, self).__init__(parent_path, raw_params)
        self._crf = None
        self._field_order = None
        self._probe = None

    def probe(self):
        if self._probe is None:
            stdout = process(
                u'ffprobe -v quiet -print_format json -select_streams v -show_streams {}'.format(
                    quote(self._parent_path)))
            self._probe = json.loads(stdout)['streams'][0]
        return self._probe

    def crf(self):
        if self._crf is None:
            stdout = process(
                u'ffmpeg -i {} -an -vframes 1 -f null - -v 48 2>&1'.format(
                    quote(self._parent_path)))
            match = re.search(r'crf=(?P<crf>[\d\.]+)', stdout)
            if match:
                self._crf = float(match.groupdict()['crf'])
        return self._crf

    def is_interlaced(self):
        if self._field_order is None:
            self._field_order = self.probe().get('field_order') or \
                ask_to_select(u'Specify field order', sorted(self._KNOWN_FO))
        if self._field_order not in self._KNOWN_FO:
            raise Exception(u'Unknown field order {}'.format(self._field_order))
        return self._field_order in (self.FO_INT_BOT, self.FO_INT_TOP)

class AudioTrack(Track):
    CODEC_AAC = 'A_AAC'
    CODEC_AC3 = 'A_AC3'
    CODEC_DTS = 'A_DTS'
    CODEC_MP3 = 'A_MPEG/L3'
    KNOWN_CODECS = set([CODEC_AAC, CODEC_AC3, CODEC_DTS, CODEC_MP3])

    def channels(self):
        return int(self._data['audio_channels'])

class SubtitleTrack(Track):
    CODEC_PGS = 'S_HDMV/PGS'

class Movie(object):
    TRACK_CLASSES = {
        Track.AUD: AudioTrack,
        Track.VID: VideoTrack,
        Track.SUB: SubtitleTrack,
    }

    def __init__(self, path):
        self._path = path
        self._mkv_tracks = None

    def path(self):
        return self._path

    def _get_tracks(self):
        if self._mkv_tracks is None:
            track_objects = {}
            # TODO do not use mkvmerge, use only ffprobe
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
                track = Movie.TRACK_CLASSES[raw_params['type']](self._path, raw_params)
                track_objects.setdefault(track.type(), [])
                track_objects[track.type()].append(track)
            self._mkv_tracks = track_objects
            assert len(self._mkv_tracks[Track.VID]) == 1
        return self._mkv_tracks

    def tracks(self, track_type):
        return self._get_tracks()[track_type]

    def video_track(self):
        return self.tracks(Track.VID)[0]

def ask_to_select(prompt, values, header=None):
    values_dict = values if isinstance(values, dict) else { i: v for i, v in enumerate(values) }
    chosen_id = None
    while chosen_id not in values_dict:
        if header is not None:
            print(header)
        for i, v in sorted(values_dict.iteritems()):
            print(u'{} {}'.format(i, v))
        chosen_id = try_int(raw_input(u'{}: '.format(prompt)))
    return values_dict[chosen_id]

def is_movie(filepath):
    return os.path.isfile(filepath) and filepath.lower().endswith('.mkv')

def mkvs(path):
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for filename in sorted(files):
                if filename.lower().endswith('.mkv'):
                    yield os.path.join(root, filename)
    elif is_movie(path):
        yield path

def ffmpeg_cmds(src, dst, options):
    return [
        u'chcp 65001 && ffmpeg -v error -stats -y -i {src} {options} {dst}'.format(
            src=quote(src), dst=quote(dst), options=u' '.join(options)),
        u'chcp 866',
    ]

def cmd_string(bytestring):
    return bytestring.decode(sys.getfilesystemencoding())

def make_output_file(root, extension):
    return os.path.join(root, u'{}.{}'.format(uuid.uuid4(), extension))

def write_commands(commands, fail_safe=True):
    with codecs.open(MUX_SCRIPT, 'a', 'cp866') as fobj:
        for command in commands:
            result_string = command.strip()
            if fail_safe:
                result_string = u'{} || exit /b 1'.format(command)
            fobj.write(u'{}\r\n'.format(result_string))
        fobj.write(u'\r\n')

def main():
    languages = sorted(LANGUAGES.iterkeys())
    parser = argparse.ArgumentParser()
    parser.add_argument('sources', type=cmd_string, nargs='+', help='paths to source directories/files')
    parser.add_argument('dst', type=cmd_string, help='path to destination directory')
    # TODO make list order matter
    parser.add_argument('-al', nargs='*', choices=languages, default=['eng', 'rus'], help='ordered list of audio languages to keep')
    parser.add_argument('-sl', nargs='*', choices=languages, default=[], help='ordered list of subtitles languages to keep')
    parser.add_argument('-dm', default=False, action='store_true', help='downmix multi-channel and/or ac3/dts audio to aac')
    parser.add_argument('-kv', default=False, action='store_true', help='keep video from re-encoding')
    parser.add_argument('-nf', type=cmd_string, default=None, help='path to names map file')
    parser.add_argument('-xx', default=False, action='store_true', help='remove original source files')
    parser.add_argument('-eo', default=False, action='store_true', help='remux only if re-encoding')
    parser.add_argument('-pp', default=False, action='store_true', help='prefer pgs subtitles')
    parser.add_argument('-cr', default=False, action='store_true', help='crop video')
    parser.add_argument('-sc', default=False, action='store_true', help='use same crop values for all files')
    parser.add_argument('-ft', help='force tune')
    # TODO add parametes to ask for file name !!!
    args = parser.parse_args()

    filenames_map = None
    if args.nf and os.path.exists(args.nf):
        filenames_map = {}
        with codecs.open(args.nf, 'r', 'utf-8') as fobj:
            for line in fobj:
                k, v = [os.path.normpath(s.strip()).replace(u'.mkv', u'') for s in line.split('=')]
                filenames_map[k] = v

    movies = {}
    for argspath in args.sources:
        for filepath in mkvs(argspath):
            cur_name = os.path.basename(filepath)
            if os.path.isdir(argspath):
                cur_name = os.path.relpath(filepath, argspath)
            cur_name = os.path.normpath(cur_name)
            new_name = cur_name
            if filenames_map is not None:
                raw_new_name_string = filenames_map[os.path.splitext(cur_name)[0]]
                new_name = None
                if raw_new_name_string == 'NO': continue
                elif raw_new_name_string == 'KEEP': new_name = cur_name
                else: new_name = u'{}.mkv'.format(raw_new_name_string)
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
    write_commands(['@echo off'], fail_safe=False)

    global_crop_params = None
    for target_path, movie in sorted(movies.iteritems(), key=lambda t: t[1].path()):
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

                comment_track_ids = [track_id for track_id, track
                    in candidates.iteritems() if any(s in track.name().lower() for s in [u'comment', u'коммент'])]
                if len(comment_track_ids) == len(candidates) - 1:
                    chosen_track_id = list(set(candidates.keys()) - set(comment_track_ids))[0]

                if args.pp and track_type == Track.SUB:
                    pgs_candidates = [track.id() for track in candidates.itervalues() if track.codecId() == SubtitleTrack.CODEC_PGS]
                    if len(pgs_candidates) == 1:
                        chosen_track_id = pgs_candidates[0]

                if chosen_track_id not in candidates:
                    candidates_strings = { t.id(): u'{} {} {}'.format(t.language(), t.codecId(), t.name())
                        for t in sorted(candidates.itervalues(), key=lambda t: t.id()) }
                    chosen_track_id = ask_to_select(u'Enter track ID', candidates_strings,
                        header=u'--- {}, {} ---'.format(track_type.capitalize(), target_lang.upper()))

                used_tracks.add(chosen_track_id)
                chosen_track = candidates[chosen_track_id]
                chosen_track.setLanguage(target_lang)
                output_tracks[track_type].append(chosen_track)

        track_sources = {}
        for track_type, track_list in output_tracks.iteritems():
            track_list.sort(key=lambda t: LANG_ORDER.index(t.language()))
            for track in track_list:
                track_sources[track.id()] = [movie.path(), track.id()]

        result_commands = [u'echo {}'.format(movie.path())]
        temporary_files = []
        encode_root = os.path.dirname(target_path)

        # TODO check if codec x264 and profile 4.1
        # TODO what if there is crf already?
        video_track = movie.video_track()
        # if not args.kv:
        # TODO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        if not args.kv and video_track.crf() is None:
            chosen_tune = args.ft or ask_to_select(
                u'Enter tune ID',
                sorted(TUNES.iterkeys(), key=lambda k: TUNES[k][TUNES_IDX_SORT_KEY]))
            tune_params = TUNES[chosen_tune]

            # TODO convert colorspace, color matrix, etc
            ffmpeg_filters = []
            if video_track.is_interlaced():
                ffmpeg_filters.append('yadif=1:-1:0')
            if args.cr:
                crop_params = None
                if global_crop_params is not None:
                    crop_params = global_crop_params
                if crop_params is None:
                    os.system('ffmpegyag')
                    crop_params = raw_input('Enter crop parameters (w:h:x:y): ')
                    if args.sc:
                        global_crop_params = crop_params

                w, h, x, y = [int(n) for n in crop_params.split(':')]
                dw = w % 16
                dh = h % 8
                x += int(math.ceil(dw * 0.5))
                y += int(math.ceil(dh * 0.5))
                w -= dw
                h -= dh
                assert w % 16 == 0 and h % 8 == 0

                ffmpeg_filters.append('crop={w}:{h}:{x}:{y}'.format(w=w, h=h, x=x, y=y))

            ffmpeg_options = ['-an', '-sn', '-dn']
            if ffmpeg_filters:
                ffmpeg_options.append('-filter:v {}'.format(','.join(ffmpeg_filters)))
            ffmpeg_options.extend([
                '-c:v libx264', '-preset veryslow',
                '-tune {}'.format(tune_params[TUNES_IDX_REAL_TUNE]),
                '-profile:v high', '-level:v 4.1', '-crf {}'.format(tune_params[TUNES_IDX_CRF]),
                '-map_metadata -1', '-map_chapters -1',
            ])
            new_video_path = make_output_file(encode_root, 'mkv')
            result_commands.extend(ffmpeg_cmds(movie.path(), new_video_path, ffmpeg_options))
            track_sources[video_track.id()] = [new_video_path, 0]
            temporary_files.append(new_video_path)

        if args.dm:
            for track in output_tracks[Track.AUD]:
                if track.codecId() not in AudioTrack.KNOWN_CODECS:
                    raise Exception(u'Unknown audio codec {}'.format(track.codecId()))
                if track.codecId() in (AudioTrack.CODEC_AC3, AudioTrack.CODEC_DTS) or track.channels() > 2:
                    wav_path = make_output_file(encode_root, 'wav')
                    result_commands.extend(ffmpeg_cmds(movie.path(), wav_path, [
                        '-dn', '-sn', '-vn',
                        '-map_metadata -1', '-map_chapters -1',
                        '-c:a pcm_f32le', '-ac 2', '-f wav', '-map 0:{}'.format(track.id()),
                    ]))

                    m4a_path = make_output_file(encode_root, 'm4a')
                    qaac_options = ['--tvbr 63', '--quality 2', '--rate keep', '--ignorelength', '--no-delay']
                    encode = u'qaac64 {} {} -o {}'.format(u' '.join(qaac_options), quote(wav_path), quote(m4a_path))
                    result_commands.append(encode)
                    track_sources[track.id()] = [m4a_path, 0]
                    temporary_files.extend([wav_path, m4a_path])

        pgs_tracks = { track.id(): track for track in output_tracks[Track.SUB]
            if track.codecId() == SubtitleTrack.CODEC_PGS }
        if pgs_tracks:
            sup_files = { track_id: make_output_file(encode_root, 'sup') for track_id in pgs_tracks.iterkeys() }
            result_commands.append(u'mkvextract tracks {} {}'.format(
                quote(movie.path()),
                u' '.join(u'{}:{}'.format(track_id, quote(sup_file)) for track_id, sup_file in sup_files.iteritems())
            ))
            for track_id, sup_file in sup_files.iteritems():
                idx_file = make_output_file(encode_root, 'idx')
                result_commands.append(u'call bdsup2sub -l {} -o {} {}'.format(
                    LANGUAGES[pgs_tracks[track_id].language()][LANGUAGES_IDX_SUB_LANG],
                    quote(idx_file), quote(sup_file)))
                track_sources[track_id] = [idx_file, 0]
                temporary_files.extend([sup_file, idx_file, u'{}.sub'.format(os.path.splitext(idx_file)[0])])

        mux = ['mkvmerge']
        mux.extend(['--output', quote(target_path)])
        mux.extend(['--no-track-tags', '--no-global-tags', '--disable-track-statistics-tags'])

        track_ids_by_files = {}
        for movie_track_id, (source_file, source_file_track_id) in track_sources.iteritems():
            track_ids_by_files.setdefault(source_file, {})[movie_track_id] = source_file_track_id

        source_file_ids = {}
        for i, (source_file, track_ids_map) in enumerate(track_ids_by_files.iteritems()):
            source_file_ids[source_file] = i
            for track_type, (tracks_flags_yes, tracks_flag_no) in Track.TYPE_FLAGS.iteritems():
                cur_file_tracks = [track for track in output_tracks[track_type] if track.id() in track_ids_map]
                if cur_file_tracks:
                    if tracks_flags_yes:
                        mux.append('{} {}'.format(tracks_flags_yes, ','.join(str(track_ids_map[track.id()]) for track in cur_file_tracks)))
                    for track in cur_file_tracks:
                        default = track.id() == output_tracks[track_type][0].id()
                        mux.append('--track-name {0}:"" --language {0}:{1} --default-track {0}:{2}'.format(track_ids_map[track.id()], track.language(), 'yes' if default else 'no'))
                elif tracks_flag_no:
                    mux.append(tracks_flag_no)
            mux.append(u'--no-track-tags --no-attachments --no-buttons --no-global-tags {}'.format(quote(source_file)))

        mux.append('--title ""')

        track_order = []
        for track_type in [Track.VID, Track.AUD, Track.SUB]:
            for track in output_tracks[track_type]:
                source_file, source_file_track_id = track_sources[track.id()]
                track_order.append('{}:{}'.format(source_file_ids[source_file], source_file_track_id))
        mux.append('--track-order {}'.format(','.join(track_order)))

        if len(source_file_ids) > 1 or not args.eo:
            result_commands.append(u' '.join(mux))

        if args.xx:
            temporary_files.append(movie.path())
        for path in sorted(set(temporary_files)):
            result_commands.append(u'if exist {path} del /q {path}'.format(path=quote(path)))

        write_commands(result_commands)

        # TODO add this to batch files
        try:
            os.makedirs(os.path.dirname(target_path))
        except:
            pass

    return 0

if __name__ == '__main__':
    sys.exit(main())
