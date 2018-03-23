import argparse
import os
import shutil
import tempfile

from modules import cli
from modules import cmd
from modules import platform

def remux_movie(src_dir, dst_dir, remux_callback):
    tmp_dir = tempfile.mkdtemp()
    if not remux_callback(tmp_dir):
        return
    if not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)
    for filename in os.listdir(tmp_dir):
        shutil.move(os.path.join(tmp_dir, filename), dst_dir)
    shutil.rmtree(tmp_dir)
    shutil.rmtree(src_dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', type=cli.argparse_path, help='path to source folder')
    parser.add_argument('dst', type=cli.argparse_path, help='path to destination folder')
    args = parser.parse_args()

    dvds = set()
    blurays = set()
    for root, folders, files in os.walk(args.src):
        for entry in folders:
            if entry == 'BDMV':
                blurays.add(root)
        for entry in files:
            _, ext = os.path.splitext(entry.lower())
            if ext == '.vob':
                dvds.add(root)

    eac3to_ids = {}
    for src_directory in sorted(blurays):
        platform.print_string(u'=== Processing "{}" ==='.format(src_directory))
        movie_id = ''
        while not movie_id.isdigit() and movie_id != 'no':
            movie_id = raw_input('Enter target movie id: ')
            if movie_id.isdigit():
                eac3to_ids[src_directory] = movie_id

    for src_directory, movie_id in sorted(eac3to_ids.iteritems()):
        def remux_callback(path):
            cwd = platform.getcwd()
            os.chdir(src_directory)
            platform.execute('eac3to {}) {}'.format(movie_id.rstrip(')'), cmd.quote(os.path.join(path, 'video.mkv'))), capture_output=False)
            os.chdir(cwd)
            return True

        dst_directory = os.path.join(args.dst, u'remux_{}'.format(os.path.basename(src_directory)))
        remux_movie(src_directory, dst_directory, remux_callback)

    for src_directory in dvds:
        makemkv_opts = [
            u'--noscan',
            u'--messages=-stderr',
            u'--progress=-stderr',
        ]
        makemkv_cmd = u'makemkvcon {opts} mkv file:{src} all {{}}'.format(
            opts=' '.join(makemkv_opts), src=cmd.quote(src_directory))

        def remux_callback(path):
            platform.execute(makemkv_cmd.format(cmd.quote(path)), capture_output=False)
            return True

        dst_name = os.path.basename(src_directory)
        if dst_name == 'VIDEO_TS':
            dst_name = os.path.basename(os.path.dirname(src_directory))
        dst_directory = os.path.join(args.dst, u'remux_{}'.format(dst_name))
        remux_movie(src_directory, dst_directory, remux_callback)

        parent_directory = os.path.dirname(src_directory)
        if os.listdir(parent_directory) == ['VIDEO_TS']:
            shutil.rmtree(parent_directory)

    return 0

if __name__ == '__main__':
    cli.run(main)
