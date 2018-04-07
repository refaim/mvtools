import json
import os
import re
import xml.dom.minidom

import platform

FFMPEG_STREAM_AUD = 'a'
FFMPEG_STREAM_SUB = 's'
FFMPEG_STREAM_VID = 'V'

def quote(path):
    if path == '-':
        return path

    q = u''
    if ' ' in path:
        q = u"'"
        if platform.is_windows() or "'" in path:
            assert '"' not in path
            q = u'"'
    return q + path + q

# TODO escape ';' and find out what characters need to escape
def escape(path):
    return re.sub(r'\^?&', u'^&', path)

def gen_del_files(*args):
    return [u'del /q {}'.format(' '.join(quote(p) for p in args))]

def gen_move_file(src_file, dst_file):
    return [
        u'robocopy {src_folder} {dst_folder} {src_name} /Z /MOV /NS /NC /NDL /NJH /NJS'.format(
            src_folder=quote(os.path.dirname(src_file)),
            dst_folder=quote(os.path.dirname(dst_file)),
            src_name=quote(os.path.basename(src_file))),
        u'if exist {dst_file} del /q {dst_file}'.format(
            dst_file=quote(dst_file)),
        u'ren {src_file} {dst_name}'.format(
            src_file=quote(os.path.join(os.path.dirname(dst_file), os.path.basename(src_file))),
            dst_name=quote(os.path.basename(dst_file)))
    ]

def gen_create_dir(dir_path):
    return [u'if not exist {path} mkdir {path}'.format(path=quote(dir_path))]

def _make_whitespaced_args_string(args):
    result = u' '
    if args:
        result = u' {} '.format(' '.join(args))
    return result

def gen_ffmpeg_convert(src_file, src_opts, dst_file, dst_opts):
    return [u'ffmpeg -v error -stats -y{src_opts}-i {src}{dst_opts}{dst}'.format(
        src=quote(src_file), src_opts=_make_whitespaced_args_string(src_opts),
        dst=quote(dst_file), dst_opts=_make_whitespaced_args_string(dst_opts))]

def gen_mkvtoolnix_extract_track(src_file, dst_file, track_id):
    return [u'mkvextract {src_file} tracks {track_id}:{dst_file}'.format(
        src_file=src_file, track_id=track_id, dst_file=dst_file)]

def gen_ffmpeg_extract_track(src_file, dst_file, track_id, src_opts=None, dst_opts=None):
    if src_opts is None: src_opts = []
    if dst_opts is None: dst_opts = []
    return gen_ffmpeg_convert(
        src_file, [] + src_opts,
        dst_file, ['-map_metadata -1', '-map_chapters -1', '-map 0:{}'.format(track_id)] + dst_opts)

def gen_bdsup2sub(src_file, dst_file, language):
    return [u'java -jar {jar} -l {lng} -o {dst} {src}'.format(
        jar=quote(platform.execute('where bdsup2sub.jar').strip()),
        lng=language, dst=quote(dst_file), src=quote(src_file))]

def ffprobe(media_path, stream_ids):
    tracks = {}
    ffprobe_opts = [
        u'-v quiet',
        u'-print_format json',
        u'-probesize {}'.format(50 * 1024 * 1024),
        u'-analyzeduration {}'.format(int(3e+7)),
        u'-show_streams',
    ]
    for stream_specifier in stream_ids:
        ffprobe = u'ffprobe {opts} -select_streams {stream} {path}'.format(
            opts=u' '.join(ffprobe_opts), stream=stream_specifier, path=quote(media_path))
        for stream in json.loads(platform.execute(ffprobe))['streams']:
            tracks[stream['index']] = stream
    return tracks

def mediainfo(media_path):
    doc = xml.dom.minidom.parseString(platform.execute(u'mediainfo --Output=XML {}'.format(quote(media_path))))
    media_info = doc.getElementsByTagName('MediaInfo')[0]
    media = media_info.getElementsByTagName('media')[0]
    result = {}
    for track in media.getElementsByTagName('track'):
        if track.getAttribute('type') in ('Video', 'Audio', 'Text'):
            track_data = {}
            for tag in track.childNodes:
                if isinstance(tag, xml.dom.minidom.Element):
                    track_data[tag.nodeName] = tag.childNodes[0].nodeValue
            track_data['ID'] = int(track_data['ID']) - 1
            result[track_data['ID']] = track_data
    return result

def detect_crf(movie_path):
    ffmpeg = u'ffmpeg -i {} -an -vframes 1 -f null - -v 48 2>&1'.format(quote(movie_path))
    stdout = platform.execute(ffmpeg)
    match = re.search(r'crf=(?P<crf>[\d\.]+)', stdout)
    return float(match.groupdict()['crf']) if match else None
