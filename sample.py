import os
import sys

from modules import cmd
from modules.ffmpeg import Ffmpeg
from modules.formats import VideoCodec, VideoCodecProfile, PictureFormat

def main(args):
    src_file, target_directory = args

    ffmpeg = Ffmpeg()
    for codec in [VideoCodec.H264, VideoCodec.H265]:
        for profile in Ffmpeg._VIDEO_CODEC_PROFILE_ENUM_TO_ARGUMENT[codec]:
            for level in Ffmpeg._VIDEO_CODEC_LEVELS[codec]:
                arg_profile = ffmpeg.build_video_codec_profile_argument(codec, profile)
                arg_level = ffmpeg.build_video_codec_level_argument(codec, level)

                dst_file = os.path.join(target_directory, '_'.join([codec.name, profile.name, level.name]) + '.mkv')
                dst_options = [
                    '-c:v {}'.format(ffmpeg.build_video_encoding_library_argument(codec)),
                    '-pix_fmt {}'.format(ffmpeg.build_picture_format_argument(PictureFormat.YUV420P)),
                ]
                if codec == VideoCodec.H264:
                    dst_options.extend(['-profile:v {}'.format(arg_profile), '-level:v {}'.format(arg_level)])
                elif codec == VideoCodec.H265:
                    dst_options.append('-x265-params "profile={}:level={}"'.format(arg_profile, arg_level))
                print cmd.gen_ffmpeg_convert(src_file, [], dst_file, dst_options)[0] + ' || exit 1'

if __name__ == '__main__':
    main(sys.argv[1:])
