# coding: utf-8

import argparse
import codecs
import os
import shutil
import sys
import uuid

from modules import cmd
from modules import ffmpeg
from modules import media
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

def try_int(value):
    try:
        return int(value)
    except:
        return None

ACTIONS_IDX_TEXT = 0
ACTIONS_IDX_ENABLED = 1
ACTIONS_IDX_FUNC = 1
def ask_to_select(prompt, values, movie_path=None, header=None):
    actions = {
        'p': ('preview', movie_path and os.path.isfile(movie_path), lambda p: os.system('mplayer {} >nul 2>&1'.format(cmd.quote(p)))),
    }
    values_dict = values if isinstance(values, dict) else { i: v for i, v in enumerate(values) }
    chosen_id = None
    while chosen_id not in values_dict:
        if header is not None:
            platform.print_string(header)
        for i, v in sorted(values_dict.iteritems()):
            platform.print_string(u'{} {}'.format(i, v))

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

def video_containers(path):
    def filter_paths(filepaths):
        for filepath in filepaths:
            if Track.VID in media.FILE_EXTENSIONS.get(platform.file_ext(filepath), []):
                yield os.path.abspath(filepath)

    data = []
    if os.path.isfile(path):
        data.append(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for filename in sorted(files):
                data.append(os.path.join(root, filename))

    for filepath in filter_paths(data):
        yield filepath

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
    parser.add_argument('sources', type=cmd.argparse_path, nargs='+', help='paths to source directories/files')
    parser.add_argument('dst', type=cmd.argparse_path, help='path to destination directory')
    parser.add_argument('--temp', type=cmd.argparse_path, help='path to temporary directory')

    # TODO add special "all" language value

    # TODO add argument groups
    parser.add_argument('-vk', default=False, action='store_true', help='keep source video')
    parser.add_argument('-vr', default=False, action='store_true', help='recode video')
    parser.add_argument('-vt', help='force tune')
    parser.add_argument('-va', default=None, choices=['16:9'], help='set video display aspect ratio')

    parser.add_argument('-cr', default=False, action='store_true', help='crop video')
    parser.add_argument('-cf', type=cmd.argparse_path, default=None, help='path to crop map file')
    parser.add_argument('-sc', default=False, action='store_true', help='use same crop values for all files')

    parser.add_argument('-al', nargs='*', choices=languages, default=[], help='ordered list of audio languages to keep')
    parser.add_argument('-ar', default=False, action='store_true', help='recode audio')
    parser.add_argument('-dm', default=False, action='store_true', help='downmix multi-channel audio to stereo')

    parser.add_argument('-sl', nargs='*', choices=languages, default=[], help='ordered list of full subtitle languages to keep')
    parser.add_argument('-fl', nargs='*', choices=languages, default=[], help='ordered list of forced subtitle languages to keep')
    parser.add_argument('-fo', default=False, action='store_true', help='make forced subtitles optional')

    parser.add_argument('-xx', default=False, action='store_true', help='remove original source files')
    parser.add_argument('-eo', default=False, action='store_true', help='remux only if re-encoding')
    # TODO check name conflicts
    parser.add_argument('-nf', type=cmd.argparse_path, default=None, help='path to names map file')

    # TODO add parametes to ask for file name !!!

    args = parser.parse_args()
    if not args.temp:
        args.temp = args.dst
    if args.cf and args.sc:
        raise Exception('Use "-sc" OR "-cf"')

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
        # TODO loop over containers is wrong :( !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        for container_path in video_containers(argspath):
            cur_name = os.path.basename(container_path)
            if os.path.isdir(argspath):
                cur_name = os.path.relpath(container_path, argspath)
            cur_name = os.path.normpath(cur_name)
            new_name = cur_name
            if filenames_map is not None:
                raw_new_name_string = filenames_map[os.path.splitext(cur_name)[0]]
                new_name = None
                if raw_new_name_string == 'NO': continue
                elif raw_new_name_string == 'KEEP': new_name = cur_name
                else: new_name = u'{}.mkv'.format(raw_new_name_string)
            new_path = os.path.join(os.path.abspath(args.dst), os.path.splitext(new_name)[0] + '.mkv')
            if raw_crops_map is not None:
                crop_args_map[container_path] = raw_crops_map[os.path.splitext(cur_name)[0]]
            # TODO find satellites !!!!!!!!!!!!!
            media_paths = [container_path]
            movies[new_path] = media.Movie([media.File(path, uuid.uuid4()) for path in media_paths])

    # TODO ignore container-set forced flag if it is on single video or audio track (clear it when parsing?)
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
    shutil.copyfile(MUX_HEADER, MUX_SCRIPT)

    # TODO catch some of my exceptions, report skipped file, ask for action, log skipped file
    common_crop_args = None
    for target_path, movie in sorted(movies.iteritems(), key=lambda m: m[1].sort_path()):
        platform.print_string(u'=== {} ==='.format(movie.sort_path()))
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
                        strings = [u'(ID {})'.format(t.id()), t.language(), t.codec_name()]
                        if t.name():
                            strings.append(t.name())
                        if t.is_default():
                            strings.append(u'(default)')
                        track_index = movie.track_index_in_type(t)
                        candidates_strings[track_index] = u' '.join(strings)
                        candidates_by_index[track_index] = t.id()
                    header = u'--- {}, {}, {} ---'.format(
                        track_type.capitalize(), target_lang.upper(), forced_string)
                    # TODO pass track source files !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    chosen_track_index = ask_to_select(u'Enter track index', candidates_strings, movie.path(), header=header)
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
                track_sources[track.id()] = [track.source_file(), track.id()]

        result_commands = [u'echo {}'.format(movie.sort_path())]
        mux_temporary_files = []

        # TODO support 2pass encoding
        # TODO what if there is crf already?
        encoded_ok = video_track.codec_id() == VideoTrack.CODEC_H264 and \
            video_track.crf() is not None and \
            video_track.profile() == VideoTrack.PROFILE_HIGH and \
            video_track.level() == VideoTrack.LEVEL_41
        if args.vr or not encoded_ok and not args.vk:
            chosen_tune = args.vt or ask_to_select(
                u'Enter tune ID',
                sorted(TUNES.iterkeys(), key=lambda k: TUNES[k][TUNES_IDX_SORT_KEY]),
                video_track.source_file())
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
            if crop_args is None:
                crop_args = [video_track.width(), video_track.height(), 0, 0]
            dw, dh, dx, dy = crop_args
            if not VideoTrack.dimensions_correct(dw, dh):
                platform.print_string('Adjusting crop by {}x{}'.format(dw % 16, dh % 8))
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
            new_video_path = platform.make_temporary_file('.mkv')
            result_commands.extend(
                ffmpeg.cmds_convert(video_track.source_file(), ffmpeg_src_options, new_video_path, ffmpeg_dst_options))
            track_sources[video_track.id()] = [new_video_path, 0]
            mux_temporary_files.append(new_video_path)

        # TODO volume normalization when downmix|recode, see
        # TODO https://github.com/mdhiggins/sickbeard_mp4_automator/issues/219 and
        # TODO https://github.com/slhck/ffmpeg-normalize/
        codecs_to_normalize = set([AudioTrack.AC3])
        codecs_to_recode = set([AudioTrack.MP2])
        downmix_codecs = codecs_to_recode | set([AudioTrack.AAC_HE, AudioTrack.AC3, AudioTrack.DTS, AudioTrack.DTS_HD])
        for track in output_tracks[Track.AUD]:
            if track.codec_id() not in AudioTrack.CODEC_NAMES:
                raise Exception('Unhandled audio codec {}'.format(track.codec_id()))
            assert track.channels() <= 6
            if track.codec_id() in codecs_to_normalize:
                # TODO change of fps AND video recode|normalize will lead to a/v desync
                src_ac3_path = platform.make_temporary_file('.ac3')
                dst_ac3_path = platform.make_temporary_file('.ac3')
                result_commands.extend(
                    ffmpeg.cmds_extract_track(track.source_file(), src_ac3_path, track.id(), [], ['-c:a copy']))
                # TODO use commercial decoders?
                # TODO specify path to log file
                result_commands.append(u'call eac3to {} {}'.format(
                    cmd.quote(src_ac3_path), cmd.quote(dst_ac3_path)))
                result_commands.append(cmd.del_files_command(src_ac3_path))
                track_sources[track.id()] = [dst_ac3_path, 0]
                mux_temporary_files.append(dst_ac3_path)
            recode = args.ar or track.codec_id() in codecs_to_recode
            recode = recode or args.dm and (track.codec_id() in downmix_codecs or track.channels() > 2)
            if recode:
                wav_path = platform.make_temporary_file('.wav')
                ffmpeg_options = ['-f wav', '-rf64 auto']
                if args.dm:
                    ffmpeg_options.append('-ac 2')
                track_file, track_id = track_sources[track.id()]
                result_commands.extend(
                    ffmpeg.cmds_extract_track(track_file, wav_path, track_id, [], ffmpeg_options))

                m4a_path = platform.make_temporary_file('.m4a')
                qaac_options = ['--tvbr {}'.format(63 if args.dm else 91), '--quality 2', '--rate keep', '--no-delay']
                encode = u'qaac64 {} {} -o {}'.format(u' '.join(qaac_options), cmd.quote(wav_path), cmd.quote(m4a_path))
                result_commands.append(encode)
                result_commands.append(cmd.del_files_command(wav_path))
                mux_temporary_files.append(m4a_path)
                track_sources[track.id()] = [m4a_path, 0]

        # TODO assert that fonts only present if subtitles ass/ssa
        # TODO support external srt subtitles
        # TODO support external subtitle charset detection & re-encoding to utf-8
        for track in output_tracks[Track.SUB]:
            if track.codec_id() not in SubtitleTrack.CODEC_NAMES:
                raise Exception('Unhandled subtitle codec {}'.format(track.codec_id()))
            if track.codec_id() == SubtitleTrack.ASS:
                # TODO do not mux zero-size result .srt file !!!
                srt_file = platform.make_temporary_file('.srt')
                result_commands.extend(ffmpeg.cmds_extract_track(track.source_file(), srt_file, track.id(), [], ['-c:s text']))
                track_sources[track.id()] = [srt_file, 0]
                mux_temporary_files.append(srt_file)
            elif track.codec_id() == SubtitleTrack.PGS:
                sup_file = platform.make_temporary_file('.sup')
                result_commands.extend(ffmpeg.cmds_convert(
                    track.source_file(), [], sup_file, ['-map 0:{}'.format(track.id()), '-c:s copy']))
                idx_file = platform.make_temporary_file('.idx')
                sub_file = u'{}.sub'.format(os.path.splitext(idx_file)[0])
                result_commands.append(u'call bdsup2sub -l {} -o {} {}'.format(
                    LANGUAGES[track.language()][LANGUAGES_IDX_SUB_LANG],
                    cmd.quote(idx_file), cmd.quote(sup_file)))
                track_sources[track.id()] = [idx_file, 0]
                result_commands.append(cmd.del_files_command(sup_file))
                mux_temporary_files.extend([idx_file, sub_file])

        mux_path = platform.make_temporary_file('.mkv')

        mux = ['mkvmerge']
        mux.extend(['--output', cmd.quote(mux_path)])
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
            file_flags = ['--no-track-tags', '--no-attachments', '--no-buttons', '--no-global-tags']
            # TODO actually search for chapters !!!!!!!!!
            if source_file != video_track.source_file():
                file_flags.append('--no-chapters')
            mux.append(u'{} {}'.format(u' '.join(file_flags), cmd.quote(source_file)))

        mux.append('--title ""')

        track_order = []
        for track_type in [Track.VID, Track.AUD, Track.SUB]:
            for track in output_tracks[track_type]:
                source_file, source_file_track_id = track_sources[track.id()]
                track_order.append('{}:{}'.format(source_file_ids[source_file], source_file_track_id))
        mux.append('--track-order {}'.format(','.join(track_order)))

        if len(source_file_ids) > 1 or not args.eo:
            result_commands.append(u' '.join(mux))
        result_commands.append(cmd.del_files_command(*sorted(set(mux_temporary_files))))
        # TODO use robocopy or dism to fully utilize 1gbps connection
        result_commands.append(cmd.copy_file_command(mux_path, target_path))
        result_commands.append(cmd.del_files_command(mux_path))
        # TODO support !!!!!!!!!!!!!!!!!!
        # if args.xx:
        #     # TODO all media files
        #     result_commands.append(cmd.del_files_command(movie.path()))

        cmd.write_batch(MUX_SCRIPT, result_commands)

        # TODO add this to batch files (mkdir creates intermediate directories automatically)
        try:
            os.makedirs(os.path.dirname(target_path))
        except:
            pass

    return 0

if __name__ == '__main__':
    sys.exit(main())
