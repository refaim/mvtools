# coding: utf-8

import argparse
import codecs
import collections
import os
import re
import shutil

import tvdb_api

from modules import cli
from modules import cmd
from modules import lang
from modules import media
from modules import misc
from modules import platform
from modules.ffmpeg import Ffmpeg
from modules.formats import VideoCodec, PictureFormat, AudioCodec, SubtitleCodec, FieldOrder, VideoCodecProfile, \
    VideoCodecLevel, FileFormat, TrackType
from modules.tracks import Track, VideoTrack

MUX_BODY = os.path.join(platform.getcwd(), u'mux.cmd')
MUX_HEAD = os.path.join(os.path.dirname(__file__), u'mux_head.cmd')

class InputTune(misc.MyEnum):
    ANIMATION = 1
    FILM = 2

class InputQuality(misc.MyEnum):
    GOOD = 1
    TRASH = 2
    SUPERTRASH = 3

CODEC_TUNES = {
    VideoCodec.H264: {
        InputTune.ANIMATION: {
            InputQuality.GOOD: (18, 'animation'),
            InputQuality.TRASH: (23, 'animation'),
        },
        InputTune.FILM: {
            InputQuality.GOOD: (22, 'film'),
            InputQuality.TRASH: (23, 'film'),
            InputQuality.SUPERTRASH: (25, 'film'),
        }
    },
    VideoCodec.H265: {
        InputTune.ANIMATION: {
            InputQuality.GOOD: (20, 'animation'),
            InputQuality.TRASH: (25, 'animation'),
        },
        InputTune.FILM: {
            InputQuality.GOOD: (24, None),
            InputQuality.TRASH: (26, None),
            InputQuality.SUPERTRASH: (28, None),
        }
    }
}

# TODO determine by device
CODEC_FFMPEG_PARAMETERS = {
    VideoCodec.H264: (VideoCodecProfile.HIGH, VideoCodecLevel.L41),
    VideoCodec.H265: (VideoCodecProfile.MAIN, VideoCodecLevel.L51),
}

CHANNEL_SCHEMES = {
    '1.0': 1,
    '2.0': 2,
    '5.1': 6,
}

ACTIONS_IDX_TEXT = 0
ACTIONS_IDX_ENABLED = 1
ACTIONS_IDX_FUNC = 2
# TODO table-like print
def ask_to_select(prompt, values, handle_response=lambda x: x, header=None):
    values_dict = values if isinstance(values, dict) else {i: v for i, v in enumerate(values)}
    chosen_id = None
    while chosen_id not in values_dict:
        if header is not None:
            platform.print_string(header)
        value_fmt = u'{:>%d} {}' % max(len(str(i)) for i in values_dict.iterkeys())
        for i, v in sorted(values_dict.iteritems()):
            platform.print_string(value_fmt.format(i, v))
        try:
            response = raw_input(u'{}: '.format(prompt)).strip().lower()
            handle_response(response)
        except EOFError:
            raise KeyboardInterrupt()
        chosen_id = misc.try_int(response)
    return chosen_id if isinstance(values, dict) else values_dict[chosen_id]

def ask_to_select_tracks(movie, track_type, candidates, header):
    def handle_response(text):
        mpv_opts = {TrackType.AUD: u'--audio-file {}', TrackType.SUB: u'--sub-file {}'}
        if text == 'p':
            # TODO add chosen audio tracks when choosing subtitles
            # TODO somehow consider track delays
            command = [u'mpv {}'.format(cmd.quote(list(movie.tracks(TrackType.VID))[0].source_file()))]
            for track in sorted(candidates, key=lambda t: movie.track_index_in_type(t)):
                if track.is_single():
                    command.append(mpv_opts[track.type()].format(cmd.quote(track.source_file())))
            platform.execute(u'{} >nul 2>&1'.format(u' '.join(command)), capture_output=False)
        return text

    candidate_strings = {}
    from_single_file = len({t.source_file() for t in candidates}) == 1
    for track in candidates:
        strings = [u'(ID {})'.format(track.id()), track.language(), track.codec_name()]
        if track_type == TrackType.AUD:
            strings.append('{}ch'.format(track.channels()))
        if track.name():
            strings.append(track.name())
        if track.is_default():
            strings.append(u'(default)')
        if not from_single_file:
            strings.append(u'[{}]'.format(os.path.basename(track.source_file())))
        candidate_strings[movie.track_index_in_type(track)] = u' '.join(strings)
    return ask_to_select(u'Enter track index', candidate_strings, handle_response, header)

def is_media_file_path(file_path):
    return len(media.File.possible_track_types(file_path)) > 0

def is_movie_satellite(movie_path, candidate_path):
    md, mn = platform.split_path(movie_path)
    cd, cn = platform.split_path(candidate_path)
    return md.lower() == cd.lower() and cn.lower().startswith(os.path.splitext(mn)[0].lower())

def find_movies(search_path, ignore_languages, detect_satellites):
    found_files = []
    if os.path.isfile(search_path):
        search_dir = os.path.dirname(search_path)
        for name in os.listdir(search_dir):
            if detect_satellites and is_movie_satellite(search_path, os.path.join(search_dir, name)):
                found_files.append(os.path.join(search_dir, name))
    elif os.path.isdir(search_path):
        for search_dir, _, files in os.walk(search_path):
            found_files.extend(os.path.join(search_dir, name) for name in files)

    media_by_folder = {}
    for path in (os.path.abspath(fp) for fp in found_files):
        if is_media_file_path(path):
            media_by_folder.setdefault(os.path.dirname(path), set()).add(path)

    media_groups = []
    for remaining_media in media_by_folder.itervalues():
        video_paths = [fp for fp in remaining_media if TrackType.VID in media.File.possible_track_types(fp)]
        for video in sorted(video_paths, key=len):
            group = []
            if video in remaining_media:
                remaining_media.remove(video)
                group = [path for path in remaining_media if detect_satellites and is_movie_satellite(video, path)]
                media_groups.append([video] + group)
            remaining_media -= set(group)

    for group in sorted(media_groups, key=lambda g: [os.path.dirname(g[0]).lower(), os.path.basename(g[0]).lower(), os.path.splitext(g[0])[1].lower()]):
        yield media.Movie(group, ignore_languages)

def read_map_file(path, handle_key, handle_value):
    result = None
    if path is not None:
        if not os.path.isfile(path):
            raise cli.Error(u'Could not open file "{}"'.format(path))
        result = {}
        with codecs.open(path, 'r', 'utf-8') as fobj:
            for line in fobj:
                raw_key, raw_val = line.split('=')
                result[handle_key(raw_key)] = handle_value(raw_val)
    return result

def add_enum_argument(parser, arg, enum_class, default, help_text):
    parser.add_argument(arg, choices=enum_class.get_names(), default=default, help=help_text)

def main():
    parser = argparse.ArgumentParser()
    # TODO support sources as wildcards
    parser.add_argument('sources', type=cli.argparse_path, nargs='+', help='paths to source directories/files')
    parser.add_argument('dst', type=cli.argparse_path, help='path to destination directory')

    # TODO add argument groups
    parser.add_argument('-vk', default=False, action='store_true', help='keep source video')
    parser.add_argument('-vr', default=False, action='store_true', help='recode video')
    parser.add_argument('-vc', choices=VideoCodec.get_names([VideoCodec.H264, VideoCodec.H265]), default=VideoCodec.H264.name, help='set video encoding codec')
    add_enum_argument(parser, '-vt', InputTune, None, 'set video encoding tune')
    add_enum_argument(parser, '-vq', InputQuality, None, 'set video encoding quality')
    parser.add_argument('-va', default=None, choices=['16:9'], help='set video display aspect ratio')
    parser.add_argument('-vs', default=None, choices=['720p', '1080p', '1440p'], help='scale video')
    parser.add_argument('-ks', default=False, action='store_true', help='keep current colorspace')

    parser.add_argument('-cr', default=False, action='store_true', help='crop video')
    parser.add_argument('-cf', type=cli.argparse_path, default=None, help='path to crop map file')
    parser.add_argument('-sc', default=False, action='store_true', help='use same crop values for all files')

    parser.add_argument('-al', nargs='*', type=cli.argparse_lang, default=[], help='ordered list of audio 3-letter language codes to keep')
    parser.add_argument('-ar', default=False, action='store_true', help='recode audio')
    parser.add_argument('-ad', default='5.1', choices=CHANNEL_SCHEMES.keys(), help='downmix to N channels')
    parser.add_argument('-aw', default=False, action='store_true', help='convert audio to wavfile before encoding')

    parser.add_argument('-sl', nargs='*', type=cli.argparse_lang, default=[], help='ordered list of full subtitle 3-letter language codes to keep')
    parser.add_argument('-fl', nargs='*', type=cli.argparse_lang, default=[], help='ordered list of forced subtitle  3-letter language codes to keep')
    parser.add_argument('-fo', default=False, action='store_true', help='make forced subtitles optional')

    parser.add_argument('-nf', type=cli.argparse_path, default=None, help='path to names map file')
    parser.add_argument('-tv', default=None, help='TV series name')
    parser.add_argument('-il', default=False, action='store_true', help='Ignore track language data')
    parser.add_argument('-xx', default=False, action='store_true', help='Remove original files after processing')
    parser.add_argument('-ma', default=False, action='store_true', help='Append mux file instead of overwrite')
    parser.add_argument('-ds', default=False, action='store_true', help='Disable movie sattelites detection')
    parser.add_argument('-sd', default=False, action='store_true', help='Securely delete files using sdelete utility')

    args = parser.parse_args()
    if args.cf and args.sc:
        parser.error(u'Use -cf or -sc, not both')
    if args.nf and args.tv:
        parser.error(u'Use -nf or -tv, not both')
    if args.vk and (args.vr or args.vt):
        parser.error(u'Use -vk or -vr/-vt, not both')
    if not args.vk and (not args.vt or not args.vq):
        parser.error(u'Set -vt and -vq')

    args.vc = VideoCodec.get_definition(args.vc)
    if args.vt:
        args.vt = InputTune.get_definition(args.vt)
    if args.vq:
        args.vq = InputQuality.get_definition(args.vq)

    def read_movie_path(path):
        path = os.path.normpath(path.strip())
        if is_media_file_path(path):
            path = os.path.splitext(path)[0]
        return path

    def read_crop_args(s):
        s = s.strip()
        if s.lower() == 'no':
            return False
        return [int(x) for x in s.split(':')]

    filenames_map = read_map_file(args.nf, read_movie_path, read_movie_path)
    raw_crops_map = read_map_file(args.cf, read_movie_path, read_crop_args)

    tvdb = None
    if args.tv:
        tvdb = tvdb_api.Tvdb()

    movies = {}
    crop_args_map = None if raw_crops_map is None else {}
    for argspath in args.sources:
        for movie_object in find_movies(argspath, args.il, not args.ds):
            cur_path = os.path.normpath(os.path.relpath(movie_object.main_path(), platform.getcwd()))
            if raw_crops_map is not None:
                crop_args_map[movie_object.main_path()] = raw_crops_map[os.path.splitext(cur_path)[0]]
            if args.tv:
                movie_name = os.path.basename(movie_object.main_path())
                src_season = int(re.match(r'.*s(\d+)', movie_name, re.IGNORECASE).group(1))
                src_episodes = [int(x) for x in re.findall(r'e(\d+)', movie_name, re.IGNORECASE)]
                ep_numbers = []
                ep_names = set()
                for src_episode in src_episodes:
                    ep_info = tvdb[args.tv][src_season][src_episode]
                    epn_dvd = ep_info['dvdEpisodeNumber']
                    epn_air = ep_info['airedEpisodeNumber']
                    if epn_dvd is not None and epn_dvd != epn_air:
                        epn_dvd_int = int(float(epn_dvd))
                        epn_dvd_frc = float(epn_dvd) - epn_dvd_int
                        assert int(epn_air) == int(round(epn_dvd_int + (epn_dvd_frc - 0.1) * 10)), 'd{} a{}'.format(epn_dvd, epn_air)
                    ep_numbers.append(int(epn_air))
                    ep_names.add(re.sub(r'\(\d\)$', '', ep_info['episodename']).strip())
                assert len(ep_numbers) > 0 and len(ep_names) == 1, ep_names
                cur_path = u'{} {}.mkv'.format('-'.join(u'{:02d}'.format(epn) for epn in sorted(ep_numbers)), list(ep_names)[0])
            elif filenames_map is not None:
                raw_new_name_string = filenames_map[os.path.splitext(cur_path)[0]]
                cur_path = None
                if raw_new_name_string == 'NO': continue
                elif raw_new_name_string == 'KEEP': cur_path = cur_path
                else: cur_path = raw_new_name_string
            if is_media_file_path(cur_path):
                cur_path = os.path.splitext(cur_path)[0]
            new_name = u'{}.mkv'.format(platform.clean_filename(os.path.basename(cur_path)))
            new_path = os.path.join(os.path.abspath(args.dst), os.path.dirname(cur_path), new_name)
            assert new_path not in movies, new_path
            movies[new_path] = movie_object

    output_track_specs = collections.OrderedDict([
        ((TrackType.VID, False), ['und']),
        ((TrackType.AUD, False), args.al),
        ((TrackType.SUB, False), args.sl),
        ((TrackType.SUB, True), args.fl),
    ])

    if not (args.ma and os.path.isfile(MUX_BODY)):
        try:
            os.remove(MUX_BODY)
        except:
            pass
        shutil.copyfile(MUX_HEAD, MUX_BODY)

    created_directories = set()
    # TODO catch some of my exceptions, report skipped file, ask for action, log skipped file
    common_crop_args = None
    for target_path, movie in sorted(movies.iteritems(), key=lambda m: m[1].main_path()):
        platform.print_string(u'=== {} ==='.format(movie.main_path()))
        output_tracks = {}
        for (track_type, _) in output_track_specs.iterkeys():
            output_tracks[track_type] = []
        used_tracks = set()
        reference_duration = movie.reference_duration() or 0
        duration_threshold = reference_duration / 100.0 * 20.0
        for (track_type, search_forced), lang_list in output_track_specs.iteritems():
            forced_string = 'Forced' if search_forced else 'Full'
            for target_lang in lang_list:
                candidates = {}
                for track in movie.tracks(track_type):
                    if track.qualified_id() in used_tracks: continue
                    if track.language() not in (target_lang, 'und') and target_lang != 'und': continue
                    if any(s in track.name().lower() for s in [u'comment', u'коммент']): continue
                    if track.is_forced() is not None:
                        if track.is_forced() != search_forced: continue
                        if not track.is_forced() and track.duration() is not None:
                            if reference_duration - track.duration() > duration_threshold: continue
                    candidates[track.qualified_id()] = track
                if not candidates:
                    if search_forced and args.fo: continue
                    raise cli.Error(u'{} {} {} not found'.format(forced_string, track_type, target_lang))

                chosen_track_id = None
                if len(candidates) == 1: chosen_track_id = list(candidates.keys())[0]

                sorted_candidates = sorted(candidates.itervalues(), key=lambda t: t.qualified_id())
                if chosen_track_id not in candidates:
                    candidates_by_index = {}
                    for track in sorted_candidates:
                        candidates_by_index[movie.track_index_in_type(track)] = track.qualified_id()
                    header = u'--- {}, {}, {} ---'.format(
                        track_type, target_lang.upper(), forced_string)
                    # TODO if tv AND if tracks ids, names and codecs same as before then choose track automatically
                    chosen_track_index = ask_to_select_tracks(movie, track_type, sorted_candidates, header)
                    chosen_track_id = candidates_by_index[chosen_track_index]

                used_tracks.add(chosen_track_id)
                chosen_track = candidates[chosen_track_id]
                chosen_track.set_language(target_lang)
                chosen_track.set_forced(search_forced)
                output_tracks[track_type].append(chosen_track)

        assert len(output_tracks[TrackType.VID]) == 1
        video_track = output_tracks[TrackType.VID][0]

        def track_sort_key(t):
            lng_idx = output_track_specs[(t.type(), t.is_forced())].index(t.language())
            return lng_idx + 1000 * int(t.is_forced())

        track_sources = {}
        for track_type, track_list in output_tracks.iteritems():
            track_list.sort(key=track_sort_key)
            for track in track_list:
                track_sources[track.qualified_id()] = [track.source_file(), track.id()]

        result_commands = [u'echo {}'.format(cmd.quote(movie.main_path()))]
        mux_temporary_files = []

        target_directory = os.path.dirname(target_path)
        if not os.path.isdir(target_directory) and target_directory not in created_directories:
            result_commands.extend(cmd.gen_create_dir(target_directory))
            created_directories.add(target_directory)

        def make_single_track_file(track, stream_id, file_ext=None, ffmpeg_opts=None, prefer_ffmpeg=True):
            if file_ext is None:
                file_ext = track.get_single_track_file_extension()
            if ffmpeg_opts is None:
                ffmpeg_opts = ['-c:{} copy'.format(stream_id)]
            if file_ext == platform.file_ext(track.source_file()) and track.is_single():
                return track.source_file(), False
            tmp_path = platform.make_temporary_file(file_ext)
            if not prefer_ffmpeg and platform.file_ext(track.source_file()) == '.mkv':
                command = cmd.gen_mkvtoolnix_extract_track(track.source_file(), tmp_path, track.id())
            else:
                command = cmd.gen_ffmpeg_extract_track(track.source_file(), tmp_path, track.id(), [], ffmpeg_opts)
            result_commands.extend(command)
            return tmp_path, True

        # TODO move to software abstraction
        source_container_supported_by_mkvmerge = video_track.container_format() not in {FileFormat.x3GP, FileFormat.SMK, FileFormat.WMV}

        source_video_codec = video_track.codec()
        source_video_crf = video_track.crf()
        source_video_profile = video_track.profile()
        source_video_level = video_track.level()

        target_video_codec = args.vc
        target_video_profile, target_video_level = CODEC_FFMPEG_PARAMETERS[target_video_codec]

        encoded_ok = source_video_codec == target_video_codec and \
            source_video_crf is not None and \
            source_video_profile == target_video_profile and \
            source_video_level == target_video_level
        if args.vr or args.vs or not encoded_ok and not args.vk:
            ffmpeg = Ffmpeg()
            target_crf, target_tune = CODEC_TUNES[target_video_codec][args.vt][args.vq]

            # TODO check out rutracker manuals for dvd rip filters and stuff
            ffmpeg_filters = []

            assert video_track.field_order() is not None
            if video_track.field_order() in (FieldOrder.INTERLACED_BOT, FieldOrder.INTERLACED_TOP):
                # TODO consider bwdif
                ffmpeg_filters.append('yadif=1:-1:1')

            if args.va:
                ffmpeg_filters.append('setdar=dar={}'.format(args.va))

            crop_args = None
            if args.cr or args.cf:
                if common_crop_args is not None:
                    crop_args = common_crop_args
                if crop_args_map is not None:
                    crop_args = crop_args_map[video_track.source_file()]
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
            if crop_args is None or not crop_args:
                crop_args = [video_track.width(), video_track.height(), 0, 0]
            dw, dh, dx, dy = crop_args
            if not VideoTrack.dimensions_correct(dw, dh):
                platform.print_string(u'Adjusting crop by {}x{}'.format(dw % 16, dh % 8))
                dw, dh, dx, dy = VideoTrack.correct_dimensions(dw, dh, dx, dy)
            assert VideoTrack.dimensions_correct(dw, dh)
            if dx > 0 or dy > 0 or dw != video_track.width() or dh != video_track.height():
                ffmpeg_filters.append('crop={w}:{h}:{x}:{y}'.format(w=dw, h=dh, x=dx, y=dy))

            # TODO support different resolutions
            # TODO forbid upscale
            if args.vs == '720p':
                ffmpeg_filters.append('scale=1280:-8')
            elif args.vs == '1080p':
                ffmpeg_filters.append('scale=1920:-8')
            elif args.vs == '1440p':  # TODO !!!!!!!!!!
                ffmpeg_filters.append('scale=-16:1440')

            src_colors = video_track.colors()
            dst_color_space = src_colors.correct_space()
            if args.ks:
                dst_color_space = src_colors.space()
            if src_colors.space() != dst_color_space:
                raise cli.Error(u'Colorspace conversion from {} to {} not implemented'.format(src_colors.space(), dst_color_space))
                # TODO specify input/output color_range
                # TODO specify each input component separately
                # TODO The input transfer characteristics, color space, color primaries and color range should be set on the input data
                # TODO clarify iall=all= format string
                # ffmpeg_filters.append('colorspace=iall={}:all={}'.format(src_color_space, dst_color_space))

            ffmpeg_src_options = []

            src_colors_range = src_colors.range()
            if src_colors_range is not None:
                ffmpeg_src_options.append('-color_range {}'.format(ffmpeg.build_color_range_argument(src_colors_range)))

            ffmpeg_dst_options = ['-an', '-sn', '-dn']
            if ffmpeg_filters:
                ffmpeg_dst_options.append('-filter:v {}'.format(','.join(ffmpeg_filters)))
            ffmpeg_dst_options.extend([
                '-c:v {}'.format(ffmpeg.build_video_encoding_library_argument(target_video_codec)),
                '-preset veryslow',
                '-pix_fmt {}'.format(ffmpeg.build_picture_format_argument(PictureFormat.YUV420P)),
                '-crf {}'.format(target_crf),
                '-map_metadata -1', '-map_chapters -1',
            ])

            arg_profile = ffmpeg.build_video_codec_profile_argument(target_video_codec, target_video_profile)
            arg_level = ffmpeg.build_video_codec_level_argument(target_video_codec, target_video_level)
            if target_video_codec == VideoCodec.H264:
                ffmpeg_dst_options.extend(['-profile:v {}'.format(arg_profile), '-level:v {}'.format(arg_level)])
            elif target_video_codec == VideoCodec.H265:
                ffmpeg_dst_options.append('-x265-params "profile={}:level={}"'.format(arg_profile, arg_level))

            if target_tune is not None:
                ffmpeg_dst_options.append('-tune {}'.format(target_tune))

            if dst_color_space is not None and (video_track.is_hd() or src_colors.space() is not None):
                ffmpeg_dst_options.extend([
                    # TODO "16-235 is a typical NTSC luma range. PAL always uses 0-255 luma range."
                    '-color_range {}'.format(ffmpeg.build_color_range_argument(src_colors.range())),
                    '-color_primaries {}'.format(ffmpeg.build_color_primaries_argument(dst_color_space)),
                    '-color_trc {}'.format(ffmpeg.build_color_trc_argument(dst_color_space)),
                    '-colorspace {}'.format(ffmpeg.build_color_space_argument(dst_color_space)),
                ])
            else:
                assert not video_track.is_hd()

            new_video_path = platform.make_temporary_file('.mkv')
            result_commands.extend(
                cmd.gen_ffmpeg_convert(video_track.source_file(), ffmpeg_src_options, new_video_path, ffmpeg_dst_options))
            track_sources[video_track.qualified_id()] = [new_video_path, 0]
            mux_temporary_files.append(new_video_path)
        elif not source_container_supported_by_mkvmerge:
            new_video_path, _ = make_single_track_file(video_track, Ffmpeg.STREAM_ARGUMENT_VID, '.mkv')
            track_sources[video_track.qualified_id()] = [new_video_path, 0]
            mux_temporary_files.append(new_video_path)

        # TODO move to software abstraction
        audio_codecs_to_keep = {AudioCodec.AAC_LC, AudioCodec.MP3}
        audio_codecs_to_denorm = {AudioCodec.AC3, AudioCodec.DTS}
        audio_codecs_to_uncompress = {
            AudioCodec.AAC_HE, AudioCodec.AAC_HE_V2, AudioCodec.AAC_LC,
            AudioCodec.AMR, AudioCodec.OPUS, AudioCodec.SPEEX, AudioCodec.COOK, AudioCodec.ASAO,
            AudioCodec.ADPCM_SWF, AudioCodec.PCM_MULAW,
            AudioCodec.VORBIS, AudioCodec.SMK,
            AudioCodec.WMA_PRO, AudioCodec.WMA_V2,
        }
        audio_codecs_to_recode = {
            AudioCodec.AMR, AudioCodec.ASAO, AudioCodec.OPUS, AudioCodec.SPEEX, AudioCodec.COOK,
            AudioCodec.EAC3, AudioCodec.DTS_ES, AudioCodec.DTS_HRA, AudioCodec.DTS_MA, AudioCodec.TRUE_HD,
            AudioCodec.ADPCM_IMA, AudioCodec.ADPCM_MS, AudioCodec.ADPCM_SWF, AudioCodec.PCM_MULAW, AudioCodec.PCM_S16L,
            AudioCodec.FLAC, AudioCodec.MP2, AudioCodec.VORBIS, AudioCodec.SMK,
            AudioCodec.WMA_PRO, AudioCodec.WMA_V2
        }

        max_audio_channels = CHANNEL_SCHEMES[args.ad]
        for track in output_tracks[TrackType.AUD]:
            need_extract = not source_container_supported_by_mkvmerge
            need_denorm = track.codec() in audio_codecs_to_denorm
            need_downmix = track.channels() > max_audio_channels
            need_recode = need_downmix or track.codec() in audio_codecs_to_recode or args.ar and track.codec() not in audio_codecs_to_keep
            need_uncompress = track.codec() in audio_codecs_to_uncompress or args.aw

            if need_extract or need_denorm or need_downmix or need_recode:

                stf_ext = None
                stf_ffmpeg_opts = None
                if need_uncompress:
                    stf_ext = '.wav'
                    stf_ffmpeg_opts = ['-f wav', '-rf64 auto']
                src_track_file, is_src_track_file_temporary = make_single_track_file(track, Ffmpeg.STREAM_ARGUMENT_AUD, stf_ext, stf_ffmpeg_opts)

                eac_track_file = src_track_file
                if need_denorm or need_downmix or need_recode:
                    eac_track_file = platform.make_temporary_file('.wav' if need_recode else platform.file_ext(src_track_file))
                    eac_opts = []
                    if need_downmix:
                        if max_audio_channels == 1:
                            pass  # will be processed later
                        elif max_audio_channels == 2:
                            eac_opts.append('-downStereo')
                        elif max_audio_channels == 6:
                            eac_opts.append('-down6')
                        else:
                            raise cli.Error(u'Unhandled channels num {}'.format(max_audio_channels))
                    if track.delay() != 0:
                        eac_opts.append('{}{}ms'.format('+' if track.delay() > 0 else '-', abs(track.delay())))
                    result_commands.append(u'call eac3to {} {} {}'.format(
                        cmd.quote(src_track_file), cmd.quote(eac_track_file), ' '.join(eac_opts)))
                    if is_src_track_file_temporary:
                        result_commands.extend(cmd.gen_del_files(args.sd, src_track_file))

                dst_track_file = eac_track_file
                if need_downmix and max_audio_channels == 1:
                    mono_track_file = platform.make_temporary_file('.wav')
                    result_commands.extend(cmd.gen_ffmpeg_convert(eac_track_file, [], mono_track_file, ['-ac 1']))
                    result_commands.extend(cmd.gen_del_files(args.sd, eac_track_file))
                    dst_track_file = mono_track_file

                if need_recode:
                    m4a_track_file = platform.make_temporary_file('.m4a')
                    qaac_opts = ['--tvbr 91', '--quality 2', '--rate keep', '--no-delay']
                    qaac = u'qaac64 {} {} -o {}'.format(u' '.join(qaac_opts), cmd.quote(dst_track_file), cmd.quote(m4a_track_file))
                    result_commands.append(qaac)
                    result_commands.extend(cmd.gen_del_files(args.sd, dst_track_file))
                    dst_track_file = m4a_track_file

                mux_temporary_files.append(dst_track_file)
                track_sources[track.qualified_id()] = [dst_track_file, 0]

        for track in output_tracks[TrackType.SUB]:
            if track.is_text():
                ffmpeg_opts = None
                if track.codec() == SubtitleCodec.MOV:
                    ffmpeg_opts = []
                track_file, is_track_file_temporary = make_single_track_file(track, Ffmpeg.STREAM_ARGUMENT_SUB, ffmpeg_opts=ffmpeg_opts)
                srt_file = platform.make_temporary_file('.srt')
                result_commands.append(u'python {script} {src_path} {dst_path}'.format(
                    script=cmd.quote(os.path.join(os.path.dirname(__file__), 'any2srt.py')),
                    src_path=cmd.quote(track_file), dst_path=cmd.quote(srt_file)))
                track_sources[track.qualified_id()] = [srt_file, 0]
                track.set_encoding(lang.norm_encoding('utf-8'))
                mux_temporary_files.append(srt_file)
                if is_track_file_temporary:
                    result_commands.extend(cmd.gen_del_files(args.sd, track_file))
            elif track.codec() == SubtitleCodec.PGS:
                track_file, is_track_file_temporary = make_single_track_file(track, Ffmpeg.STREAM_ARGUMENT_SUB, prefer_ffmpeg=False)
                idx_file = platform.make_temporary_file('.idx')
                sub_file = u'{}.sub'.format(os.path.splitext(idx_file)[0])
                result_commands.extend(cmd.gen_bdsup2sub(track_file, idx_file, lang.alpha2(track.language())))
                track_sources[track.qualified_id()] = [idx_file, 0]
                mux_temporary_files.extend([idx_file, sub_file])
                if is_track_file_temporary:
                    result_commands.extend(cmd.gen_del_files(args.sd, track_file))

        mux_path = platform.make_temporary_file('.mkv')

        # TODO add cover to files
        mux = ['mkvmerge']
        mux.extend(['--output', cmd.quote(mux_path)])
        mux.extend(['--no-track-tags', '--no-global-tags', '--disable-track-statistics-tags'])

        track_ids_by_files = {}
        for qualified_id, (source_file, source_file_track_id) in track_sources.iteritems():
            track_ids_by_files.setdefault(source_file, {})[qualified_id] = source_file_track_id
        if source_container_supported_by_mkvmerge:
            track_ids_by_files.setdefault(video_track.source_file(), {})

        # TODO tracks need to be extracted from 3gp and wmv containers before passing to mkvmerge
        source_file_ids = {}
        for i, (source_file, track_ids_map) in enumerate(track_ids_by_files.iteritems()):
            source_file_ids[source_file] = i
            for track_type, (tracks_flags_yes, tracks_flag_no) in Track.TYPE_FLAGS.iteritems():
                cur_file_tracks = [track for track in output_tracks[track_type] if track.qualified_id() in track_ids_map]
                if cur_file_tracks:
                    if tracks_flags_yes:
                        mux.append('{} {}'.format(tracks_flags_yes, ','.join(str(track_ids_map[track.qualified_id()]) for track in cur_file_tracks)))
                    for track in cur_file_tracks:
                        default = track.qualified_id() == output_tracks[track_type][0].qualified_id()
                        file_track_id = track_ids_map[track.qualified_id()]
                        mux.append('--track-name {0}:""'.format(file_track_id))
                        if track_type == TrackType.SUB and track.encoding() is not None:
                            mux.append('--sub-charset {0}:{1}'.format(file_track_id, track.encoding()))
                        mux.append('--language {0}:{1}'.format(file_track_id, track.language()))
                        mux.append('--default-track {0}:{1}'.format(file_track_id, 'yes' if default else 'no'))
                        if track.is_forced():
                            mux.append('--forced-track {0}:yes'.format(file_track_id))
                elif tracks_flag_no:
                    mux.append(tracks_flag_no)
            file_flags = ['--no-track-tags', '--no-attachments', '--no-buttons', '--no-global-tags']
            if source_file != video_track.source_file():
                file_flags.append('--no-chapters')
            mux.append(u'{} {}'.format(u' '.join(file_flags), cmd.quote(source_file)))

        mux.append('--title ""')

        track_order = []
        for track_type in [TrackType.VID, TrackType.AUD, TrackType.SUB]:
            for track in output_tracks[track_type]:
                source_file, source_file_track_id = track_sources[track.qualified_id()]
                track_order.append('{}:{}'.format(source_file_ids[source_file], source_file_track_id))
        mux.append('--track-order {}'.format(','.join(track_order)))

        result_commands.append(u' '.join(mux))
        if len(mux_temporary_files) > 0:
            result_commands.extend(cmd.gen_del_files(args.sd, *sorted(set(mux_temporary_files))))

        # TODO mark mkv file with mkvexport version
        if movie.chapters_path() is not None:
            result_commands.append(u'mkvpropedit --chapters {} {}'.format(
                cmd.quote(movie.chapters_path()), cmd.quote(mux_path)))

        clean_mux_path = platform.make_temporary_file('.mkv')
        result_commands.append(u'mkclean {} {}'.format(cmd.quote(mux_path), cmd.quote(clean_mux_path)))
        result_commands.extend(cmd.gen_del_files(args.sd, mux_path))
        result_commands.extend(cmd.gen_move_file(clean_mux_path, target_path, args.sd))

        if args.xx:
            result_commands.extend(cmd.gen_del_files(
                args.sd,
                *sorted(set(media_file.path() for media_file in movie.media_files()))))

        allowed_exit_codes = {'robocopy': 1, 'mkvmerge': 1}
        with codecs.open(MUX_BODY, 'a', 'utf-8') as body_file:
            for command in result_commands:
                fail_exit_code = 1
                for program, code in allowed_exit_codes.iteritems():
                    if program in command.lower():
                        fail_exit_code = code + 1
                stop_statement = u'call :stop {}'.format(misc.random_printable(8))
                if fail_exit_code == 1: prepared_commands = [u'{} || {}'.format(command.strip(), stop_statement)]
                else: prepared_commands = [command.strip(), u'if errorlevel {} {}'.format(fail_exit_code, stop_statement)]
                for prep_command in prepared_commands:
                    body_file.write(u'{}\r\n'.format(prep_command))
            body_file.write(u'\r\n')

    return 0


if __name__ == '__main__':
    cli.run(main)
