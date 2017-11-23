#!/usr/bin/python

from __future__ import print_function

import argparse
import os
import re
import subprocess
import sys

TRACKS_TYPES = {
    'video': 'v',
    'audio': 'a',
    'subtitles': 's',
}

def quote(path):
    character = "'"
    if 'win' in sys.platform or '"' in path:
        character = '"'
    return character + path + character

def movies(path):
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.endswith('.mkv'):
                yield os.path.join(root, filename)

def process(command):
    # commandString = command
    # if isinstance(command, list):
    #     commandString = ' '.join(command)
    # print(commandString, file=sys.stderr)
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0 or stderr:
        print(stderr, file=sys.stderr)
        raise Exception()
    return stdout

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', help='path to source directory')
    parser.add_argument('dst', help='path to destination directory')
    parser.add_argument('--alangs', nargs='*', choices=['rus', 'eng', 'jpn'], default=['eng', 'rus'], help='ordered list of audio languages to keep')
    parser.add_argument('--slangs', nargs='*', choices=['rus', 'eng', 'jpn'], default=['eng', 'rus'], help='ordered list of subtitles languages to keep')
    parser.add_argument('--fnames', default=None, help='path to names map file')
    parser.add_argument('-ws', '--with-subtitles', action='store_true', default=False, help='keep subtitles')
    parser.add_argument('-wc', '--with-chapters', action='store_true', default=False, help='keep chapters')
    args = parser.parse_args()

    langs = { 'a': args.alangs, 's': args.slangs }

    namesMap = None
    if args.fnames:
        namesMap = {}
        with open(args.fnames) as fobj:
            for line in fobj:
                k, v = [os.path.normpath(s.strip()) for s in line.split('=')]
                namesMap[k] = v

    for movie in movies(args.src):
        curName = os.path.normpath(os.path.relpath(movie, args.src))
        newName = curName
        if namesMap is not None:
            newNameRaw = namesMap[os.path.splitext(curName)[0]]
            newName = None
            if newNameRaw == 'NO':
                continue
            elif newNameRaw == 'KEEP':
                newName = curName
            else:
                newName = newNameRaw + '.mkv'

        stdout = process(['mkvmerge', '--identify-verbose', movie])
        srcTracks = { k: [] for k in TRACKS_TYPES.itervalues() }
        for line in stdout.splitlines():
            if line.startswith('Track'):
                match = re.match(r'^Track ID (?P<id>\d+): (?P<type>[a-z]+).+$', line)
                track = match.groupdict()
                for rawString in re.match(r'^.+?\[(.+?)\].*$', line).group(1).split():
                    k, v = rawString.split(':')
                    for rawKey, dstKey in [('language', 'lang'), ('track_name', 'name')]:
                        if k == rawKey:
                            track[dstKey] = v
                ttype = TRACKS_TYPES[track['type']]
                if ttype == 'v':
                    track['lang'] = 'und'
                track['name'] = track.get('name', '').replace('\\s', ' ')
                if ttype == 'v' or track['lang'] in langs[ttype] or track['lang'] == 'und':
                    srcTracks[ttype].append(track)
        assert len(srcTracks['v']) == 1

        dstTracks = { k: [] for k in TRACKS_TYPES.itervalues() }
        dstTracks['v'] = srcTracks['v']

        outputTrackTypes = ['a']
        if args.with_subtitles:
            outputTrackTypes.append('s')
        for ttype in outputTrackTypes:
            for lang in langs[ttype]:
                langTracks = { track['id']: track for track in srcTracks[ttype] if track['lang'] in (lang, 'und') }
                if len(langTracks) == 0:
                    raise Exception('{} {} track not found'.format(ttype, lang))

                trackId = None
                if len(langTracks) == 1 and list(langTracks.values())[0]['lang'] != 'und':
                    trackId = list(langTracks.keys())[0]
                while trackId not in langTracks:
                    print(curName)
                    print('=== Select {} {} Track ==='.format(lang.upper(), { v: k for k, v in TRACKS_TYPES.iteritems() }[ttype]))
                    for track in sorted(langTracks.itervalues(), key=lambda x: x['id']):
                        # TODO cyrillic encoding
                        print('{} {} {}'.format(track['id'], track['lang'], track['name']))
                    print('===')
                    trackId = raw_input('ID: ')

                langTracks[trackId]['lang'] = lang
                dstTracks[ttype].append(langTracks[trackId])

        for ttype in outputTrackTypes:
            dstTracks[ttype].sort(key=lambda x: langs[ttype].index(x['lang']))

        command = ['mkvmerge']
        if not args.with_subtitles:
            command.append('--no-subtitles')
        if not args.with_chapters:
            command.append('--no-chapters')
        command.extend(['--output', quote(os.path.join(os.path.abspath(args.dst), newName))])
        command.extend(['--no-track-tags', '--no-global-tags', '--disable-track-statistics-tags'])

        for ttype, prefix in [('v', None), ('a', 'audio'), ('s', 'subtitle')]:
            if len(dstTracks[ttype]) > 0:
                if prefix is not None:
                    command.append('--{}-tracks {}'.format(prefix, ','.join(x['id'] for x in dstTracks[ttype])))
                for i, track in enumerate(dstTracks[ttype]):
                    command.append('--track-name {0}:"" --language {0}:{1} --default-track {0}:{2}'.format(track['id'], track['lang'], 'yes' if i == 0 else 'no'))

        command.append(quote(os.path.abspath(movie)))
        command.append('--title ""')

        order = []
        for ttype in ['v', 'a', 's']:
            order.extend('0:{}'.format(track['id']) for track in dstTracks[ttype])
        command.append('--track-order {}'.format(','.join(order)))

        print(' '.join(command), file=sys.stderr)

    return 0

if __name__ == '__main__':
    sys.exit(main())
