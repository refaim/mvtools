# coding: utf-8

import json
import re

import cmd
import platform

STREAM_AUD = 'a'
STREAM_SUB = 's'
STREAM_VID = 'V'

def identify_tracks(media_path, stream_ids):
    tracks = {}
    template = u'ffprobe -v quiet -print_format json -show_streams -select_streams'
    for stream_specifier in stream_ids:
        ffprobe = u' '.join([template, stream_specifier, cmd.quote(media_path)])
        for stream in json.loads(platform.execute(ffprobe))['streams']:
            tracks[stream['index']] = stream
    return tracks

# TODO progress bar, estimate, size difference in files
# TODO support windows cmd window header progress
def cmds_convert(src_file, src_opts, dst_file, dst_opts):
    ffmpeg = 'ffmpeg -v error -stats -y{src_opts}-i {src}{dst_opts}{dst}'.format(
        src=cmd.quote(src_file), src_opts=cmd.make_whitespaced_args_string(src_opts),
        dst=cmd.quote(dst_file), dst_opts=cmd.make_whitespaced_args_string(dst_opts))
    commands = [ffmpeg]
    if platform.is_windows():
        commands = [u'chcp 65001 >nul && {}'.format(ffmpeg), u'chcp 866 >nul']
    return commands

def cmds_extract_track(src_file, dst_file, track_id, src_opts=None, dst_opts=None):
    if src_opts is None: src_opts = []
    if dst_opts is None: dst_opts = []
    return cmds_convert(
        src_file, [] + src_opts,
        dst_file, ['-map_metadata -1', '-map_chapters -1', '-map 0:{}'.format(track_id)] + dst_opts)

def detect_crf(video_path):
    ffmpeg = u'ffmpeg -i {} -an -vframes 1 -f null - -v 48 2>&1'.format(cmd.quote(video_path))
    stdout = platform.execute(ffmpeg)
    match = re.search(r'crf=(?P<crf>[\d\.]+)', stdout)
    return float(match.groupdict()['crf']) if match else None
