# coding: utf-8

import argparse
import codecs
import collections
import os
import shutil

from modules import cli
from modules import cmd
from modules import ffmpeg
from modules import lang
from modules import media
from modules import misc
from modules import platform
from modules.tracks import Track, VideoTrack, Colors, AudioTrack, SubtitleTrack

LANG_ORDER = ['und', 'jpn', 'eng', 'rus']

MUX_SCRIPT = os.path.join(os.getcwd(), 'mux.cmd')
MUX_HEADER = os.path.join(os.path.dirname(__file__), 'mux_header.cmd')

TUNES_IDX_SORT_KEY = 0
TUNES_IDX_CRF = 1
TUNES_IDX_REAL_TUNE = 2
TUNES = {
    'animation': (1, 18, 'animation'),
    'film': (2, 22, 'film'),
    'trash': (3, 23, 'film'),
    'supertrash': (4, 25, 'film'),
}

# TODO move out
LANGUAGES_IDX_SUB_LANG = 0
LANGUAGES = {
    'rus': ('ru',),
    'eng': ('en',),
    'jpn': ('jp',),
}

ACTIONS_IDX_TEXT = 0
ACTIONS_IDX_ENABLED = 1
ACTIONS_IDX_FUNC = 2
# TODO table-like print
def ask_to_select(prompt, values, handle_response=lambda x: x, header=None):
    values_dict = values if isinstance(values, dict) else { i: v for i, v in enumerate(values) }
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
        MPV_OPTS = { Track.AUD: '--audio-file {}', Track.SUB: '--sub-file {}' }
        if text == 'p':
            command = [u'mpv {}'.format(cmd.quote(list(movie.tracks(Track.VID))[0].source_file()))]
            for track in sorted(candidates, key=lambda t: movie.track_index_in_type(t)):
                if track.is_single():
                    command.append(MPV_OPTS[track.type()].format(cmd.quote(track.source_file())))
            os.system(u'{} >nul 2>&1'.format(u' '.join(command)))
        return text

    candidate_strings = {}
    from_single_file = len({ t.source_file() for t in candidates }) == 1
    for track in candidates:
        strings = [u'(ID {})'.format(track.id()), track.language(), track.codec_name()]
        if track_type == Track.AUD:
            strings.append('{}ch'.format(track.channels()))
        if track.name():
            strings.append(track.name())
        if track.is_default():
            strings.append(u'(default)')
        if not from_single_file:
            strings.append(u'[{}]'.format(os.path.basename(track.source_file())))
        candidate_strings[movie.track_index_in_type(track)] = u' '.join(strings)
    return ask_to_select(u'Enter track index', candidate_strings, handle_response, header)

def is_movie_satellite(movie_path, candidate_path):
    return os.path.basename(candidate_path).lower().startswith(os.path.splitext(os.path.basename(movie_path))[0].lower())

def find_movies(search_path):
    found_files = []
    if os.path.isfile(search_path):
        search_dir = os.path.dirname(search_path)
        for name in os.listdir(search_dir):
            if is_movie_satellite(search_path, name):
                found_files.append(os.path.join(search_dir, name))
    elif os.path.isdir(search_path):
        for search_dir, _, files in os.walk(search_path):
            found_files.extend(os.path.join(search_dir, name) for name in files)

    media_by_folder = {}
    for path in (os.path.abspath(fp) for fp in found_files):
        if len(media.File.possible_track_types(path)) > 0:
            media_by_folder.setdefault(os.path.dirname(path), set()).add(path)

    media_groups = []
    for remaining_media in media_by_folder.itervalues():
        video_paths = [fp for fp in remaining_media if Track.VID in media.File.possible_track_types(fp)]
        for video in sorted(video_paths):
            group = []
            if video in remaining_media:
                remaining_media.remove(video)
                group = [path for path in remaining_media if is_movie_satellite(video, path)]
                media_groups.append([video] + group)
            remaining_media -= set(group)

    for group in media_groups:
        yield media.Movie(group)

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

def main():
    languages = sorted(LANGUAGES.iterkeys())
    parser = argparse.ArgumentParser()
    parser.add_argument('sources', type=cli.argparse_path, nargs='+', help='paths to source directories/files')
    parser.add_argument('dst', type=cli.argparse_path, help='path to destination directory')

    # TODO add argument groups
    parser.add_argument('-vk', default=False, action='store_true', help='keep source video')
    parser.add_argument('-vr', default=False, action='store_true', help='recode video')
    parser.add_argument('-vt', help='force tune')
    parser.add_argument('-va', default=None, choices=['16:9'], help='set video display aspect ratio')

    parser.add_argument('-cr', default=False, action='store_true', help='crop video')
    parser.add_argument('-cf', type=cli.argparse_path, default=None, help='path to crop map file')
    parser.add_argument('-sc', default=False, action='store_true', help='use same crop values for all files')

    parser.add_argument('-al', nargs='*', choices=languages, default=[], help='ordered list of audio languages to keep')
    parser.add_argument('-ar', default=False, action='store_true', help='recode audio')
    parser.add_argument('-a2', default=False, action='store_true', help='downmix multi-channel audio to stereo')

    parser.add_argument('-sl', nargs='*', choices=languages, default=[], help='ordered list of full subtitle languages to keep')
    parser.add_argument('-fl', nargs='*', choices=languages, default=[], help='ordered list of forced subtitle languages to keep')
    parser.add_argument('-fo', default=False, action='store_true', help='make forced subtitles optional')

    parser.add_argument('-eo', default=False, action='store_true', help='remux only if re-encoding')
    parser.add_argument('-nf', type=cli.argparse_path, default=None, help='path to names map file')

    # TODO add parametes to ask for file name !!!

    args = parser.parse_args()
    if args.cf and args.sc:
        raise cli.Error(u'Use "-sc" OR "-cf"')

    def read_movie_path(path):
        return os.path.splitext(os.path.normpath(path.strip()))[0]

    def read_crop_args(s):
        s = s.strip()
        if s.lower() == 'no':
            return False
        return [int(x) for x in s.split(':')]

    filenames_map = read_map_file(args.nf, read_movie_path, read_movie_path)
    raw_crops_map = read_map_file(args.cf, read_movie_path, read_crop_args)

    movies = {}
    crop_args_map = None if raw_crops_map is None else {}
    for argspath in args.sources:
        for movie_object in find_movies(argspath):
            cur_name = os.path.normpath(os.path.relpath(movie_object.main_path(), os.getcwd()))
            new_name = cur_name
            if filenames_map is not None:
                raw_new_name_string = filenames_map[os.path.splitext(cur_name)[0]]
                new_name = None
                if raw_new_name_string == 'NO': continue
                elif raw_new_name_string == 'KEEP': new_name = cur_name
                else: new_name = u'{}.mkv'.format(raw_new_name_string)
            new_path = os.path.join(os.path.abspath(args.dst), os.path.splitext(new_name)[0] + '.mkv')
            if raw_crops_map is not None:
                crop_args_map[movie_object.main_path()] = raw_crops_map[os.path.splitext(cur_name)[0]]
            assert new_path not in movies
            movies[new_path] = movie_object

    output_track_specs = collections.OrderedDict([
        ((Track.VID, False), ['und']),
        ((Track.AUD, False), args.al),
        ((Track.SUB, False), args.sl),
        ((Track.SUB, True), args.fl),
    ])

    try:
        os.remove(MUX_SCRIPT)
    except:
        pass
    shutil.copyfile(MUX_HEADER, MUX_SCRIPT)

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
                        track_type.capitalize(), target_lang.upper(), forced_string)
                    chosen_track_index = ask_to_select_tracks(movie, track_type, sorted_candidates, header)
                    chosen_track_id = candidates_by_index[chosen_track_index]

                used_tracks.add(chosen_track_id)
                chosen_track = candidates[chosen_track_id]
                chosen_track.set_language(target_lang)
                chosen_track.set_forced(search_forced)
                output_tracks[track_type].append(chosen_track)

        assert len(output_tracks[Track.VID]) == 1
        video_track = output_tracks[Track.VID][0]

        def track_sort_key(t):
            lng_idx = output_track_specs[(t.type(), t.is_forced())].index(t.language())
            return lng_idx + 1000 * int(t.is_forced())

        track_sources = {}
        for track_type, track_list in output_tracks.iteritems():
            track_list.sort(key=track_sort_key)
            for track in track_list:
                track_sources[track.qualified_id()] = [track.source_file(), track.id()]

        result_commands = [u'echo {}'.format(movie.main_path())]
        mux_temporary_files = []

        target_directory = os.path.dirname(target_path)
        if not os.path.isdir(target_directory) and target_directory not in created_directories:
           result_commands.append(cmd.create_dir_command(target_directory))
           created_directories.add(target_directory)

        # TODO support 2pass encoding
        # TODO what if there is crf already?
        encoded_ok = video_track.codec_id() == VideoTrack.CODEC_H264 and \
            video_track.crf() is not None and \
            video_track.profile() == VideoTrack.PROFILE_HIGH and \
            video_track.level() == VideoTrack.LEVEL_41
        if args.vr or not encoded_ok and not args.vk:
            chosen_tune = args.vt or ask_to_select(u'Enter tune ID',
                sorted(TUNES.iterkeys(), key=lambda k: TUNES[k][TUNES_IDX_SORT_KEY]))
            tune_params = TUNES[chosen_tune]

            # TODO check out rutracker manuals for dvd rip filters and stuff
            ffmpeg_filters = []

            # TODO what about interleaved?
            assert video_track.field_order() is not None
            if video_track.field_order() in (VideoTrack.FO_INT_BOT, VideoTrack.FO_INT_TOP):
                ffmpeg_filters.append('yadif=1:-1:1')

            crop_args = None
            if args.cr:
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

            if args.va:
                ffmpeg_filters.append('setdar=dar={}'.format(args.va))

            src_colors = video_track.colors()
            assert video_track.pix_fmt() == VideoTrack.YUV420P
            assert src_colors.range() == Colors.RANGE_TV

            dst_color_space = src_colors.correct_space()
            if src_colors.space() != dst_color_space:
                raise cli.Error(u'Colorspace conversion not implemented')
                # TODO specify input/output color_range
                # TODO specify each input component separately
                # TODO The input transfer characteristics, color space, color primaries and color range should be set on the input data
                # TODO clarify iall=all= format string
                # ffmpeg_filters.append('colorspace=iall={}:all={}'.format(src_color_space, dst_color_space))

            ffmpeg_src_options = ['-color_range {}'.format(src_colors.range())]
            ffmpeg_dst_options = ['-an', '-sn', '-dn']
            if ffmpeg_filters:
                ffmpeg_dst_options.append('-filter:v {}'.format(','.join(ffmpeg_filters)))
            # TODO do not specify color primaries if source SD and values unknown
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
            new_video_path = platform.make_temporary_file('.mkv')
            result_commands.extend(
                ffmpeg.cmds_convert(video_track.source_file(), ffmpeg_src_options, new_video_path, ffmpeg_dst_options))
            track_sources[video_track.qualified_id()] = [new_video_path, 0]
            mux_temporary_files.append(new_video_path)

        def make_single_track_file(track, stream_id):
            if track.is_single():
                return (track.source_file(), False)
            extension = track.get_single_track_file_extension()
            ffmpeg_opts = ['-c:{} copy'.format(stream_id)]
            # TODO move it out !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            if stream_id == ffmpeg.STREAM_AUD and track.codec_id() in (AudioTrack.AAC_LC, AudioTrack.AAC_HE):
                extension = '.wav'
                ffmpeg_opts = ['-f wav', '-rf64 auto']
            tmp_path = platform.make_temporary_file(extension)
            result_commands.extend(ffmpeg.cmds_extract_track(track.source_file(), tmp_path, track.id(), [], ffmpeg_opts))
            return (tmp_path, True)

        # TODO change of fps AND video recode|normalize will lead to a/v desync
        audio_codecs_to_denorm = set([AudioTrack.AC3, AudioTrack.DTS])
        audio_codecs_to_recode = set([AudioTrack.DTSHRA, AudioTrack.DTSMA, AudioTrack.EAC3, AudioTrack.FLAC, AudioTrack.MP2, AudioTrack.PCM_S16L, AudioTrack.TRUE_HD])
        audio_codecs_to_keep = set([AudioTrack.AAC_LC, AudioTrack.MP3])
        max_audio_channels = 2 if args.a2 else 6
        for track in output_tracks[Track.AUD]:
            if track.codec_unknown():
                raise cli.Error(u'Unhandled audio codec {}'.format(track.codec_id()))

            need_denorm = track.codec_id() in audio_codecs_to_denorm
            need_downmix = track.channels() > max_audio_channels
            need_recode = need_downmix or track.codec_id() in audio_codecs_to_recode or args.ar and track.codec_id() not in audio_codecs_to_keep

            if need_denorm or need_downmix or need_recode:
                src_track_file, is_src_track_file_temporary = make_single_track_file(track, ffmpeg.STREAM_AUD)
                eac_track_file = platform.make_temporary_file('.wav' if need_recode else platform.file_ext(src_track_file))
                eac_opts = []
                if need_downmix:
                    eac_opts.append('-downStereo' if max_audio_channels == 2 else '-down6')
                result_commands.append(u'call eac3to {} {} {}'.format(
                    cmd.quote(src_track_file), cmd.quote(eac_track_file), ' '.join(eac_opts)))
                if is_src_track_file_temporary:
                    result_commands.append(cmd.del_files_command(src_track_file))

                dst_track_file = eac_track_file
                if need_recode:
                    m4a_track_file = platform.make_temporary_file('.m4a')
                    qaac_opts = ['--tvbr 91', '--quality 2', '--rate keep', '--no-delay']
                    qaac = u'qaac64 {} {} -o {}'.format(u' '.join(qaac_opts), cmd.quote(eac_track_file), cmd.quote(m4a_track_file))
                    result_commands.append(qaac)
                    result_commands.append(cmd.del_files_command(eac_track_file))
                    dst_track_file = m4a_track_file

                mux_temporary_files.append(dst_track_file)
                track_sources[track.qualified_id()] = [dst_track_file, 0]

        for track in output_tracks[Track.SUB]:
            if track.codec_unknown():
                raise cli.Error(u'Unhandled subtitle codec {}'.format(track.codec_id()))
            if track.is_text():
                # TODO tx3g should be converted to ass without -c:s copy
                track_file, is_track_file_temporary = make_single_track_file(track, ffmpeg.STREAM_SUB)
                srt_file = platform.make_temporary_file('.srt')
                result_commands.append(u'python {script} {src_path} {dst_path}'.format(
                    script=cmd.quote(os.path.join(os.path.dirname(__file__), 'any2srt.py')),
                    src_path=cmd.quote(track_file), dst_path=cmd.quote(srt_file)))
                track_sources[track.qualified_id()] = [srt_file, 0]
                track.set_encoding(lang.norm_encoding('utf-8'))
                mux_temporary_files.append(srt_file)
                if is_track_file_temporary:
                    result_commands.append(cmd.del_files_command(track_file))
            elif track.codec_id() == SubtitleTrack.PGS:
                track_file, is_track_file_temporary = make_single_track_file(track, ffmpeg.STREAM_SUB)
                idx_file = platform.make_temporary_file('.idx')
                sub_file = u'{}.sub'.format(os.path.splitext(idx_file)[0])
                result_commands.append(u'call bdsup2sub -l {} -o {} {}'.format(
                    LANGUAGES[track.language()][LANGUAGES_IDX_SUB_LANG],
                    cmd.quote(idx_file), cmd.quote(track_file)))
                track_sources[track.qualified_id()] = [idx_file, 0]
                mux_temporary_files.extend([idx_file, sub_file])
                if is_track_file_temporary:
                    result_commands.append(cmd.del_files_command(track_file))

        mux_path = platform.make_temporary_file('.mkv')

        mux = ['mkvmerge']
        mux.extend(['--output', cmd.quote(mux_path)])
        mux.extend(['--no-track-tags', '--no-global-tags', '--disable-track-statistics-tags'])

        track_ids_by_files = {}
        for qualified_id, (source_file, source_file_track_id) in track_sources.iteritems():
            track_ids_by_files.setdefault(source_file, {})[qualified_id] = source_file_track_id
        track_ids_by_files.setdefault(video_track.source_file(), {})

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
                        if track_type == Track.SUB and track.encoding() is not None:
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
        for track_type in [Track.VID, Track.AUD, Track.SUB]:
            for track in output_tracks[track_type]:
                source_file, source_file_track_id = track_sources[track.qualified_id()]
                track_order.append('{}:{}'.format(source_file_ids[source_file], source_file_track_id))
        mux.append('--track-order {}'.format(','.join(track_order)))

        if len(source_file_ids) > 1 or not args.eo:
            result_commands.append(u' '.join(mux))
        if len(mux_temporary_files) > 0:
            result_commands.append(cmd.del_files_command(*sorted(set(mux_temporary_files))))

        if movie.chapters_path() is not None:
            result_commands.append(u'mkvpropedit --chapters {} {}'.format(
                cmd.quote(movie.chapters_path()), cmd.quote(mux_path)))

        result_commands.extend(cmd.move_file_commands(mux_path, target_path))

        # TODO return xx flag

        cmd.write_batch(MUX_SCRIPT, result_commands)

    return 0

if __name__ == '__main__':
    cli.run(main)
