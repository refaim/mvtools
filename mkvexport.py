# coding: utf-8

from __future__ import print_function

import argparse
import codecs
import functools
import json
import locale
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

MOVIE_EXTENSIONS = set([
    '.mkv',
    '.mpg',
])
MEDIA_EXTENSIONS = MOVIE_EXTENSIONS | set([
    '.srt',
])

def safe_print(s, *args, **kwargs):
    assert isinstance(s, unicode)
    print(s.encode(sys.stdout.encoding, errors='ignore'), *args, **kwargs)

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
    cmd_encoding = locale.getpreferredencoding()
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
    SUB = 'subtitle'

    TYPE_FLAGS = {
        VID: (None, '-D'),
        AUD: ('--audio-tracks', '-A'),
        SUB: ('--subtitle-tracks', '-S'),
    }

    def __init__(self, parent_path, ffm_data):
        self._parent_path = parent_path
        self._ffm_data = ffm_data
        self._duration = None

    def _tags(self):
        return self._ffm_data.setdefault('tags', {})

    def id(self):
        return self._ffm_data['index']

    def type(self):
        return self._ffm_data['codec_type']

    def codec_id(self):
        return self._ffm_data['codec_name']

    def name(self):
        return self._tags().get('title', '')

    def language(self):
        result = self._tags().get('language')
        if result in [None, 'non']:
            result = 'und'
        return result

    def set_language(self, value):
        self._tags()['language'] = value

    _DURATION_REGEXP = re.compile(r'(?P<hh>\d+):(?P<mm>\d+):(?P<ss>[\d\.]+)')

    def duration(self):
        if self._duration is None:
            duration_string = self._tags().get('DURATION-eng')
            if duration_string:
                match = self._DURATION_REGEXP.match(duration_string)
                value = match.groupdict()
                self._duration = (int(value['hh']) * 60 + int(value['mm'])) * 60 + float(value['ss'])
        return self._duration

    def is_forced(self):
        return bool(self._ffm_data['disposition']['forced']) or \
            any(s in self.name().lower() for s in [u'forced', u'форсир'])

    def is_default(self):
        return bool(self._ffm_data['disposition']['default'])

class VideoTrack(Track):
    PAL = 'not_ffmpeg_const_pal'
    NTSC = 'not_ffmpeg_const_ntsc'
    _STANDARDS = {
        '13978/583': NTSC,
        '20327/813': PAL,
        '20877/835': PAL,
        '24000/1001': NTSC,
        '25/1': PAL,
        '2997/125': NTSC,
        '30000/1001': NTSC,
    }

    YUV420P = 'yuv420p'
    CODEC_H264 = 'h264'
    PROFILE_HIGH = 'High'
    LEVEL_41 = 41

    FO_PRG = 'progressive'
    FO_INT_TOP = 'tt'
    FO_INT_BOT = 'bb'

    def __init__(self, parent_path, ffm_data):
        super(VideoTrack, self).__init__(parent_path, ffm_data)
        self._crf = None
        self._field_order = None
        self._colors = Colors(self.width(), self.height(), self.standard(), self._ffm_data)

    def width(self):
        p = self._ffm_data
        assert p['width'] == p['coded_width'] or p['coded_width'] == 0
        return p['width']

    def height(self):
        p = self._ffm_data
        assert p['height'] == p['coded_height'] or p['coded_height'] == 0
        return p['height']

    def profile(self):
        return self._ffm_data['profile']

    def level(self):
        return self._ffm_data['level']

    def pix_fmt(self):
        return self._ffm_data['pix_fmt']

    def crf(self):
        if self._crf is None:
            stdout = process(
                u'ffmpeg -i {} -an -vframes 1 -f null - -v 48 2>&1'.format(
                    quote(self._parent_path)))
            match = re.search(r'crf=(?P<crf>[\d\.]+)', stdout)
            if match:
                self._crf = float(match.groupdict()['crf'])
        return self._crf

    def colors(self):
        return self._colors

    def standard(self):
        return self._STANDARDS[self._ffm_data['r_frame_rate']]

    # TODO what about interleaved?
    def is_interlaced(self):
        if self._field_order is None:
            orders = (self.FO_PRG, self.FO_INT_BOT, self.FO_INT_TOP)
            fo = self._ffm_data.get('field_order') or \
                ask_to_select(u'Specify field order', sorted(orders))
            assert fo in orders
            self._field_order = fo
        return self._field_order in (self.FO_INT_BOT, self.FO_INT_TOP)

class Colors(object):
    BT_709 = 'bt709'
    BT_601_PAL = 'bt470bg'
    BT_601_NTSC = 'smpte170m'

    RANGE_TV = 'tv'

    def __init__(self, w, h, standard, ffm_data):
        self._width = w
        self._height = h
        self._standard = standard
        self._ffm_data = ffm_data

    def range(self):
        result = self._ffm_data.get('color_range')
        if result is None and self._ffm_data['pix_fmt'] == VideoTrack.YUV420P:
            result = self.RANGE_TV
        return result

    def correct_space(self):
        result = None
        if self._height >= 720:
            result = self.BT_709
        elif self._standard == VideoTrack.PAL:
            result = self.BT_601_PAL
        elif self._standard == VideoTrack.NTSC:
            result = self.BT_601_NTSC
        return result

    def _guess_metric(self, metric):
        result = self._ffm_data.get(metric)
        if result is None:
            result = self.correct_space()
        assert result in (self.BT_709, self.BT_601_PAL, self.BT_601_NTSC)
        return result

    def space(self):
        return self._guess_metric('color_space')

    def trc(self):
        return self._guess_metric('color_transfer')

    def primaries(self):
        return self._guess_metric('color_primaries')

class AudioTrack(Track):
    AAC = 'aac'
    AC3 = 'ac3'
    DTS = 'dts'
    MP2 = 'mp2'
    MP3 = 'mp3'
    CODEC_IDS = set([AAC, AC3, DTS, MP2, MP3])

    def channels(self):
        return int(self._ffm_data['channels'])

    def sample_rate(self):
        return int(self._ffm_data['sample_rate'])

    def is_pcm(self):
        # TODO
        # return self.codec_id() in (self.AMS,)
        return False

class WavFormat(object):
    FMT_SIGNED = 's'
    FMT_UNSIGNED = 'u'
    FMT_FLOAT = 'f'

    ENDIAN_LITTLE = 'le'
    ENDIAN_BIG = 'be'

    def __init__(self, codec_id):
        match = re.match(r'^pcm_(?P<f>s|u|f)(?P<b>16|32)(?P<e>le|be)', codec_id)
        value = match.groupdict()
        self._format = value['f']
        self._bits = int(value['b'])
        self._endianness = value['e']

    def format(self):
        return self._format

    def bits(self):
        return self._bits

    def endianness(self):
        return self._endianness

class SubtitleTrack(Track):
    # TODO use strings "srt", "pgs" etc for formats
    PGS = 'hdmv_pgs_subtitle'
    SRT = 'subrip'
    CODEC_IDS = set([PGS, SRT])

class Movie(object):
    TRACK_CLASSES = {
        Track.AUD: AudioTrack,
        Track.VID: VideoTrack,
        Track.SUB: SubtitleTrack,
    }

    def __init__(self, path):
        self._path = path
        self._tracks_by_type = None

    def path(self):
        return self._path

    def _ffprobe(self):
        tracks = {}
        for stream_specifier in ('a', 'V', 's'):
            stdout = process(
                u'ffprobe -v quiet -print_format json -show_streams -select_streams {} {}'.format(
                    stream_specifier, quote(self._path)))
            for stream in json.loads(stdout)['streams']:
                tracks[stream['index']] = stream
        return tracks

    def _get_tracks(self):
        if self._tracks_by_type is None:
            ffprobe_data = self._ffprobe()
            tracks_data = {}
            for track_id, track in ffprobe_data.iteritems():
                tracks_data.setdefault(track['codec_type'], {})[track_id] = track
            assert len(tracks_data[Track.VID]) == 1

            frame_lengths = {}
            for track_id, track_data in tracks_data.get(Track.SUB, {}).iteritems():
                track_length = track_data.get('tags', {}).get('NUMBER_OF_FRAMES-eng', None)
                if track_length is None:
                    frame_lengths = None
                    break
                frame_lengths[track_id] = int(track_length)
            if frame_lengths:
                max_length = max(frame_lengths.itervalues())
                forced_track_threshold = max_length / 100.0 * 50.0
                for track_id, track_length in frame_lengths.iteritems():
                    if (max_length - track_length) > forced_track_threshold:
                        tracks_data[Track.SUB][track_id]['disposition']['forced'] = True

            self._tracks_by_type = {}
            for track_type, tracks_of_type in tracks_data.iteritems():
                self._tracks_by_type.setdefault(track_type, [])
                for track_id, track_data in tracks_of_type.iteritems():
                    track = Movie.TRACK_CLASSES[track_type](self._path, track_data)
                    self._tracks_by_type[track_type].append(track)

        return self._tracks_by_type

    def tracks(self, track_type):
        return self._get_tracks()[track_type]

    def video_track(self):
        return self.tracks(Track.VID)[0]

    def track_index_in_type(self, track):
        return list(self.tracks(track.type())).index(track) + 1

def movie_dimensions_correct(w, h):
    return w % 16 == h % 8 == 0

def correct_movie_dimensions(w, h, x, y):
    dw = w % 16
    dh = h % 8
    return (w - dw, h - dh, x + int(math.ceil(dw * 0.5)), y + int(math.ceil(dh * 0.5)))

ACTIONS_IDX_TEXT = 0
ACTIONS_IDX_ENABLED = 1
ACTIONS_IDX_FUNC = 1
def ask_to_select(prompt, values, movie_path=None, header=None):
    actions = {
        'p': ('preview', movie_path and os.path.isfile(movie_path), lambda p: os.system('mplayer {} >nul 2>&1'.format(quote(p)))),
    }
    values_dict = values if isinstance(values, dict) else { i: v for i, v in enumerate(values) }
    chosen_id = None
    while chosen_id not in values_dict:
        if header is not None:
            print(header)
        for i, v in sorted(values_dict.iteritems()):
            safe_print(u'{} {}'.format(i, v))

        hint_strings = [u'{} {}'.format(key.upper(), text)
            for key, (text, enabled, _) in sorted(actions.iteritems()) if enabled]
        prompt_strings = [prompt]
        if hint_strings:
            prompt_strings.append('({})'.format(u', '.join(hint_strings)))
        final_prompt = u'{}: '.format(u' '.join(prompt_strings))

        response = raw_input(final_prompt).strip().lower()
        action = actions.get(response)
        if action and action[ACTIONS_IDX_ENABLED]:
            action[ACTIONS_IDX_FUNC](movie_path)
        else:
            chosen_id = try_int(response)
    return chosen_id if isinstance(values, dict) else values_dict[chosen_id]

def is_movie(filepath):
    return os.path.isfile(filepath) and os.path.splitext(filepath.lower())[1] in MOVIE_EXTENSIONS

def mkvs(path):
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for filename in sorted(files):
                filepath = os.path.join(root, filename)
                if is_movie(filepath):
                    yield filepath
    elif is_movie(path):
        yield path

# TODO progress bar, estimate, size difference in files
# TODO support windows cmd window header progress
def ffmpeg_cmds(src, dst, src_options, dst_options):
    return [
        u'chcp 65001 >nul && ffmpeg -v error -stats -y {src_opt} -i {src} {dst_opt} {dst}'.format(
            src=quote(src), src_opt=u' '.join(src_options),
            dst=quote(dst), dst_opt=u' '.join(dst_options)),
        u'chcp 866 >nul',
    ]

def cmd_path(bytestring):
    return os.path.abspath(os.path.expandvars(bytestring.decode(sys.getfilesystemencoding())))

def make_output_file(root, extension):
    return os.path.join(root, u'{}.{}'.format(uuid.uuid4(), extension.lstrip('.')))

def make_delete_command(filepath):
    return u'del /q {path}'.format(path=quote(filepath))

def write_commands(commands, fail_safe=True):
    with codecs.open(MUX_SCRIPT, 'a', 'cp866') as fobj:
        for command in commands:
            result_string = command.strip()
            if fail_safe:
                result_string = u'{} || exit /b 1'.format(command)
            # TODO Операция «Ы» и другие приключения Шурика.mkv
            fobj.write(u'{}\r\n'.format(result_string))
        fobj.write(u'\r\n')

def read_map_file(path, handle_key, handle_value):
    result = None
    if path is not None:
        if not os.path.isfile(path):
            raise Exception(u'Could not open file "{}"'.format(path))
        result = {}
        with codecs.open(path, 'r', 'utf-8') as fobj:
            for line in fobj:
                raw_key, raw_val = line.split('=')
                result[handle_key(raw_key)] = handle_value(raw_val)
    return result

def main():
    languages = sorted(LANGUAGES.iterkeys())
    parser = argparse.ArgumentParser()
    parser.add_argument('sources', type=cmd_path, nargs='+', help='paths to source directories/files')
    parser.add_argument('dst', type=cmd_path, help='path to destination directory')
    parser.add_argument('--temp', type=cmd_path, help='path to temporary directory')

    # TODO add special "all" language value

    # TODO add argument groups
    parser.add_argument('-vk', default=False, action='store_true', help='keep source video')
    parser.add_argument('-vr', default=False, action='store_true', help='recode video')
    parser.add_argument('-vt', help='force tune')

    parser.add_argument('-cr', default=False, action='store_true', help='crop video')
    parser.add_argument('-cf', type=cmd_path, default=None, help='path to crop map file')
    parser.add_argument('-sc', default=False, action='store_true', help='use same crop values for all files')

    parser.add_argument('-al', nargs='*', choices=languages, default=['eng', 'rus'], help='ordered list of audio languages to keep')
    parser.add_argument('-ar', default=False, action='store_true', help='recode audio')
    parser.add_argument('-dm', default=False, action='store_true', help='downmix multi-channel audio to stereo')

    parser.add_argument('-sl', nargs='*', choices=languages, default=[], help='ordered list of full subtitle languages to keep')
    parser.add_argument('-fl', nargs='*', choices=languages, default=[], help='ordered list of forced subtitle languages to keep')
    parser.add_argument('-fo', default=False, action='store_true', help='make forced subtitles optional')

    parser.add_argument('-xx', default=False, action='store_true', help='remove original source files')
    parser.add_argument('-eo', default=False, action='store_true', help='remux only if re-encoding')
    # TODO check name conflicts
    parser.add_argument('-nf', type=cmd_path, default=None, help='path to names map file')

    # TODO add parametes to ask for file name !!!

    args = parser.parse_args()
    if not args.temp:
        args.temp = args.dst
    if args.cf and args.sc:
        raise Exception('Use "-sc" OR "-cf"')

    make_temp_file = functools.partial(make_output_file, args.temp)

    def read_movie_path(path):
        # TODO use MOVIE_EXTENSIONS
        return os.path.normpath(path.strip()).replace(u'.mkv', u'')

    def read_crop_args(s):
        return [int(x) for x in s.strip().split(':')]

    filenames_map = read_map_file(args.nf, read_movie_path, read_movie_path)
    raw_crops_map = read_map_file(args.cf, read_movie_path, read_crop_args)

    movies = {}
    crop_args_map = None if raw_crops_map is None else {}
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
            cur_path = os.path.abspath(filepath)
            new_path = os.path.join(os.path.abspath(args.dst), new_name)
            if raw_crops_map is not None:
                crop_args_map[cur_path] = raw_crops_map[os.path.splitext(cur_name)[0]]
            movies[new_path] = Movie(cur_path)

    output_track_specs = {
        (Track.VID, False): ['und'],
        (Track.AUD, False): args.al,
        (Track.SUB, False): args.sl,
        (Track.SUB, True): args.fl,
    }

    try:
        os.remove(MUX_SCRIPT)
    except:
        pass
    write_commands(['@echo off'], fail_safe=False)

    # TODO catch some of my exceptions, report skipped file, ask for action, log skipped file
    common_crop_args = None
    for target_path, movie in sorted(movies.iteritems(), key=lambda t: t[1].path()):
        safe_print(u'=== {} ==='.format(movie.path()))
        output_tracks = {}
        for (track_type, _) in output_track_specs.iterkeys():
            output_tracks[track_type] = []
        used_tracks = set()
        reference_duration = movie.video_track().duration() or 0
        duration_threshold = reference_duration / 100.0 * 20.0
        for (track_type, search_forced), lang_list in output_track_specs.iteritems():
            forced_string = 'Forced' if search_forced else 'Full'
            for target_lang in lang_list:
                candidates = {}
                # TODO show tracks from all source media files
                # TODO print track file name if tracks from multiple files are present
                for track in movie.tracks(track_type):
                    if track.id() in used_tracks: continue
                    if track.is_forced() != search_forced: continue
                    if not track.is_forced() and abs((track.duration() or 0) - reference_duration) > duration_threshold: continue
                    if track.language() not in (target_lang, 'und') and target_lang != 'und': continue
                    if any(s in track.name().lower() for s in [u'comment', u'коммент']): continue
                    candidates[track.id()] = track
                if not candidates:
                    if search_forced and args.fo: continue
                    raise Exception('{} {} {} not found'.format(forced_string, track_type, target_lang))

                chosen_track_id = None
                if len(candidates) == 1: chosen_track_id = list(candidates.keys())[0]

                # TODO audio: prefer DVO|MVO to AVO (but not if AVO Goblin)

                if chosen_track_id not in candidates:
                    candidates_by_index = {}
                    candidates_strings = {}
                    for t in sorted(candidates.itervalues(), key=lambda t: t.id()):
                        strings = [u'(ID {})'.format(t.id()), t.language(), t.codec_id()]
                        if t.name():
                            strings.append(t.name())
                        if t.is_default():
                            strings.append(u'(default)')
                        track_index = movie.track_index_in_type(t)
                        candidates_strings[track_index] = u' '.join(strings)
                        candidates_by_index[track_index] = t.id()
                    header = u'--- {}, {}, {} ---'.format(
                        track_type.capitalize(), target_lang.upper(), forced_string)
                    chosen_track_index = ask_to_select(u'Enter track index', candidates_strings, movie.path(), header=header)
                    chosen_track_id = candidates_by_index[chosen_track_index]

                used_tracks.add(chosen_track_id)
                chosen_track = candidates[chosen_track_id]
                chosen_track.set_language(target_lang)
                output_tracks[track_type].append(chosen_track)

        def track_sort_key(t):
            lng_idx = output_track_specs[(t.type(), t.is_forced())].index(t.language())
            return lng_idx + 1000 * int(t.is_forced())

        track_sources = {}
        for track_type, track_list in output_tracks.iteritems():
            track_list.sort(key=track_sort_key)
            for track in track_list:
                track_sources[track.id()] = [movie.path(), track.id()]

        result_commands = [u'echo {}'.format(movie.path())]
        mux_temporary_files = []

        # TODO support 2pass encoding
        # TODO what if there is crf already?
        video_track = movie.video_track()
        encoded_ok = video_track.codec_id() == VideoTrack.CODEC_H264 and \
            video_track.crf() is not None and \
            video_track.profile() == VideoTrack.PROFILE_HIGH and \
            video_track.level() == VideoTrack.LEVEL_41
        if args.vr or not encoded_ok and not args.vk:
            chosen_tune = args.vt or ask_to_select(
                u'Enter tune ID',
                sorted(TUNES.iterkeys(), key=lambda k: TUNES[k][TUNES_IDX_SORT_KEY]),
                movie.path())
            tune_params = TUNES[chosen_tune]

            # TODO check out rutracker manuals for dvd rip filters and stuff
            ffmpeg_filters = []
            if video_track.is_interlaced():
                ffmpeg_filters.append('yadif=1:-1:1')

            crop_args = None
            if args.cr:
                if common_crop_args is not None:
                    crop_args = common_crop_args
                if crop_args_map is not None:
                    crop_args = crop_args_map[movie.path()]
                if crop_args is None:
                    os.system('ffmpegyag')
                    while crop_args is None:
                        try:
                            crop_args = [int(x) for x in
                                raw_input('Enter crop parameters (w:h:x:y): ').strip().split(':')]
                        except:
                            pass
                    if args.sc:
                        common_crop_args = crop_args
            if crop_args is None:
                crop_args = [video_track.width(), video_track.height(), 0, 0]
            dw, dh, dx, dy = crop_args
            if not movie_dimensions_correct(dw, dh):
                print('Adjusting crop by {}x{}'.format(dw % 16, dh % 8))
                dw, dh, dx, dy = correct_movie_dimensions(dw, dh, dx, dy)
            assert movie_dimensions_correct(dw, dh)
            if dx > 0 or dy > 0 or dw != video_track.width() or dh != video_track.height():
                ffmpeg_filters.append('crop={w}:{h}:{x}:{y}'.format(w=dw, h=dh, x=dx, y=dy))

            src_colors = video_track.colors()
            assert video_track.pix_fmt() == VideoTrack.YUV420P
            assert src_colors.range() == Colors.RANGE_TV

            dst_color_space = src_colors.correct_space()
            if src_colors.space() != dst_color_space:
                raise Exception('Not implemented')
                # TODO specify input/output color_range
                # TODO specify each input component separately
                # TODO The input transfer characteristics, color space, color primaries and color range should be set on the input data
                # TODO clarify iall=all= format string
                # ffmpeg_filters.append('colorspace=iall={}:all={}'.format(src_color_space, dst_color_space))

            ffmpeg_src_options = ['-color_range {}'.format(src_colors.range())]
            ffmpeg_dst_options = ['-an', '-sn', '-dn']
            if ffmpeg_filters:
                ffmpeg_dst_options.append('-filter:v {}'.format(','.join(ffmpeg_filters)))
            ffmpeg_dst_options.extend([
                '-c:v libx264', '-preset veryslow', '-pix_fmt {}'.format(VideoTrack.YUV420P),
                '-tune {}'.format(tune_params[TUNES_IDX_REAL_TUNE]),
                '-profile:v high', '-level:v 4.1', '-crf {}'.format(tune_params[TUNES_IDX_CRF]),
                '-map_metadata -1', '-map_chapters -1',
                '-color_range {}'.format(Colors.RANGE_TV), # TODO "16-235 is a typical NTSC luma range. PAL always uses 0-255 luma range."
                '-color_primaries {}'.format(dst_color_space),
                '-color_trc {}'.format('gamma28' if dst_color_space == Colors.BT_601_PAL else dst_color_space),
                '-colorspace {}'.format(dst_color_space),
            ])
            new_video_path = make_temp_file('.mkv')
            result_commands.extend(ffmpeg_cmds(movie.path(), new_video_path, ffmpeg_src_options, ffmpeg_dst_options))
            track_sources[video_track.id()] = [new_video_path, 0]
            mux_temporary_files.append(new_video_path)

        # TODO differ DTS from DTS-HD and vice-versa
        # TODO normalize dvd sound with eac3to
        codecs_to_recode = set([AudioTrack.MP2])
        downmix_codecs = codecs_to_recode | set([AudioTrack.AC3, AudioTrack.DTS])
        for track in output_tracks[Track.AUD]:
            if track.codec_id() not in AudioTrack.CODEC_IDS:
                raise Exception('Unhandled audio codec {}'.format(track.codec_id()))
            assert track.channels() <= 6
            recode = args.ar or track.codec_id() in codecs_to_recode
            recode = recode or args.dm and (track.codec_id() in downmix_codecs or track.channels() > 2)
            if recode:
                wav_path = make_temp_file('.wav')
                wav_format = WavFormat(track.codec_id() if track.is_pcm() else 'pcm_f32le')
                ffm_codec = 'copy' if track.is_pcm() else 'pcm_{}{}{}'.format(wav_format.format(), wav_format.bits(), wav_format.endianness())
                ffmpeg_options = ['-dn', '-sn', '-vn', '-map_metadata -1', '-map_chapters -1',
                    '-c:a {}'.format(ffm_codec), '-rf64 auto']
                if args.dm:
                    ffmpeg_options.append('-ac 2')
                ffmpeg_options.extend(['-f wav', '-map 0:{}'.format(track.id())])
                result_commands.extend(ffmpeg_cmds(movie.path(), wav_path, [], ffmpeg_options))

                m4a_path = make_temp_file('.m4a')
                qaac_options = [
                    '--tvbr {}'.format(63 if args.dm else 91), '--quality 2',
                    '--rate keep', '--no-delay',
                    '--raw', '--raw-channels {}'.format(2 if args.dm else track.channels()),
                    '--raw-rate {}'.format(track.sample_rate()),
                    '--raw-format {}{}{}'.format(wav_format.format(), wav_format.bits(), wav_format.endianness()[0])
                ]
                encode = u'qaac64 {} {} -o {}'.format(u' '.join(qaac_options), quote(wav_path), quote(m4a_path))
                result_commands.append(encode)
                result_commands.append(make_delete_command(wav_path))
                mux_temporary_files.append(m4a_path)
                track_sources[track.id()] = [m4a_path, 0]

        # TODO assert that fonts only present if subtitles ass/ssa
        # TODO support external srt subtitles
        # TODO support ass to srt convertation
        # TODO support external subtitle charset detection & re-encoding to utf-8
        for track in output_tracks[Track.SUB]:
            if track.codec_id() not in SubtitleTrack.CODEC_IDS:
                raise Exception('Unhandled subtitle codec {}'.format(track.codec_id()))
            if track.codec_id() == SubtitleTrack.PGS:
                sup_file = make_temp_file('.sup')
                # TODO use track.source_path() or smth similar instead of movie.path() here and in all other places
                result_commands.extend(ffmpeg_cmds(
                    movie.path(), sup_file, '', ['-map 0:{}'.format(track.id()), '-c:s copy']))
                idx_file = make_temp_file('.idx')
                sub_file = u'{}.sub'.format(os.path.splitext(idx_file)[0])
                result_commands.append(u'call bdsup2sub -l {} -o {} {}'.format(
                    LANGUAGES[track.language()][LANGUAGES_IDX_SUB_LANG],
                    quote(idx_file), quote(sup_file)))
                track_sources[track.id()] = [idx_file, 0]
                result_commands.append(make_delete_command(sup_file))
                mux_temporary_files.extend([idx_file, sub_file])

        mux_path = make_output_file(args.temp, 'mkv')

        mux = ['mkvmerge']
        mux.extend(['--output', quote(mux_path)])
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
                        file_track_id = track_ids_map[track.id()]
                        mux.append('--track-name {0}:""'.format(file_track_id))
                        mux.append('--language {0}:{1}'.format(file_track_id, track.language()))
                        mux.append('--default-track {0}:{1}'.format(file_track_id, 'yes' if default else 'no'))
                        if track.is_forced():
                            mux.append('--forced-track {0}:yes'.format(file_track_id))
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
        for path in sorted(set(mux_temporary_files)):
            result_commands.append(make_delete_command(path))
        # TODO use robocopy or dism to fully utilize 1gbps connection
        result_commands.append(u'copy /z {} {}'.format(quote(mux_path), quote(target_path)))
        result_commands.append(make_delete_command(mux_path))
        if args.xx:
            result_commands.append(make_delete_command(movie.path()))

        write_commands(result_commands)

        # TODO add this to batch files (mkdir creates intermediate directories automatically)
        try:
            os.makedirs(os.path.dirname(target_path))
        except:
            pass

    return 0

if __name__ == '__main__':
    sys.exit(main())
