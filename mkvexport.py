#!/usr/bin/python
# coding: utf-8

from __future__ import print_function

import argparse
import codecs
import os
import re
import subprocess
import sys

LANG_ORDER = ['und', 'jpn', 'eng', 'rus']
MUX_SCRIPT = 'mux.cmd'

def translate(value):
    rus_string = 'абвгдеёжзиклмнопрстуфхцчшщьыъэюя'
    eng_list = "a|b|v|g|d|e|e|zh|z|i|k|l|m|n|o|p|r|s|t|u|f|h|c|ch|sh|shch|'|y|'|e|yu|ya".split('|')
    return ''.join(eng_list[rus_string.index(c)] if c in rus_string else c for c in value)

def pprint(value):
    print(translate(value))

def quote(path):
    character = "'"
    if 'win' in sys.platform or '"' in path:
        character = '"'
    return character + path + character

def process(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0 or stderr:
        print(stderr, file=sys.stderr)
        raise Exception()
    return stdout

class Track(object):
    AUD = 'audio'
    VID = 'video'
    SUB = 'subtitles'

    def __init__(self, raw_params):
        self._data = raw_params

    def id(self):
        return self._data['id']

    def type(self):
        return self._data['type']

    def name(self):
        return self._data.get('track_name', '').replace('\\s', ' ')

    def language(self):
        return self._data['language']

    def setLanguage(self, value):
        self._data['language'] = value

    def codecId(self):
        return self._data['codec_id'] # TODO enum

    def audioChannels(self):
        return int(self._data['audio_channels'])

class Movie(object):
    def __init__(self, path):
        self._path = path
        self._tracks = None

    def path(self):
        return self._path

    def _get_tracks(self):
        if self._tracks is None:
            track_objects = {}
            raw_strings = (line for line in process(['mkvmerge', '--identify-verbose', self._path]).splitlines() if line.startswith('Track'))
            for line in raw_strings:
                match = re.match(r'^Track ID (?P<id>\d+): (?P<type>[a-z]+).+$', line)
                raw_params = match.groupdict()
                for raw_string in re.match(r'^.+?\[(.+?)\].*$', line).group(1).split():
                    k, v = raw_string.split(':')
                    raw_params[k] = v
                track = Track(raw_params)
                track_objects.setdefault(track.type(), [])
                track_objects[track.type()].append(track)
            self._tracks = track_objects
            assert len(self._tracks[Track.VID]) == 1
        return self._tracks

    def tracks(self, track_type):
        return self._get_tracks()[track_type]

def mkvs(path):
    for root, dirs, files in os.walk(path):
        for filename in sorted(files):
            if filename.endswith('.mkv'):
                yield os.path.join(root, filename)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', help='path to source directory')
    parser.add_argument('dst', help='path to destination directory')
    parser.add_argument('-al', nargs='*', choices=['rus', 'eng', 'jpn'], default=['eng', 'rus'], help='ordered list of audio languages to keep')
    parser.add_argument('-sl', nargs='*', choices=['rus', 'eng', 'jpn'], default=[], help='ordered list of subtitles languages to keep')
    parser.add_argument('-dm', default=False, action='store_true', help='downmix multi-channel audio to aac')
    parser.add_argument('-nf', default=None, help='path to names map file')
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

    for target_path, movie in movies.iteritems():
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
                    pprint(movie.path())
                    pprint('=== {}, {} ==='.format(track_type.capitalize(), target_lang.upper()))
                    for cand in sorted(candidates.itervalues(), key=lambda x: x.id()):
                        pprint('{} {} {} {}'.format(cand.id(), cand.language(), cand.codecId(), cand.name()))
                    chosen_track_id = raw_input('Enter track ID: ') # TODO abort, retry, preview, undo, wtf

                used_tracks.add(chosen_track_id)
                chosen_track = candidates[chosen_track_id]
                chosen_track.setLanguage(target_lang)
                output_tracks[track_type].append(chosen_track)

        for track_type, track_list in output_tracks.iteritems():
            track_list.sort(key=lambda t: LANG_ORDER.index(t.language()))

        if args.dm: # TODO implement
            for track in output_tracks[Track.AUD]:
                if track.audioChannels() > 2:
                    ffm = ['ffmpeg']
                    ffm.extend(['-i', quote(movie.path())])
                    # TODO map tracks
                    ffm.extend(['-f wav', '-acodec pcm_f32le', '-ac 2'])
                    # qaac.exe --tvbr 127 --quality 2 --rate keep --ignorelength --no-delay - -o "audio-2ch-downmix.m4a"
                    print(' '.join(ffm), file=sys.stderr)

        track_type_prefixes = {
            Track.VID: None,
            Track.AUD: 'audio',
            Track.SUB: 'subtitle',
        }

        mux = ['mkvmerge']
        mux.extend(['--output', quote(target_path)])
        mux.extend(['--no-track-tags', '--no-global-tags', '--disable-track-statistics-tags'])

        for track_type, prefix in track_type_prefixes.iteritems():
            tracks = output_tracks[track_type]
            if tracks:
                if prefix:
                    mux.append('--{}-tracks {}'.format(prefix, ','.join(track.id() for track in tracks)))
                for i, track in enumerate(tracks):
                    mux.append('--track-name {0}:"" --language {0}:{1} --default-track {0}:{2}'.format(track.id(), track.language(), 'yes' if i == 0 else 'no'))

        mux.append(quote(movie.path()))
        mux.append('--title ""')

        track_order = []
        for track_type in [Track.VID, Track.AUD, Track.SUB]:
            track_order.extend('0:{}'.format(track.id()) for track in output_tracks[track_type])
        mux.append('--track-order {}'.format(','.join(track_order)))

        with codecs.open(MUX_SCRIPT, 'a', 'cp866') as fobj:
            fobj.write(u' '.join(mux) + '\r\n')

    return 0

if __name__ == '__main__':
    sys.exit(main())
