from __future__ import print_function

import codecs
import os
import re
import subprocess
import sys

import rt.log
import rt.process

CRFS = {
    'animation': 18,
    'film': 22,
    'trash': 23,
}

TUNES = {
    'trash': 'film',
    'film': 'film',
    'animation': 'animation',
}

def jobs(root):
    for filename in list(os.listdir(root)):
        filepath = os.path.join(root, filename)
        if os.path.isfile(filepath) and filename.endswith('.job'):
            with codecs.open(filepath, 'r', 'utf-8') as fobj:
                for line in (l.strip() for l in fobj):
                    data = line.split()
                    dsttune = data[0]
                    srcscan = data[1]
                    srcpath = ' '.join(data[2:])
                    dstpath = os.path.join(os.path.dirname(srcpath), u'{}_enc_{}.mkv'.format(os.path.splitext(os.path.basename(srcpath))[0], dsttune))
                    yield (srcpath, srcscan, dstpath, dsttune)
            os.remove(filepath)

def vbr(srcpath):
    tmppath = u'{}.mp4'.format(os.path.splitext(srcpath)[0])
    rt.process.run(gl, u'ffmpeg -threads 0 -y -i "{src}" -an -sn -dn -c:v copy "{dst}"'.format(src=srcpath, dst=tmppath), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, _ = rt.process.run(gl, u'ffmpeg -i "{src}"'.format(src=tmppath), ignoreErrors=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    match = re.search(r'Stream #0:0.+?Video:.+?(\d+) kb/s', stdout)
    result = int(match.group(1))
    os.remove(tmppath)
    return result * 1000.0

def encode(srcpath, srcscan, srcbps, dstpath, dsttune):
    # gpu
    # 'ffmpeg -y -threads 4 -hwaccel cuvid -i "{src}" -an -sn -c:v h264_nvenc -preset slow -rc constqp -qp 20 -pix_fmt yuv420p -profile:v high -level:v 4.1 "{dst}"'

    # kbps = '{}K'.format(int(srcbps / 1000.0))
    options = [
        '-an',
        '-sn',
        '-dn',
        '-c:v libx264',
        '-preset veryslow',
        '-tune {}'.format(TUNES[dsttune]),
        '-profile:v high',
        '-level:v 4.1',
        '-crf {}'.format(CRFS[dsttune]),
        '-map_metadata -1',
        '-map_chapters -1',
        # '-maxrate {}'.format(kbps),
        # '-bufsize {}'.format(kbps),
    ]
    if srcscan == 'int':
        options.append('-vf yadif')
    rt.process.run(gl, u'ffmpeg -y -i "{src}" {options} "{dst}"'.format(src=srcpath, dst=dstpath, options=u' '.join(options)), shell=True)

def main(root):
    while True:
        for srcpath, srcscan, dstpath, dsttune in jobs(root):
            gl.info(u'START {}'.format(srcpath))

            # logEntry(LOG_CATEGORY_INFO, u'Discovering bitrate')
            # srcbps = vbr(srcpath)
            # logEntry(LOG_CATEGORY_INFO, u'{} kbps'.format(int(srcbps / 1000.0)))
            srcbps = 0

            gl.info(u'Encoding...')
            encode(srcpath, srcscan, srcbps, dstpath, dsttune)
            gl.info(u'READY {}'.format(srcpath))

if __name__ == '__main__':
    root = sys.argv[1]
    gl = rt.log.Logger(filepath=os.path.join(root, u'daemon.log'), stderr=True)
    main(root)
