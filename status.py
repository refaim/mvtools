from __future__ import print_function

import argparse
import pymediainfo
import os
import sys

def movies(path):
    for root, dirs, files in os.walk(path):
        for filename in sorted(files):
            if filename.endswith('.mkv') and not filename.endswith('_enc.mkv'):
                filepath = os.path.join(root, filename)
                yield os.path.relpath(filepath, path), pymediainfo.MediaInfo.parse(filepath)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('storage', help='path to movies directory')
    parser.add_argument('-m', '--mode', choices=['res', 'bit'], default=None)
    args = parser.parse_args()

    if args.mode is None:
        print('No mode specified')
        return 1

    for filepath, movie in movies(args.storage):
        vtracks = [track for track in movie.tracks if track.track_type == 'Video']
        assert len(vtracks) == 1
        video = vtracks[0]
        if args.mode == 'res':
            if video.width < 1920 or video.height < 1080:
                print('{0:4} {1:4}  {2}'.format(video.width, video.height, filepath))
        elif args.mode == 'bit':
            for attr in dir(video):
                if not attr.startswith('_'):
                    print(attr, getattr(video, attr))
            # cabac=1 / ref=4 / deblock=1:1:1 / analyse=0x3:0x133 / me=umh / subme=10 / psy=1 / psy_rd=0.40:0.00 / mixed_ref=1 / me_range=24 / chroma_me=1 / trellis=2 / 8x8dct=1 / cqm=0 / deadzone=21,11 / fast_pskip=1 / chroma_qp_offset=-2 / threads=4 / lookahead_threads=1 / sliced_threads=0 / nr=0 / decimate=1 / interlaced=0 / bluray_compat=0 / constrained_intra=0 / bframes=10 / b_pyramid=2 / b_adapt=2 / b_bias=0 / direct=3 / weightb=1 / open_gop=0 / weightp=2 / keyint=250 / keyint_min=23 / scenecut=40 / intra_refresh=0 / rc_lookahead=60 / rc=crf / mbtree=1 / crf=18.0 / qcomp=0.60 / qpmin=0 / qpmax=69 / qpstep=4 / ip_ratio=1.40 / aq=1:0.60
            # exit()

    return 0

if __name__ == '__main__':
    sys.exit(main())
